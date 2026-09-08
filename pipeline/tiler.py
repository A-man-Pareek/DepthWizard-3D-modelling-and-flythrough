"""Tiling engine for high-resolution geospatial and aerial imagery inference.

Supports arbitrary image sizes (e.g., 256x256, 1024x1024, 4000x4000) via
overlapping sliding window inference with 2D Hann window blending, eliminating
boundary seams and edge artifacts while preserving the exact native raster resolution.
"""

from typing import Callable, Generator, List, Optional, Tuple, Union
import numpy as np
import torch
import torch.nn.functional as F


def create_2d_window(tile_size: int, blend_mode: str = "hann", device: Optional[torch.device] = None) -> torch.Tensor:
    """Create a 2D smooth weighting window for tile blending.

    Args:
        tile_size: Square tile dimension (default 256).
        blend_mode: Blending window function ('hann', 'bartlett', 'uniform').
        device: PyTorch device.

    Returns:
        2D torch.Tensor of shape (1, 1, tile_size, tile_size).
    """
    if blend_mode == "hann":
        # 1D Hann window: 0.5 * (1 - cos(2*pi*n / (N-1)))
        # To avoid zeros at boundaries, use a raised cosine with small baseline epsilon
        w_1d = torch.hann_window(tile_size, periodic=False, dtype=torch.float32)
        w_1d = torch.clamp(w_1d, min=1e-3)
        w_2d = torch.outer(w_1d, w_1d)
    elif blend_mode == "bartlett":
        w_1d = torch.bartlett_window(tile_size, periodic=False, dtype=torch.float32)
        w_1d = torch.clamp(w_1d, min=1e-3)
        w_2d = torch.outer(w_1d, w_1d)
    elif blend_mode == "uniform":
        w_2d = torch.ones((tile_size, tile_size), dtype=torch.float32)
    else:
        raise ValueError(f"Unsupported blend_mode: '{blend_mode}'. Choose 'hann', 'bartlett', or 'uniform'.")

    w_2d = w_2d.unsqueeze(0).unsqueeze(0)  # Shape: (1, 1, H, W)
    if device is not None:
        w_2d = w_2d.to(device)
    return w_2d


def compute_tile_slices(length: int, tile_size: int, stride: int) -> List[Tuple[int, int]]:
    """Compute 1D slice coordinates covering length with step size stride.

    Guarantees full coverage. If length does not align with stride, the final tile
    is positioned at (length - tile_size, length) to avoid out-of-bounds without extra padding.
    """
    if length <= tile_size:
        return [(0, length)]

    starts = list(range(0, length - tile_size + 1, stride))
    if starts[-1] + tile_size < length:
        starts.append(length - tile_size)
    return [(s, s + tile_size) for s in starts]


class ImageTiler:
    """Production tiler for sliding-window inference with seamless Hann blending."""

    def __init__(
        self,
        tile_size: int = 256,
        overlap: int = 64,
        blend_mode: str = "hann",
        batch_size: int = 4,
    ):
        """Initialize ImageTiler.

        Args:
            tile_size: Tile width and height (default 256 for HTC-DC Net and SegFormer).
            overlap: Overlap in pixels between adjacent tiles (default 64, stride 192).
            blend_mode: 'hann', 'bartlett', or 'uniform'.
            batch_size: Maximum batch size when feeding tiles to the model.
        """
        assert tile_size > 0, "tile_size must be positive"
        assert 0 <= overlap < tile_size, "overlap must be < tile_size"
        self.tile_size = tile_size
        self.overlap = overlap
        self.stride = tile_size - overlap
        self.blend_mode = blend_mode
        self.batch_size = batch_size

    def predict_tiled(
        self,
        image: torch.Tensor,
        predict_fn: Callable[[torch.Tensor], torch.Tensor],
        device: Optional[torch.device] = None,
    ) -> torch.Tensor:
        """Run seamless sliding-window inference over an arbitrary-sized input tensor.

        Args:
            image: Input tensor of shape (C, H, W) or (1, C, H, W). Values should already
                   be normalized according to model requirements.
            predict_fn: Callable taking a tile batch of shape (B, C, tile_size, tile_size)
                        and returning predicted output of shape (B, Out_C, tile_size, tile_size)
                        or (B, tile_size, tile_size).
            device: Computation device. If None, inferred from image or predict_fn.

        Returns:
            Reconstructed output tensor of exact shape (Out_C, H, W) or (1, Out_C, H, W).
        """
        squeeze_batch = False
        if image.ndim == 3:
            image = image.unsqueeze(0)
            squeeze_batch = True
        elif image.ndim != 4:
            raise ValueError(f"Expected 3D (C, H, W) or 4D (1, C, H, W) image tensor, got shape {image.shape}")

        _, c, orig_h, orig_w = image.shape
        dev = device if device is not None else image.device

        # Handle small images smaller than tile_size by reflection padding
        pad_top = 0
        pad_bottom = 0
        pad_left = 0
        pad_right = 0

        if orig_h < self.tile_size:
            diff_h = self.tile_size - orig_h
            pad_top = diff_h // 2
            pad_bottom = diff_h - pad_top

        if orig_w < self.tile_size:
            diff_w = self.tile_size - orig_w
            pad_left = diff_w // 2
            pad_right = diff_w - pad_left

        if pad_top > 0 or pad_bottom > 0 or pad_left > 0 or pad_right > 0:
            mode = "reflect" if (orig_h > 1 and orig_w > 1 and pad_top < orig_h and pad_left < orig_w) else "replicate"
            padded_image = F.pad(image, (pad_left, pad_right, pad_top, pad_bottom), mode=mode)
        else:
            padded_image = image

        _, _, cur_h, cur_w = padded_image.shape

        # Fast path: exactly one tile needed
        if cur_h == self.tile_size and cur_w == self.tile_size:
            with torch.no_grad():
                tile_in = padded_image.to(dev)
                pred_tile = predict_fn(tile_in)
                if pred_tile.ndim == 3:
                    pred_tile = pred_tile.unsqueeze(1)
            # Crop back to original dimensions
            cropped_pred = pred_tile[:, :, pad_top:pad_top + orig_h, pad_left:pad_left + orig_w]
            return cropped_pred.squeeze(0) if squeeze_batch else cropped_pred

        # Compute tile coordinates
        y_slices = compute_tile_slices(cur_h, self.tile_size, self.stride)
        x_slices = compute_tile_slices(cur_w, self.tile_size, self.stride)

        # Precompute 2D window
        window = create_2d_window(self.tile_size, blend_mode=self.blend_mode, device=dev)

        # Run first tile to determine output channel count
        first_tile = padded_image[:, :, y_slices[0][0]:y_slices[0][1], x_slices[0][0]:x_slices[0][1]].to(dev)
        with torch.no_grad():
            first_pred = predict_fn(first_tile)
            if first_pred.ndim == 3:
                first_pred = first_pred.unsqueeze(1)
        out_channels = first_pred.shape[1]

        # Allocate full resolution accumulation and weight buffers
        pred_accum = torch.zeros((1, out_channels, cur_h, cur_w), dtype=torch.float32, device=dev)
        weight_accum = torch.zeros((1, 1, cur_h, cur_w), dtype=torch.float32, device=dev)

        # Batch tiles for inference
        tile_coords = [(ys, ye, xs, xe) for ys, ye in y_slices for xs, xe in x_slices]
        batch_tiles = []
        batch_coords = []

        for ys, ye, xs, xe in tile_coords:
            tile = padded_image[:, :, ys:ye, xs:xe]
            batch_tiles.append(tile)
            batch_coords.append((ys, ye, xs, xe))

            if len(batch_tiles) == self.batch_size:
                self._process_tile_batch(batch_tiles, batch_coords, predict_fn, window, pred_accum, weight_accum, dev)
                batch_tiles = []
                batch_coords = []

        if batch_tiles:
            self._process_tile_batch(batch_tiles, batch_coords, predict_fn, window, pred_accum, weight_accum, dev)

        # Normalize accumulated predictions by accumulated weights
        weight_accum = torch.clamp(weight_accum, min=1e-8)
        output = pred_accum / weight_accum

        # Crop back to original dimensions
        output = output[:, :, pad_top:pad_top + orig_h, pad_left:pad_left + orig_w]

        return output.squeeze(0) if squeeze_batch else output

    def _process_tile_batch(
        self,
        batch_tiles: List[torch.Tensor],
        batch_coords: List[Tuple[int, int, int, int]],
        predict_fn: Callable[[torch.Tensor], torch.Tensor],
        window: torch.Tensor,
        pred_accum: torch.Tensor,
        weight_accum: torch.Tensor,
        device: torch.device,
    ) -> None:
        """Process a single batch of tiles and accumulate into full output canvas."""
        batch_tensor = torch.cat(batch_tiles, dim=0).to(device)
        with torch.no_grad():
            preds = predict_fn(batch_tensor)
            if preds.ndim == 3:
                preds = preds.unsqueeze(1)

        for i, (ys, ye, xs, xe) in enumerate(batch_coords):
            p = preds[i:i+1]
            pred_accum[:, :, ys:ye, xs:xe] += p * window
            weight_accum[:, :, ys:ye, xs:xe] += window

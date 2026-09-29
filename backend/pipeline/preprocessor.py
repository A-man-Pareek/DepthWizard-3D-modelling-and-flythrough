"""Step 2: Preprocessing for HTC-DC Net and downstream models.

Key production principles:
1. NEVER downsample full images to 256x256. Full spatial dimensions (H, W) are preserved.
2. Supports arbitrary satellite/aerial rasters (uint8, uint16, float32, multi-band).
3. Normalization conforms exactly to HTC-DC Net expectations (GBH dataset statistics / ImageNet).
4. Handles alpha channels, single-band grayscale, and nodata values.
"""

import os
from typing import Optional, Tuple, Union
import numpy as np
import torch


# Default statistics matching GBH dataset loader formula in dataloaders.py
# (online_get_image_stats operates on 0-255 RGB float arrays: ImageNet standard * 255)
DEFAULT_MEAN = [123.675, 116.280, 103.530]
DEFAULT_STD = [58.395, 57.120, 57.375]


class PreprocessedData:
    """Container for preprocessed image data preserving full spatial resolution."""

    def __init__(
        self,
        tensor: torch.Tensor,
        rgb_uint8: np.ndarray,
        original_shape: Tuple[int, int],
        nodata_mask: Optional[np.ndarray] = None,
    ):
        self.tensor = tensor  # Shape: (1, 3, H, W) normalized float32
        self.rgb_uint8 = rgb_uint8  # Shape: (H, W, 3) uint8 [0, 255]
        self.original_shape = original_shape  # (H, W)
        self.nodata_mask = nodata_mask  # Shape: (H, W) bool, True = valid


def preprocess_for_model(
    image_array: np.ndarray,
    stats_file: Optional[str] = None,
    device: Union[str, torch.device] = "cpu",
    nodata_mask: Optional[np.ndarray] = None,
) -> PreprocessedData:
    """Preprocess raw input array into full-resolution normalized tensor and RGB uint8.

    Args:
        image_array: Raw numpy array of shape (H, W, C), (H, W), or (C, H, W).
        stats_file: Optional path to image_stats.pickle.
        device: Device to place the tensor on.
        nodata_mask: Optional boolean mask (True = valid, False = nodata).

    Returns:
        PreprocessedData containing:
            - tensor: (1, 3, H, W) normalized tensor matching exact native resolution (H, W)
            - rgb_uint8: (H, W, 3) uint8 array for SegFormer and visualization
            - original_shape: (H, W)
            - nodata_mask: (H, W) boolean mask
    """
    # 1. Normalize layout to (H, W, C)
    arr = _ensure_hwc(image_array)
    orig_h, orig_w = arr.shape[:2]

    # 2. Extract 3-channel RGB uint8 representation preserving full resolution
    rgb_uint8 = _to_rgb_uint8(arr, nodata_mask)

    # 3. Apply normalization for HTC-DC Net
    # HTC-DC Net dataloader loads uint8/float in 0..255 and normalizes by mean and std
    img_float = rgb_uint8.astype(np.float32)
    mean, std = _load_dataset_stats(stats_file)

    # Transpose to (3, H, W)
    chw = np.transpose(img_float, (2, 0, 1))

    mean_arr = np.array(mean, dtype=np.float32)[:, None, None]
    std_arr = np.array(std, dtype=np.float32)[:, None, None]
    normalized = (chw - mean_arr) / std_arr

    # Build tensor of shape (1, 3, H, W)
    tensor = torch.from_numpy(normalized).unsqueeze(0).to(device=device, dtype=torch.float32)

    return PreprocessedData(
        tensor=tensor,
        rgb_uint8=rgb_uint8,
        original_shape=(orig_h, orig_w),
        nodata_mask=nodata_mask,
    )


def _ensure_hwc(arr: np.ndarray) -> np.ndarray:
    """Ensure array has (H, W, C) layout."""
    if arr.ndim == 2:
        return arr[:, :, None]
    elif arr.ndim == 3:
        # If channels are first (e.g., 3, H, W or 4, H, W) and C < min(H, W)
        if arr.shape[0] in (1, 3, 4) and arr.shape[0] < arr.shape[1] and arr.shape[0] < arr.shape[2]:
            return np.transpose(arr, (1, 2, 0))
        return arr
    else:
        raise ValueError(f"Unsupported image array shape: {arr.shape}")


def _to_rgb_uint8(arr: np.ndarray, nodata_mask: Optional[np.ndarray] = None) -> np.ndarray:
    """Convert input array of arbitrary channels and dtypes to (H, W, 3) uint8."""
    h, w = arr.shape[:2]
    c = arr.shape[2]

    if c == 1:
        bands = [arr[:, :, 0], arr[:, :, 0], arr[:, :, 0]]
    elif c == 3:
        bands = [arr[:, :, 0], arr[:, :, 1], arr[:, :, 2]]
    elif c >= 4:
        # If RGBA or multi-band, take first 3 bands
        bands = [arr[:, :, 0], arr[:, :, 1], arr[:, :, 2]]
    else:
        raise ValueError(f"Unexpected number of channels: {c}")

    rgb_stack = np.stack(bands, axis=-1)

    # Convert to float for scaling
    rgb_float = rgb_stack.astype(np.float32)

    # If already uint8 in 0..255
    if arr.dtype == np.uint8:
        return rgb_stack.astype(np.uint8)

    # If uint16 or float satellite raster (e.g., Sentinel-2 with values up to 10000)
    # Apply robust percentile-based stretch
    valid_pixels = rgb_float
    if nodata_mask is not None:
        valid_pixels = rgb_float[nodata_mask]

    if valid_pixels.size > 0 and (np.nanmax(valid_pixels) > 255.0 or np.nanmax(valid_pixels) <= 1.0):
        p2 = np.nanpercentile(valid_pixels, 2)
        p98 = np.nanpercentile(valid_pixels, 98)
        if p98 > p2:
            rgb_float = np.clip((rgb_float - p2) / (p98 - p2) * 255.0, 0, 255)
        else:
            rgb_float = np.clip(rgb_float, 0, 255)
    else:
        rgb_float = np.clip(rgb_float, 0, 255)

    return rgb_float.astype(np.uint8)


def _load_dataset_stats(stats_file: Optional[str] = None) -> Tuple[list, list]:
    """Load exact mean and std from image_stats.pickle if exists, else defaults."""
    if stats_file and os.path.exists(stats_file):
        try:
            mean, std = torch.load(stats_file, map_location="cpu")
            return list(mean), list(std)
        except Exception:
            pass

    # Project root discovery
    curr_dir = os.path.dirname(os.path.abspath(__file__))
    root_dir = os.path.dirname(curr_dir)
    common_stats_paths = [
        os.path.join(root_dir, "data", "gbh", "image_stats.pickle"),
        os.path.join(root_dir, "HTC-DC-Net", "data", "gbh", "image_stats.pickle"),
        os.path.join(root_dir, "HTC-DC-Net", "image_stats.pickle"),
    ]
    for p in common_stats_paths:
        if os.path.exists(p):
            try:
                mean, std = torch.load(p, map_location="cpu")
                return list(mean), list(std)
            except Exception:
                continue

    return DEFAULT_MEAN, DEFAULT_STD

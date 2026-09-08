"""High-resolution sliding-window inference for SegFormer semantic segmentation."""

from typing import Any, Dict, Optional, Tuple, Union
import numpy as np
import torch

from pipeline.tiler import ImageTiler
from segmentation.model import SegFormerModelWrapper
from segmentation.preprocessing import preprocess_for_segformer
from segmentation.postprocessing import postprocess_segmentation_logits


class SegFormerInferenceRunner:
    """Production inference runner for high-resolution semantic segmentation."""

    def __init__(
        self,
        model_name_or_path: Optional[str] = None,
        device: Optional[str] = None,
        tile_size: int = 512,
        overlap: int = 128,
        batch_size: int = 2,
    ):
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.wrapper = SegFormerModelWrapper(
            model_name_or_path=model_name_or_path or "nvidia/segformer-b0-finetuned-ade-512-512",
            device=self.device,
        )
        self.tile_size = tile_size
        self.tiler = ImageTiler(tile_size=tile_size, overlap=overlap, blend_mode="hann", batch_size=batch_size)

    def segment(
        self,
        rgb_image: np.ndarray,
        nodata_mask: Optional[np.ndarray] = None,
    ) -> Dict[str, Any]:
        """Perform semantic segmentation on an arbitrary-resolution RGB image.

        Args:
            rgb_image: (H, W, 3) uint8 RGB image array.
            nodata_mask: Optional boolean mask (True = valid pixel, False = nodata).

        Returns:
            Dictionary containing:
                - class_map: (H, W) uint8 class map matching input resolution
                - confidence_map: (H, W) float32 probabilities
                - class_distribution: class breakdown list
                - id2label: label dictionary
        """
        orig_h, orig_w = rgb_image.shape[:2]

        # 1. Preprocess to normalized tensor
        tensor = preprocess_for_segformer(rgb_image, device=self.device)

        # 2. Sliding window inference using ImageTiler
        def predict_fn(tile_batch: torch.Tensor) -> torch.Tensor:
            return self.wrapper.forward_logits(tile_batch)

        reconstructed_logits = self.tiler.predict_tiled(
            tensor,
            predict_fn=predict_fn,
            device=torch.device(self.device),
        )

        # 3. Postprocess into class map and distribution
        results = postprocess_segmentation_logits(
            logits=reconstructed_logits,
            id2label=self.wrapper.id2label,
            nodata_mask=nodata_mask,
        )
        results["id2label"] = self.wrapper.id2label
        results["resolution"] = [orig_w, orig_h]

        return results

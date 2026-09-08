"""Preprocessing module for SegFormer semantic segmentation."""

from typing import Tuple, Union
import numpy as np
import torch

IMAGENET_MEAN = np.array([0.485, 0.456, 0.406], dtype=np.float32).reshape(3, 1, 1)
IMAGENET_STD = np.array([0.229, 0.224, 0.225], dtype=np.float32).reshape(3, 1, 1)


def preprocess_for_segformer(
    rgb_image: np.ndarray,
    device: Union[str, torch.device] = "cpu",
) -> torch.Tensor:
    """Prepare RGB uint8 image array for SegFormer sliding-window inference.

    Args:
        rgb_image: (H, W, 3) uint8 array in [0, 255].
        device: Target computation device.

    Returns:
        torch.Tensor of shape (1, 3, H, W) with standard ImageNet normalization.
    """
    assert rgb_image.ndim == 3 and rgb_image.shape[2] == 3, f"Expected (H, W, 3) RGB image, got {rgb_image.shape}"

    # Transpose to (3, H, W) and scale to [0, 1]
    chw = np.transpose(rgb_image, (2, 0, 1)).astype(np.float32) / 255.0
    normalized = (chw - IMAGENET_MEAN) / IMAGENET_STD

    tensor = torch.from_numpy(normalized).unsqueeze(0).to(device=device, dtype=torch.float32)
    return tensor

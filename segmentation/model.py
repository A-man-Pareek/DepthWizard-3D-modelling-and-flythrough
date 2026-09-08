"""SegFormer model wrapper for semantic segmentation."""

import os
from typing import Any, Dict, Optional
import torch
from transformers import SegformerForSemanticSegmentation, SegformerImageProcessor

DEFAULT_SEGFORMER_MODEL = "nvidia/segformer-b0-finetuned-ade-512-512"


class SegFormerModelWrapper:
    """Wrapper managing SegFormer model loading, evaluation mode, and label mapping."""

    def __init__(
        self,
        model_name_or_path: str = DEFAULT_SEGFORMER_MODEL,
        device: Optional[str] = None,
    ):
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.model_name_or_path = model_name_or_path

        print(f"[SegFormer] Loading model '{self.model_name_or_path}' on device: {self.device}...")
        self.processor = SegformerImageProcessor.from_pretrained(self.model_name_or_path)
        self.model = SegformerForSemanticSegmentation.from_pretrained(self.model_name_or_path)
        self.model.to(self.device)
        self.model.eval()

        self.id2label: Dict[int, str] = {int(k): str(v) for k, v in self.model.config.id2label.items()}
        self.num_classes: int = len(self.id2label)
        print(f"[SegFormer] Loaded {self.num_classes} semantic classes.")

    def forward_logits(self, pixel_values: torch.Tensor) -> torch.Tensor:
        """Run forward pass returning logits of shape (B, num_classes, H, W)."""
        pixel_values = pixel_values.to(self.device)
        with torch.no_grad():
            outputs = self.model(pixel_values=pixel_values)
            logits = outputs.logits
            # Interpolate logits back to input patch size if downsampled
            if logits.shape[-2:] != pixel_values.shape[-2:]:
                logits = torch.nn.functional.interpolate(
                    logits,
                    size=pixel_values.shape[-2:],
                    mode="bilinear",
                    align_corners=False,
                )
        return logits

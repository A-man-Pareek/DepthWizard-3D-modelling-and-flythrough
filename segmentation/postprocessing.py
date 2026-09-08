"""Post-processing module for SegFormer semantic segmentation."""

from typing import Any, Dict, List, Optional
import numpy as np
import torch
import torch.nn.functional as F


def postprocess_segmentation_logits(
    logits: torch.Tensor,
    id2label: Dict[int, str],
    nodata_mask: Optional[np.ndarray] = None,
) -> Dict[str, Any]:
    """Convert reconstructed logits tensor to class map, confidence, and class distribution.

    Args:
        logits: Tensor of shape (num_classes, H, W) or (1, num_classes, H, W).
        id2label: Mapping from class integer IDs to class name strings.
        nodata_mask: Optional boolean mask (True = valid, False = nodata).

    Returns:
        Dictionary containing:
            - class_map: 2D uint8 numpy array of shape (H, W) with class IDs
            - confidence_map: 2D float32 numpy array of shape (H, W) with probabilities
            - class_distribution: List of dicts with detected class counts and percentages
    """
    if logits.ndim == 4:
        logits = logits.squeeze(0)

    # Compute softmax probabilities
    probs = F.softmax(logits, dim=0)

    # Argmax class map and maximum confidence
    conf, class_indices = torch.max(probs, dim=0)

    class_map = class_indices.cpu().numpy().astype(np.uint8)
    confidence_map = conf.cpu().numpy().astype(np.float32)

    # Apply nodata mask if present
    if nodata_mask is not None:
        class_map[~nodata_mask] = 0
        confidence_map[~nodata_mask] = 0.0

    # Compute class distribution statistics
    unique_ids, counts = np.unique(class_map, return_counts=True)
    total_pixels = class_map.size

    class_distribution = []
    for cid, cnt in zip(unique_ids, counts):
        cid_int = int(cid)
        class_distribution.append({
            "class_id": cid_int,
            "class_name": id2label.get(cid_int, f"class_{cid_int}"),
            "pixel_count": int(cnt),
            "percentage": float(round((cnt / total_pixels) * 100.0, 2)),
        })

    # Sort distribution by pixel count descending
    class_distribution.sort(key=lambda x: x["pixel_count"], reverse=True)

    return {
        "class_map": class_map,
        "confidence_map": confidence_map,
        "class_distribution": class_distribution,
    }

"""Step 3: HTC-DC Net Model Runner.

Provides production inference for high-resolution aerial and satellite imagery:
1. Strict checkpoint verification and loading (no uninitialized weights in production).
2. Authoritative configuration matching the HTC-DC Net architecture.
3. Native resolution preservation via ImageTiler sliding-window Hann-weighted inference.
4. Robust output sanitization (non-negative, NaN/Inf cleanup).
"""

import os
import sys
from typing import Any, Dict, Optional, Union
import numpy as np
import torch

# Ensure project root and HTC-DC-Net repository are on sys.path deterministically
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
HTCDC_DIR = os.path.join(PROJECT_ROOT, "HTC-DC-Net")

if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
if HTCDC_DIR not in sys.path:
    sys.path.insert(0, HTCDC_DIR)

from htcdc import UBins
from pipeline.tiler import ImageTiler


class HTCDCInferenceRunner:
    """Production wrapper for height estimation inference with HTC-DC Net."""

    def __init__(
        self,
        checkpoint_path: Optional[str] = None,
        cfgs: Optional[Dict[str, Any]] = None,
        device: Optional[str] = None,
        require_checkpoint: bool = True,
    ):
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.require_checkpoint = require_checkpoint

        # Authoritative architectural configuration
        self.cfgs: Dict[str, Any] = {
            "model": "htcdc",
            "backbone": "efficientnetb0",
            "patch_size": 4,
            "fusion_mode": "last",
            "head_tail_cut": False,
            "earlier": False,
            "prob_loss": False,
            "pretrained": True,
            "num_classes": 256,
            "h_max": 33.0,
            "device": self.device,
        }
        if cfgs:
            self.cfgs.update(cfgs)

        print(f"[HTC-DC Net] Initializing model architecture on device: {self.device}...")
        self.model = UBins(self.cfgs)
        self.model.to(self.device)
        self.model.eval()

        self.checkpoint_loaded = False
        self.loaded_checkpoint_path: Optional[str] = None

        # Resolve and load checkpoint
        if checkpoint_path is not None:
            resolved_ckpt = self._resolve_checkpoint_path(checkpoint_path)
            if resolved_ckpt:
                self.load_checkpoint(resolved_ckpt)
            else:
                raise FileNotFoundError(
                    f"[HTC-DC Net] Explicitly specified checkpoint path does not exist: '{checkpoint_path}'"
                )
        else:
            resolved_ckpt = self._resolve_default_candidates()
            if resolved_ckpt:
                self.load_checkpoint(resolved_ckpt)
            elif self.require_checkpoint:
                raise FileNotFoundError(
                    "[HTC-DC Net] Required model checkpoint not found in default candidates."
                )
            else:
                print("[HTC-DC Net] Warning: Operating without trained checkpoint weights.")

        # Default tiler instance for arbitrary dimension images
        self.default_tiler = ImageTiler(tile_size=256, overlap=64, blend_mode="hann", batch_size=4)

    def _resolve_checkpoint_path(self, path: str) -> Optional[str]:
        """Resolve explicitly provided checkpoint path."""
        if os.path.isabs(path) and os.path.isfile(path):
            return path
        rel_to_root = os.path.join(PROJECT_ROOT, path)
        if os.path.isfile(rel_to_root):
            return rel_to_root
        if os.path.isfile(path):
            return os.path.abspath(path)
        return None

    def _resolve_default_candidates(self) -> Optional[str]:
        """Search default candidate paths when no path is explicitly provided."""
        env_ckpt = os.environ.get("HTCDC_CHECKPOINT")
        if env_ckpt and os.path.isfile(env_ckpt):
            return os.path.abspath(env_ckpt)

        candidates = [
            os.path.join(PROJECT_ROOT, "checkpoints", "checkpoint_best_rmse.pth.tar"),
            os.path.join(PROJECT_ROOT, "HTC-DC-Net", "checkpoints", "checkpoint_best_rmse.pth.tar"),
            os.path.join(PROJECT_ROOT, "checkpoint_best_rmse.pth.tar"),
            os.path.join(PROJECT_ROOT, "checkpoints", "checkpoint_last.pth.tar"),
        ]
        for c in candidates:
            if os.path.isfile(c):
                return c

        return None

    def load_checkpoint(self, checkpoint_path: str, strict: bool = True) -> None:
        """Strictly load weights into the HTC-DC Net architecture."""
        if not os.path.isfile(checkpoint_path):
            raise FileNotFoundError(f"[HTC-DC Net] Checkpoint file does not exist: {checkpoint_path}")

        print(f"[HTC-DC Net] Loading weights from: {checkpoint_path}")
        chkpt = torch.load(checkpoint_path, map_location=self.device)
        state_dict = chkpt.get("state_dict", chkpt)

        # Clean 'module.' prefix if saved from DataParallel / DistributedDataParallel
        clean_state_dict = {}
        for k, v in state_dict.items():
            new_key = k[7:] if k.startswith("module.") else k
            clean_state_dict[new_key] = v

        self.model.load_state_dict(clean_state_dict, strict=strict)
        self.checkpoint_loaded = True
        self.loaded_checkpoint_path = checkpoint_path
        self.model.eval()
        print(f"[HTC-DC Net] Checkpoint successfully verified and loaded (strict={strict}).")

    def run_inference(
        self,
        tensor: torch.Tensor,
        tiler: Optional[ImageTiler] = None,
    ) -> np.ndarray:
        """Run height estimation inference preserving exact native spatial dimensions.

        Args:
            tensor: Input tensor of shape (1, 3, H, W) or (3, H, W) normalized float32.
            tiler: Optional ImageTiler instance (defaults to self.default_tiler).

        Returns:
            2D numpy array of shape (H, W) containing non-negative relative height values.
        """
        if tensor.ndim == 3:
            tensor = tensor.unsqueeze(0)
        elif tensor.ndim != 4:
            raise ValueError(f"Expected 3D or 4D tensor, got shape {tensor.shape}")

        _, _, h, w = tensor.shape
        active_tiler = tiler or self.default_tiler

        def model_predict_fn(tile_batch: torch.Tensor) -> torch.Tensor:
            tile_batch = tile_batch.to(self.device)
            with torch.no_grad():
                out = self.model.predict(tile_batch)
            return out

        if h == 256 and w == 256:
            # Single tile fast path
            with torch.no_grad():
                pred_tensor = model_predict_fn(tensor)
        else:
            # High-resolution seamless sliding-window inference with Hann blending
            pred_tensor = active_tiler.predict_tiled(
                tensor,
                predict_fn=model_predict_fn,
                device=torch.device(self.device),
            )

        # Squeeze to 2D (H, W) numpy float32
        rel_height = pred_tensor.squeeze().cpu().numpy().astype(np.float32)

        # Sanitize NaNs, Infs, and enforce non-negativity for relative nDSM
        rel_height = np.nan_to_num(rel_height, nan=0.0, posinf=0.0, neginf=0.0)
        rel_height = np.maximum(rel_height, 0.0)

        return rel_height

    @property
    def is_loaded(self) -> bool:
        return self.checkpoint_loaded

    @property
    def status(self) -> Dict[str, Any]:
        return {
            "model_loaded": True,
            "checkpoint_loaded": self.checkpoint_loaded,
            "checkpoint_path": self.loaded_checkpoint_path,
            "device": self.device,
            "config": self.cfgs,
        }

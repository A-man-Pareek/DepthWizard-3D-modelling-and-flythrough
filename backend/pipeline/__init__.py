"""DepthWizard pipeline package."""
import os
import sys

_htcdc_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "HTC-DC-Net"))
if _htcdc_dir not in sys.path:
    sys.path.insert(0, _htcdc_dir)

from .pipeline import HeightEstimationPipeline, PipelineResult

__all__ = ["HeightEstimationPipeline", "PipelineResult"]

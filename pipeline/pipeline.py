"""Unified Height Estimation and Geospatial Pipeline.

Orchestrates Steps 1 through 5:
1. Image Inspection: Preserves native (W, H), CRS, transform, bounds, and nodata.
2. Preprocessing: Conforms to HTC-DC Net expectations without downsampling.
3. HTC-DC Net Inference: Sliding-window Hann-weighted inference over arbitrary dimensions.
4. Calibration & DSM: Real DEM lookup, RANSAC outlier rejection, metric nDSM, and DSM.
5. Export: GeoTIFFs matching exact input grid, clean JSON metadata, download URLs.
+ SegFormer Segmentation: Optional semantic segmentation preserving native spatial grid.
"""

import os
from typing import Any, Dict, List, Optional, Tuple, Union
import numpy as np

from .inspector import inspect_image, ImageInspectionResult
from .preprocessor import preprocess_for_model, PreprocessedData
from .model_runner import HTCDCInferenceRunner
from .calibration import calibrate_height, CalibrationResult
from .exporter import export_pipeline_products, assemble_and_export, ExportResult, DEFAULT_NODATA


class PipelineResult:
    """Encapsulates full pipeline execution artifacts and metadata."""

    def __init__(
        self,
        inspection: ImageInspectionResult,
        preprocessed: PreprocessedData,
        relative_ndsm: np.ndarray,
        calibration: CalibrationResult,
        exported_products: Dict[str, Any],
        segmentation: Optional[Dict[str, Any]] = None,
    ):
        self.inspection = inspection
        self.preprocessed = preprocessed
        self.relative_ndsm = relative_ndsm
        self.calibration = calibration
        self.exported_products = exported_products
        self.segmentation = segmentation

    @property
    def primary_product(self) -> Dict[str, Any]:
        """Return the highest fidelity height product exported."""
        for key in ("dsm", "metric_ndsm", "relative_ndsm"):
            if key in self.exported_products:
                return self.exported_products[key]
        return next(iter(self.exported_products.values()), {})

    @property
    def metadata(self) -> Dict[str, Any]:
        """Clean summary metadata dictionary for API responses."""
        prim = self.primary_product
        h, w = self.inspection.original_shape
        res: Dict[str, Any] = {
            "mode": self.calibration.mode,
            "units": self.calibration.units,
            "confidence": self.calibration.confidence,
            "resolution": [w, h],
            "is_georeferenced": self.inspection.is_georeferenced,
            "crs": str(self.inspection.crs) if self.inspection.crs else None,
            "bounds": list(self.inspection.bounds) if self.inspection.bounds else None,
            "scale_factor": float(self.calibration.scale_factor),
            "offset": float(self.calibration.offset),
            "calibration_metrics": self.calibration.metrics,
            "products": self.exported_products,
        }
        if self.segmentation:
            res["segmentation"] = {
                "class_distribution": self.segmentation.get("class_distribution", []),
                "detected_class_count": len(self.segmentation.get("class_distribution", [])),
            }
        return res

    @property
    def raster_path(self) -> str:
        return self.primary_product.get("file_path", "")

    @property
    def filename(self) -> str:
        return self.primary_product.get("filename", "")

    @property
    def is_geotiff(self) -> bool:
        return self.primary_product.get("is_geotiff", False)

    def to_dict(self) -> Dict[str, Any]:
        return self.metadata


class HeightEstimationPipeline:
    """Production height estimation pipeline orchestrating HTC-DC Net and DEM calibration."""

    def __init__(
        self,
        checkpoint_path: Optional[str] = None,
        dem_dir: str = "data/srtm",
        device: Optional[str] = None,
        require_checkpoint: bool = True,
    ):
        self.dem_dir = dem_dir
        self.device = device
        self.runner = HTCDCInferenceRunner(
            checkpoint_path=checkpoint_path,
            device=device,
            require_checkpoint=require_checkpoint,
        )
        self._segformer = None

    @property
    def segformer(self):
        """Lazy-loaded SegFormer inference runner."""
        if self._segformer is None:
            from segmentation import SegFormerInferenceRunner
            self._segformer = SegFormerInferenceRunner(device=self.runner.device)
        return self._segformer

    def process(
        self,
        input_source: Any,
        run_segmentation: bool = False,
        dem_dir: Optional[str] = None,
        dem_files: Optional[List[str]] = None,
        reference_ndsm: Optional[np.ndarray] = None,
        output_dir: str = "outputs",
        base_name: Optional[str] = None,
    ) -> PipelineResult:
        """Execute the complete production pipeline on an arbitrary raster or image."""
        os.makedirs(output_dir, exist_ok=True)
        active_dem_dir = dem_dir or self.dem_dir

        # STEP 1: Load and inspect (never loses native resolution, CRS, transform, or nodata)
        insp = inspect_image(input_source)

        # STEP 2: Preprocess for HTC-DC Net (preserves exact spatial resolution)
        preproc = preprocess_for_model(
            image_array=insp.image_array,
            device=self.runner.device,
            nodata_mask=insp.nodata_mask,
        )

        # STEP 3: Run HTC-DC Net inference via high-resolution sliding-window blending
        relative_ndsm = self.runner.run_inference(preproc.tensor)

        # STEP 4: Calibrate heights, query real DEM, generate metric nDSM and DSM
        calib = calibrate_height(
            relative_ndsm=relative_ndsm,
            is_georeferenced=insp.is_georeferenced,
            crs=insp.crs,
            transform=insp.transform,
            bounds=insp.bounds,
            nodata_mask=insp.nodata_mask,
            rgb_image=preproc.rgb_uint8,
            dem_dir=active_dem_dir,
            dem_files=dem_files,
            reference_ndsm=reference_ndsm,
        )

        # Optional: Run SegFormer Semantic Segmentation on full resolution
        seg_res: Optional[Dict[str, Any]] = None
        if run_segmentation:
            try:
                print("[Pipeline] Running SegFormer semantic segmentation...")
                seg_res = self.segformer.segment(
                    rgb_image=preproc.rgb_uint8,
                    nodata_mask=insp.nodata_mask,
                )
            except Exception as e:
                print(f"[Pipeline] Warning: Segmentation failed: {e}")

        # STEP 5: Export distinct geospatial products (GeoTIFFs with exact CRS and transform)
        products_to_export: Dict[str, Optional[np.ndarray]] = {
            "relative_ndsm": calib.relative_ndsm,
            "metric_ndsm": calib.metric_ndsm,
            "dem": calib.dem,
            "dsm": calib.dsm,
        }
        if seg_res is not None and "class_map" in seg_res:
            products_to_export["segmentation"] = seg_res["class_map"]

        exported_products = export_pipeline_products(
            products=products_to_export,
            output_dir=output_dir,
            base_name=base_name or insp.driver or "raster",
            crs=insp.crs if insp.is_georeferenced else None,
            transform=insp.transform if insp.is_georeferenced else None,
            nodata=DEFAULT_NODATA,
        )

        return PipelineResult(
            inspection=insp,
            preprocessed=preproc,
            relative_ndsm=relative_ndsm,
            calibration=calib,
            exported_products=exported_products,
            segmentation=seg_res,
        )

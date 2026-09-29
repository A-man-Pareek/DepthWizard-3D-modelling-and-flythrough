
"""Step 5: Assemble and export results.

Production-grade geospatial raster export:
1. NEVER dumps multi-megabyte 2D raster grids into JSON responses.
2. Returns clean JSON metadata, summary statistics, and download paths/URLs.
3. Exports GeoTIFFs preserving exact input spatial dimensions (H, W), original CRS,
   affine transform, and nodata values (-9999.0).
4. Exports distinct, strictly separated products:
     - relative_ndsm
     - metric_ndsm
     - dem
     - dsm
     - segmentation
"""

import json
import os
import uuid
from typing import Any, Dict, List, Optional, Tuple, Union
import numpy as np
import rasterio
from rasterio.crs import CRS
from rasterio.transform import Affine

DEFAULT_NODATA = -9999.0


class ProductExportInfo:
    """Metadata for an individual exported raster product."""

    def __init__(
        self,
        product_type: str,
        filename: str,
        file_path: str,
        is_geotiff: bool,
        shape: Tuple[int, int],
        crs: Optional[str] = None,
        nodata: Optional[float] = None,
        stats: Optional[Dict[str, float]] = None,
    ):
        self.product_type = product_type
        self.filename = filename
        self.file_path = file_path
        self.is_geotiff = is_geotiff
        self.shape = shape
        self.crs = crs
        self.nodata = nodata
        self.stats = stats or {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "product_type": self.product_type,
            "filename": self.filename,
            "file_path": self.file_path,
            "download_url": f"/download/{self.filename}",
            "is_geotiff": self.is_geotiff,
            "shape": list(self.shape),
            "crs": self.crs,
            "nodata": self.nodata,
            "statistics": self.stats,
        }


def compute_raster_statistics(arr: np.ndarray, nodata: float = DEFAULT_NODATA) -> Dict[str, float]:
    """Compute summary statistics excluding nodata and NaNs."""
    valid_mask = (arr != nodata) & (~np.isnan(arr))
    valid_pixels = arr[valid_mask]

    if valid_pixels.size == 0:
        return {
            "min": 0.0,
            "max": 0.0,
            "mean": 0.0,
            "std": 0.0,
            "valid_ratio": 0.0,
        }

    return {
        "min": float(np.min(valid_pixels)),
        "max": float(np.max(valid_pixels)),
        "mean": float(np.mean(valid_pixels)),
        "std": float(np.std(valid_pixels)),
        "valid_ratio": float(valid_pixels.size / arr.size),
    }


def normalize_metadata_fields(
    primary_arr: np.ndarray,
    mode: Optional[str] = None,
    units: Optional[str] = None,
    confidence: Optional[str] = None,
    is_georeferenced: bool = False,
) -> Dict[str, Any]:
    """Normalize metadata into the exact required 5-key contract."""
    h, w = primary_arr.shape[:2]

    # Mode: "absolute-geo" | "absolute-semantic" | "relative"
    norm_mode = mode or ("absolute-geo" if is_georeferenced else "relative")
    if norm_mode not in ("absolute-geo", "absolute-semantic", "relative"):
        if "geo" in norm_mode:
            norm_mode = "absolute-geo"
        elif "sem" in norm_mode or "ref" in norm_mode:
            norm_mode = "absolute-semantic"
        else:
            norm_mode = "relative"

    # Units: "meters" | "relative_units"
    if units in ("meters", "relative_units"):
        norm_units = units
    else:
        norm_units = "meters" if norm_mode in ("absolute-geo", "absolute-semantic") else "relative_units"

    # Confidence: "high" | "medium" | "n/a"
    conf_str = str(confidence).lower() if confidence else ""
    if conf_str == "high":
        norm_conf = "high"
    elif conf_str == "medium":
        norm_conf = "medium"
    else:
        norm_conf = "n/a"

    clean_grid = np.nan_to_num(primary_arr, nan=0.0, posinf=0.0, neginf=0.0).astype(float).tolist()

    return {
        "mode": norm_mode,
        "units": norm_units,
        "confidence": norm_conf,
        "resolution": [int(w), int(h)],
        "height_grid": clean_grid,
    }


def export_single_raster(
    data: np.ndarray,
    output_path: str,
    crs: Optional[CRS] = None,
    transform: Optional[Affine] = None,
    nodata: float = DEFAULT_NODATA,
    description: Optional[str] = None,
    dtype: Optional[np.dtype] = None,
) -> bool:
    """Write 2D numpy array to TIFF or GeoTIFF."""
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    h, w = data.shape[:2]

    target_dtype = dtype or (rasterio.uint8 if data.dtype == np.uint8 else rasterio.float32)
    is_geotiff = (crs is not None) and (transform is not None)

    write_kwargs: Dict[str, Any] = {
        "driver": "GTiff",
        "height": h,
        "width": w,
        "count": 1,
        "dtype": target_dtype,
    }

    if is_geotiff:
        write_kwargs["crs"] = crs
        write_kwargs["transform"] = transform
        write_kwargs["nodata"] = nodata
    elif target_dtype == rasterio.float32:
        write_kwargs["nodata"] = nodata

    with rasterio.open(output_path, "w", **write_kwargs) as dst:
        dst.write(data.astype(target_dtype), 1)
        if description:
            dst.set_band_description(1, description)

    return is_geotiff


def export_pipeline_products(
    products: Dict[str, Optional[np.ndarray]],
    output_dir: str = "outputs",
    base_name: Optional[str] = None,
    crs: Optional[CRS] = None,
    transform: Optional[Affine] = None,
    nodata: float = DEFAULT_NODATA,
    mode: Optional[str] = None,
    units: Optional[str] = None,
    confidence: Optional[str] = None,
    generate_metadata_json: bool = True,
) -> Dict[str, Any]:
    """Export all available pipeline products and compile response metadata."""
    os.makedirs(output_dir, exist_ok=True)
    prefix = (base_name or "output").replace(" ", "_")

    exported_products: Dict[str, Any] = {}
    crs_str = crs.to_string() if (crs and hasattr(crs, "to_string")) else (str(crs) if crs else None)
    is_georeferenced = (crs is not None) and (transform is not None)

    product_configs = {
        "relative_ndsm": ("relative_ndsm.tif", "HTC-DC Net Relative Above-Ground Height", rasterio.float32),
        "metric_ndsm": ("metric_ndsm.tif", "Calibrated Above-Ground Height (meters)", rasterio.float32),
        "dem": ("dem.tif", "Bare-Earth Digital Elevation Model (meters)", rasterio.float32),
        "dsm": ("dsm.tif", "Digital Surface Model DEM + nDSM (meters)", rasterio.float32),
        "pred_height": ("pred_height.tif", "Predicted Height Single-Band Float32", rasterio.float32),
        "segmentation": ("segmentation.tif", "Semantic Segmentation Class Map", rasterio.uint8),
    }

    for prod_key, (suffix, desc, dt) in product_configs.items():
        arr = products.get(prod_key)
        if arr is None:
            continue

        filename = f"{prefix}_{suffix}"
        file_path = os.path.abspath(os.path.join(output_dir, filename))

        is_geo = export_single_raster(
            data=arr,
            output_path=file_path,
            crs=crs,
            transform=transform,
            nodata=nodata if dt == rasterio.float32 else 0,
            description=desc,
            dtype=dt,
        )

        stats = compute_raster_statistics(arr, nodata=nodata if dt == rasterio.float32 else -1)

        info = ProductExportInfo(
            product_type=prod_key,
            filename=filename,
            file_path=file_path,
            is_geotiff=is_geo,
            shape=arr.shape,
            crs=crs_str,
            nodata=nodata if dt == rasterio.float32 else None,
            stats=stats,
        )
        exported_products[prod_key] = info.to_dict()

    # Identify primary height product array
    primary_arr: Optional[np.ndarray] = None
    for k in ("dsm", "pred_height", "metric_ndsm", "relative_ndsm"):
        if products.get(k) is not None:
            primary_arr = products[k]
            break

    # Always ensure primary Height/DSM rasters (<base_name>_dsm.tif and <base_name>_pred_height.tif) are written to disk
    if primary_arr is not None:
        dsm_filename = f"{prefix}_dsm.tif"
        dsm_path = os.path.abspath(os.path.join(output_dir, dsm_filename))
        if not os.path.isfile(dsm_path):
            export_single_raster(
                data=primary_arr,
                output_path=dsm_path,
                crs=crs if is_georeferenced else None,
                transform=transform if is_georeferenced else None,
                nodata=nodata,
                description="Digital Surface Model / Primary Height Product",
                dtype=rasterio.float32,
            )

        pred_filename = f"{prefix}_pred_height.tif"
        pred_path = os.path.abspath(os.path.join(output_dir, pred_filename))
        if not os.path.isfile(pred_path):
            export_single_raster(
                data=primary_arr,
                output_path=pred_path,
                crs=crs if is_georeferenced else None,
                transform=transform if is_georeferenced else None,
                nodata=nodata,
                description="Predicted Height (Single-Band Float32)",
                dtype=rasterio.float32,
            )

        # Export exact 5-key standalone metadata JSON and summary statistics JSON
        if generate_metadata_json:
            meta_dict = normalize_metadata_fields(
                primary_arr=primary_arr,
                mode=mode,
                units=units,
                confidence=confidence,
                is_georeferenced=is_georeferenced,
            )
            meta_filename = f"{prefix}_metadata.json"
            meta_path = os.path.abspath(os.path.join(output_dir, meta_filename))
            with open(meta_path, "w") as f:
                json.dump(meta_dict, f, indent=2)

            summary_filename = f"{prefix}_summary.json"
            summary_path = os.path.abspath(os.path.join(output_dir, summary_filename))
            summary_content = {
                "base_name": prefix,
                "mode": meta_dict["mode"],
                "units": meta_dict["units"],
                "confidence": meta_dict["confidence"],
                "raw_confidence": confidence,
                "resolution": meta_dict["resolution"],
                "is_georeferenced": is_georeferenced,
                "crs": crs_str,
                "statistics": compute_raster_statistics(primary_arr, nodata=nodata),
                "raster_files": {
                    "dsm": dsm_path,
                    "pred_height": pred_path,
                },
                "metadata_json": meta_path,
                "products": exported_products,
            }
            with open(summary_path, "w") as f:
                json.dump(summary_content, f, indent=2)

    return exported_products


class ExportResult:
    """Backward compatibility container for single product export."""

    def __init__(
        self,
        metadata: Dict[str, Any],
        raster_path: str,
        filename: str,
        is_geotiff: bool,
    ):
        self.metadata = metadata
        self.raster_path = raster_path
        self.filename = filename
        self.is_geotiff = is_geotiff

    def to_dict(self) -> Dict[str, Any]:
        return {
            **self.metadata,
            "raster_filename": self.filename,
            "raster_path": self.raster_path,
            "is_geotiff": self.is_geotiff,
        }


def assemble_and_export(
    height_grid: np.ndarray,
    mode: str,
    units: str,
    confidence: str,
    is_georeferenced: bool,
    crs: Optional[Any] = None,
    transform: Optional[Any] = None,
    output_dir: str = "outputs",
    base_name: Optional[str] = None,
) -> ExportResult:
    """Backward compatible single-raster export."""
    os.makedirs(output_dir, exist_ok=True)
    prefix = (base_name or "height_map").replace(" ", "_")
    filename = f"{prefix}_dsm.tif"
    file_path = os.path.abspath(os.path.join(output_dir, filename))

    is_geo = export_single_raster(
        data=height_grid,
        output_path=file_path,
        crs=crs if is_georeferenced else None,
        transform=transform if is_georeferenced else None,
        nodata=DEFAULT_NODATA,
        description=f"Height map ({mode})",
    )

    stats = compute_raster_statistics(height_grid, nodata=DEFAULT_NODATA)
    metadata = {
        "mode": mode,
        "units": units,
        "confidence": confidence,
        "resolution": [int(height_grid.shape[1]), int(height_grid.shape[0])],
        "statistics": stats,
    }

    return ExportResult(
        metadata=metadata,
        raster_path=file_path,
        filename=filename,
        is_geotiff=is_geo,
    )



"""Step 4A: DEM Manager for AOI matching, mosaicking, reprojection, and nodata handling.

Strictly searches real DEM rasters (SRTM / Copernicus / 3DEP).
Never synthesizes fake sinusoidal or synthetic terrain.
Reprojects to the exact target raster grid (H, W), CRS, and affine transform.
"""

import glob
import os
from typing import List, Optional, Tuple, Union
import numpy as np
import rasterio
from rasterio.crs import CRS
from rasterio.enums import Resampling
from rasterio.merge import merge
from rasterio.transform import Affine
from rasterio.warp import reproject, transform_bounds

DEFAULT_DEM_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "srtm"))
DEFAULT_NODATA = -9999.0


class DEMResult:
    """Container for processed DEM aligned to target raster grid."""

    def __init__(
        self,
        dem_array: np.ndarray,
        crs: CRS,
        transform: Affine,
        shape: Tuple[int, int],
        nodata: float = DEFAULT_NODATA,
        source_files: Optional[List[str]] = None,
        valid_pixel_ratio: float = 1.0,
    ):
        self.dem_array = dem_array  # 2D float32 (H, W)
        self.crs = crs
        self.transform = transform
        self.shape = shape
        self.nodata = nodata
        self.source_files = source_files or []
        self.valid_pixel_ratio = valid_pixel_ratio

    @property
    def valid_mask(self) -> np.ndarray:
        """Boolean mask: True = valid elevation, False = nodata / NaN."""
        return (self.dem_array != self.nodata) & (~np.isnan(self.dem_array))


class DEMManager:
    """Manages geospatial DEM lookup, mosaicking, and reprojection."""

    def __init__(self, dem_dir: Optional[str] = None):
        self.dem_dir = dem_dir or DEFAULT_DEM_DIR
        os.makedirs(self.dem_dir, exist_ok=True)

    def find_intersecting_dem_files(
        self,
        target_bounds: Tuple[float, float, float, float],
        target_crs: CRS,
    ) -> List[str]:
        """Find all DEM raster files whose bounding box intersects target_bounds."""
        patterns = ["*.tif", "*.tiff", "*.hgt", "*.dem"]
        candidate_files = []
        for p in patterns:
            candidate_files.extend(glob.glob(os.path.join(self.dem_dir, "**", p), recursive=True))

        if not candidate_files:
            return []

        intersecting_files = []
        minx_tgt, miny_tgt, maxx_tgt, maxy_tgt = target_bounds

        for file_path in candidate_files:
            try:
                with rasterio.open(file_path) as dem_src:
                    dem_bounds = dem_src.bounds
                    dem_crs = dem_src.crs

                    # Transform target bounds into DEM CRS
                    if dem_crs != target_crs:
                        t_minx, t_miny, t_maxx, t_maxy = transform_bounds(
                            target_crs, dem_crs, minx_tgt, miny_tgt, maxx_tgt, maxy_tgt
                        )
                    else:
                        t_minx, t_miny, t_maxx, t_maxy = minx_tgt, miny_tgt, maxx_tgt, maxy_tgt

                    # Check 2D bounding box intersection
                    intersects = not (
                        t_maxx < dem_bounds.left
                        or t_minx > dem_bounds.right
                        or t_maxy < dem_bounds.bottom
                        or t_miny > dem_bounds.top
                    )
                    if intersects:
                        intersecting_files.append(file_path)
            except Exception as e:
                print(f"[DEMManager] Warning: could not inspect candidate DEM '{file_path}': {e}")
                continue

        return intersecting_files

    def get_aligned_dem(
        self,
        target_bounds: Tuple[float, float, float, float],
        target_crs: CRS,
        target_transform: Affine,
        target_shape: Tuple[int, int],
        dem_files: Optional[List[str]] = None,
    ) -> Optional[DEMResult]:
        """Retrieve, mosaic, and reproject DEM to the exact target raster grid.

        Args:
            target_bounds: (left, bottom, right, top)
            target_crs: rasterio CRS of the input raster
            target_transform: Affine transform of the input raster
            target_shape: (H, W) target spatial dimensions
            dem_files: Optional list of explicit DEM files. If None, auto-searches dem_dir.

        Returns:
            DEMResult if intersecting DEM exists, else None.
        """
        if dem_files is None:
            dem_files = self.find_intersecting_dem_files(target_bounds, target_crs)

        if not dem_files:
            print(f"[DEMManager] No intersecting DEM tiles found in '{self.dem_dir}'.")
            return None

        print(f"[DEMManager] Found {len(dem_files)} intersecting DEM tile(s): {dem_files}")

        src_datasets = []
        try:
            for f in dem_files:
                src_datasets.append(rasterio.open(f))

            # If multiple files, mosaic them; if single file, read directly
            if len(src_datasets) > 1:
                mosaic_data, mosaic_transform = merge(src_datasets)
                mosaic_crs = src_datasets[0].crs
                mosaic_nodata = src_datasets[0].nodata or DEFAULT_NODATA
            else:
                ds = src_datasets[0]
                mosaic_data = ds.read(1)[None, :, :]
                mosaic_transform = ds.transform
                mosaic_crs = ds.crs
                mosaic_nodata = ds.nodata or DEFAULT_NODATA

            # Prepare destination buffer matching target raster grid exactly
            target_h, target_w = target_shape
            destination = np.full((target_h, target_w), DEFAULT_NODATA, dtype=np.float32)

            # Reproject to exact target CRS and affine grid
            reproject(
                source=mosaic_data[0].astype(np.float32),
                destination=destination,
                src_transform=mosaic_transform,
                src_crs=mosaic_crs,
                src_nodata=mosaic_nodata,
                dst_transform=target_transform,
                dst_crs=target_crs,
                dst_nodata=DEFAULT_NODATA,
                resampling=Resampling.bilinear,
            )

            # Compute valid ratio
            valid_count = np.count_nonzero((destination != DEFAULT_NODATA) & (~np.isnan(destination)))
            total_count = destination.size
            valid_ratio = float(valid_count / total_count) if total_count > 0 else 0.0

            return DEMResult(
                dem_array=destination,
                crs=target_crs,
                transform=target_transform,
                shape=target_shape,
                nodata=DEFAULT_NODATA,
                source_files=dem_files,
                valid_pixel_ratio=valid_ratio,
            )

        finally:
            for ds in src_datasets:
                try:
                    ds.close()
                except Exception:
                    pass

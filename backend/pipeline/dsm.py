"""Step 4C: DSM Generation and Validation.

Strict mathematical relationships:
  - relative_ndsm: Raw model output (relative height values).
  - metric_ndsm: Calibrated canopy/building height in meters:
        metric_ndsm = relative_ndsm * scale_factor + offset
  - dem: Ground/bare-earth elevation in meters (from real SRTM/DEM).
  - dsm: Digital Surface Model in meters:
        DSM = DEM + metric_ndsm
"""

from typing import Any, Dict, Optional, Tuple
import numpy as np

DEFAULT_NODATA = -9999.0


def generate_metric_ndsm(
    relative_ndsm: np.ndarray,
    scale_factor: float = 1.0,
    offset: float = 0.0,
    nodata_mask: Optional[np.ndarray] = None,
    nodata_val: float = DEFAULT_NODATA,
) -> np.ndarray:
    """Apply linear calibration to transform relative nDSM to metric nDSM (meters).

    Args:
        relative_ndsm: 2D float32 array of relative heights.
        scale_factor: Multiplicative scale factor from calibration.
        offset: Additive offset in meters.
        nodata_mask: Optional boolean mask (True = valid pixel, False = nodata).
        nodata_val: Sentinel value for nodata pixels (-9999.0).

    Returns:
        2D float32 array of calibrated metric height in meters.
    """
    assert relative_ndsm.ndim == 2, f"Expected 2D array, got ndim={relative_ndsm.ndim}"

    metric = relative_ndsm.astype(np.float32) * float(scale_factor) + float(offset)
    # Heights above ground cannot be negative
    metric = np.maximum(metric, 0.0)

    if nodata_mask is not None:
        metric[~nodata_mask] = nodata_val

    return metric


def generate_dsm(
    dem: np.ndarray,
    metric_ndsm: np.ndarray,
    dem_nodata: float = DEFAULT_NODATA,
    ndsm_nodata: float = DEFAULT_NODATA,
    output_nodata: float = DEFAULT_NODATA,
) -> np.ndarray:
    """Generate Digital Surface Model (DSM) by adding metric nDSM to bare-earth DEM.

    Formula: DSM(y, x) = DEM(y, x) + metric_ndsm(y, x)

    Args:
        dem: 2D float32 bare-earth elevation raster.
        metric_ndsm: 2D float32 calibrated above-ground height raster.
        dem_nodata: Sentinel value representing missing data in DEM.
        ndsm_nodata: Sentinel value representing missing data in nDSM.
        output_nodata: Sentinel value for missing data in resulting DSM.

    Returns:
        2D float32 DSM raster of identical dimensions.
    """
    if dem.shape != metric_ndsm.shape:
        raise ValueError(
            f"Shape mismatch: DEM {dem.shape} does not match metric_ndsm {metric_ndsm.shape}"
        )

    # Valid mask: both DEM and nDSM must have valid non-NaN data
    dem_valid = (dem != dem_nodata) & (~np.isnan(dem))
    ndsm_valid = (metric_ndsm != ndsm_nodata) & (~np.isnan(metric_ndsm))
    combined_valid = dem_valid & ndsm_valid

    dsm = np.full(dem.shape, output_nodata, dtype=np.float32)
    dsm[combined_valid] = dem[combined_valid] + metric_ndsm[combined_valid]

    return dsm


def validate_dsm(
    dsm: np.ndarray,
    dem: np.ndarray,
    metric_ndsm: np.ndarray,
    nodata: float = DEFAULT_NODATA,
) -> Dict[str, Any]:
    """Validate DSM correctness and return detailed physical statistics."""
    valid = (
        (dsm != nodata)
        & (dem != nodata)
        & (metric_ndsm != nodata)
        & (~np.isnan(dsm))
        & (~np.isnan(dem))
        & (~np.isnan(metric_ndsm))
    )

    valid_count = int(np.count_nonzero(valid))
    total_count = int(dsm.size)
    valid_ratio = float(valid_count / total_count) if total_count > 0 else 0.0

    if valid_count == 0:
        return {
            "is_valid": False,
            "error": "No valid intersecting pixels between DSM and DEM.",
            "valid_pixel_count": 0,
            "valid_ratio": 0.0,
        }

    valid_dsm = dsm[valid]
    valid_dem = dem[valid]
    valid_ndsm = metric_ndsm[valid]

    # Verify mathematical constraint: DSM >= DEM - epsilon everywhere
    diff = valid_dsm - valid_dem
    min_diff = float(np.min(diff))
    violates_lower_bound = min_diff < -1e-3

    # Check for extreme anomalies (e.g. canopy heights > 300m or surface elevation > 9000m)
    max_height = float(np.max(valid_ndsm))
    min_elev = float(np.min(valid_dsm))
    max_elev = float(np.max(valid_dsm))

    is_physically_plausible = (
        not violates_lower_bound
        and -500.0 <= min_elev <= 9000.0
        and -500.0 <= max_elev <= 9000.0
        and max_height <= 400.0
    )

    return {
        "is_valid": is_physically_plausible,
        "valid_pixel_count": valid_count,
        "total_pixel_count": total_count,
        "valid_ratio": valid_ratio,
        "dsm_min": min_elev,
        "dsm_max": max_elev,
        "dsm_mean": float(np.mean(valid_dsm)),
        "dsm_std": float(np.std(valid_dsm)),
        "ndsm_max": max_height,
        "ndsm_mean": float(np.mean(valid_ndsm)),
        "min_dsm_minus_dem": min_diff,
    }

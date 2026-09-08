"""Unit tests for calibration, RANSAC fitting, and DSM formulas."""

import numpy as np
from pipeline.calibration import calibrate_height, _fit_ransac
from pipeline.dsm import generate_dsm, generate_metric_ndsm, validate_dsm


def test_metric_ndsm_scaling():
    rel = np.array([[1.0, 2.0], [3.0, 4.0]], dtype=np.float32)
    metric = generate_metric_ndsm(rel, scale_factor=2.0, offset=1.0)
    expected = np.array([[3.0, 5.0], [7.0, 9.0]], dtype=np.float32)
    assert np.allclose(metric, expected)


def test_dsm_generation_and_validation():
    dem = np.full((100, 100), 500.0, dtype=np.float32)
    metric_ndsm = np.random.uniform(2.0, 30.0, (100, 100)).astype(np.float32)

    dsm = generate_dsm(dem, metric_ndsm)
    val = validate_dsm(dsm, dem, metric_ndsm)

    assert val["is_valid"] is True
    assert val["valid_ratio"] == 1.0
    assert val["dsm_min"] >= 500.0
    assert val["min_dsm_minus_dem"] >= 0.0


def test_ransac_outlier_rejection():
    rel = np.linspace(2.0, 35.0, 200).reshape(10, 20).astype(np.float32)
    ground_truth = rel * 1.5 + 0.8

    # Inject 15% extreme outliers
    noisy = ground_truth.copy()
    noisy[:2, :15] += 100.0

    fit = _fit_ransac(rel, noisy)
    assert abs(fit["scale"] - 1.5) < 0.15
    assert abs(fit["offset"] - 0.8) < 1.0
    assert fit["outlier_ratio"] > 0.05
    assert fit["rmse"] < 5.0


def test_uncalibrated_relative_no_fake_dem():
    rel = np.random.uniform(5.0, 20.0, (64, 64)).astype(np.float32)
    res = calibrate_height(rel, is_georeferenced=False)
    assert res.mode == "relative"
    assert res.units == "relative_units"
    assert res.confidence == "unavailable"
    assert res.metric_ndsm is None
    assert res.dem is None
    assert res.dsm is None


if __name__ == "__main__":
    test_metric_ndsm_scaling()
    test_dsm_generation_and_validation()
    test_ransac_outlier_rejection()
    test_uncalibrated_relative_no_fake_dem()
    print("All calibration and DSM tests passed!")

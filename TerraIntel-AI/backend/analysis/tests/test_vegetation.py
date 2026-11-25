"""Unit tests for analysis.vegetation."""
import numpy as np
import pytest

from analysis.vegetation import compute_ndvi, round_half_up, summarize_ndvi


def test_round_half_up() -> None:
    assert round_half_up(0.12345, 4) == "0.1235"
    assert round_half_up(12.345, 2) == "12.35"
    assert round_half_up(12.3, 0) == "12"


def test_compute_ndvi_guards_zero_and_clamps() -> None:
    b8 = np.array([0.8, 0.0, -0.5, 1.0])
    b4 = np.array([0.2, 0.0, 0.5, 0.0])
    ndvi = compute_ndvi(b8, b4)
    assert np.isclose(ndvi[0], 0.6)
    assert np.isnan(ndvi[1])
    assert np.isnan(ndvi[2])
    assert np.isclose(ndvi[3], 1.0)


def test_summarize_ndvi_excludes_anomalous_and_flags_low_coverage() -> None:
    arr = np.array([-0.25, 0.1, 0.3, 0.5, np.nan])
    summary = summarize_ndvi(arr, total_cropland_pixels=20)
    assert summary.valid_pixel_count == 3
    assert summary.anomalous_pixel_count == 1
    assert summary.valid_pixel_pct == pytest.approx(15.0)
    assert summary.anomalous_pixel_pct == pytest.approx(5.0)
    assert summary.low_coverage is True
    assert summary.p50_ndvi == pytest.approx(0.3)


def test_summarize_ndvi_all_invalid_or_empty() -> None:
    summary = summarize_ndvi(np.array([-0.5, np.nan]), total_cropland_pixels=10)
    assert summary.valid_pixel_count == 0
    assert summary.low_coverage is True
    assert summary.mean_ndvi == 0.0

    with pytest.raises(ValueError):
        summarize_ndvi(np.array([0.2]), total_cropland_pixels=0)

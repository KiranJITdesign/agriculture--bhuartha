"""Unit tests for analysis.comparison Delta NDVI binning."""
import numpy as np
import pytest

from analysis.comparison import bin_delta_ndvi


def test_bin_delta_ndvi_sums_to_100_pct() -> None:
    a = np.array([0.30, 0.40, 0.50, 0.60, np.nan])
    b = np.array([0.42, 0.38, 0.55, 0.45, 0.50])
    summary = bin_delta_ndvi(a, b, pixel_area_ha=0.01)
    assert summary.analysed_area_ha == pytest.approx(0.04)
    assert sum(bin_item.area_pct for bin_item in summary.bins) == pytest.approx(100.0)
    assert sum(bin_item.area_ha for bin_item in summary.bins) == pytest.approx(0.04)


def test_bin_delta_ndvi_empty() -> None:
    summary = bin_delta_ndvi(np.array([np.nan]), np.array([0.2]), pixel_area_ha=0.01)
    assert summary.analysed_area_ha == 0.0
    assert all(b.area_pct == 0.0 for b in summary.bins)

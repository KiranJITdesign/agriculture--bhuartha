"""Unit tests for analysis.classification (100% branch coverage on threshold logic)."""
import numpy as np
import pytest

from analysis.classification import (
    VigourClass,
    VigourThresholds,
    classify_ndvi_array,
    classify_ndvi_value,
    compute_low_vigour_zones,
)


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (0.05, VigourClass.LOW),
        (0.1999, VigourClass.LOW),
        (0.20, VigourClass.MODERATE),
        (0.45, VigourClass.MODERATE),
        (0.4501, VigourClass.HIGH),
        (0.70, VigourClass.HIGH),
        (0.7001, VigourClass.VERY_HIGH),
    ],
)
def test_classify_ndvi_value_all_branches(value: float, expected: VigourClass) -> None:
    assert classify_ndvi_value(value) == expected


def test_classify_ndvi_array_and_empty() -> None:
    arr = np.array([-0.2, 0.1, 0.3, 0.6, 0.8, np.nan])
    breakdown = classify_ndvi_array(arr, pixel_area_ha=0.01)
    by_class = {b.vigour_class: b for b in breakdown}
    assert by_class[VigourClass.LOW].area_ha == pytest.approx(0.01)
    assert by_class[VigourClass.MODERATE].area_pct == pytest.approx(25.0)
    assert by_class[VigourClass.HIGH].area_pct == pytest.approx(25.0)
    assert by_class[VigourClass.VERY_HIGH].area_pct == pytest.approx(25.0)

    empty = classify_ndvi_array(np.array([np.nan]), pixel_area_ha=0.01)
    assert all(b.area_pct == 0.0 for b in empty)


def test_compute_low_vigour_zones_separates_absolute_and_relative() -> None:
    # p50 = 0.50, iqr = 0.20 -> relative_cutoff = 0.30
    # Pixels < 0.20: 0.05, 0.15 (both < 0.30 as well)
    # Test tighter cutoff: p50 = 0.25, iqr = 0.15 -> cutoff = 0.10
    arr = np.array([0.05, 0.15, 0.25, 0.50])
    res = compute_low_vigour_zones(
        arr,
        pixel_area_ha=0.01,
        p50_ndvi=0.25,
        iqr_ndvi=0.15,
        thresholds=VigourThresholds(),
    )
    assert res.absolute_low_area_ha == pytest.approx(0.02)
    assert res.relative_low_area_ha == pytest.approx(0.01)
    assert res.relative_cutoff_ndvi == pytest.approx(0.10)

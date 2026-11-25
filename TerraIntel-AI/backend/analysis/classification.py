"""Pure vegetation vigour classification and low-vigour zone detection."""
from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

import numpy as np
from numpy.typing import NDArray


class VigourClass(StrEnum):
    LOW = "LOW"
    MODERATE = "MODERATE"
    HIGH = "HIGH"
    VERY_HIGH = "VERY_HIGH"


@dataclass(frozen=True)
class VigourThresholds:
    """Persisted NDVI thresholds per analysis."""

    low_max: float = 0.20
    moderate_max: float = 0.45
    high_max: float = 0.70


@dataclass(frozen=True)
class ClassBreakdown:
    """Area and share for a single vigour class."""

    vigour_class: VigourClass
    area_ha: float
    area_pct: float


@dataclass(frozen=True)
class LowVigourResult:
    """Separate absolute and relative low-vigour areas (ha)."""

    absolute_low_area_ha: float
    relative_low_area_ha: float
    relative_cutoff_ndvi: float


def classify_ndvi_value(
    value: float, thresholds: VigourThresholds = VigourThresholds()
) -> VigourClass:
    """Classify a single NDVI value into LOW / MODERATE / HIGH / VERY_HIGH."""
    if value < thresholds.low_max:
        return VigourClass.LOW
    if value <= thresholds.moderate_max:
        return VigourClass.MODERATE
    if value <= thresholds.high_max:
        return VigourClass.HIGH
    return VigourClass.VERY_HIGH


def classify_ndvi_array(
    ndvi_values: NDArray[np.floating],
    pixel_area_ha: float,
    thresholds: VigourThresholds = VigourThresholds(),
) -> list[ClassBreakdown]:
    """Compute area_ha and area_pct for each vigour class from valid NDVI pixels."""
    arr = np.asarray(ndvi_values, dtype=np.float64)
    valid = arr[np.isfinite(arr) & (arr >= -0.1)]
    total = int(valid.size)

    masks = {
        VigourClass.LOW: valid < thresholds.low_max,
        VigourClass.MODERATE: (valid >= thresholds.low_max) & (valid <= thresholds.moderate_max),
        VigourClass.HIGH: (valid > thresholds.moderate_max) & (valid <= thresholds.high_max),
        VigourClass.VERY_HIGH: valid > thresholds.high_max,
    }
    results: list[ClassBreakdown] = []
    for cls in (VigourClass.LOW, VigourClass.MODERATE, VigourClass.HIGH, VigourClass.VERY_HIGH):
        count = int(np.sum(masks[cls]))
        area_ha = count * pixel_area_ha
        area_pct = (count / total * 100.0) if total > 0 else 0.0
        results.append(ClassBreakdown(vigour_class=cls, area_ha=area_ha, area_pct=area_pct))
    return results


def compute_low_vigour_zones(
    ndvi_values: NDArray[np.floating],
    pixel_area_ha: float,
    p50_ndvi: float,
    iqr_ndvi: float,
    thresholds: VigourThresholds = VigourThresholds(),
) -> LowVigourResult:
    """
    Compute absolute and relative low-vigour areas separately.
    Relative low-vigour pixel qualifies iff:
      NDVI < low_threshold AND NDVI < (p50 - 1.0 * IQR)
    """
    arr = np.asarray(ndvi_values, dtype=np.float64)
    valid = arr[np.isfinite(arr) & (arr >= -0.1)]
    relative_cutoff = p50_ndvi - 1.0 * iqr_ndvi

    abs_mask = valid < thresholds.low_max
    rel_mask = abs_mask & (valid < relative_cutoff)

    return LowVigourResult(
        absolute_low_area_ha=float(np.sum(abs_mask)) * pixel_area_ha,
        relative_low_area_ha=float(np.sum(rel_mask)) * pixel_area_ha,
        relative_cutoff_ndvi=float(relative_cutoff),
    )

"""Pure NDVI computation and summary statistics (no Django imports)."""
from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

import numpy as np
from numpy.typing import NDArray

ANOMALOUS_NDVI_THRESHOLD = -0.1


def round_half_up(value: float, decimals: int) -> str:
    """Format a float with deterministic ROUND_HALF_UP to `decimals` places."""
    quant = Decimal("1") if decimals == 0 else Decimal(f"1e-{decimals}")
    rounded = Decimal(str(value)).quantize(quant, rounding=ROUND_HALF_UP)
    return f"{rounded:.{decimals}f}"


def compute_ndvi(b8: NDArray[np.floating], b4: NDArray[np.floating]) -> NDArray[np.float64]:
    """Compute (B8 - B4) / (B8 + B4) clamped to [-1, 1], guarding B8 + B4 <= 0."""
    b8_f = np.asarray(b8, dtype=np.float64)
    b4_f = np.asarray(b4, dtype=np.float64)
    denom = b8_f + b4_f
    ndvi = np.full(denom.shape, np.nan, dtype=np.float64)
    valid = np.isfinite(denom) & (denom > 0.0)
    ndvi[valid] = np.clip((b8_f[valid] - b4_f[valid]) / denom[valid], -1.0, 1.0)
    return ndvi


@dataclass(frozen=True)
class VegetationSummary:
    """Cropland-scoped NDVI summary statistics."""

    mean_ndvi: float
    p25_ndvi: float
    p50_ndvi: float
    p75_ndvi: float
    iqr_ndvi: float
    min_ndvi: float
    max_ndvi: float
    valid_pixel_count: int
    anomalous_pixel_count: int
    total_cropland_pixels: int
    valid_pixel_pct: float
    anomalous_pixel_pct: float
    low_coverage: bool


def summarize_ndvi(
    ndvi_values: NDArray[np.floating],
    total_cropland_pixels: int,
) -> VegetationSummary:
    """Compute NDVI summary excluding NaN and anomalous (< -0.1) pixels."""
    if total_cropland_pixels <= 0:
        raise ValueError("total_cropland_pixels must be positive")

    arr = np.asarray(ndvi_values, dtype=np.float64)
    finite = arr[np.isfinite(arr)]
    anomalous_mask = finite < ANOMALOUS_NDVI_THRESHOLD
    anomalous_count = int(np.sum(anomalous_mask))
    valid = finite[~anomalous_mask]
    valid_count = int(valid.size)

    valid_pct = min(100.0, (valid_count / total_cropland_pixels) * 100.0)
    anomalous_pct = min(100.0, (anomalous_count / total_cropland_pixels) * 100.0)

    if valid_count == 0:
        return VegetationSummary(
            mean_ndvi=0.0,
            p25_ndvi=0.0,
            p50_ndvi=0.0,
            p75_ndvi=0.0,
            iqr_ndvi=0.0,
            min_ndvi=0.0,
            max_ndvi=0.0,
            valid_pixel_count=0,
            anomalous_pixel_count=anomalous_count,
            total_cropland_pixels=total_cropland_pixels,
            valid_pixel_pct=valid_pct,
            anomalous_pixel_pct=anomalous_pct,
            low_coverage=True,
        )

    p25, p50, p75 = np.percentile(valid, [25.0, 50.0, 75.0])
    return VegetationSummary(
        mean_ndvi=float(np.mean(valid)),
        p25_ndvi=float(p25),
        p50_ndvi=float(p50),
        p75_ndvi=float(p75),
        iqr_ndvi=float(p75 - p25),
        min_ndvi=float(np.min(valid)),
        max_ndvi=float(np.max(valid)),
        valid_pixel_count=valid_count,
        anomalous_pixel_count=anomalous_count,
        total_cropland_pixels=total_cropland_pixels,
        valid_pixel_pct=valid_pct,
        anomalous_pixel_pct=anomalous_pct,
        low_coverage=valid_pct < 30.0,
    )

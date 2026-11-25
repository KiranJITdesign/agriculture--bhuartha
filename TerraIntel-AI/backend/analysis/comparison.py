"""Pure two-period Delta NDVI binning computation (no Django imports)."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

BIN_STEP = 0.05


@dataclass(frozen=True)
class DeltaNdviBin:
    """Single +/-0.05 Delta NDVI bin."""

    bin_min: float
    bin_max: float
    area_ha: float
    area_pct: float


@dataclass(frozen=True)
class DeltaNdviSummary:
    """Summary of two-period NDVI difference."""

    mean_delta_ndvi: float
    analysed_area_ha: float
    bins: list[DeltaNdviBin]


def bin_delta_ndvi(
    ndvi_period_a: NDArray[np.floating],
    ndvi_period_b: NDArray[np.floating],
    pixel_area_ha: float,
) -> DeltaNdviSummary:
    """
    Compute Delta NDVI = B - A and bin into 0.05-wide intervals across [-1.0, 1.0].
    Bins sum to 100% of analysed area.
    """
    a = np.asarray(ndvi_period_a, dtype=np.float64)
    b = np.asarray(ndvi_period_b, dtype=np.float64)
    valid = np.isfinite(a) & np.isfinite(b) & (a >= -0.1) & (b >= -0.1)
    delta = np.clip(b[valid] - a[valid], -1.0, 1.0)
    total = int(delta.size)

    edges = np.round(np.arange(-1.0, 1.0 + BIN_STEP / 2.0, BIN_STEP), 2)
    if total == 0:
        bins = [
            DeltaNdviBin(
                bin_min=float(edges[i]),
                bin_max=float(edges[i + 1]),
                area_ha=0.0,
                area_pct=0.0,
            )
            for i in range(len(edges) - 1)
        ]
        return DeltaNdviSummary(mean_delta_ndvi=0.0, analysed_area_ha=0.0, bins=bins)

    counts, _ = np.histogram(delta, bins=edges)
    analysed_area_ha = float(total) * pixel_area_ha
    bins = []
    for i, count in enumerate(counts):
        c = int(count)
        bins.append(
            DeltaNdviBin(
                bin_min=float(edges[i]),
                bin_max=float(edges[i + 1]),
                area_ha=c * pixel_area_ha,
                area_pct=(c / total) * 100.0,
            )
        )
    return DeltaNdviSummary(
        mean_delta_ndvi=float(np.mean(delta)),
        analysed_area_ha=analysed_area_ha,
        bins=bins,
    )

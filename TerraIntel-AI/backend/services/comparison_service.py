"""Two-period NDVI difference comparison service using GEE and RdBu 11-class ramp."""
from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

import ee

from analysis.comparison import DeltaNdviBin

from .exceptions import ServiceError, ServiceFailureCode
from .gee_service import S2_COLLECTION, execute_with_retry, init_gee
from .ndvi_service import (
    TILE_TTL_HOURS,
    _tile_url_from_map_id,
    apply_s2_mask_pipeline,
    build_cropland_mask,
    compute_ndvi_band,
)
from .stac_service import compare_ndvi_stac

# ColorBrewer RdBu 11-class diverging ramp (centred at 0, from design-tokens.md)
RDBU_11_PALETTE = [
    "#67001f",
    "#b2182b",
    "#d6604d",
    "#f4a582",
    "#fddbc7",
    "#f7f7f7",
    "#d1e5f0",
    "#92c5de",
    "#4393c3",
    "#2166ac",
    "#053061",
]


@dataclass(frozen=True)
class ComparisonResult:
    mean_delta_ndvi: float
    analysed_area_ha: float
    diff_tile_url: str
    tiles_expires_at: str
    bins: list[DeltaNdviBin]


def compare_ndvi_periods(
    *,
    geometry_geojson: dict[str, Any],
    period_a_start: str,
    period_a_end: str,
    period_b_start: str,
    period_b_end: str,
) -> ComparisonResult:
    """Compute Delta NDVI = Period B - Period A over cropland mask and bin at +/-0.05."""
    provider = os.environ.get("SATELLITE_PROVIDER", "").lower()
    if provider == "stac" or (not provider and not os.environ.get("GEE_PROJECT_ID")):
        mean_delta, area_ha, diff_url, expires_at, bins = compare_ndvi_stac(
            geometry_geojson=geometry_geojson,
            period_a_start=period_a_start,
            period_a_end=period_a_end,
            period_b_start=period_b_start,
            period_b_end=period_b_end,
        )
        return ComparisonResult(
            mean_delta_ndvi=mean_delta,
            analysed_area_ha=area_ha,
            diff_tile_url=diff_url,
            tiles_expires_at=expires_at,
            bins=bins,
        )

    init_gee()

    def _run() -> ComparisonResult:
        aoi = ee.Geometry(geometry_geojson)
        cropland_mask = build_cropland_mask(aoi)

        col_a = (
            ee.ImageCollection(S2_COLLECTION)
            .filterBounds(aoi)
            .filterDate(period_a_start, period_a_end)
        )
        col_b = (
            ee.ImageCollection(S2_COLLECTION)
            .filterBounds(aoi)
            .filterDate(period_b_start, period_b_end)
        )
        if int(col_a.size().getInfo() or 0) == 0 or int(col_b.size().getInfo() or 0) == 0:
            raise ServiceError(
                ServiceFailureCode.NO_SCENES_FOUND,
                "Both comparison periods require at least one Sentinel-2 scene.",
            )

        ndvi_a = compute_ndvi_band(
            col_a.map(lambda img: apply_s2_mask_pipeline(img, aoi, cropland_mask)).median()
        )
        ndvi_b = compute_ndvi_band(
            col_b.map(lambda img: apply_s2_mask_pipeline(img, aoi, cropland_mask)).median()
        )

        valid_a = ndvi_a.updateMask(ndvi_a.gte(-0.1))
        valid_b = ndvi_b.updateMask(ndvi_b.gte(-0.1))
        delta = valid_b.subtract(valid_a).clamp(-1.0, 1.0).rename("DELTA_NDVI")

        area_ha_img = ee.Image.pixelArea().divide(10_000.0).updateMask(delta.mask())
        analysed_area_ha = float(
            (
                area_ha_img.reduceRegion(
                    reducer=ee.Reducer.sum(), geometry=aoi, scale=10, maxPixels=1e9
                ).getInfo()
                or {}
            ).get("area", 0.0)
            or 0.0
        )
        if analysed_area_ha <= 0.0:
            raise ServiceError(
                ServiceFailureCode.NO_SCENES_FOUND,
                "No overlapping valid cropland pixels between the two periods.",
            )

        mean_delta = float(
            (
                delta.reduceRegion(
                    reducer=ee.Reducer.mean(), geometry=aoi, scale=10, maxPixels=10**9
                ).getInfo()
                or {}
            ).get("DELTA_NDVI", 0.0)
            or 0.0
        )

        hist_info = (
            delta.reduceRegion(
                reducer=ee.Reducer.fixedHistogram(-1.0, 1.0, 40),
                geometry=aoi,
                scale=10,
                maxPixels=10**9,
            ).getInfo()
            or {}
        ).get("DELTA_NDVI", [])

        total_count = sum(float(row[1]) for row in hist_info) if hist_info else 0.0
        bins: list[DeltaNdviBin] = []
        for idx in range(40):
            b_min = round(-1.0 + idx * 0.05, 2)
            b_max = round(b_min + 0.05, 2)
            cnt = float(hist_info[idx][1]) if idx < len(hist_info) else 0.0
            share = (cnt / total_count) if total_count > 0 else 0.0
            bins.append(
                DeltaNdviBin(
                    bin_min=b_min,
                    bin_max=b_max,
                    area_ha=share * analysed_area_ha,
                    area_pct=share * 100.0,
                )
            )

        diff_map_id = delta.getMapId({"min": -0.5, "max": 0.5, "palette": RDBU_11_PALETTE})
        expires_at = (datetime.now(UTC) + timedelta(hours=TILE_TTL_HOURS)).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        )
        return ComparisonResult(
            mean_delta_ndvi=mean_delta,
            analysed_area_ha=analysed_area_ha,
            diff_tile_url=_tile_url_from_map_id(diff_map_id),
            tiles_expires_at=expires_at,
            bins=bins,
        )

    return execute_with_retry(_run)

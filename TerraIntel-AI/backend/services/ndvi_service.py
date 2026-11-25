"""Sentinel-2 NDVI computation, 5-step masking, areal stats, and tile URL generation."""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any, cast

import ee

from .exceptions import ServiceError, ServiceFailureCode
from .gee_service import S2_COLLECTION, execute_with_retry, init_gee
from .stac_service import compute_ndvi_stac

logger = logging.getLogger(__name__)

# Official ESA WorldCover 10m v200 collection:
# https://developers.google.com/earth-engine/datasets/catalog/ESA_WorldCover_v200
WORLDCOVER_COLLECTION = "ESA/WorldCover/v200"
WORLDCOVER_CROPLAND_CLASS = 40

# ColorBrewer YlGn 9-class palette (from design-tokens.md)
YLGN_9_PALETTE = [
    "#ffffe5",
    "#f7fcb9",
    "#d9f0a3",
    "#addd8e",
    "#78c679",
    "#41ab5d",
    "#238443",
    "#006837",
    "#004529",
]

MAX_EXACT_PIXELS = 5_000_000
TILE_TTL_HOURS = 6


@dataclass(frozen=True)
class NdviCompositeResult:
    """Output of Sentinel-2 NDVI composite and areal statistics."""

    mean_ndvi: float
    p25_ndvi: float
    p50_ndvi: float
    p75_ndvi: float
    min_ndvi: float
    max_ndvi: float
    cropland_area_ha: float
    valid_area_ha: float
    valid_pixel_pct: float
    anomalous_pixel_pct: float
    sampled: bool
    low_coverage: bool
    ndvi_tile_url: str
    true_colour_tile_url: str
    tiles_expires_at: str
    scenes: list[dict[str, str]]
    absolute_low_area_ha: float = 0.0
    relative_low_area_ha: float = 0.0
    class_stats: list[dict[str, Any]] | None = None
    low_zone_polygons: list[dict[str, Any]] | None = None


def build_cropland_mask(aoi: ee.Geometry) -> ee.Image:
    """Step 1 & 2: Clip to region boundary and mask to ESA WorldCover == 40."""
    worldcover = ee.ImageCollection(WORLDCOVER_COLLECTION).first().clip(aoi)
    return cast(ee.Image, worldcover.select("Map").eq(WORLDCOVER_CROPLAND_CLASS))


def apply_s2_mask_pipeline(image: ee.Image, aoi: ee.Geometry, cropland_mask: ee.Image) -> ee.Image:
    """
    Apply masking in exact PRD §8.2 order:
    1. region boundary
    2. WorldCover == 40
    3. SCL not in {3, 8, 9, 10, 11}
    4. MSK_CLDPRB <= 40
    5. B8 + B4 > 0
    """
    # 1. Region boundary
    clipped = image.clip(aoi)
    # 2. WorldCover == 40
    step2 = clipped.updateMask(cropland_mask)
    # 3. SCL not in {3, 8, 9, 10, 11}
    scl = step2.select("SCL")
    scl_mask = (
        scl.neq(3)
        .And(scl.neq(8))
        .And(scl.neq(9))
        .And(scl.neq(10))
        .And(scl.neq(11))
    )
    step3 = step2.updateMask(scl_mask)
    # 4. MSK_CLDPRB <= 40
    cloud_prob_mask = step3.select("MSK_CLDPRB").lte(40)
    step4 = step3.updateMask(cloud_prob_mask)
    # 5. B8 + B4 > 0 (divide-by-zero guard)
    b8 = step4.select("B8").toFloat()
    b4 = step4.select("B4").toFloat()
    sum_mask = b8.add(b4).gt(0)
    return step4.updateMask(sum_mask)


def compute_ndvi_band(masked_image: ee.Image) -> ee.Image:
    """Compute (B8 - B4) / (B8 + B4) clamped to [-1, 1]."""
    ndvi = masked_image.normalizedDifference(["B8", "B4"]).rename("NDVI")
    return cast(ee.Image, ndvi.clamp(-1.0, 1.0))


def _tile_url_from_map_id(map_id_dict: dict[str, Any]) -> str:
    fetcher = map_id_dict.get("tile_fetcher")
    if fetcher is not None and hasattr(fetcher, "url_format"):
        return str(fetcher.url_format)
    return str(map_id_dict.get("urlFormat", ""))


def compute_ndvi_analysis(
    geometry_geojson: dict[str, Any],
    start_date: str,
    end_date: str,
) -> NdviCompositeResult:
    """Run Sentinel-2 NDVI composite, stats, and tile URL generation for a region."""
    provider = os.environ.get("SATELLITE_PROVIDER", "").lower()
    if provider == "stac" or (not provider and not os.environ.get("GEE_PROJECT_ID")):
        stac_out = compute_ndvi_stac(geometry_geojson, start_date, end_date)
        return NdviCompositeResult(
            mean_ndvi=float(stac_out["mean_ndvi"]),
            p25_ndvi=float(stac_out["p25_ndvi"]),
            p50_ndvi=float(stac_out["p50_ndvi"]),
            p75_ndvi=float(stac_out["p75_ndvi"]),
            min_ndvi=float(stac_out["min_ndvi"]),
            max_ndvi=float(stac_out["max_ndvi"]),
            cropland_area_ha=float(stac_out["cropland_area_ha"]),
            valid_area_ha=float(stac_out["valid_area_ha"]),
            valid_pixel_pct=float(stac_out["valid_pixel_pct"]),
            anomalous_pixel_pct=float(stac_out["anomalous_pixel_pct"]),
            sampled=bool(stac_out["sampled"]),
            low_coverage=bool(stac_out["low_coverage"]),
            ndvi_tile_url=str(stac_out["ndvi_tile_url"]),
            true_colour_tile_url=str(stac_out["true_colour_tile_url"]),
            tiles_expires_at=str(stac_out["tiles_expires_at"]),
            scenes=list(stac_out["scenes"]),
            absolute_low_area_ha=float(stac_out["absolute_low_area_ha"]),
            relative_low_area_ha=float(stac_out["relative_low_area_ha"]),
            class_stats=list(stac_out["class_stats"]),
            low_zone_polygons=list(stac_out.get("low_zone_polygons", [])),
        )

    init_gee()

    def _run() -> NdviCompositeResult:
        aoi = ee.Geometry(geometry_geojson)
        cropland_mask = build_cropland_mask(aoi)

        raw_collection = (
            ee.ImageCollection(S2_COLLECTION)
            .filterBounds(aoi)
            .filterDate(start_date, end_date)
        )
        scene_count = int(raw_collection.size().getInfo() or 0)
        if scene_count == 0:
            raise ServiceError(
                ServiceFailureCode.NO_SCENES_FOUND,
                f"No Sentinel-2 scenes found between {start_date} and {end_date}.",
            )

        # Cropland area in hectares using ee.Image.pixelArea()
        cropland_area_img = ee.Image.pixelArea().divide(10_000.0).updateMask(cropland_mask)
        cropland_area_ha = float(
            (
                cropland_area_img.reduceRegion(
                    reducer=ee.Reducer.sum(),
                    geometry=aoi,
                    scale=10,
                    maxPixels=1e9,
                ).getInfo()
                or {}
            ).get("area", 0.0)
            or 0.0
        )
        if cropland_area_ha <= 0.0:
            raise ServiceError(
                ServiceFailureCode.NO_CROPLAND,
                "Region contains no ESA WorldCover class 40 cropland.",
            )

        masked_col = raw_collection.map(lambda img: apply_s2_mask_pipeline(img, aoi, cropland_mask))
        composite = masked_col.median()
        ndvi_full = compute_ndvi_band(composite)

        # Separate anomalous (< -0.1) vs valid (>= -0.1) pixels inside cropland mask
        valid_ndvi = ndvi_full.updateMask(ndvi_full.gte(-0.1))
        anomalous_mask = ndvi_full.lt(-0.1)

        pixel_area_ha = ee.Image.pixelArea().divide(10_000.0)
        valid_area_ha = float(
            (
                pixel_area_ha.updateMask(valid_ndvi.mask())
                .reduceRegion(reducer=ee.Reducer.sum(), geometry=aoi, scale=10, maxPixels=1e9)
                .getInfo()
                or {}
            ).get("area", 0.0)
            or 0.0
        )
        anomalous_area_ha = float(
            (
                pixel_area_ha.updateMask(anomalous_mask)
                .reduceRegion(reducer=ee.Reducer.sum(), geometry=aoi, scale=10, maxPixels=1e9)
                .getInfo()
                or {}
            ).get("area", 0.0)
            or 0.0
        )

        valid_pixel_pct = min(100.0, (valid_area_ha / cropland_area_ha) * 100.0)
        anomalous_pixel_pct = min(100.0, (anomalous_area_ha / cropland_area_ha) * 100.0)

        pixel_count = int(
            (
                valid_ndvi.reduceRegion(
                    reducer=ee.Reducer.count(), geometry=aoi, scale=10, maxPixels=10**9
                ).getInfo()
                or {}
            ).get("NDVI", 0)
            or 0
        )
        if pixel_count == 0:
            raise ServiceError(
                ServiceFailureCode.NO_SCENES_FOUND,
                "All Sentinel-2 observations were masked by cloud/shadow filters.",
            )

        sampled = pixel_count > MAX_EXACT_PIXELS
        stat_scale = 100 if sampled else 10  # 1% area sampling when > 5M pixels
        stats = (
            valid_ndvi.reduceRegion(
                reducer=(
                    ee.Reducer.mean()
                    .combine(ee.Reducer.minMax(), sharedInputs=True)
                    .combine(ee.Reducer.percentile([25, 50, 75]), sharedInputs=True)
                ),
                geometry=aoi,
                scale=stat_scale,
                maxPixels=10**9,
            ).getInfo()
            or {}
        )

        # Scene provenance
        col_info = raw_collection.sort("system:time_start", False).limit(20).getInfo() or {}
        scenes: list[dict[str, str]] = []
        for feat in col_info.get("features", []):
            props = feat.get("properties", {})
            ts_ms = props.get("system:time_start")
            acq = (
                datetime.fromtimestamp(ts_ms / 1000.0, tz=UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
                if isinstance(ts_ms, (int, float))
                else ""
            )
            scenes.append(
                {
                    "scene_id": str(props.get("PRODUCT_ID") or feat.get("id") or ""),
                    "acquired_at": acq,
                }
            )

        ndvi_map_id = valid_ndvi.getMapId({"min": 0.0, "max": 0.9, "palette": YLGN_9_PALETTE})
        tc_map_id = composite.getMapId({"bands": ["B4", "B3", "B2"], "min": 0, "max": 3000})
        expires_at = (datetime.now(UTC) + timedelta(hours=TILE_TTL_HOURS)).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        )

        return NdviCompositeResult(
            mean_ndvi=float(stats.get("NDVI_mean") or 0.0),
            p25_ndvi=float(stats.get("NDVI_p25") or 0.0),
            p50_ndvi=float(stats.get("NDVI_p50") or 0.0),
            p75_ndvi=float(stats.get("NDVI_p75") or 0.0),
            min_ndvi=float(stats.get("NDVI_min") or 0.0),
            max_ndvi=float(stats.get("NDVI_max") or 0.0),
            cropland_area_ha=cropland_area_ha,
            valid_area_ha=valid_area_ha,
            valid_pixel_pct=valid_pixel_pct,
            anomalous_pixel_pct=anomalous_pixel_pct,
            sampled=sampled,
            low_coverage=valid_pixel_pct < 30.0,
            ndvi_tile_url=_tile_url_from_map_id(ndvi_map_id),
            true_colour_tile_url=_tile_url_from_map_id(tc_map_id),
            tiles_expires_at=expires_at,
            scenes=scenes,
        )

    return execute_with_retry(_run)

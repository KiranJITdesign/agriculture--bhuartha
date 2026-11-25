"""ESA WorldCover class 40 cropland mask and pre-check service."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

import ee

from .exceptions import ServiceError, ServiceFailureCode
from .gee_service import execute_with_retry, init_gee
from .ndvi_service import WORLDCOVER_COLLECTION, WORLDCOVER_CROPLAND_CLASS

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class CroplandCoverage:
    """Cropland area and share within an AOI."""

    cropland_area_ha: float
    total_area_ha: float
    cropland_pct: float


def compute_cropland_coverage(geometry_geojson: dict[str, Any]) -> CroplandCoverage:
    """
    Compute ESA WorldCover class 40 cropland area (ha) using ee.Image.pixelArea().
    Raises ServiceError(NO_CROPLAND) when cropland area <= 0.
    """
    init_gee()

    def _run() -> CroplandCoverage:
        aoi = ee.Geometry(geometry_geojson)
        worldcover = ee.ImageCollection(WORLDCOVER_COLLECTION).first().clip(aoi)
        cropland_mask = worldcover.select("Map").eq(WORLDCOVER_CROPLAND_CLASS)

        pixel_area_ha = ee.Image.pixelArea().divide(10_000.0)
        total_ha = float(
            (
                pixel_area_ha.reduceRegion(
                    reducer=ee.Reducer.sum(), geometry=aoi, scale=10, maxPixels=1e9
                ).getInfo()
                or {}
            ).get("area", 0.0)
            or 0.0
        )
        cropland_ha = float(
            (
                pixel_area_ha.updateMask(cropland_mask)
                .reduceRegion(reducer=ee.Reducer.sum(), geometry=aoi, scale=10, maxPixels=1e9)
                .getInfo()
                or {}
            ).get("area", 0.0)
            or 0.0
        )
        if cropland_ha <= 0.0:
            raise ServiceError(
                ServiceFailureCode.NO_CROPLAND,
                "Selected boundary contains no ESA WorldCover class 40 cropland.",
            )
        pct = min(100.0, (cropland_ha / total_ha) * 100.0) if total_ha > 0 else 0.0
        return CroplandCoverage(
            cropland_area_ha=cropland_ha,
            total_area_ha=total_ha,
            cropland_pct=pct,
        )

    return execute_with_retry(_run)

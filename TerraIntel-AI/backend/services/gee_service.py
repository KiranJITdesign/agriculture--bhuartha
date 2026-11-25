"""Google Earth Engine initialization, retry with jitter, and scene lookup."""
from __future__ import annotations

import logging
import os
import random
import threading
import time
from collections.abc import Callable
from typing import Any, TypeVar

import ee

from .exceptions import ServiceError, ServiceFailureCode
from .stac_service import search_s2_stac_scenes

logger = logging.getLogger(__name__)

# Official GEE Sentinel-2 Surface Reflectance Harmonized collection:
# https://developers.google.com/earth-engine/datasets/catalog/COPERNICUS_S2_SR_HARMONIZED
S2_COLLECTION = "COPERNICUS/S2_SR_HARMONIZED"
GEE_TIMEOUT_SECONDS = 300

_T = TypeVar("_T")
_init_lock = threading.Lock()
_initialized = False


def init_gee(
    project_id: str | None = None,
    service_account_key: str | None = None,
) -> None:
    """Initialize Google Earth Engine once per process in a thread-safe manner."""
    global _initialized
    if _initialized:
        return

    with _init_lock:
        if _initialized:
            return
        proj = project_id or os.environ.get("GEE_PROJECT_ID") or None
        key_path = service_account_key or os.environ.get("GEE_SERVICE_ACCOUNT_KEY") or None
        try:
            if key_path:
                credentials = ee.ServiceAccountCredentials(email=None, key_file=key_path)
                ee.Initialize(credentials=credentials, project=proj)
            elif proj:
                ee.Initialize(project=proj)
            else:
                ee.Initialize()
            _initialized = True
            logger.info("Initialized Google Earth Engine (project=%s)", proj or "default")
        except Exception as exc:
            logger.exception("Failed to initialize Google Earth Engine")
            raise ServiceError(
                ServiceFailureCode.SATELLITE_UNAVAILABLE,
                f"Google Earth Engine initialization failed: {exc}",
            ) from exc


def _reset_gee_init_for_tests() -> None:
    """Reset init state (unit tests only)."""
    global _initialized
    with _init_lock:
        _initialized = False


def map_gee_error(exc: Exception) -> ServiceError:
    """Map an Earth Engine or transport exception to a closed-enum ServiceError."""
    if isinstance(exc, ServiceError):
        return exc
    msg = str(exc).lower()
    if "quota" in msg or "rate limit" in msg or "429" in msg or "too many requests" in msg:
        return ServiceError(ServiceFailureCode.QUOTA_EXCEEDED, str(exc))
    if "timeout" in msg or "timed out" in msg or "deadline" in msg or "504" in msg:
        return ServiceError(ServiceFailureCode.UPSTREAM_TIMEOUT, str(exc))
    return ServiceError(ServiceFailureCode.SATELLITE_UNAVAILABLE, str(exc))


def _is_retryable(err: ServiceError) -> bool:
    return err.code in {
        ServiceFailureCode.SATELLITE_UNAVAILABLE,
        ServiceFailureCode.UPSTREAM_TIMEOUT,
        ServiceFailureCode.QUOTA_EXCEEDED,
    }


def execute_with_retry(
    fn: Callable[[], _T],
    *,
    max_attempts: int = 3,
    base_delay_s: float = 1.0,
    max_delay_s: float = 16.0,
) -> _T:
    """Execute a GEE call with exponential backoff and full jitter."""
    last_error: ServiceError | None = None
    for attempt in range(1, max_attempts + 1):
        try:
            return fn()
        except Exception as exc:
            mapped = map_gee_error(exc)
            last_error = mapped
            if attempt >= max_attempts or not _is_retryable(mapped):
                raise mapped from exc
            cap = min(max_delay_s, base_delay_s * (2 ** (attempt - 1)))
            sleep_s = random.uniform(0.0, cap)
            logger.warning(
                "GEE call failed (attempt %d/%d, code=%s), retrying in %.2fs",
                attempt,
                max_attempts,
                mapped.code.value,
                sleep_s,
            )
            time.sleep(sleep_s)
    assert last_error is not None
    raise last_error


def list_recent_s2_scenes(
    geometry_geojson: dict[str, Any],
    start_date: str,
    end_date: str,
    limit: int = 3,
) -> list[dict[str, str]]:
    """
    Return up to `limit` most recent Sentinel-2 scene IDs and acquisition dates.
    Uses keyless Element84 Earth Search STAC when GEE_PROJECT_ID is unset.
    """
    provider = os.environ.get("SATELLITE_PROVIDER", "").lower()
    if provider == "stac" or (not provider and not os.environ.get("GEE_PROJECT_ID")):
        stac_scenes = search_s2_stac_scenes(
            geometry_geojson=geometry_geojson,
            start_date=start_date,
            end_date=end_date,
            limit=limit,
        )
        return [{"scene_id": s.scene_id, "acquired_at": s.acquired_at} for s in stac_scenes]

    init_gee()

    def _query() -> list[dict[str, str]]:
        aoi = ee.Geometry(geometry_geojson)
        collection = (
            ee.ImageCollection(S2_COLLECTION)
            .filterBounds(aoi)
            .filterDate(start_date, end_date)
            .sort("system:time_start", False)
            .limit(limit)
        )
        info = collection.getInfo()
        features = info.get("features", []) if isinstance(info, dict) else []
        scenes: list[dict[str, str]] = []
        for feat in features:
            props = feat.get("properties", {})
            scene_id = str(props.get("PRODUCT_ID") or feat.get("id") or "")
            ts_ms = props.get("system:time_start")
            acq_date = ""
            if isinstance(ts_ms, (int, float)):
                acq_date = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(ts_ms / 1000.0))
            scenes.append({"scene_id": scene_id, "acquired_at": acq_date})
        return scenes

    return execute_with_retry(_query)

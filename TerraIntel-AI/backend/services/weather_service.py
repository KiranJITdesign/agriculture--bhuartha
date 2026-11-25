"""NASA POWER daily rainfall and temperature service with 7-day cache and 5-year anomaly."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any

import requests

from .exceptions import ServiceError, ServiceFailureCode

logger = logging.getLogger(__name__)

# Official NASA POWER Temporal Daily Point API (Agroclimatology community):
# https://power.larc.nasa.gov/docs/services/api/temporal/daily/
NASA_POWER_URL = "https://power.larc.nasa.gov/api/temporal/daily/point"
NASA_POWER_TIMEOUT_SECONDS = 20
WEATHER_CACHE_TTL_SECONDS = 7 * 24 * 60 * 60
_FILL_VALUE = -999.0

# Simple process-local fallback cache when Django/Redis cache is unavailable
_local_cache: dict[str, tuple[float, WeatherSummary]] = {}


@dataclass(frozen=True)
class DailyWeatherPoint:
    date: str
    rainfall_mm: float
    temperature_c: float


@dataclass(frozen=True)
class WeatherSummary:
    region_id: str
    start_date: str
    end_date: str
    total_rainfall_mm: float
    mean_temperature_c: float
    baseline_rainfall_mm: float
    anomaly_pct: float | None
    anomaly_reason: str | None
    daily: list[DailyWeatherPoint]
    cached: bool = False


def _shift_year(d: date, years: int) -> date:
    try:
        return d.replace(year=d.year + years)
    except ValueError:
        # Feb 29 -> Feb 28
        return d.replace(year=d.year + years, day=28)


def _fetch_power_window(lat: float, lon: float, start: date, end: date) -> list[DailyWeatherPoint]:
    params = {
        "parameters": "PRECTOTCORR,T2M",
        "community": "AG",
        "longitude": f"{lon:.4f}",
        "latitude": f"{lat:.4f}",
        "start": start.strftime("%Y%m%d"),
        "end": end.strftime("%Y%m%d"),
        "format": "JSON",
    }
    try:
        resp = requests.get(NASA_POWER_URL, params=params, timeout=NASA_POWER_TIMEOUT_SECONDS)
        resp.raise_for_status()
        payload: dict[str, Any] = resp.json()
    except requests.Timeout as exc:
        raise ServiceError(
            ServiceFailureCode.UPSTREAM_TIMEOUT,
            "NASA POWER request timed out.",
        ) from exc
    except requests.RequestException as exc:
        raise ServiceError(
            ServiceFailureCode.SATELLITE_UNAVAILABLE,
            f"NASA POWER request failed: {exc}",
        ) from exc

    params_data = payload.get("properties", {}).get("parameter", {})
    rain_map: dict[str, float] = params_data.get("PRECTOTCORR", {})
    temp_map: dict[str, float] = params_data.get("T2M", {})

    points: list[DailyWeatherPoint] = []
    cur = start
    while cur <= end:
        key = cur.strftime("%Y%m%d")
        rain = float(rain_map.get(key, _FILL_VALUE))
        temp = float(temp_map.get(key, _FILL_VALUE))
        if rain > _FILL_VALUE and temp > _FILL_VALUE:
            points.append(
                DailyWeatherPoint(
                    date=cur.isoformat(),
                    rainfall_mm=max(0.0, rain),
                    temperature_c=temp,
                )
            )
        cur += timedelta(days=1)
    return points


def _cache_get(key: str) -> WeatherSummary | None:
    import time

    entry = _local_cache.get(key)
    if entry is None:
        return None
    expires_at, val = entry
    if time.monotonic() > expires_at:
        _local_cache.pop(key, None)
        return None
    return val


def _cache_set(key: str, val: WeatherSummary) -> None:
    import time

    _local_cache[key] = (time.monotonic() + WEATHER_CACHE_TTL_SECONDS, val)


def get_weather_summary(
    *,
    region_id: str,
    centroid_lat: float,
    centroid_lon: float,
    start_date: str,
    end_date: str,
) -> WeatherSummary:
    """Fetch NASA POWER weather summary + 5-year rainfall anomaly with 7-day cache."""
    cache_key = f"weather:{region_id}:{start_date}:{end_date}"
    cached = _cache_get(cache_key)
    if cached is not None:
        return WeatherSummary(
            region_id=cached.region_id,
            start_date=cached.start_date,
            end_date=cached.end_date,
            total_rainfall_mm=cached.total_rainfall_mm,
            mean_temperature_c=cached.mean_temperature_c,
            baseline_rainfall_mm=cached.baseline_rainfall_mm,
            anomaly_pct=cached.anomaly_pct,
            anomaly_reason=cached.anomaly_reason,
            daily=cached.daily,
            cached=True,
        )

    start_d = datetime.strptime(start_date, "%Y-%m-%d").date()
    end_d = datetime.strptime(end_date, "%Y-%m-%d").date()

    current_points = _fetch_power_window(centroid_lat, centroid_lon, start_d, end_d)
    total_rain = sum(p.rainfall_mm for p in current_points)
    mean_temp = (
        sum(p.temperature_c for p in current_points) / len(current_points)
        if current_points
        else 0.0
    )

    baseline_totals: list[float] = []
    for offset in range(1, 6):
        b_start = _shift_year(start_d, -offset)
        b_end = _shift_year(end_d, -offset)
        pts = _fetch_power_window(centroid_lat, centroid_lon, b_start, b_end)
        if pts:
            baseline_totals.append(sum(p.rainfall_mm for p in pts))

    baseline_mean = (
        sum(baseline_totals) / len(baseline_totals) if baseline_totals else 0.0
    )

    if baseline_mean <= 0.0:
        anomaly_pct: float | None = None
        anomaly_reason: str | None = "NO_BASELINE_RAIN"
    else:
        anomaly_pct = ((total_rain - baseline_mean) / baseline_mean) * 100.0
        anomaly_reason = None

    summary = WeatherSummary(
        region_id=region_id,
        start_date=start_date,
        end_date=end_date,
        total_rainfall_mm=total_rain,
        mean_temperature_c=mean_temp,
        baseline_rainfall_mm=baseline_mean,
        anomaly_pct=anomaly_pct,
        anomaly_reason=anomaly_reason,
        daily=current_points,
        cached=False,
    )
    _cache_set(cache_key, summary)
    return summary

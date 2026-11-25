"""Unit tests for weather_service (NASA POWER, 7-day cache, zero-baseline guard)."""
from unittest.mock import MagicMock, patch

from services.weather_service import _local_cache, get_weather_summary


def _mock_power_response(rain: float, temp: float) -> MagicMock:
    resp = MagicMock()
    resp.raise_for_status.return_value = None
    resp.json.return_value = {
        "properties": {
            "parameter": {
                "PRECTOTCORR": {
                    "20261001": rain,
                    "20261002": rain,
                    "20251001": rain,
                    "20251002": rain,
                    "20241001": rain,
                    "20241002": rain,
                    "20231001": rain,
                    "20231002": rain,
                    "20221001": rain,
                    "20221002": rain,
                    "20211001": rain,
                    "20211002": rain,
                },
                "T2M": {
                    "20261001": temp,
                    "20261002": temp,
                    "20251001": temp,
                    "20251002": temp,
                    "20241001": temp,
                    "20241002": temp,
                    "20231001": temp,
                    "20231002": temp,
                    "20221001": temp,
                    "20221002": temp,
                    "20211001": temp,
                    "20211002": temp,
                },
            }
        }
    }
    return resp


def test_weather_zero_baseline_guard_and_cache() -> None:
    _local_cache.clear()
    mock_resp = _mock_power_response(0.0, 26.5)
    with patch("services.weather_service.requests.get", return_value=mock_resp):
        res = get_weather_summary(
            region_id="reg-1",
            centroid_lat=20.0,
            centroid_lon=78.0,
            start_date="2026-10-01",
            end_date="2026-10-02",
        )
    assert res.anomaly_pct is None
    assert res.anomaly_reason == "NO_BASELINE_RAIN"
    assert res.total_rainfall_mm == 0.0
    assert res.mean_temperature_c == 26.5
    assert res.cached is False

    # Second call hits 7-day cache without network
    err = AssertionError("should not fetch")
    with patch("services.weather_service.requests.get", side_effect=err):
        res2 = get_weather_summary(
            region_id="reg-1",
            centroid_lat=20.0,
            centroid_lon=78.0,
            start_date="2026-10-01",
            end_date="2026-10-02",
        )
    assert res2.cached is True

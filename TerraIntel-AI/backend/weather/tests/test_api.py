"""Contract tests for /api/v1/weather/."""
from unittest.mock import patch

import pytest
from django.contrib.gis.geos import Polygon
from rest_framework.test import APIClient

from regions.models import AgriculturalRegion
from services.weather_service import DailyWeatherPoint, WeatherSummary


@pytest.mark.django_db
def test_weather_api_contract() -> None:
    region = AgriculturalRegion.objects.create(
        name="Weather Plot",
        boundary=Polygon(
            ((78.0, 20.0), (78.01, 20.0), (78.01, 20.01), (78.0, 20.01), (78.0, 20.0)), srid=4326
        ),
    )
    fake_summary = WeatherSummary(
        region_id=str(region.id),
        start_date="2026-10-01",
        end_date="2026-10-02",
        total_rainfall_mm=12.5,
        mean_temperature_c=24.3,
        baseline_rainfall_mm=10.0,
        anomaly_pct=25.0,
        anomaly_reason=None,
        daily=[
            DailyWeatherPoint(date="2026-10-01", rainfall_mm=5.0, temperature_c=24.1),
            DailyWeatherPoint(date="2026-10-02", rainfall_mm=7.5, temperature_c=24.5),
        ],
        cached=False,
    )
    client = APIClient()
    with patch("weather.views.get_weather_summary", return_value=fake_summary):
        resp = client.get(
            f"/api/v1/weather/?region={region.id}&start_date=2026-10-01&end_date=2026-10-02"
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_rainfall_mm"] == "12.50"
    assert data["mean_temperature_c"] == "24.30"
    assert data["anomaly_pct"] == "25.00"
    assert len(data["daily"]) == 2

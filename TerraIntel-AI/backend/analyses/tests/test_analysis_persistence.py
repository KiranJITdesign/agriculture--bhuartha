"""Tests for CropAnalysis persistence and 24-hour caching."""
import time
from unittest.mock import patch

import pytest
from django.contrib.gis.geos import Polygon
from rest_framework.test import APIClient

from analyses.models import CropAnalysis
from regions.models import AgriculturalRegion
from services.ndvi_service import NdviCompositeResult


@pytest.mark.django_db
def test_crop_analysis_persistence_and_24h_cache() -> None:
    region = AgriculturalRegion.objects.create(
        name="Cached Field",
        boundary=Polygon(
            ((0.0, 0.0), (0.01, 0.0), (0.01, 0.01), (0.0, 0.01), (0.0, 0.0)), srid=4326
        ),
    )
    fake_res = NdviCompositeResult(
        mean_ndvi=0.6123,
        p25_ndvi=0.4500,
        p50_ndvi=0.6200,
        p75_ndvi=0.7400,
        min_ndvi=0.1800,
        max_ndvi=0.8500,
        cropland_area_ha=100.0,
        valid_area_ha=92.5,
        valid_pixel_pct=92.5,
        anomalous_pixel_pct=0.5,
        sampled=False,
        low_coverage=False,
        ndvi_tile_url="https://earthengine.googleapis.com/tiles/{z}/{x}/{y}",
        true_colour_tile_url="https://earthengine.googleapis.com/tc/{z}/{x}/{y}",
        tiles_expires_at="2026-11-26T00:00:00Z",
        scenes=[{"scene_id": "S2A_MSIL2A_TEST", "acquired_at": "2026-11-01T00:00:00Z"}],
    )
    client = APIClient()
    payload = {"region": str(region.id), "start_date": "2026-10-01", "end_date": "2026-11-01"}

    with patch("analyses.tasks.compute_ndvi_analysis", return_value=fake_res):
        r1 = client.post("/api/v1/jobs/", payload, format="json")
    assert r1.status_code == 202
    assert CropAnalysis.objects.count() == 1

    t0 = time.perf_counter()
    r2 = client.post("/api/v1/jobs/", payload, format="json")
    elapsed_ms = (time.perf_counter() - t0) * 1000.0
    assert r2.status_code == 200
    assert r2.json()["cached"] is True
    assert r2.json()["analysis"]["mean_ndvi"] == "0.6123"
    assert elapsed_ms < 300.0

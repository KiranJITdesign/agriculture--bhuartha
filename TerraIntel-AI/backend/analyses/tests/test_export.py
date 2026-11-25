"""Tests for low-vigour GeoJSON export (<= 5 MB)."""
import json
import math
from decimal import Decimal

import pytest
from django.contrib.gis.geos import Polygon
from django.utils import timezone
from rest_framework.test import APIClient

from analyses.models import AnalysisJob, CropAnalysis, JobStatus, LowVigourZone
from regions.models import AgriculturalRegion
from services.export_service import MAX_GEOJSON_BYTES, build_low_vigour_geojson


def test_build_low_vigour_geojson_simplifies_to_under_5mb() -> None:
    pts = [
        [0.01 * math.cos(2 * math.pi * i / 1000), 0.01 * math.sin(2 * math.pi * i / 1000)]
        for i in range(1000)
    ]
    pts.append(pts[0])
    payload = build_low_vigour_geojson(
        [{"geometry": {"type": "Polygon", "coordinates": [pts]}, "properties": {"area_ha": "1.20"}}]
    )
    assert len(payload) <= MAX_GEOJSON_BYTES
    fc = json.loads(payload)
    assert fc["type"] == "FeatureCollection"
    assert len(fc["features"]) == 1


@pytest.mark.django_db
def test_low_vigour_export_endpoint() -> None:
    poly = Polygon(((0.0, 0.0), (0.01, 0.0), (0.01, 0.01), (0.0, 0.01), (0.0, 0.0)), srid=4326)
    region = AgriculturalRegion.objects.create(name="Export Plot", boundary=poly)
    job = AnalysisJob.objects.create(
        region=region, start_date="2026-10-01", end_date="2026-11-01", status=JobStatus.SUCCEEDED
    )
    analysis = CropAnalysis.objects.create(
        job=job,
        region=region,
        start_date="2026-10-01",
        end_date="2026-11-01",
        mean_ndvi=Decimal("0.4500"),
        p25_ndvi=Decimal("0.2500"),
        p50_ndvi=Decimal("0.4500"),
        p75_ndvi=Decimal("0.6000"),
        min_ndvi=Decimal("0.1000"),
        max_ndvi=Decimal("0.7500"),
        cropland_area_ha=Decimal("100.00"),
        valid_area_ha=Decimal("90.00"),
        valid_pixel_pct=Decimal("90.00"),
        tiles_expires_at=timezone.now(),
    )
    LowVigourZone.objects.create(analysis=analysis, geometry=poly, area_ha=Decimal("5.00"))
    client = APIClient()
    resp = client.get(f"/api/v1/analyses/{analysis.id}/low-vigour.geojson")
    assert resp.status_code == 200
    assert len(resp.content) <= MAX_GEOJSON_BYTES
    assert resp.json()["features"][0]["properties"]["area_ha"] == "5.00"

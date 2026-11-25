"""Integration tests for /api/v1/compare/."""
from unittest.mock import patch

import pytest
from django.contrib.gis.geos import Polygon
from rest_framework.test import APIClient

from analysis.comparison import DeltaNdviBin
from regions.models import AgriculturalRegion
from services.comparison_service import ComparisonResult


@pytest.mark.django_db
def test_compare_endpoint_returns_bins_summing_to_100_pct() -> None:
    region = AgriculturalRegion.objects.create(
        name="Compare Plot",
        boundary=Polygon(
            ((0.0, 0.0), (0.01, 0.0), (0.01, 0.01), (0.0, 0.01), (0.0, 0.0)), srid=4326
        ),
    )
    fake_res = ComparisonResult(
        mean_delta_ndvi=0.075,
        analysed_area_ha=100.0,
        diff_tile_url="https://earthengine.googleapis.com/diff/{z}/{x}/{y}",
        tiles_expires_at="2026-11-26T00:00:00Z",
        bins=[
            DeltaNdviBin(bin_min=0.05, bin_max=0.10, area_ha=100.0, area_pct=100.0),
        ],
    )
    client = APIClient()
    with patch("analyses.views.compare_ndvi_periods", return_value=fake_res):
        resp = client.post(
            "/api/v1/compare/",
            {
                "region": str(region.id),
                "period_a_start": "2026-09-01",
                "period_a_end": "2026-09-30",
                "period_b_start": "2026-10-01",
                "period_b_end": "2026-10-31",
            },
            format="json",
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["mean_delta_ndvi"] == "0.0750"
    assert sum(float(b["area_pct"]) for b in data["bins"]) == pytest.approx(100.0)

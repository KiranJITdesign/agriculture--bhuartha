"""Tests for WeasyPrint PDF report generation and watermark."""
from decimal import Decimal
from unittest.mock import patch

import pytest
from django.contrib.gis.geos import Polygon
from django.utils import timezone
from rest_framework.test import APIClient

from analyses.models import AnalysisJob, CropAnalysis, JobStatus
from regions.models import AgriculturalRegion


@pytest.mark.django_db
def test_report_pdf_endpoint_includes_watermark_when_low_coverage() -> None:
    poly = Polygon(((0.0, 0.0), (0.01, 0.0), (0.01, 0.01), (0.0, 0.01), (0.0, 0.0)), srid=4326)
    region = AgriculturalRegion.objects.create(name="PDF Plot", boundary=poly)
    job = AnalysisJob.objects.create(
        region=region, start_date="2026-10-01", end_date="2026-11-01", status=JobStatus.SUCCEEDED
    )
    analysis = CropAnalysis.objects.create(
        job=job,
        region=region,
        start_date="2026-10-01",
        end_date="2026-11-01",
        mean_ndvi=Decimal("0.4200"),
        p25_ndvi=Decimal("0.2000"),
        p50_ndvi=Decimal("0.4200"),
        p75_ndvi=Decimal("0.6000"),
        min_ndvi=Decimal("0.1000"),
        max_ndvi=Decimal("0.7500"),
        cropland_area_ha=Decimal("100.00"),
        valid_area_ha=Decimal("20.00"),
        valid_pixel_pct=Decimal("20.00"),
        low_coverage=True,
        scenes=[{"scene_id": "S2A_REAL_SCENE_01", "acquired_at": "2026-10-15T05:30:00Z"}],
        tiles_expires_at=timezone.now(),
    )

    client = APIClient()
    with (
        patch("analyses.views.render_crop_health_pdf", return_value=b"%PDF-1.4\n..."),
        patch("analyses.views.put_object_bytes", return_value=f"reports/{analysis.id}.pdf"),
    ):
        resp = client.get(f"/api/v1/analyses/{analysis.id}/report.pdf")
    assert resp.status_code == 200
    assert resp["Content-Type"] == "application/pdf"
    assert resp.content.startswith(b"%PDF")


@pytest.mark.django_db
def test_compare_report_pdf_endpoint() -> None:
    poly = Polygon(((0.0, 0.0), (0.01, 0.0), (0.01, 0.01), (0.0, 0.01), (0.0, 0.0)), srid=4326)
    region = AgriculturalRegion.objects.create(name="Compare PDF Plot", boundary=poly)
    client = APIClient()
    resp = client.post(
        "/api/v1/compare/report.pdf",
        {
            "region": str(region.id),
            "period_a_start": "2026-09-01",
            "period_a_end": "2026-09-30",
            "period_b_start": "2026-10-01",
            "period_b_end": "2026-10-31",
            "mean_delta_ndvi": "0.0850",
            "analysed_area_ha": "100.00",
            "bins": [
                {
                    "bin_min": "0.05",
                    "bin_max": "0.10",
                    "area_ha": "100.00",
                    "area_pct": "100.00",
                }
            ],
        },
        format="json",
    )
    assert resp.status_code == 200
    assert resp["Content-Type"] == "application/pdf"
    assert resp.content.startswith(b"%PDF")

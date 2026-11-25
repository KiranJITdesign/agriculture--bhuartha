"""Tests for AnalysisJob submission, polling, and failure_code handling."""
from unittest.mock import patch

import pytest
from django.contrib.gis.geos import Polygon
from rest_framework.test import APIClient

from analyses.models import AnalysisJob, JobStatus
from regions.models import AgriculturalRegion
from services.exceptions import ServiceError, ServiceFailureCode
from services.ndvi_service import NdviCompositeResult


@pytest.mark.django_db
def test_submit_and_poll_job_success() -> None:
    region = AgriculturalRegion.objects.create(
        name="Plot A",
        boundary=Polygon(
            ((0.0, 0.0), (0.01, 0.0), (0.01, 0.01), (0.0, 0.01), (0.0, 0.0)), srid=4326
        ),
    )
    fake_res = NdviCompositeResult(
        mean_ndvi=0.55,
        p25_ndvi=0.40,
        p50_ndvi=0.56,
        p75_ndvi=0.68,
        min_ndvi=0.12,
        max_ndvi=0.82,
        cropland_area_ha=100.0,
        valid_area_ha=95.0,
        valid_pixel_pct=95.0,
        anomalous_pixel_pct=0.0,
        sampled=False,
        low_coverage=False,
        ndvi_tile_url="https://earthengine.googleapis.com/tiles/{z}/{x}/{y}",
        true_colour_tile_url="https://earthengine.googleapis.com/tc/{z}/{x}/{y}",
        tiles_expires_at="2026-11-26T00:00:00Z",
        scenes=[{"scene_id": "S2A_TEST", "acquired_at": "2026-11-01T00:00:00Z"}],
    )
    client = APIClient()
    with patch("analyses.tasks.compute_ndvi_analysis", return_value=fake_res):
        resp = client.post(
            "/api/v1/jobs/",
            {"region": str(region.id), "start_date": "2026-10-01", "end_date": "2026-11-01"},
            format="json",
        )
    assert resp.status_code == 202
    job_id = resp.json()["id"]
    poll = client.get(f"/api/v1/jobs/{job_id}/")
    assert poll.status_code == 200
    assert poll.json()["status"] == JobStatus.SUCCEEDED
    assert poll.json()["progress_pct"] == 100


@pytest.mark.django_db
def test_job_failure_records_failure_code() -> None:
    region = AgriculturalRegion.objects.create(
        name="Plot B",
        boundary=Polygon(
            ((0.0, 0.0), (0.01, 0.0), (0.01, 0.01), (0.0, 0.01), (0.0, 0.0)), srid=4326
        ),
    )
    client = APIClient()
    with patch(
        "analyses.tasks.compute_ndvi_analysis",
        side_effect=ServiceError(ServiceFailureCode.NO_SCENES_FOUND, "No scenes"),
    ):
        resp = client.post(
            "/api/v1/jobs/",
            {"region": str(region.id), "start_date": "2026-10-01", "end_date": "2026-11-01"},
            format="json",
        )
    assert resp.status_code == 202
    job = AnalysisJob.objects.get(id=resp.json()["id"])
    assert job.status == JobStatus.FAILED
    assert job.failure_code == "NO_SCENES_FOUND"

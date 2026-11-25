"""AnalysisJob model for tracking async Sentinel-2 processing."""
from __future__ import annotations

import uuid

from django.contrib.gis.db import models


class JobStatus(models.TextChoices):
    PENDING = "PENDING", "Pending"
    RUNNING = "RUNNING", "Running"
    SUCCEEDED = "SUCCEEDED", "Succeeded"
    FAILED = "FAILED", "Failed"


class AnalysisJob(models.Model):
    """Tracks asynchronous crop health analysis execution."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    region = models.ForeignKey(
        "regions.AgriculturalRegion",
        on_delete=models.CASCADE,
        related_name="analysis_jobs",
    )
    start_date = models.DateField()
    end_date = models.DateField()
    status = models.CharField(max_length=16, choices=JobStatus.choices, default=JobStatus.PENDING)
    stage = models.CharField(max_length=32, default="QUEUED")
    progress_pct = models.PositiveSmallIntegerField(default=0)
    failure_code = models.CharField(max_length=40, blank=True, default="")
    failure_detail = models.TextField(blank=True, default="")
    celery_task_id = models.CharField(max_length=255, blank=True, default="")
    trace_id = models.CharField(max_length=64, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Job {self.id} ({self.status})"


class CropAnalysis(models.Model):
    """Persisted cropland-scoped NDVI analysis with thresholds and provenance."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    job = models.OneToOneField(AnalysisJob, on_delete=models.CASCADE, related_name="analysis")
    region = models.ForeignKey(
        "regions.AgriculturalRegion",
        on_delete=models.CASCADE,
        related_name="analyses",
    )
    start_date = models.DateField()
    end_date = models.DateField()

    mean_ndvi = models.DecimalField(max_digits=6, decimal_places=4)
    p25_ndvi = models.DecimalField(max_digits=6, decimal_places=4)
    p50_ndvi = models.DecimalField(max_digits=6, decimal_places=4)
    p75_ndvi = models.DecimalField(max_digits=6, decimal_places=4)
    min_ndvi = models.DecimalField(max_digits=6, decimal_places=4)
    max_ndvi = models.DecimalField(max_digits=6, decimal_places=4)

    low_threshold = models.DecimalField(max_digits=6, decimal_places=4, default=0.2000)
    moderate_threshold = models.DecimalField(max_digits=6, decimal_places=4, default=0.4500)
    high_threshold = models.DecimalField(max_digits=6, decimal_places=4, default=0.7000)

    cropland_area_ha = models.DecimalField(max_digits=12, decimal_places=2)
    valid_area_ha = models.DecimalField(max_digits=12, decimal_places=2)
    absolute_low_area_ha = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    relative_low_area_ha = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    valid_pixel_pct = models.DecimalField(max_digits=5, decimal_places=2)
    anomalous_pixel_pct = models.DecimalField(max_digits=5, decimal_places=2, default=0)

    sampled = models.BooleanField(default=False)
    low_coverage = models.BooleanField(default=False)

    ndvi_tile_url = models.TextField(blank=True, default="")
    true_colour_tile_url = models.TextField(blank=True, default="")
    tiles_expires_at = models.DateTimeField()

    scenes = models.JSONField(default=list)
    raster_object_key = models.CharField(max_length=512, blank=True, default="")
    report_object_key = models.CharField(max_length=512, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["region", "start_date", "end_date", "-created_at"]),
        ]

    def __str__(self) -> str:
        return f"Analysis {self.id} ({self.region.name} {self.start_date}..{self.end_date})"


class VegetationClassStat(models.Model):
    """Per-vigour-class areal breakdown for a CropAnalysis."""

    analysis = models.ForeignKey(
        CropAnalysis,
        on_delete=models.CASCADE,
        related_name="class_stats",
    )
    vigour_class = models.CharField(max_length=16)
    area_ha = models.DecimalField(max_digits=12, decimal_places=2)
    area_pct = models.DecimalField(max_digits=5, decimal_places=2)

    class Meta:
        unique_together = [("analysis", "vigour_class")]
        ordering = ["vigour_class"]


class LowVigourZone(models.Model):
    """Polygonized low-vigour field inspection candidate in PostGIS."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    analysis = models.ForeignKey(
        CropAnalysis,
        on_delete=models.CASCADE,
        related_name="low_vigour_zones",
    )
    zone_type = models.CharField(max_length=16, default="RELATIVE")
    geometry = models.PolygonField(srid=4326)
    area_ha = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        ordering = ["-area_ha"]


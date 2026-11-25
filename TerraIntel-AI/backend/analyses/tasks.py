"""Celery tasks for async NDVI analysis."""
from __future__ import annotations

import json
import logging
from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal

from celery import shared_task
from celery.exceptions import SoftTimeLimitExceeded
from django.contrib.gis.geos import GEOSGeometry

from analysis.classification import VigourThresholds
from services.exceptions import ServiceError, ServiceFailureCode
from services.ndvi_service import compute_ndvi_analysis

from .models import AnalysisJob, CropAnalysis, JobStatus, LowVigourZone, VegetationClassStat

logger = logging.getLogger(__name__)


def _dec(val: float, places: int) -> Decimal:
    quant = Decimal(f"1e-{places}")
    return Decimal(str(val)).quantize(quant, rounding=ROUND_HALF_UP)


@shared_task(bind=True, soft_time_limit=300, time_limit=330)
def run_ndvi_analysis_task(self: object, job_id: str) -> str:
    """Execute Sentinel-2 NDVI analysis for an AnalysisJob with stage updates."""
    job = AnalysisJob.objects.select_related("region").get(id=job_id)
    job.status = JobStatus.RUNNING
    job.stage = "MASKING"
    job.progress_pct = 20
    job.save(update_fields=["status", "stage", "progress_pct", "updated_at"])

    try:
        geometry_geojson = json.loads(job.region.boundary.geojson)
        job.stage = "COMPUTING_NDVI"
        job.progress_pct = 50
        job.save(update_fields=["stage", "progress_pct", "updated_at"])

        result = compute_ndvi_analysis(
            geometry_geojson=geometry_geojson,
            start_date=job.start_date.isoformat(),
            end_date=job.end_date.isoformat(),
        )

        job.stage = "PERSISTING"
        job.progress_pct = 85
        job.save(update_fields=["stage", "progress_pct", "updated_at"])

        thresholds = VigourThresholds()
        expires_dt = datetime.fromisoformat(result.tiles_expires_at.replace("Z", "+00:00"))
        analysis = CropAnalysis.objects.create(
            job=job,
            region=job.region,
            start_date=job.start_date,
            end_date=job.end_date,
            mean_ndvi=_dec(result.mean_ndvi, 4),
            p25_ndvi=_dec(result.p25_ndvi, 4),
            p50_ndvi=_dec(result.p50_ndvi, 4),
            p75_ndvi=_dec(result.p75_ndvi, 4),
            min_ndvi=_dec(result.min_ndvi, 4),
            max_ndvi=_dec(result.max_ndvi, 4),
            low_threshold=_dec(thresholds.low_max, 4),
            moderate_threshold=_dec(thresholds.moderate_max, 4),
            high_threshold=_dec(thresholds.high_max, 4),
            cropland_area_ha=_dec(result.cropland_area_ha, 2),
            valid_area_ha=_dec(result.valid_area_ha, 2),
            absolute_low_area_ha=_dec(result.absolute_low_area_ha, 2),
            relative_low_area_ha=_dec(result.relative_low_area_ha, 2),
            valid_pixel_pct=_dec(result.valid_pixel_pct, 2),
            anomalous_pixel_pct=_dec(result.anomalous_pixel_pct, 2),
            sampled=result.sampled,
            low_coverage=result.low_coverage,
            ndvi_tile_url=result.ndvi_tile_url,
            true_colour_tile_url=result.true_colour_tile_url,
            tiles_expires_at=expires_dt,
            scenes=result.scenes,
        )
        stats_rows = result.class_stats or [
            {"vigour_class": c, "area_ha": 0.0, "area_pct": 0.0}
            for c in ("LOW", "MODERATE", "HIGH", "VERY_HIGH")
        ]
        VegetationClassStat.objects.bulk_create(
            [
                VegetationClassStat(
                    analysis=analysis,
                    vigour_class=str(row["vigour_class"]),
                    area_ha=_dec(float(row["area_ha"]), 2),
                    area_pct=_dec(float(row["area_pct"]), 2),
                )
                for row in stats_rows
            ]
        )

        if result.low_zone_polygons:
            zone_objs = []
            for item in result.low_zone_polygons:
                geom = GEOSGeometry(json.dumps(item["geometry"]), srid=4326)
                if geom.geom_type == "Polygon":
                    zone_objs.append(
                        LowVigourZone(
                            analysis=analysis,
                            zone_type="RELATIVE",
                            geometry=geom,
                            area_ha=_dec(float(item["area_ha"]), 2),
                        )
                    )
            if zone_objs:
                LowVigourZone.objects.bulk_create(zone_objs)

        job.stage = "DONE"
        job.progress_pct = 100
        job.status = JobStatus.SUCCEEDED
        job.save(update_fields=["stage", "progress_pct", "status", "updated_at"])
        return str(job.id)
    except ServiceError as exc:
        logger.warning("Analysis job %s failed with %s: %s", job.id, exc.code.value, exc.message)
        job.status = JobStatus.FAILED
        job.failure_code = exc.code.value
        job.failure_detail = exc.message
        job.save(update_fields=["status", "failure_code", "failure_detail", "updated_at"])
        return str(job.id)
    except SoftTimeLimitExceeded as exc:
        logger.error("Analysis job %s exceeded time limit", job.id)
        job.status = JobStatus.FAILED
        job.failure_code = ServiceFailureCode.UPSTREAM_TIMEOUT.value
        job.failure_detail = "Analysis exceeded 300s time limit."
        job.save(update_fields=["status", "failure_code", "failure_detail", "updated_at"])
        raise exc
    except Exception as exc:
        logger.exception("Analysis job %s crashed unexpectedly", job.id)
        job.status = JobStatus.FAILED
        job.failure_code = ServiceFailureCode.SATELLITE_UNAVAILABLE.value
        job.failure_detail = str(exc)
        job.save(update_fields=["status", "failure_code", "failure_detail", "updated_at"])
        raise

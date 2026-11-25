"""Core HTTP views."""
from __future__ import annotations

import logging
import os
from typing import Any

import boto3
import redis
from botocore.exceptions import BotoCoreError, ClientError
from django.conf import settings
from django.db import connections
from django.db.utils import OperationalError
from django.http import HttpRequest, JsonResponse

logger = logging.getLogger(__name__)


def health_check(request: HttpRequest) -> JsonResponse:
    """Return service and dependency connectivity status."""
    deps: dict[str, str] = {}
    healthy = True

    try:
        engine = settings.DATABASES["default"]["ENGINE"]
        with connections["default"].cursor() as cursor:
            if "spatialite" in engine:
                cursor.execute("SELECT spatialite_version();")
            else:
                cursor.execute("SELECT PostGIS_Version();")
            cursor.fetchone()
        deps["postgres_postgis"] = "ok"
    except OperationalError as exc:
        logger.warning("Postgres/PostGIS health check failed: %s", exc)
        deps["postgres_postgis"] = "error"
        healthy = False

    if getattr(settings, "CELERY_TASK_ALWAYS_EAGER", False):
        deps["redis"] = "ok (eager)"
    else:
        try:
            client = redis.Redis.from_url(settings.CELERY_BROKER_URL, socket_connect_timeout=2)
            client.ping()
            deps["redis"] = "ok"
        except redis.RedisError as exc:
            logger.warning("Redis health check failed: %s", exc)
            deps["redis"] = "error"
            healthy = False

    if not os.environ.get("S3_ENDPOINT_URL"):
        deps["storage"] = "ok (local)"
    else:
        try:
            s3 = boto3.client(
                "s3",
                endpoint_url=settings.S3_ENDPOINT_URL,
                aws_access_key_id=settings.S3_ACCESS_KEY_ID,
                aws_secret_access_key=settings.S3_SECRET_ACCESS_KEY,
                region_name=settings.S3_REGION_NAME,
            )
            s3.list_buckets()
            deps["minio"] = "ok"
        except (BotoCoreError, ClientError) as exc:
            logger.warning("MinIO/S3 health check failed: %s", exc)
            deps["minio"] = "error"
            healthy = False

    payload: dict[str, Any] = {
        "status": "ok" if healthy else "degraded",
        "trace_id": getattr(request, "trace_id", ""),
        "dependencies": deps,
    }
    return JsonResponse(payload, status=200 if healthy else 503)

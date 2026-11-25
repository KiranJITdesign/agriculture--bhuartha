"""Object storage service: local filesystem fallback or S3/MinIO via boto3."""
from __future__ import annotations

import logging
import os
from pathlib import Path

import boto3
from botocore.exceptions import BotoCoreError, ClientError

from .exceptions import ServiceError, ServiceFailureCode

logger = logging.getLogger(__name__)
LOCAL_MEDIA_ROOT = Path(__file__).resolve().parent.parent / "media"


def _use_s3() -> bool:
    return bool(os.environ.get("S3_ENDPOINT_URL"))


def _s3_client():
    return boto3.client(
        "s3",
        endpoint_url=os.environ.get("S3_ENDPOINT_URL", "http://localhost:9000"),
        aws_access_key_id=os.environ.get("MINIO_ROOT_USER", "minioadmin"),
        aws_secret_access_key=os.environ.get("MINIO_ROOT_PASSWORD", "minioadmin"),
        region_name=os.environ.get("S3_REGION_NAME", "us-east-1"),
    )


def ensure_bucket(bucket: str | None = None) -> str:
    """Ensure the target S3/MinIO bucket exists."""
    target = bucket or os.environ.get("S3_BUCKET_NAME", "terraintel-artifacts")
    client = _s3_client()
    try:
        client.head_bucket(Bucket=target)
    except ClientError:
        client.create_bucket(Bucket=target)
    return target


def put_object_bytes(key: str, data: bytes, content_type: str) -> str:
    """Upload bytes to local media storage or MinIO/S3 and return the object key."""
    if not _use_s3():
        dest = LOCAL_MEDIA_ROOT / key
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
        return key

    bucket = os.environ.get("S3_BUCKET_NAME", "terraintel-artifacts")
    try:
        client = _s3_client()
        ensure_bucket(bucket)
        client.put_object(Bucket=bucket, Key=key, Body=data, ContentType=content_type)
        return key
    except (BotoCoreError, ClientError) as exc:
        logger.exception("Failed to upload object %s to bucket %s", key, bucket)
        raise ServiceError(
            ServiceFailureCode.SATELLITE_UNAVAILABLE,
            f"Object storage upload failed: {exc}",
        ) from exc


def get_object_bytes(key: str) -> bytes:
    """Download bytes from local media storage or MinIO/S3."""
    if not _use_s3():
        src = LOCAL_MEDIA_ROOT / key
        if not src.exists():
            raise ServiceError(
                ServiceFailureCode.SATELLITE_UNAVAILABLE,
                f"Local artifact not found: {key}",
            )
        return src.read_bytes()

    bucket = os.environ.get("S3_BUCKET_NAME", "terraintel-artifacts")
    try:
        client = _s3_client()
        resp = client.get_object(Bucket=bucket, Key=key)
        return bytes(resp["Body"].read())
    except (BotoCoreError, ClientError) as exc:
        logger.exception("Failed to download object %s", key)
        raise ServiceError(
            ServiceFailureCode.SATELLITE_UNAVAILABLE,
            f"Object storage download failed: {exc}",
        ) from exc

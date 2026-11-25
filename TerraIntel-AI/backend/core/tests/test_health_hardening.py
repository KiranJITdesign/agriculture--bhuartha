"""Tests for deep /health/ degradation, trace_id propagation, and JSON logging."""
import json
import logging
from unittest.mock import patch

import redis
from django.test import Client, override_settings

from core.logging import JsonLogFormatter, set_trace_id


def test_json_log_formatter_includes_trace_id() -> None:
    set_trace_id("trace-abc-123")
    record = logging.LogRecord(
        name="terraintel",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="hello",
        args=(),
        exc_info=None,
    )
    parsed = json.loads(JsonLogFormatter().format(record))
    assert parsed["trace_id"] == "trace-abc-123"
    assert parsed["message"] == "hello"


@override_settings(CELERY_TASK_ALWAYS_EAGER=False)
def test_health_degrades_503_when_redis_down() -> None:
    client = Client()
    with (
        patch("core.views.connections"),
        patch("core.views.redis.Redis.from_url") as mock_redis,
        patch("core.views.boto3.client"),
    ):
        mock_redis.return_value.ping.side_effect = redis.RedisError("Connection refused")
        resp = client.get("/health/", HTTP_X_TRACE_ID="chaos-trace-1")
    assert resp.status_code == 503
    data = resp.json()
    assert data["status"] == "degraded"
    assert data["dependencies"]["redis"] == "error"
    assert data["trace_id"] == "chaos-trace-1"
    assert resp["X-Trace-ID"] == "chaos-trace-1"

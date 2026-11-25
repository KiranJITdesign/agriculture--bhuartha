"""Unit tests for gee_service."""
from unittest.mock import MagicMock, patch

import pytest

from services.exceptions import ServiceError, ServiceFailureCode
from services.gee_service import (
    _reset_gee_init_for_tests,
    execute_with_retry,
    init_gee,
    map_gee_error,
)


def test_init_once_per_process() -> None:
    _reset_gee_init_for_tests()
    with patch("services.gee_service.ee.Initialize") as mock_init:
        init_gee(project_id="test-proj")
        init_gee(project_id="test-proj")
        assert mock_init.call_count == 1
    _reset_gee_init_for_tests()


def test_map_gee_error_codes() -> None:
    q = map_gee_error(RuntimeError("Quota exceeded 429"))
    assert q.code == ServiceFailureCode.QUOTA_EXCEEDED
    t = map_gee_error(RuntimeError("Request timed out"))
    assert t.code == ServiceFailureCode.UPSTREAM_TIMEOUT
    s = map_gee_error(RuntimeError("Backend down"))
    assert s.code == ServiceFailureCode.SATELLITE_UNAVAILABLE


def test_execute_with_retry_succeeds_after_transient_error() -> None:
    fn = MagicMock(side_effect=[RuntimeError("504 timeout"), "ok"])
    with patch("services.gee_service.time.sleep"):
        assert execute_with_retry(fn, max_attempts=3, base_delay_s=0.01) == "ok"
    assert fn.call_count == 2


def test_execute_with_retry_raises_after_max_attempts() -> None:
    fn = MagicMock(side_effect=RuntimeError("Quota exceeded"))
    with patch("services.gee_service.time.sleep"):
        with pytest.raises(ServiceError) as exc_info:
            execute_with_retry(fn, max_attempts=2, base_delay_s=0.01)
    assert exc_info.value.code == ServiceFailureCode.QUOTA_EXCEEDED

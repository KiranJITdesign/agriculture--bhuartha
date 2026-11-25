"""RFC 9457 problem+json error handling and closed-enum failure codes."""
from __future__ import annotations

import uuid
from enum import StrEnum
from typing import Any

from rest_framework import status
from rest_framework.exceptions import APIException, ValidationError
from rest_framework.response import Response
from rest_framework.views import exception_handler


class FailureCode(StrEnum):
    SATELLITE_UNAVAILABLE = "SATELLITE_UNAVAILABLE"
    NO_SCENES_FOUND = "NO_SCENES_FOUND"
    NO_CROPLAND = "NO_CROPLAND"
    UPSTREAM_TIMEOUT = "UPSTREAM_TIMEOUT"
    BOUNDARY_TOO_LARGE = "BOUNDARY_TOO_LARGE"
    BOUNDARY_INVALID = "BOUNDARY_INVALID"
    QUOTA_EXCEEDED = "QUOTA_EXCEEDED"


FAILURE_STATUS_MAP: dict[FailureCode, int] = {
    FailureCode.SATELLITE_UNAVAILABLE: status.HTTP_503_SERVICE_UNAVAILABLE,
    FailureCode.NO_SCENES_FOUND: status.HTTP_422_UNPROCESSABLE_ENTITY,
    FailureCode.NO_CROPLAND: status.HTTP_422_UNPROCESSABLE_ENTITY,
    FailureCode.UPSTREAM_TIMEOUT: status.HTTP_504_GATEWAY_TIMEOUT,
    FailureCode.BOUNDARY_TOO_LARGE: status.HTTP_400_BAD_REQUEST,
    FailureCode.BOUNDARY_INVALID: status.HTTP_400_BAD_REQUEST,
    FailureCode.QUOTA_EXCEEDED: status.HTTP_429_TOO_MANY_REQUESTS,
}


class DomainFailure(APIException):
    """Domain exception mapped to RFC 9457 application/problem+json."""

    def __init__(self, code: FailureCode, detail: str, status_code: int | None = None) -> None:
        self.failure_code = code
        self.status_code = status_code or FAILURE_STATUS_MAP[code]
        super().__init__(detail=detail, code=code.value)


def problem_response(
    *,
    code: str,
    title: str,
    detail: Any,
    status_code: int,
    trace_id: str | None = None,
) -> Response:
    """Build an RFC 9457 application/problem+json Response."""
    tid = trace_id or str(uuid.uuid4())
    payload = {
        "type": f"https://terraintel.local/errors/{code.lower()}",
        "title": title,
        "status": status_code,
        "detail": detail,
        "code": code,
        "trace_id": tid,
    }
    return Response(payload, status=status_code, content_type="application/problem+json")


def custom_exception_handler(exc: Exception, context: dict[str, Any]) -> Response | None:
    """Map DomainFailure and DRF exceptions into RFC 9457 problem+json."""
    request = context.get("request")
    trace_id = getattr(request, "trace_id", None) if request is not None else None

    if isinstance(exc, DomainFailure):
        return problem_response(
            code=exc.failure_code.value,
            title=exc.failure_code.value.replace("_", " ").title(),
            detail=str(exc.detail),
            status_code=exc.status_code,
            trace_id=trace_id,
        )

    response = exception_handler(exc, context)
    if response is None:
        return None

    code = "VALIDATION_ERROR" if isinstance(exc, ValidationError) else "API_ERROR"
    return problem_response(
        code=code,
        title=code.replace("_", " ").title(),
        detail=response.data,
        status_code=response.status_code,
        trace_id=trace_id,
    )

"""HTTP middleware for trace_id propagation."""
from __future__ import annotations

import uuid
from collections.abc import Callable

from django.http import HttpRequest, HttpResponse

from .logging import set_trace_id


class TraceIdMiddleware:
    """Attach X-Trace-ID to request, log context, and response headers."""

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        trace_id = request.headers.get("X-Trace-ID") or str(uuid.uuid4())
        request.trace_id = trace_id  # type: ignore[attr-defined]
        set_trace_id(trace_id)
        response = self.get_response(request)
        response["X-Trace-ID"] = trace_id
        return response

"""Service-layer domain exceptions mapped to closed-enum failure codes."""
from __future__ import annotations

from enum import StrEnum


class ServiceFailureCode(StrEnum):
    SATELLITE_UNAVAILABLE = "SATELLITE_UNAVAILABLE"
    NO_SCENES_FOUND = "NO_SCENES_FOUND"
    NO_CROPLAND = "NO_CROPLAND"
    UPSTREAM_TIMEOUT = "UPSTREAM_TIMEOUT"
    BOUNDARY_TOO_LARGE = "BOUNDARY_TOO_LARGE"
    BOUNDARY_INVALID = "BOUNDARY_INVALID"
    QUOTA_EXCEEDED = "QUOTA_EXCEEDED"


class ServiceError(Exception):
    """Base exception raised by services/ with a closed-enum failure code."""

    def __init__(self, code: ServiceFailureCode, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(message)

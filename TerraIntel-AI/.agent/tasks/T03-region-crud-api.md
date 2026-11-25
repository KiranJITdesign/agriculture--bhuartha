# T03 — Region CRUD API + serializer validation + tests

## Goal
Implement `/api/v1/regions/` CRUD endpoints with DRF serializer validation: simplify geometries to ≤500 vertices, enforce area 0.1–50,000 ha, map invalid/oversized boundaries to RFC 9457 `problem+json` (`BOUNDARY_INVALID`, `BOUNDARY_TOO_LARGE`), and add integration tests.

## Files to touch
- `backend/config/urls.py`
- `backend/regions/serializers.py`
- `backend/regions/views.py`
- `backend/regions/urls.py`
- `backend/core/exceptions.py`
- `backend/regions/tests/test_api.py`

## Spec reference
- PRD §§6, 7, 9; `.agent/context/api-contract.md`

## Verification
```bash
pytest backend/regions/tests/test_api.py
```
`pytest` green; 400 cases (`BOUNDARY_INVALID`, `BOUNDARY_TOO_LARGE`) exercised.

## Out of scope
- GEE integration
- Frontend regions page (T15)

## Result
- Implemented `core/exceptions.py` (RFC 9457 `application/problem+json` + closed-enum `FailureCode`), `regions/serializers.py` (≤500 vertices simplification, 0.1–50,000 ha validation), `regions/views.py`, `regions/urls.py`, and `regions/tests/test_api.py`.
- **Blocked on runtime verification (`pytest backend/regions/tests/test_api.py`):** PostGIS database and GDAL/GEOS libraries are not available locally (Docker not installed).


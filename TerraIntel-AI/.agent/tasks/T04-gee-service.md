# T04 — gee_service.py — auth, init-once per process, retry with jitter, error mapping

## Goal
Implement `gee_service.py` with thread-safe init-once GEE authentication per process, exponential backoff retry with jitter, and mapping of GEE errors to closed-enum failure codes (`SATELLITE_UNAVAILABLE`, `UPSTREAM_TIMEOUT`, `QUOTA_EXCEEDED`).

## Files to touch
- `backend/analysis/__init__.py`
- `backend/services/__init__.py`
- `backend/services/gee_service.py`
- `backend/services/exceptions.py`
- `backend/services/tests/__init__.py`
- `backend/services/tests/test_gee_service.py`

## Spec reference
- PRD §§5, 7, 11

## Verification
```bash
python -c "from services.gee_service import list_recent_s2_scenes; print(list_recent_s2_scenes(...))"
```
Script prints 3 most recent S2 (`COPERNICUS/S2_SR_HARMONIZED`) scene IDs over a hardcoded polygon.

## Out of scope
- Cloud masking, NDVI computation, or tile URLs (T05)
- WorldCover masking (T09)

## Result
- `services/gee_service.py` and `services/exceptions.py` implemented; `ruff` and `mypy` clean; 4 unit tests in `services/tests/test_gee_service.py` passed.
- **Blocked on live GEE verification:** No `~/.config/earthengine/credentials` or `GEE_PROJECT_ID` configured locally.


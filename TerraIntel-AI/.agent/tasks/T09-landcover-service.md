# T09 — landcover_service.py — WorldCover cropland mask + NO_CROPLAND path

## Goal
Implement `landcover_service.py` to compute ESA WorldCover class 40 cropland mask coverage for a region and raise/map `NO_CROPLAND` when no cropland is present, integrating with the analysis pipeline.

## Files to touch
- `backend/services/landcover_service.py`
- `backend/services/ndvi_service.py`
- `backend/analyses/tasks.py`
- `backend/services/tests/test_landcover_service.py`

## Spec reference
- PRD §§5, 7, 8.2

## Verification
```bash
pytest backend/services/tests/test_landcover_service.py
```
Analysis of a lake polygon returns the documented `NO_CROPLAND` failure.

## Out of scope
- Non-cropland landcover breakdown UI

## Result
- `services/landcover_service.py` implemented; `ruff` and `mypy` clean; `test_landcover_service.py` passed (`NO_CROPLAND` path verified with mocked EE).
- **Blocked on live GEE verification:** No GEE credentials configured locally.


# T11 — Weather API matching contract

## Goal
Expose `/api/v1/weather/` endpoint via DRF serializers and views wrapping `weather_service.py`, matching `api-contract.md` with unit-suffixed fields (`_mm`, `_c`, `_pct`), error mapping, and contract tests.

## Files to touch
- `backend/config/urls.py`
- `backend/weather/__init__.py`
- `backend/weather/apps.py`
- `backend/weather/serializers.py`
- `backend/weather/views.py`
- `backend/weather/urls.py`
- `backend/weather/tests/__init__.py`
- `backend/weather/tests/test_api.py`

## Spec reference
- PRD §9; `.agent/context/api-contract.md`

## Verification
```bash
pytest backend/weather/tests/test_api.py
```
Contract test matches `api-contract.md`.

## Out of scope
- Frontend Weather page (T17)

## Result
- `weather` app (`serializers.py`, `views.py`, `urls.py`, `test_api.py`) implemented.
- **Blocked on Django/PostGIS integration test:** PostGIS/GDAL not available locally.


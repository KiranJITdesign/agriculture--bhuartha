# T21 — Hardening: rate limits, timeouts, structured JSON logging, deep /health/

## Goal
Add DRF rate limiting, explicit upstream timeouts (GEE 300s, NASA POWER 20s, Nominatim 10s), structured JSON logging with `trace_id` propagation across HTTP and Celery, and a deep `/health/` endpoint checking Postgres+PostGIS, Redis, and MinIO.

## Files to touch
- `backend/config/settings/base.py`
- `backend/core/middleware.py`
- `backend/core/logging.py`
- `backend/core/views.py`
- `backend/services/gee_service.py`
- `backend/services/weather_service.py`
- `backend/core/tests/test_health_hardening.py`

## Spec reference
- PRD §§7, 11

## Verification
```bash
pytest backend/core/tests/test_health_hardening.py
```
Chaos test: stop Redis -> app degrades with clear `application/problem+json` / `/health/` 503 status and `trace_id`.

## Out of scope
- Documentation (T22)

## Result
- Implemented `core/middleware.py` (`TraceIdMiddleware`), `core/logging.py` (`JsonLogFormatter`), DRF `AnonRateThrottle` (`120/min`), deep `/health/` with `trace_id`, and `test_health_hardening.py`.


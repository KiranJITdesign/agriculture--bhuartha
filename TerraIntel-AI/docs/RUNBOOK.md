# Operational Runbook — TerraIntel AI Module 3

## Health Checks
- `GET /health/` verifies Postgres+PostGIS (`SELECT PostGIS_Version()`), Redis (`PING`), and MinIO (`list_buckets`).
- Returns `200` when all dependencies are healthy, or `503` with `status: "degraded"` and `trace_id`.

## Upstream Timeouts & Retries
- **Google Earth Engine:** 300s Celery soft time limit, 3 attempts with exponential backoff + full jitter.
- **NASA POWER:** 20s HTTP timeout, 7-day cache.
- **Nominatim:** 10s AbortController timeout on frontend location search.

## Incident Triage
1. Capture the `trace_id` from the UI error banner or `X-Trace-ID` header.
2. Search structured JSON logs by `trace_id`.
3. Inspect failed `AnalysisJob` records for `failure_code` (`SATELLITE_UNAVAILABLE`, `NO_SCENES_FOUND`, `NO_CROPLAND`, `UPSTREAM_TIMEOUT`, `QUOTA_EXCEEDED`).

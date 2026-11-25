# API Contract — TerraIntel AI Module 3

> **Note:** PRD §9 verbatim content was referenced in the bootstrap prompt (`[Paste PRD §9 verbatim]`). This file records all API contract rules specified in the project brief. Specific endpoint URLs and request/response JSON schemas not yet specified are tracked in `.agent/QUESTIONS.md`.

## Base Path & Versioning
- Base path: `/api/v1/`
- Field names are stable; renaming requires `/api/v2/`.
- Timestamps: ISO 8601 UTC with `Z` suffix.
- Coordinates: GeoJSON `[lon, lat]`, SRID `4326`.
- Pagination: `{count, next, previous, results}`.
- Numeric formatting: API returns already-formatted strings (4 dp for NDVI, 2 dp for ha, round half-up); every numeric field name carries its unit (`_ha`, `_mm`, `_c`, `_pct`).
- Tile URLs: Frontend treats `tiles.expires_at` as authoritative.

## Error Envelope (RFC 9457 `application/problem+json`)
Views map closed-enum failure codes to `application/problem+json` responses, including `trace_id`:
- `SATELLITE_UNAVAILABLE`
- `NO_SCENES_FOUND`
- `NO_CROPLAND`
- `UPSTREAM_TIMEOUT`
- `BOUNDARY_TOO_LARGE`
- `BOUNDARY_INVALID`
- `QUOTA_EXCEEDED`

## Endpoints (from Task Breakdown)
- `GET /health/` — Deep health check of application and dependencies (Postgres+PostGIS, Redis, MinIO).
- `/api/v1/regions/` — `AgriculturalRegion` CRUD (simplify to ≤500 vertices, area 0.1–50,000 ha).
- `/api/v1/analyses/` & `/api/v1/jobs/` — Submit/poll `AnalysisJob`, retrieve `CropAnalysis` & `VegetationClassStat` (`cached: true` within 24h), low-vigour GeoJSON export (≤5 MB), WeasyPrint PDF report.
- `/api/v1/weather/` — NASA POWER weather summary + 5-year baseline anomaly (7-day cache).
- `/api/v1/compare/` — Two-period `ΔNDVI` comparison (binned at `±0.05`).

*(Exact route paths, HTTP methods, auth headers, and request/response payloads to be confirmed from PRD §9 in `.agent/QUESTIONS.md` before T03/T11/T12.)*

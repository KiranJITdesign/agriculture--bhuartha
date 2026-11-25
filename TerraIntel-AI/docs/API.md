# API Reference (`/api/v1/`)

All errors follow RFC 9457 (`application/problem+json`) with `code` and `trace_id`.
All numeric values are returned as pre-formatted strings with unit-suffixed keys (`_ha`, `_mm`, `_c`, `_pct`).

## Endpoints
- `GET /health/` — Deep dependency check (`postgres_postgis`, `redis`, `minio`).
- `GET, POST /api/v1/regions/` — List/create `AgriculturalRegion` (GeoJSON Polygon SRID 4326, 0.1–50,000 ha, simplified to ≤500 vertices).
- `GET, PATCH, DELETE /api/v1/regions/{id}/` — Retrieve/update/delete a region.
- `POST /api/v1/jobs/` — Submit async NDVI analysis (`{region, start_date, end_date}`). Returns `202` with job or `200` with `cached: true` if an identical analysis exists within 24h.
- `GET /api/v1/jobs/{id}/` — Poll job `status`, `stage`, `progress_pct`, and `failure_code`.
- `GET /api/v1/analyses/` & `GET /api/v1/analyses/{id}/` — Retrieve persisted `CropAnalysis` with `class_stats`, `scenes`, and `tiles`.
- `GET /api/v1/analyses/{id}/low-vigour.geojson` — Download simplified low-vigour zones (≤5 MB).
- `GET /api/v1/analyses/{id}/report.pdf` — Download 2-page WeasyPrint PDF report with scene provenance.
- `GET /api/v1/weather/?region={uuid}&start_date=YYYY-MM-DD&end_date=YYYY-MM-DD` — NASA POWER daily rainfall/temperature + 5-year anomaly.
- `POST /api/v1/compare/` — Two-period `ΔNDVI` comparison binned at `±0.05`.

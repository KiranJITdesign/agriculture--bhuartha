# TerraIntel AI — Module 3: Agriculture & Crop Health Analysis (PRD)

> **Note:** Sections 5–13 of the original PRD document were referenced in the bootstrap prompt (`[Paste the PRD sections 5 through 13 from the previous document here]`). This file captures every specification, invariant, and architectural rule provided in the project brief. Any unstated details from PRD §§5–13 are logged in `.agent/QUESTIONS.md` and must be confirmed before implementing affected tasks.

## 5. Functional Requirements & Scope
A Django + PostGIS + Leaflet application where a user draws an agricultural boundary, picks a date range, and receives:
- Sentinel-2 true-colour + NDVI maps (Google Earth Engine, `COPERNICUS/S2_SR_HARMONIZED`)
- Cropland-scoped NDVI statistics (masked to ESA WorldCover class 40)
- Low-vigour zones flagged as field-inspection candidates
- NASA POWER rainfall + temperature for the same window
- Two-period NDVI difference comparison (`ΔNDVI`, binned at `±0.05`)
- A downloadable PDF report containing real scene provenance (WeasyPrint, 2 pages)

Fixed technology stack:
- **Backend:** Python 3.11, Django, Django REST Framework, PostgreSQL + PostGIS, Celery + Redis, MinIO (local) / S3 (prod)
- **Geospatial / Science:** Google Earth Engine Python API, Rasterio, GeoPandas, Shapely, NumPy, Pandas
- **Frontend:** Vanilla HTML / CSS / ES-module JavaScript, Leaflet + leaflet-draw, Chart.js, Lucide icons (1.5px stroke, 16/20px). **No React, no Tailwind CDN, no build step, no framework.**

## 6. Data Model
- `AgriculturalRegion`: PostGIS `GeometryField` (SRID 4326, GeoJSON `[lon, lat]`), `area_hectares` (area 0.1–50,000 ha, simplified to ≤ 500 vertices).
- `AnalysisJob`: Celery-backed async job with stage/progress reporting and closed-enum `failure_code`.
- `CropAnalysis`: Persisted NDVI analysis results, thresholds (persisted per analysis for historical interpretability), coverage percentage, `sampled` flag, 24h cache on identical requests.
- `VegetationClassStat`: Per-class statistics (`LOW`, `MODERATE`, `HIGH`, `VERY_HIGH`).
- Low-vigour polygons: Stored in PostGIS `GeometryField`, not JSON blobs.
- Rasters and PDFs: Stored in object storage (MinIO local / S3 prod). Postgres stores keys and metadata only — no `bytea` raster columns.

## 7. Layering & Engineering Standards
- Strict layer separation: `views.py` (HTTP only) → `serializers.py` (validation/shape) → `services/` (external I/O) → `analysis/` (pure computation) → `models.py` (persistence).
- `analysis/` functions are pure: no Django imports, take/return plain data (numpy, dataclasses).
- `views.py` contains orchestration and nothing else; `services/` contains no HTTP concerns.
- Determinism: persist decimals at 4 dp (NDVI) / 2 dp (ha), round half-up. API returns already-formatted strings so the frontend never formats.
- Every numeric field name carries its unit (`_ha`, `_mm`, `_c`, `_pct`).
- Failure codes (closed enum): `SATELLITE_UNAVAILABLE`, `NO_SCENES_FOUND`, `NO_CROPLAND`, `UPSTREAM_TIMEOUT`, `BOUNDARY_TOO_LARGE`, `BOUNDARY_INVALID`, `QUOTA_EXCEEDED`. Views map these to `application/problem+json`. Nothing else catches broad `Exception`.

## 8. Algorithms & Non-Negotiable Invariants
### 8.2 Masking Order (`ndvi_service.py`)
Must be executed in **exact** order:
1. Region boundary
2. ESA WorldCover == 40 (cropland)
3. `SCL` ∉ `{3, 8, 9, 10, 11}`
4. `MSK_CLDPRB <= 40`
5. `B8 + B4 > 0`

Any statistic computed before step 5 is a defect.

### NDVI & Vigour Classification
- **NDVI:** `(B8 - B4) / (B8 + B4)`, clamped `[-1, 1]`, divide-by-zero guarded.
- Values `< -0.1` inside the cropland mask are `anomalous` — excluded from stats, reported as `anomalous_pixel_pct`.
- **Vigour classes:** `LOW < 0.20`, `MODERATE 0.20–0.45`, `HIGH 0.45–0.70`, `VERY_HIGH > 0.70`. Thresholds persisted per analysis.
- **Low-vigour zone:** pixel qualifies iff `NDVI < low_threshold` **AND** `NDVI < (p50 - 1.0 * IQR)`. Report **two numbers separately**: absolute low area (ha) and relative low area (ha).
- **Coverage flag:** `valid_pixel_pct < 30` → `LOW_COVERAGE`; UI shows warning banner; PDF report watermarked "insufficient coverage". Never display a low-vigour area without its coverage percentage adjacent.
- **Areal stats:** Use `ee.Image.pixelArea()` — never a hardcoded pixel-area formula.
- **Percentiles:** Histogram-derived. If pixel count > 5,000,000, a documented 1% random sample is permitted and `sampled=true` must be recorded.

### Weather Anomaly (NASA POWER)
- 7-day cache.
- If the 5-year baseline mean is 0, `anomaly_pct = null` with reason `NO_BASELINE_RAIN`. Never divide by zero, never emit `Infinity`.

### Comparison (`ΔNDVI`)
- Two-period NDVI difference comparison binned at `±0.05`; bins sum to 100% of analysed area.

## 9. API Contract
See `.agent/context/api-contract.md`.

## 10. UI & Design System
- See `.agent/context/design-tokens.md`.
- `api.js` is the only module that calls `fetch` (centralises auth, error parsing, `trace_id` extraction).
- `chartTheme.js` configures all Chart.js instances identically.
- Every async surface has 4 states: loading (skeleton matching final layout), empty (explains why + next action), error (inline, retry, `trace_id` copy), partial (coverage banner).
- Copy rules: no exclamation marks, no emoji, no "AI-powered"/"smart"/"revolutionary". Numbers always carry units. Say "low vegetation greenness", never "unhealthy crops". Disclaimers sit adjacent to the claim they qualify.
- Pages: Dashboard, Regions (Leaflet + leaflet-draw + Nominatim), Crop Health (layer switcher, fixed bordered legend, stats, histogram), Weather (dual-axis rainfall + temperature, shaded window, CSV export), Compare (side-by-side synced maps + diverging diff map).

## 11. Non-Functional Requirements (NFRs)
- Rate limits & timeouts: GEE `300s`, NASA POWER `20s`, Nominatim `10s`.
- Structured JSON logging with `trace_id` propagation.
- Deep `/health/` endpoint checking all dependencies (Postgres+PostGIS, Redis, MinIO, etc.).
- Low-vigour GeoJSON export: polygonized, simplified, `<= 5 MB`.

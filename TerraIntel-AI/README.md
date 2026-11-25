# TerraIntel AI — Module 3: Agriculture & Crop Health Analysis

Satellite-based agricultural monitoring application built with Django, PostGIS, Celery, Google Earth Engine, NASA POWER, Leaflet, and Chart.js.

## Stack
- **Backend:** Python 3.11, Django 5, DRF, PostgreSQL 16 + PostGIS 3.4, Celery + Redis, MinIO (S3)
- **Science / EO:** `earthengine-api` (`COPERNICUS/S2_SR_HARMONIZED`, `ESA/WorldCover/v200`), Rasterio, GeoPandas, Shapely, NumPy, Pandas, WeasyPrint
- **Frontend:** Vanilla HTML, CSS, ES-module JavaScript, Leaflet + `leaflet-draw`, Chart.js (no build step)

## Quickstart
1. Copy `.env.example` to `.env` (defaults to keyless open-source `SATELLITE_PROVIDER=stac`, local SpatiaLite DB, and local media storage).
2. Run database migrations:
   ```bash
   make migrate
   ```
3. Start the backend server (`http://127.0.0.1:8000`):
   ```bash
   make dev
   ```
4. Start the frontend server (`http://127.0.0.1:3000`) in a second terminal:
   ```bash
   make dev-frontend
   ```
5. Verify health:
   ```bash
   curl -sf http://127.0.0.1:8000/health/
   ```

## Quality Checks
```bash
make lint
make typecheck
make test
```

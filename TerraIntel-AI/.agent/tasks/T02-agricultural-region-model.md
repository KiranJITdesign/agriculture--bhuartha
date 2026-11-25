# T02 — AgriculturalRegion model, GeoDjango, migration, admin

## Goal
Create the `regions` Django app with the `AgriculturalRegion` GeoDjango model (`GeometryField` SRID 4326, `area_hectares`), initial migration, and Django Admin registration.

## Files to touch
- `backend/config/settings/base.py`
- `backend/regions/__init__.py`
- `backend/regions/apps.py`
- `backend/regions/models.py`
- `backend/regions/admin.py`
- `backend/regions/migrations/__init__.py`
- `backend/regions/migrations/0001_initial.py`
- `backend/regions/tests/__init__.py`
- `backend/regions/tests/test_models.py`

## Spec reference
- PRD §6, §9 (GeoJSON `[lon, lat]`, SRID 4326)

## Verification
```bash
pytest backend/regions/tests/test_models.py
```
Create region via admin with a real polygon; `area_hectares` within 0.5% of QGIS.

## Out of scope
- DRF serializers and API endpoints (T03)
- Frontend map drawing (T15)

## Result
- `AgriculturalRegion` model, GeoDjango admin, initial migration `0001_initial.py`, and `test_models.py` created.
- **Blocked on runtime verification (`pytest backend/regions/tests/test_models.py`):** PostGIS database and GDAL/GEOS libraries are not available locally (Docker not installed).


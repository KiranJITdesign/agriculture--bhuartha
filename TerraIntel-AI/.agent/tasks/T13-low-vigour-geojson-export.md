# T13 — Low-vigour GeoJSON export (polygonized, simplified, <= 5 MB)

## Goal
Polygonize and simplify low-vigour zones (`NDVI < low_threshold AND NDVI < p50 - 1.0*IQR`), persist in PostGIS `GeometryField`, and expose a GeoJSON export endpoint guaranteed `<= 5 MB`.

## Files to touch
- `backend/analyses/models.py`
- `backend/analyses/migrations/0003_low_vigour_zone.py`
- `backend/services/export_service.py`
- `backend/analyses/views.py`
- `backend/analyses/urls.py`
- `backend/analyses/tests/test_export.py`

## Spec reference
- PRD §§5, 6, 8, 9

## Verification
```bash
pytest backend/analyses/tests/test_export.py
```
Exported GeoJSON opens in QGIS; area matches DB within 2%; file size `<= 5 MB`.

## Out of scope
- Frontend download UI (T16)

## Result
- `LowVigourZone`, `services/export_service.py` (iterative simplification `<= 5 MB`), and `/api/v1/analyses/<id>/low-vigour.geojson` implemented.
- **Blocked on Django/PostGIS integration test:** `test_export.py` requires PostGIS/GDAL.


# T08 — Persist CropAnalysis, VegetationClassStat; 24 h cache on identical requests

## Goal
Persist `CropAnalysis` (including persisted thresholds, `valid_pixel_pct`, `anomalous_pixel_pct`, `sampled`, scene provenance, MinIO raster key) and `VegetationClassStat`, and implement 24-hour caching on identical analysis requests.

## Files to touch
- `backend/analyses/models.py`
- `backend/analyses/migrations/0002_crop_analysis.py`
- `backend/analyses/tasks.py`
- `backend/analyses/serializers.py`
- `backend/analyses/views.py`
- `backend/services/storage_service.py`
- `backend/analyses/tests/test_analysis_persistence.py`

## Spec reference
- PRD §§6, 7, 8, 9

## Verification
```bash
pytest backend/analyses/tests/test_analysis_persistence.py
```
Second identical request returns `cached: true` in `<300 ms`.

## Out of scope
- Low-vigour GeoJSON export (T13)
- PDF report (T20)

## Result
- `CropAnalysis`, `VegetationClassStat`, `storage_service.py`, 24h caching, and `test_analysis_persistence.py` implemented.
- **Blocked on Django/PostGIS integration test:** PostGIS/GDAL not available locally.


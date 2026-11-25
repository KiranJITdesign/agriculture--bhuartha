# T12 — Comparison service + endpoint (Delta NDVI binned at +/-0.05)

## Goal
Implement two-period NDVI difference (`ΔNDVI`) comparison in pure analysis/service layers and expose `/api/v1/compare/`, binning `ΔNDVI` at `±0.05` such that bins sum to 100% of analysed area, plus tile URL for the diverging difference layer.

## Files to touch
- `backend/config/urls.py`
- `backend/analysis/comparison.py`
- `backend/analysis/tests/test_comparison.py`
- `backend/services/comparison_service.py`
- `backend/analyses/serializers.py`
- `backend/analyses/views.py`
- `backend/analyses/urls.py`
- `backend/analyses/tests/test_compare_api.py`

## Spec reference
- PRD §§5, 8, 9

## Verification
```bash
pytest backend/analysis/tests/test_comparison.py backend/analyses/tests/test_compare_api.py
```
Compare two real analyses; bins sum to 100% of analysed area.

## Out of scope
- Frontend Compare page (T18)

## Result
- `analysis/comparison.py` (`±0.05` bins summing to 100%) and `services/comparison_service.py` + `/api/v1/compare/` implemented; `test_comparison.py` passed; `ruff` and `mypy` clean.
- **Blocked on Django/PostGIS integration test:** `test_compare_api.py` requires PostGIS/GDAL.


# T07 — AnalysisJob + Celery task + stage/progress reporting

## Goal
Create the `analyses` app with `AnalysisJob` model, Celery task for async NDVI execution with stage/progress reporting, and API endpoints to submit and poll jobs, mapping worker failures to closed-enum `failure_code`s.

## Files to touch
- `backend/config/settings/base.py`
- `backend/config/urls.py`
- `backend/analyses/__init__.py`
- `backend/analyses/apps.py`
- `backend/analyses/models.py`
- `backend/analyses/tasks.py`
- `backend/analyses/serializers.py`
- `backend/analyses/views.py`
- `backend/analyses/urls.py`
- `backend/analyses/migrations/__init__.py`
- `backend/analyses/migrations/0001_initial.py`
- `backend/analyses/tests/__init__.py`
- `backend/analyses/tests/test_jobs.py`

## Spec reference
- PRD §§6, 7, 9

## Verification
```bash
pytest backend/analyses/tests/test_jobs.py
```
Submit -> poll -> `SUCCEEDED`; kill worker mid-job -> `FAILED` with `failure_code`.

## Out of scope
- 24h result caching and `CropAnalysis` persistence (T08)

## Result
- `AnalysisJob`, `run_ndvi_analysis_task`, serializers, views, and `test_jobs.py` implemented.
- **Blocked on Django/PostGIS integration test:** PostGIS/GDAL not available locally.


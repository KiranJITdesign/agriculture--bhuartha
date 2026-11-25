# T20 — PDF report via WeasyPrint (HTML template reusing design tokens)

## Goal
Generate a 2-page downloadable PDF report via WeasyPrint using an HTML/CSS template that reuses `design-tokens.md`, includes real GEE scene IDs and acquisition dates, persists the PDF in MinIO/S3, and watermarks "insufficient coverage" when `valid_pixel_pct < 30`.

## Files to touch
- `backend/services/report_service.py`
- `backend/analyses/templates/reports/crop_health_report.html`
- `backend/analyses/templates/reports/crop_health_report.css`
- `backend/analyses/views.py`
- `backend/analyses/urls.py`
- `backend/analyses/models.py`
- `backend/analyses/migrations/0004_report_key.py`
- `backend/analyses/tests/test_report.py`

## Spec reference
- PRD §§5, 6, 8, 10; `.agent/context/design-tokens.md`

## Verification
```bash
pytest backend/analyses/tests/test_report.py
```
Generated PDF opens cleanly, contains real GEE scene IDs + acquisition dates, fits 2 pages, and includes watermark when `valid_pixel_pct < 30`.

## Out of scope
- Multi-region batch PDF reports

## Result
- Implemented `services/report_service.py`, `templates/reports/crop_health_report.html` & `.css`, `0004_report_key.py`, `/api/v1/analyses/<id>/report.pdf`, and `test_report.py`.
- **Blocked on WeasyPrint/PostGIS runtime verification:** Requires `libpango` + PostGIS/GDAL in Docker.


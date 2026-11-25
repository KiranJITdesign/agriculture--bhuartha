# ADR 0001: Stack and Strict Layering

## Status
Accepted

## Decision
- Backend uses Django + DRF + PostGIS + Celery/Redis with strict layering: `views.py` (HTTP) -> `serializers.py` (validation/formatting) -> `services/` (external I/O) -> `analysis/` (pure NumPy/dataclasses, zero Django imports) -> `models.py` (persistence).
- Frontend uses vanilla HTML/CSS/ES modules with Leaflet and Chart.js and zero build tooling.

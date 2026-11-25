# T01 — Skeleton: settings split, docker-compose, .env.example, pre-commit, CI

## Goal
Bootstrap the Django project skeleton with split settings (`base`, `local`, `prod`, `test`), `docker-compose.yml` (Postgres+PostGIS, Redis, MinIO), `.env.example`, `Makefile`, `requirements.txt`, pre-commit hooks (ruff, mypy), GitHub Actions CI, and a basic `/health/` endpoint.

## Files to touch
- `backend/manage.py`
- `backend/config/__init__.py`
- `backend/config/settings/__init__.py`
- `backend/config/settings/base.py`
- `backend/config/settings/local.py`
- `backend/config/settings/prod.py`
- `backend/config/settings/test.py`
- `backend/config/urls.py`
- `backend/config/wsgi.py`
- `backend/config/celery.py`
- `backend/core/__init__.py`
- `backend/core/views.py`
- `backend/requirements.txt`
- `backend/pyproject.toml`
- `docker-compose.yml`
- `Makefile`
- `.env.example`
- `.pre-commit-config.yaml`
- `.github/workflows/ci.yml`
- `docs/CHANGELOG.md`

## Spec reference
- PRD §§5, 7, 11

## Verification
```bash
make dev && curl -sf http://localhost:8000/health/
```
`make dev` boots; `/health/` returns 200 with all deps green.

## Out of scope
- Domain models (`AgriculturalRegion`, `AnalysisJob`, etc.)
- Deep dependency health checks beyond basic connectivity (expanded in T21)
- Frontend files

## Result
- Files created per "Files to touch".
- `py -3.12 -m compileall -q .` passed with 0 syntax errors.
- **Blocked on runtime verification (`make dev && curl -sf http://localhost:8000/health/`):** `docker` / `docker compose` is not installed on this machine, so Postgres+PostGIS, Redis, and MinIO containers could not be booted locally.


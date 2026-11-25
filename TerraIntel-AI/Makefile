.PHONY: dev dev-frontend migrate test lint typecheck

migrate:
	cd backend && python manage.py migrate

dev:
	cd backend && python manage.py runserver 127.0.0.1:8010

dev-frontend:
	python -m http.server 3000 -d frontend

test:
	cd backend && pytest

lint:
	cd backend && ruff check .

typecheck:
	cd backend && mypy analysis services

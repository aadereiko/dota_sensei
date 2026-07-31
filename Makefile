.PHONY: help setup db db-stop migrate revision backend frontend test lint

help:
	@echo "setup     - create backend venv + install frontend deps"
	@echo "db        - start postgres on 5473"
	@echo "migrate   - apply alembic migrations"
	@echo "revision  - autogenerate a migration (M=\"message\")"
	@echo "backend   - run the API on 8273"
	@echo "frontend  - run the dev server on 5273"
	@echo "test      - backend tests"
	@echo "lint      - ruff + tsc"

setup:
	cd backend && python3 -m venv .venv && .venv/bin/pip install -e '.[dev]'
	cd frontend && npm install
	test -f .env || cp .env.example .env

db:
	docker compose up -d postgres

db-stop:
	docker compose stop postgres

migrate:
	cd backend && .venv/bin/alembic upgrade head

revision:
	cd backend && .venv/bin/alembic revision --autogenerate -m "$(M)"

backend:
	cd backend && .venv/bin/python -m app.main

frontend:
	cd frontend && npm run dev

test:
	cd backend && .venv/bin/pytest

lint:
	cd backend && .venv/bin/ruff check .
	cd frontend && npm run typecheck

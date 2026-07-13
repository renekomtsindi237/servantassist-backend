# ──────────────────────────────────────────────────────────────────────────
# ServantAssist Backend — Makefile
# Project management, development, and testing
# ──────────────────────────────────────────────────────────────────────────

.PHONY: help install dev migrate-head migrate-rollback migrate-gen \
        migrate-staging migrate-staging-rollback migrate-staging-gen \
        migrate-production migrate-production-rollback \
        test test-unit test-e2e test-security test-performance test-coverage \
        lint format type-check docker-test docker-build docker-up docker-down docker-logs \
        staging-build staging-up staging-down staging-logs staging-restart \
        prod-build prod-up prod-down prod-logs prod-restart clean \
        build up down restart logs ps shell migrate

# Variables
PYTHON := ./venv/bin/python
PIP := ./venv/bin/pip
PYTEST := ./venv/bin/pytest
UVICORN := ./venv/bin/uvicorn
ALEMBIC := ./venv/bin/alembic
DOCKER_COMPOSE := docker compose

# Setup environment
setup:
	python3 -m venv venv
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt -r requirements-dev.txt

install:
	$(PIP) install -r requirements.txt -r requirements-dev.txt

dev:
	APP_ENV=development $(UVICORN) src.main:app --reload --host 0.0.0.0 --port 8000

# Help command
help:
	@echo "ServantAssist Backend Management"
	@echo ""
	@echo "Usage: make [target]"
	@echo ""
	@echo "Development Targets:"
	@echo "  setup            Set up virtual environment and install dependencies"
	@echo "  install          Install production and development dependencies"
	@echo "  dev              Start development server with reload"
	@echo ""
	@echo "Database Targets:"
	@echo "  migrate-head     Run all pending migrations"
	@echo "  migrate-rollback Rollback the last migration"
	@echo "  migrate-gen      Generate a new migration (usage: make migrate-gen msg=\"message\")"
	@echo ""
	@echo "Testing Targets:"
	@echo "  test             Run all tests"
	@echo "  test-unit        Run unit tests"
	@echo "  test-e2e         Run end-to-end tests"
	@echo "  test-security    Run security & RBAC tests"
	@echo "  test-performance Run performance tests"
	@echo "  test-coverage    Run tests and generate coverage report (html)"
	@echo ""
	@echo "Code Quality Targets:"
	@echo "  lint             Run ruff/flake8/black checks"
	@echo "  format           Format code with black/ruff/isort"
	@echo "  type-check       Run mypy type checks"
	@echo ""
	@echo "Docker Targets (development):"
	@echo "  docker-build     Build backend docker image"
	@echo "  docker-up        Start all services with docker-compose (local PostgreSQL)"
	@echo "  docker-down      Stop and remove containers"
	@echo "  docker-logs      View logs from all services"
	@echo "  docker-test      Run tests inside docker"
	@echo ""
	@echo "Staging Targets (Supabase):"
	@echo "  staging-build    Build docker image for staging"
	@echo "  staging-up       Start staging services (Supabase DB)"
	@echo "  staging-down     Stop staging services"
	@echo "  staging-logs     View staging logs"
	@echo "  staging-restart  Restart staging backend"
	@echo "  migrate-staging          Run Alembic migrations on Supabase staging"
	@echo "  migrate-staging-rollback Rollback last migration on staging"
	@echo ""
	@echo "Production Targets (Supabase):"
	@echo "  prod-build       Build docker image for production"
	@echo "  prod-up          Start production services (Supabase DB)"
	@echo "  prod-down        Stop production services"
	@echo "  prod-logs        View production logs"
	@echo "  prod-restart     Restart production backend"
	@echo "  migrate-production          Run Alembic migrations on Supabase production"
	@echo "  migrate-production-rollback Rollback last migration on production"
	@echo ""
	@echo "Cleanup Targets:"
	@echo "  clean            Remove cache and temporary files"

# Implementation

migrate-head:
	$(ALEMBIC) upgrade head

migrate-rollback:
	$(ALEMBIC) downgrade -1

migrate-gen:
	$(ALEMBIC) revision --autogenerate -m "$(msg)"

# ── Migrations Supabase STAGING (via container Docker) ────────────────────────
# Le service "migrate" (profil migrate) utilise SUPABASE_DB_DIRECT_URL
# depuis .env.staging — connexion directe port 5432, pas de pgbouncer.
migrate-staging:
	@echo "Migration Supabase STAGING..."
	$(DOCKER_COMPOSE) -f docker-compose.staging.yml \
		--profile migrate \
		run --rm migrate \
		alembic upgrade head

migrate-staging-rollback:
	@echo "Rollback STAGING (-1)..."
	$(DOCKER_COMPOSE) -f docker-compose.staging.yml \
		--profile migrate \
		run --rm migrate \
		alembic downgrade -1

migrate-staging-gen:
	@test -n "$(msg)" || (echo "Usage: make migrate-staging-gen msg=\"description\"" && exit 1)
	$(DOCKER_COMPOSE) -f docker-compose.staging.yml \
		--profile migrate \
		run --rm migrate \
		alembic revision --autogenerate -m "$(msg)"

migrate-staging-history:
	$(DOCKER_COMPOSE) -f docker-compose.staging.yml \
		--profile migrate \
		run --rm migrate \
		alembic history --verbose

migrate-staging-current:
	$(DOCKER_COMPOSE) -f docker-compose.staging.yml \
		--profile migrate \
		run --rm migrate \
		alembic current

# ── Migrations Supabase PRODUCTION (via container Docker) ─────────────────────
migrate-production:
	@echo "Migration Supabase PRODUCTION..."
	@echo "Appuyez sur ENTREE pour continuer, CTRL+C pour annuler."
	@read _
	$(DOCKER_COMPOSE) -f docker-compose.production.yml \
		--profile migrate \
		run --rm migrate \
		alembic upgrade head

migrate-production-rollback:
	@echo "ROLLBACK PRODUCTION - etes-vous sur ?"
	@read _
	$(DOCKER_COMPOSE) -f docker-compose.production.yml \
		--profile migrate \
		run --rm migrate \
		alembic downgrade -1

test:
	$(PYTEST)

test-unit:
	$(PYTEST) -m unit

test-e2e:
	$(PYTEST) -m e2e

test-security:
	$(PYTEST) -m security

test-performance:
	$(PYTEST) -m performance

test-coverage:
	$(PYTEST) --cov=src --cov-report=html --cov-report=term-missing

lint:
	./venv/bin/ruff check src tests
	$(PYTHON) -m black --check src tests

format:
	$(PYTHON) -m black src tests
	./venv/bin/ruff check --fix src tests

type-check:
	./venv/bin/mypy src

docker-test:
	$(DOCKER_COMPOSE) run --rm test

docker-build:
	$(DOCKER_COMPOSE) build

docker-up:
	$(DOCKER_COMPOSE) up -d

docker-down:
	$(DOCKER_COMPOSE) down

docker-logs:
	$(DOCKER_COMPOSE) logs -f

# ── Staging (Supabase) ────────────────────────────────────────────────────────
staging-build:
	$(DOCKER_COMPOSE) -f docker-compose.staging.yml build

staging-up:
	$(DOCKER_COMPOSE) -f docker-compose.staging.yml up -d

staging-down:
	$(DOCKER_COMPOSE) -f docker-compose.staging.yml down

staging-logs:
	$(DOCKER_COMPOSE) -f docker-compose.staging.yml logs -f

staging-restart:
	$(DOCKER_COMPOSE) -f docker-compose.staging.yml restart backend

# ── Production (Supabase) ─────────────────────────────────────────────────────
prod-build:
	$(DOCKER_COMPOSE) -f docker-compose.production.yml build

prod-up:
	$(DOCKER_COMPOSE) -f docker-compose.production.yml up -d

prod-down:
	$(DOCKER_COMPOSE) -f docker-compose.production.yml down

prod-logs:
	$(DOCKER_COMPOSE) -f docker-compose.production.yml logs -f

prod-restart:
	$(DOCKER_COMPOSE) -f docker-compose.production.yml restart backend

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".ruff_cache" -exec rm -rf {} +
	find . -type d -name "htmlcov" -exec rm -rf {} +
	rm -f .coverage coverage.xml junit.xml

# ── Alias simples ─────────────────────────────────────────────────────────────
build:
	$(DOCKER_COMPOSE) build

up:
	$(DOCKER_COMPOSE) up -d

down:
	$(DOCKER_COMPOSE) down

restart:
	$(DOCKER_COMPOSE) restart

logs:
	$(DOCKER_COMPOSE) logs -f

ps:
	$(DOCKER_COMPOSE) ps

shell:
	$(DOCKER_COMPOSE) exec backend bash

migrate:
	$(DOCKER_COMPOSE) exec backend alembic upgrade head

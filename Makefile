# ──────────────────────────────────────────────────────────────────────────
# ServantAssist Backend — Makefile
# Project management, development, and testing
# ──────────────────────────────────────────────────────────────────────────

.PHONY: help install dev migrate-head migrate-rollback test test-unit test-e2e test-security test-performance test-coverage lint format docker-build docker-up docker-down docker-logs clean

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
	@echo "Docker Targets:"
	@echo "  docker-build     Build backend docker image"
	@echo "  docker-up        Start all services with docker-compose"
	@echo "  docker-down      Stop and remove containers"
	@echo "  docker-logs      View logs from all services"
	@echo "  docker-test      Run tests inside docker"
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

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".ruff_cache" -exec rm -rf {} +
	find . -type d -name "htmlcov" -exec rm -rf {} +
	rm -f .coverage coverage.xml junit.xml

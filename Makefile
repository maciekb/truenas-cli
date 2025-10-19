.PHONY: help install install-dev lint format type-check test clean

help:
	@echo "TrueNAS API Client - Development Commands"
	@echo ""
	@echo "Setup:"
	@echo "  make install          Install core dependencies"
	@echo "  make install-dev      Install development dependencies"
	@echo ""
	@echo "Code Quality:"
	@echo "  make lint             Run linters (ruff)"
	@echo "  make format           Format code (ruff formatter)"
	@echo "  make type-check       Run type checker (pyrefly)"
	@echo "  make format-check     Check formatting without modifying"
	@echo ""
	@echo "Testing:"
	@echo "  make test             Run tests with coverage"
	@echo "  make test-fast        Run tests without coverage"
	@echo ""
	@echo "Utilities:"
	@echo "  make clean            Remove build artifacts and caches"
	@echo "  make qa               Run all quality checks (lint, format, type-check)"
	@echo ""

install:
	uv sync

install-dev:
	uv sync --group dev

lint:
	uv run ruff check src tests

format:
	uv run ruff format src tests

format-check:
	uv run ruff format src tests --check

type-check:
	uv run pyrefly check

test:
	uv run pytest --cov=src --cov-report=term-missing tests

test-fast:
	uv run pytest tests

test-watch:
	uv run pytest --looponfail tests

qa: lint format-check type-check
	@echo "All quality checks passed!"

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type d -name .pytest_cache -exec rm -rf {} +
	find . -type d -name .mypy_cache -exec rm -rf {} +
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	find . -type f -name .DS_Store -delete
	rm -rf build dist .coverage htmlcov

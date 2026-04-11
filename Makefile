.PHONY: install install-dev test test-cov lint format format-check type-check check run clean

install:
	uv sync

install-dev:
	uv sync --group dev --group test

test:
	uv run pytest tests/ -m "not e2e" -v

test-cov:
	uv run pytest tests/ -m "not e2e" --cov=src/wican_blade_mcp --cov-report=term-missing -v

lint:
	uv run ruff check src/ tests/

format:
	uv run ruff format src/ tests/

format-check:
	uv run ruff format --check src/ tests/

type-check:
	uv run mypy src/wican_blade_mcp

check: lint format-check type-check
	@echo "All quality checks passed!"

run:
	uv run wican-blade-mcp

clean:
	rm -rf .pytest_cache .mypy_cache .ruff_cache dist build *.egg-info
	find . -type d -name __pycache__ -exec rm -rf {} +

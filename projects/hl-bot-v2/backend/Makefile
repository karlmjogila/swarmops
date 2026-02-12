.PHONY: install run test lint format type-check clean help

help:
	@echo "Available commands:"
	@echo "  make install     - Install dependencies"
	@echo "  make run         - Run the development server"
	@echo "  make test        - Run tests"
	@echo "  make test-cov    - Run tests with coverage"
	@echo "  make lint        - Lint code with ruff"
	@echo "  make format      - Format code with ruff"
	@echo "  make type-check  - Type check with mypy"
	@echo "  make clean       - Clean cache files"

install:
	poetry install

run:
	poetry run uvicorn hl_bot.main:app --reload --port 8000

test:
	poetry run pytest -v

test-cov:
	poetry run pytest --cov=hl_bot --cov-report=html --cov-report=term

lint:
	poetry run ruff check .

format:
	poetry run ruff format .

type-check:
	poetry run mypy src/hl_bot

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type d -name .pytest_cache -exec rm -rf {} +
	find . -type d -name .ruff_cache -exec rm -rf {} +
	find . -type d -name .mypy_cache -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	rm -rf htmlcov/
	rm -rf .coverage

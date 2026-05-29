.PHONY: help install install-dev test lint format clean run

help:
	@echo "Available targets:"
	@echo "  install      Install production dependencies"
	@echo "  install-dev  Install dev + notebook dependencies"
	@echo "  test         Run unit tests"
	@echo "  test-all     Run all tests including integration"
	@echo "  lint         Run ruff linter"
	@echo "  format       Run black formatter"
	@echo "  clean        Remove build artifacts"
	@echo "  run          Start the bot"

install:
	pip install -r requirements.txt

install-dev:
	pip install -r requirements.txt
	pip install jupyter matplotlib seaborn plotly

test:
	pytest tests/unit -v

test-all:
	pytest tests -v

lint:
	ruff check src tests scripts

format:
	black src tests scripts

clean:
	rm -rf build/ dist/ .egg-info/ .pytest_cache/ .mypy_cache/
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

run:
	python scripts/start_bot.py

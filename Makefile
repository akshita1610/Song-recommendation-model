# Song Recommendation System - Makefile
# Convenience commands for development

.PHONY: help install install-dev install-prod format lint test clean run run-api docs

# Default target
help:
	@echo "🎵 Song Recommendation System - Development Commands"
	@echo ""
	@echo "Setup:"
	@echo "  install      Install package in development mode"
	@echo "  install-dev  Install with development dependencies"
	@echo "  install-prod Install with production dependencies"
	@echo ""
	@echo "Applications:"
	@echo "  run          Run Streamlit application"
	@echo "  run-api      Run FastAPI web server"
	@echo "  run-debug    Run Streamlit with debug logging"
	@echo ""
	@echo "Development:"
	@echo "  format       Format code with black and isort"
	@echo "  lint         Run linting (mypy, ruff, flake8)"
	@echo "  type-check   Run MyPy type checking"
	@echo "  test         Run tests with coverage"
	@echo "  test-watch   Run tests in watch mode"
	@echo "  test-fast    Run tests excluding slow tests"
	@echo ""
	@echo "Documentation:"
	@echo "  docs         Generate documentation"
	@echo "  docs-serve   Serve documentation locally"
	@echo ""
	@echo "Cleanup:"
	@echo "  clean        Clean cache and build files"

# Installation
install:
	pip install -e .

install-dev:
	pip install -e .[dev]

install-prod:
	pip install -e .[prod]

install-api:
	pip install -e .[api,dev]

# Code quality
format:
	black src/ main.py
	isort src/ main.py

lint:
	mypy src/
	ruff check src/ main.py
	flake8 src/ main.py

lint-fix:
	ruff check --fix src/ main.py

type-check:
	mypy src/ --show-error-codes

# Testing
test:
	pytest tests/ -v --cov=src --cov-report=html --cov-report=term

test-watch:
	pytest-watch tests/ -v

test-fast:
	pytest tests/ -v -m "not slow"

# Application
run:
	streamlit run main.py

run-api:
	uvicorn src.api:app --reload --host 0.0.0.0 --port 8000

run-debug:
	streamlit run main.py --logger.level debug

run-api-debug:
	uvicorn src.api:app --reload --host 0.0.0.0 --port 8000 --log-level debug

# Cleanup
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	rm -rf .pytest_cache/
	rm -rf .mypy_cache/
	rm -rf htmlcov/
	rm -rf .coverage

# Documentation
docs:
	cd docs && make html

docs-serve:
	cd docs/_build/html && python -m http.server 8000

# Development workflow
dev-setup: install-dev
	pre-commit install
	mkdir -p logs cache data
	if [ ! -f .env ]; then cp .env.example .env; fi

dev-api-setup: install-api
	pre-commit install
	mkdir -p logs cache data static templates
	if [ ! -f .env ]; then cp .env.example .env; fi

ci: format lint test

# Docker (if needed)
docker-build:
	docker build -t song-recommendation-system .

docker-run:
	docker run -p 8000:8000 song-recommendation-system

# Database operations
db-init:
	@echo "🗄️ Initializing database..."
	mkdir -p data
	touch data/song_recommendation.db

db-migrate:
	@echo "🔄 Running database migrations..."
	# Add migration commands here

# API testing
test-api:
	@echo "🧪 Testing API endpoints..."
	curl -X GET http://localhost:8000/api/v1/health
	curl -X GET http://localhost:8000/api/v1/search?query=test

# Development server with all features
dev-all: dev-api-setup
	@echo "🚀 Starting development environment..."
	@echo "📱 API Server: http://localhost:8000"
	@echo "📚 API Docs: http://localhost:8000/docs"
	@echo "🔍 ReDoc: http://localhost:8000/redoc"
	@echo ""
	@echo "Run 'make run-api' to start the server"

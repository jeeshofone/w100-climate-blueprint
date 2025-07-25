# W100 Smart Control Integration - Development Commands
# These commands match exactly what runs in GitHub Actions

.PHONY: help install test lint type-check format clean all

help:  ## Show this help message
	@echo "W100 Smart Control Integration - Development Commands"
	@echo "These commands match exactly what runs in GitHub Actions"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install:  ## Install test dependencies (same as GitHub Actions)
	python -m pip install --upgrade pip
	pip install -r requirements_test.txt

test:  ## Run tests with coverage (same as GitHub Actions)
	python -m pytest tests/ -v --cov=custom_components/w100_smart_control --cov-report=term-missing --cov-report=xml

test-quick:  ## Run tests without coverage
	python -m pytest tests/ -v

lint:  ## Run all linting checks (same as GitHub Actions)
	@echo "Running black..."
	black --check --diff custom_components/
	@echo "Running isort..."
	isort --check-only --diff custom_components/
	@echo "Running flake8..."
	flake8 custom_components/

type-check:  ## Run type checking (same as GitHub Actions)
	mypy custom_components/ --ignore-missing-imports

format:  ## Format code (fix linting issues)
	black custom_components/
	isort custom_components/

clean:  ## Clean up generated files
	rm -rf htmlcov/
	rm -rf .coverage
	rm -rf coverage.xml
	rm -rf .pytest_cache/
	rm -rf tests/__pycache__/
	rm -rf custom_components/**/__pycache__/
	find . -name "*.pyc" -delete

all: install lint type-check test  ## Run all checks (same as GitHub Actions)

# GitHub Actions simulation
github-test:  ## Simulate exactly what GitHub Actions test job does
	@echo "=== Simulating GitHub Actions Test Job ==="
	@echo "Step 1: Install dependencies"
	python -m pip install --upgrade pip
	pip install -r requirements_test.txt
	@echo ""
	@echo "Step 2: Run tests"
	python -m pytest tests/ -v --cov=custom_components/w100_smart_control --cov-report=term-missing --cov-report=xml
	@echo ""
	@echo "✅ GitHub Actions test simulation complete"

github-lint:  ## Simulate exactly what GitHub Actions lint job does
	@echo "=== Simulating GitHub Actions Lint Job ==="
	@echo "Step 1: Install dependencies"
	python -m pip install --upgrade pip
	pip install -r requirements_test.txt
	@echo ""
	@echo "Step 2: Run black"
	black --check --diff custom_components/
	@echo ""
	@echo "Step 3: Run isort"
	isort --check-only --diff custom_components/
	@echo ""
	@echo "Step 4: Run flake8"
	flake8 custom_components/
	@echo ""
	@echo "Step 5: Run mypy"
	mypy custom_components/ --ignore-missing-imports
	@echo ""
	@echo "✅ GitHub Actions lint simulation complete"

github-all:  ## Simulate both GitHub Actions jobs
	@echo "=== Simulating All GitHub Actions Jobs ==="
	$(MAKE) github-test
	@echo ""
	$(MAKE) github-lint
	@echo ""
	@echo "🎉 All GitHub Actions simulations complete!"
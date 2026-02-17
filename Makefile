.PHONY: help install test lint format clean dev deploy

help:
	@echo "CloudForge Bug Intelligence - Development Commands"
	@echo ""
	@echo "Setup:"
	@echo "  make install          Install all dependencies (backend, infrastructure, dashboard)"
	@echo "  make install-backend  Install backend dependencies"
	@echo "  make install-infra    Install infrastructure dependencies"
	@echo "  make install-dashboard Install dashboard dependencies"
	@echo ""
	@echo "Development:"
	@echo "  make dev              Start all services for local development"
	@echo "  make dev-backend      Start backend API server"
	@echo "  make dev-dashboard    Start dashboard development server"
	@echo "  make localstack       Start LocalStack for local AWS emulation"
	@echo ""
	@echo "Testing:"
	@echo "  make test             Run all tests"
	@echo "  make test-backend     Run backend tests"
	@echo "  make test-infra       Run infrastructure tests"
	@echo "  make test-dashboard   Run dashboard tests"
	@echo ""
	@echo "Code Quality:"
	@echo "  make lint             Run linters on all projects"
	@echo "  make format           Format code in all projects"
	@echo "  make type-check       Run type checking"
	@echo ""
	@echo "Deployment:"
	@echo "  make deploy           Deploy infrastructure to AWS"
	@echo "  make deploy-infra     Deploy only infrastructure"
	@echo ""
	@echo "Cleanup:"
	@echo "  make clean            Remove build artifacts and caches"

# Installation
install: install-backend install-infra install-dashboard

install-backend:
	cd backend && pip install -r requirements.txt

install-infra:
	cd infrastructure && npm install

install-dashboard:
	cd dashboard && npm install

# Development
dev:
	@echo "Starting LocalStack, Backend, and Dashboard..."
	@echo "Press Ctrl+C to stop all services"
	docker-compose up -d localstack
	@echo "Waiting for LocalStack to be ready..."
	@sleep 5
	@echo "Starting backend and dashboard in parallel..."
	@make -j2 dev-backend dev-dashboard

dev-backend:
	cd backend && uvicorn cloudforge.api.main:app --reload --host 0.0.0.0 --port 8000

dev-dashboard:
	cd dashboard && npm run dev

localstack:
	docker-compose up -d localstack
	@echo "LocalStack started on http://localhost:4566"

# Testing
test: test-backend test-infra test-dashboard

test-backend:
	cd backend && pytest

test-infra:
	cd infrastructure && npm test

test-dashboard:
	cd dashboard && npm test

# Code Quality
lint: lint-backend lint-infra lint-dashboard

lint-backend:
	cd backend && ruff check . && mypy cloudforge/

lint-infra:
	cd infrastructure && npm run lint

lint-dashboard:
	cd dashboard && npm run lint

format: format-backend format-infra format-dashboard

format-backend:
	cd backend && black . && ruff check . --fix

format-infra:
	cd infrastructure && npm run format

format-dashboard:
	cd dashboard && npm run format

type-check:
	cd backend && mypy cloudforge/
	cd infrastructure && npm run build
	cd dashboard && npm run build

# Deployment
deploy: deploy-infra

deploy-infra:
	cd infrastructure && npx cdk deploy --all

# Cleanup
clean:
	@echo "Cleaning build artifacts..."
	rm -rf backend/__pycache__
	rm -rf backend/.pytest_cache
	rm -rf backend/.coverage
	rm -rf backend/htmlcov
	rm -rf backend/.mypy_cache
	rm -rf backend/.ruff_cache
	rm -rf backend/dist
	rm -rf backend/build
	rm -rf infrastructure/dist
	rm -rf infrastructure/cdk.out
	rm -rf infrastructure/node_modules
	rm -rf dashboard/dist
	rm -rf dashboard/node_modules
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	@echo "Cleanup complete!"

# Docker
docker-up:
	docker-compose up -d

docker-down:
	docker-compose down

docker-logs:
	docker-compose logs -f

# AWS Setup
aws-setup:
	@echo "Setting up AWS resources..."
	aws dynamodb create-table \
		--table-name cloudforge-workflows \
		--attribute-definitions AttributeName=workflow_id,AttributeType=S \
		--key-schema AttributeName=workflow_id,KeyType=HASH \
		--billing-mode PAY_PER_REQUEST \
		--endpoint-url http://localhost:4566 || true
	aws dynamodb create-table \
		--table-name cloudforge-bugs \
		--attribute-definitions AttributeName=workflow_id,AttributeType=S AttributeName=bug_id,AttributeType=S \
		--key-schema AttributeName=workflow_id,KeyType=HASH AttributeName=bug_id,KeyType=RANGE \
		--billing-mode PAY_PER_REQUEST \
		--endpoint-url http://localhost:4566 || true
	aws s3 mb s3://cloudforge-artifacts --endpoint-url http://localhost:4566 || true
	@echo "AWS resources created!"

.PHONY: venv install clean test help build docker-build docker-push helm-deps helm-install helm-upgrade deploy deploy-all

# Variables
VENV_DIR := venv
PYTHON := python3
VENV_PYTHON := $(VENV_DIR)/bin/python
VENV_PIP := $(VENV_DIR)/bin/pip
REQUIREMENTS := backend/services/sreagent/requirements.txt

# Docker variables
IMAGE_NAME := sreagent
IMAGE_TAG := $(shell git describe --tags --always --dirty 2>/dev/null || echo "0.1.0")
DOCKER_REGISTRY ?= localhost:5000
IMAGE_REPO ?= $(DOCKER_REGISTRY)/$(IMAGE_NAME)
FULL_IMAGE := $(IMAGE_REPO):$(IMAGE_TAG)

# Helm variables
HELM_CHART := helm/sreagent
RELEASE_NAME ?= sreagent
NAMESPACE ?= sreagent
ENV ?= dev
VALUES_FILE := $(HELM_CHART)/values-$(ENV).yaml

# Default target
.DEFAULT_GOAL := help

# Create virtual environment
venv:
	@echo "Creating Python virtual environment..."
	@if [ -d "$(VENV_DIR)" ]; then \
		echo "Virtual environment already exists at $(VENV_DIR)"; \
	else \
		$(PYTHON) -m venv $(VENV_DIR); \
		echo "Virtual environment created at $(VENV_DIR)"; \
		echo "To activate, run: source $(VENV_DIR)/bin/activate"; \
	fi

# Install dependencies
install: venv
	@echo "Installing dependencies..."
	@if [ -f "$(REQUIREMENTS)" ]; then \
		$(VENV_PIP) install --upgrade pip; \
		$(VENV_PIP) install -r $(REQUIREMENTS); \
		echo "Dependencies installed successfully"; \
	else \
		echo "Warning: $(REQUIREMENTS) not found. Skipping dependency installation."; \
	fi

# Install in development mode (if setup.py exists)
install-dev: install
	@if [ -f "backend/services/sreagent/setup.py" ]; then \
		$(VENV_PIP) install -e backend/services/sreagent/; \
		echo "Package installed in development mode"; \
	fi

# Clean virtual environment
clean:
	@echo "Removing virtual environment..."
	@rm -rf $(VENV_DIR)
	@echo "Virtual environment removed"

# Run tests (if tests directory exists)
test: venv
	@if [ -d "tests" ]; then \
		$(VENV_PIP) install -r tests/requirements.txt 2>/dev/null || true; \
		$(VENV_PYTHON) -m pytest tests/ -v; \
	else \
		echo "No tests directory found"; \
	fi

# Build Docker image
docker-build:
	@echo "Building Docker image: $(FULL_IMAGE)"
	@docker build -t $(FULL_IMAGE) -t $(IMAGE_REPO):latest .
	@echo "Docker image built successfully: $(FULL_IMAGE)"

# Push Docker image
docker-push: docker-build
	@echo "Pushing Docker image: $(FULL_IMAGE)"
	@docker push $(FULL_IMAGE)
	@docker push $(IMAGE_REPO):latest
	@echo "Docker image pushed successfully"

# Update Helm dependencies
helm-deps:
	@echo "Updating Helm dependencies..."
	@cd $(HELM_CHART) && helm dependency update
	@echo "Helm dependencies updated"

# Install Helm chart
helm-install: helm-deps
	@echo "Installing Helm chart: $(RELEASE_NAME) in namespace: $(NAMESPACE)"
	@kubectl create namespace $(NAMESPACE) 2>/dev/null || true
	@helm install $(RELEASE_NAME) $(HELM_CHART) \
		--namespace $(NAMESPACE) \
		--set image.repository=$(IMAGE_REPO) \
		--set image.tag=$(IMAGE_TAG) \
		$(if $(wildcard $(VALUES_FILE)),-f $(VALUES_FILE),)
	@echo "Helm chart installed successfully"

# Upgrade Helm chart
helm-upgrade: helm-deps
	@echo "Upgrading Helm chart: $(RELEASE_NAME) in namespace: $(NAMESPACE)"
	@helm upgrade $(RELEASE_NAME) $(HELM_CHART) \
		--namespace $(NAMESPACE) \
		--set image.repository=$(IMAGE_REPO) \
		--set image.tag=$(IMAGE_TAG) \
		$(if $(wildcard $(VALUES_FILE)),-f $(VALUES_FILE),) \
		--install
	@echo "Helm chart upgraded successfully"

# Deploy to Kubernetes (build, push, and deploy)
deploy: docker-build docker-push helm-upgrade
	@echo "Deployment completed successfully!"
	@echo "Image: $(FULL_IMAGE)"
	@echo "Release: $(RELEASE_NAME)"
	@echo "Namespace: $(NAMESPACE)"
	@echo ""
	@echo "To check status, run:"
	@echo "  kubectl get pods -n $(NAMESPACE)"
	@echo "  kubectl get svc -n $(NAMESPACE)"

# Deploy all (build, test, push, and deploy)
deploy-all: test docker-build docker-push helm-upgrade
	@echo "Full deployment completed successfully!"
	@echo "Image: $(FULL_IMAGE)"
	@echo "Release: $(RELEASE_NAME)"
	@echo "Namespace: $(NAMESPACE)"
	@echo ""
	@echo "To check status, run:"
	@echo "  kubectl get pods -n $(NAMESPACE)"
	@echo "  kubectl get svc -n $(NAMESPACE)"
	@echo "  kubectl port-forward -n $(NAMESPACE) svc/$(RELEASE_NAME) 8000:80"

# Build everything (local build without push)
build: test docker-build
	@echo "Build completed successfully!"
	@echo "Image: $(FULL_IMAGE)"

# Show help message
help:
	@echo "Available targets:"
	@echo ""
	@echo "Development:"
	@echo "  make venv          - Create Python virtual environment"
	@echo "  make install       - Create venv and install dependencies"
	@echo "  make install-dev   - Install in development mode"
	@echo "  make test          - Run tests"
	@echo "  make clean         - Remove virtual environment"
	@echo ""
	@echo "Docker:"
	@echo "  make docker-build  - Build Docker image"
	@echo "  make docker-push   - Build and push Docker image"
	@echo ""
	@echo "Helm:"
	@echo "  make helm-deps     - Update Helm chart dependencies"
	@echo "  make helm-install  - Install Helm chart to Kubernetes"
	@echo "  make helm-upgrade  - Upgrade Helm chart in Kubernetes"
	@echo ""
	@echo "Deployment:"
	@echo "  make build         - Build and test (no push)"
	@echo "  make deploy        - Build, push, and deploy to Kubernetes"
	@echo "  make deploy-all    - Test, build, push, and deploy (full pipeline)"
	@echo ""
	@echo "Environment variables:"
	@echo "  DOCKER_REGISTRY    - Docker registry URL (default: localhost:5000)"
	@echo "  IMAGE_REPO         - Full image repository (default: \$${DOCKER_REGISTRY}/sreagent)"
	@echo "  IMAGE_TAG          - Image tag (default: git tag or 0.1.0)"
	@echo "  RELEASE_NAME       - Helm release name (default: sreagent)"
	@echo "  NAMESPACE          - Kubernetes namespace (default: sreagent)"
	@echo "  ENV                - Environment: dev or prod (default: dev)"
	@echo ""
	@echo "Examples:"
	@echo "  make deploy ENV=dev NAMESPACE=sreagent-dev"
	@echo "  make deploy-all DOCKER_REGISTRY=myregistry.com IMAGE_TAG=v1.0.0"
	@echo "  make deploy ENV=prod NAMESPACE=sreagent-prod RELEASE_NAME=sreagent-prod"
	@echo ""
	@echo "After creating the virtual environment, activate it with:"
	@echo "  source $(VENV_DIR)/bin/activate"


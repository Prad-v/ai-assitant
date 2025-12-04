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

# Cluster Inventory variables
CLUSTER_INVENTORY_IMAGE_NAME := cluster-inventory
CLUSTER_INVENTORY_IMAGE_TAG := $(shell git describe --tags --always --dirty 2>/dev/null || echo "0.1.0")
CLUSTER_INVENTORY_IMAGE_REPO ?= $(DOCKER_REGISTRY)/$(CLUSTER_INVENTORY_IMAGE_NAME)
CLUSTER_INVENTORY_FULL_IMAGE := $(CLUSTER_INVENTORY_IMAGE_REPO):$(CLUSTER_INVENTORY_IMAGE_TAG)

# Frontend variables
FRONTEND_IMAGE_NAME := sreagent-frontend
FRONTEND_IMAGE_TAG := $(shell git describe --tags --always --dirty 2>/dev/null || echo "0.1.0")
FRONTEND_IMAGE_REPO ?= $(DOCKER_REGISTRY)/$(FRONTEND_IMAGE_NAME)
FRONTEND_FULL_IMAGE := $(FRONTEND_IMAGE_REPO):$(FRONTEND_IMAGE_TAG)

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

# Test API endpoints through nginx proxy
test-api-nginx:
	@echo "Testing API endpoints through nginx proxy..."
	@echo "FRONTEND_URL: $${FRONTEND_URL:-http://localhost:3000}"
	@echo ""
	@if [ -z "$$FRONTEND_URL" ]; then \
		echo "Note: Set FRONTEND_URL environment variable if frontend is not on localhost:3000"; \
		echo "Example: FRONTEND_URL=http://localhost:3000 make test-api-nginx"; \
		echo ""; \
	fi
	@bash tests/test_api_nginx.sh

# Test API endpoints in Kubernetes cluster
test-api-k8s:
	@echo "Testing API endpoints in Kubernetes cluster..."
	@echo "Setting up port-forward..."
	@TEST_PORT=$$(($$RANDOM % 1000 + 3000)); \
	echo "Setting up port-forward on port $$TEST_PORT..."; \
	kubectl port-forward -n $(NAMESPACE) svc/$(RELEASE_NAME)-frontend $$TEST_PORT:3000 > /tmp/k8s-port-forward.log 2>&1 & \
	PORT_FORWARD_PID=$$!; \
	echo "Waiting for port-forward to be ready..."; \
	for i in 1 2 3 4 5; do \
		sleep 2; \
		if curl -s -f http://localhost:$$TEST_PORT/api/health > /dev/null 2>&1; then \
			echo "Port-forward ready!"; \
			break; \
		fi; \
		echo "Attempt $$i/5: Port-forward not ready yet..."; \
	done; \
	echo "Running API tests on port $$TEST_PORT..."; \
	FRONTEND_URL=http://localhost:$$TEST_PORT bash tests/test_api_nginx.sh; \
	TEST_EXIT=$$?; \
	kill $$PORT_FORWARD_PID 2>/dev/null || true; \
	pkill -f "port-forward.*$$TEST_PORT" 2>/dev/null || true; \
	exit $$TEST_EXIT

# Test UI endpoints
test-ui:
	@echo "Testing UI endpoints..."
	@echo "FRONTEND_URL: $${FRONTEND_URL:-http://localhost:3000}"
	@echo ""
	@if [ -z "$$FRONTEND_URL" ]; then \
		echo "Note: Set FRONTEND_URL environment variable if frontend is not on localhost:3000"; \
		echo "Example: FRONTEND_URL=http://localhost:3000 make test-ui"; \
		echo ""; \
	fi
	@bash tests/test_ui.sh

# Test UI in Kubernetes cluster
test-ui-k8s:
	@echo "Testing UI in Kubernetes cluster..."
	@echo "Setting up port-forward..."
	@TEST_PORT=$$(($$RANDOM % 1000 + 3000)); \
	echo "Setting up port-forward on port $$TEST_PORT..."; \
	kubectl port-forward -n $(NAMESPACE) svc/$(RELEASE_NAME)-frontend $$TEST_PORT:3000 > /tmp/k8s-ui-port-forward.log 2>&1 & \
	PORT_FORWARD_PID=$$!; \
	echo "Waiting for port-forward to be ready..."; \
	for i in 1 2 3 4 5; do \
		sleep 2; \
		if curl -s -f http://localhost:$$TEST_PORT/ > /dev/null 2>&1; then \
			echo "Port-forward ready!"; \
			break; \
		fi; \
		echo "Attempt $$i/5: Port-forward not ready yet..."; \
	done; \
	echo "Running UI tests on port $$TEST_PORT..."; \
	FRONTEND_URL=http://localhost:$$TEST_PORT bash tests/test_ui.sh; \
	TEST_EXIT=$$?; \
	kill $$PORT_FORWARD_PID 2>/dev/null || true; \
	pkill -f "port-forward.*$$TEST_PORT" 2>/dev/null || true; \
	exit $$TEST_EXIT

# Run all tests (API + UI)
test-all-k8s: test-api-k8s test-ui-k8s
	@echo "All tests completed!"

# Build Docker image
docker-build:
	@echo "Building Docker image: $(FULL_IMAGE)"
	@docker build -t $(FULL_IMAGE) -t $(IMAGE_REPO):latest .
	@echo "Docker image built successfully: $(FULL_IMAGE)"

# Build Cluster Inventory Docker image
cluster-inventory-docker-build:
	@echo "Building Cluster Inventory Docker image: $(CLUSTER_INVENTORY_FULL_IMAGE)"
	@docker build -t $(CLUSTER_INVENTORY_FULL_IMAGE) -t $(CLUSTER_INVENTORY_IMAGE_REPO):latest -f backend/services/cluster-inventory/Dockerfile .
	@echo "Cluster Inventory Docker image built successfully: $(CLUSTER_INVENTORY_FULL_IMAGE)"

# Build Frontend Docker image
frontend-docker-build:
	@echo "Building Frontend Docker image: $(FRONTEND_FULL_IMAGE)"
	@docker build -t $(FRONTEND_FULL_IMAGE) -t $(FRONTEND_IMAGE_REPO):latest ./frontend
	@echo "Frontend Docker image built successfully: $(FRONTEND_FULL_IMAGE)"

# Push Docker image
docker-push: docker-build
	@echo "Pushing Docker image: $(FULL_IMAGE)"
	@docker push $(FULL_IMAGE)
	@docker push $(IMAGE_REPO):latest
	@echo "Docker image pushed successfully"

# Push Cluster Inventory Docker image
cluster-inventory-docker-push: cluster-inventory-docker-build
	@echo "Pushing Cluster Inventory Docker image: $(CLUSTER_INVENTORY_FULL_IMAGE)"
	@docker push $(CLUSTER_INVENTORY_FULL_IMAGE)
	@docker push $(CLUSTER_INVENTORY_IMAGE_REPO):latest
	@echo "Cluster Inventory Docker image pushed successfully"

# Push Frontend Docker image
frontend-docker-push: frontend-docker-build
	@echo "Pushing Frontend Docker image: $(FRONTEND_FULL_IMAGE)"
	@docker push $(FRONTEND_FULL_IMAGE)
	@docker push $(FRONTEND_IMAGE_REPO):latest
	@echo "Frontend Docker image pushed successfully"

# Update Helm dependencies
helm-deps:
	@echo "Updating Helm dependencies..."
	@cd $(HELM_CHART) && helm dependency update
	@cd helm/cluster-inventory && helm dependency update 2>/dev/null || true
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

# Install Cluster Inventory Helm chart
cluster-inventory-helm-install: helm-deps
	@echo "Installing Cluster Inventory Helm chart in namespace: $(NAMESPACE)"
	@kubectl create namespace $(NAMESPACE) 2>/dev/null || true
	@helm install cluster-inventory helm/cluster-inventory \
		--namespace $(NAMESPACE) \
		--set image.repository=$(CLUSTER_INVENTORY_IMAGE_REPO) \
		--set image.tag=$(CLUSTER_INVENTORY_IMAGE_TAG) \
		--install
	@echo "Cluster Inventory Helm chart installed successfully"

# Upgrade Cluster Inventory Helm chart
cluster-inventory-helm-upgrade: helm-deps
	@echo "Upgrading Cluster Inventory Helm chart in namespace: $(NAMESPACE)"
	@helm upgrade cluster-inventory helm/cluster-inventory \
		--namespace $(NAMESPACE) \
		--set image.repository=$(CLUSTER_INVENTORY_IMAGE_REPO) \
		--set image.tag=$(CLUSTER_INVENTORY_IMAGE_TAG) \
		--install
	@echo "Cluster Inventory Helm chart upgraded successfully"

# Upgrade Helm chart
helm-upgrade: helm-deps cluster-inventory-helm-upgrade
	@echo "Upgrading Helm chart: $(RELEASE_NAME) in namespace: $(NAMESPACE)"
	@helm upgrade $(RELEASE_NAME) $(HELM_CHART) \
		--namespace $(NAMESPACE) \
		--set image.repository=$(IMAGE_REPO) \
		--set image.tag=$(IMAGE_TAG) \
		--set frontend.image.repository=$(FRONTEND_IMAGE_REPO) \
		--set frontend.image.tag=$(FRONTEND_IMAGE_TAG) \
		$(if $(wildcard $(VALUES_FILE)),-f $(VALUES_FILE),) \
		--install
	@echo "Helm chart upgraded successfully"

# Deploy to Kubernetes (build, push, and deploy)
deploy: docker-build docker-push cluster-inventory-docker-build cluster-inventory-docker-push frontend-docker-build frontend-docker-push helm-upgrade
	@echo "Deployment completed successfully!"
	@echo "Backend Image: $(FULL_IMAGE)"
	@echo "Frontend Image: $(FRONTEND_FULL_IMAGE)"
	@echo "Release: $(RELEASE_NAME)"
	@echo "Namespace: $(NAMESPACE)"
	@echo ""
	@echo "To check status, run:"
	@echo "  kubectl get pods -n $(NAMESPACE)"
	@echo "  kubectl get svc -n $(NAMESPACE)"
	@echo ""
	@echo "To access the React UI:"
	@echo "  kubectl port-forward -n $(NAMESPACE) svc/$(RELEASE_NAME)-frontend 3000:3000"

# Deploy all (build, test, push, and deploy)
deploy-all: test docker-build docker-push cluster-inventory-docker-build cluster-inventory-docker-push frontend-docker-build frontend-docker-push helm-upgrade
	@echo "Full deployment completed successfully!"
	@echo "Backend Image: $(FULL_IMAGE)"
	@echo "Frontend Image: $(FRONTEND_FULL_IMAGE)"
	@echo "Release: $(RELEASE_NAME)"
	@echo "Namespace: $(NAMESPACE)"
	@echo ""
	@echo "To check status, run:"
	@echo "  kubectl get pods -n $(NAMESPACE)"
	@echo "  kubectl get svc -n $(NAMESPACE)"
	@echo ""
	@echo "To access services:"
	@echo "  React UI: kubectl port-forward -n $(NAMESPACE) svc/$(RELEASE_NAME)-frontend 3000:3000"
	@echo "  ADK Web UI: kubectl port-forward -n $(NAMESPACE) svc/$(RELEASE_NAME) 8000:80"

# Build everything (local build without push)
build: test docker-build cluster-inventory-docker-build frontend-docker-build
	@echo "Build completed successfully!"
	@echo "Backend Image: $(FULL_IMAGE)"
	@echo "Cluster Inventory Image: $(CLUSTER_INVENTORY_FULL_IMAGE)"
	@echo "Frontend Image: $(FRONTEND_FULL_IMAGE)"

# Show help message
help:
	@echo "Available targets:"
	@echo ""
	@echo "Development:"
	@echo "  make venv          - Create Python virtual environment"
	@echo "  make install       - Create venv and install dependencies"
	@echo "  make install-dev   - Install in development mode"
	@echo "  make test          - Run Python tests"
	@echo "  make test-api-nginx - Test API endpoints through nginx (requires FRONTEND_URL)"
	@echo "  make test-api-k8s  - Test API endpoints in Kubernetes cluster"
	@echo "  make test-ui       - Test UI endpoints (requires FRONTEND_URL)"
	@echo "  make test-ui-k8s   - Test UI endpoints in Kubernetes cluster"
	@echo "  make test-all-k8s  - Run all tests (API + UI) in Kubernetes cluster"
	@echo "  make clean         - Remove virtual environment"
	@echo ""
	@echo "Docker:"
	@echo "  make docker-build                    - Build backend Docker image"
	@echo "  make docker-push                     - Build and push backend Docker image"
	@echo "  make cluster-inventory-docker-build   - Build cluster inventory Docker image"
	@echo "  make cluster-inventory-docker-push    - Build and push cluster inventory Docker image"
	@echo "  make frontend-docker-build            - Build frontend Docker image"
	@echo "  make frontend-docker-push             - Build and push frontend Docker image"
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


# Makefile for RHOAI MCP Server Container Management
# Supports both Docker and Podman

# =============================================================================
# Configuration
# =============================================================================

IMAGE_NAME ?= rhoai-mcp
IMAGE_TAG ?= latest
FULL_IMAGE := $(IMAGE_NAME):$(IMAGE_TAG)
CONTAINER_NAME ?= rhoai-mcp

# Container runtime detection (prefer podman if available)
CONTAINER_RUNTIME := $(shell command -v podman 2>/dev/null || command -v docker 2>/dev/null)

# Runtime configuration
PORT ?= 8000
KUBECONFIG ?= $(HOME)/.kube/config
LOG_LEVEL ?= INFO

.PHONY: help build build-no-cache run run-http run-stdio run-dev run-token stop logs shell clean info

# =============================================================================
# Help
# =============================================================================

help: ## Show this help message
	@echo "RHOAI MCP Server - Container Management"
	@echo ""
	@echo "Detected runtime: $(CONTAINER_RUNTIME)"
	@echo ""
	@echo "Usage: make [target]"
	@echo ""
	@echo "Targets:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}'

# =============================================================================
# Build
# =============================================================================

build: ## Build the container image
	$(CONTAINER_RUNTIME) build -t $(FULL_IMAGE) .

build-no-cache: ## Build the container image without cache
	$(CONTAINER_RUNTIME) build --no-cache -t $(FULL_IMAGE) .

# =============================================================================
# Run
# =============================================================================

run: run-http ## Default: run with HTTP (SSE) transport

run-http: ## Run with HTTP (SSE) transport on port $(PORT)
	$(CONTAINER_RUNTIME) run --rm --name $(CONTAINER_NAME) \
		-p $(PORT):8000 \
		-v $(KUBECONFIG):/app/kubeconfig/config:ro \
		-e RHOAI_MCP_AUTH_MODE=kubeconfig \
		-e RHOAI_MCP_KUBECONFIG_PATH=/app/kubeconfig/config \
		-e RHOAI_MCP_LOG_LEVEL=$(LOG_LEVEL) \
		$(FULL_IMAGE) --transport sse

run-streamable: ## Run with streamable-http transport
	$(CONTAINER_RUNTIME) run --rm --name $(CONTAINER_NAME) \
		-p $(PORT):8000 \
		-v $(KUBECONFIG):/app/kubeconfig/config:ro \
		-e RHOAI_MCP_AUTH_MODE=kubeconfig \
		-e RHOAI_MCP_KUBECONFIG_PATH=/app/kubeconfig/config \
		-e RHOAI_MCP_LOG_LEVEL=$(LOG_LEVEL) \
		$(FULL_IMAGE) --transport streamable-http

run-stdio: ## Run with STDIO transport (interactive)
	$(CONTAINER_RUNTIME) run --rm -it --name $(CONTAINER_NAME) \
		-v $(KUBECONFIG):/app/kubeconfig/config:ro \
		-e RHOAI_MCP_AUTH_MODE=kubeconfig \
		-e RHOAI_MCP_KUBECONFIG_PATH=/app/kubeconfig/config \
		-e RHOAI_MCP_LOG_LEVEL=$(LOG_LEVEL) \
		$(FULL_IMAGE) --transport stdio

run-dev: ## Run with debug logging and dangerous ops enabled
	$(CONTAINER_RUNTIME) run --rm --name $(CONTAINER_NAME) \
		-p $(PORT):8000 \
		-v $(KUBECONFIG):/app/kubeconfig/config:ro \
		-e RHOAI_MCP_AUTH_MODE=kubeconfig \
		-e RHOAI_MCP_KUBECONFIG_PATH=/app/kubeconfig/config \
		-e RHOAI_MCP_LOG_LEVEL=DEBUG \
		-e RHOAI_MCP_ENABLE_DANGEROUS_OPERATIONS=true \
		$(FULL_IMAGE) --transport sse

run-token: ## Run with token auth (requires TOKEN and API_SERVER)
ifndef TOKEN
	$(error TOKEN is required. Usage: make run-token TOKEN=<token> API_SERVER=<url>)
endif
ifndef API_SERVER
	$(error API_SERVER is required. Usage: make run-token TOKEN=<token> API_SERVER=<url>)
endif
	$(CONTAINER_RUNTIME) run --rm --name $(CONTAINER_NAME) \
		-p $(PORT):8000 \
		-e RHOAI_MCP_AUTH_MODE=token \
		-e RHOAI_MCP_API_TOKEN=$(TOKEN) \
		-e RHOAI_MCP_API_SERVER=$(API_SERVER) \
		-e RHOAI_MCP_LOG_LEVEL=$(LOG_LEVEL) \
		$(FULL_IMAGE) --transport sse

run-background: ## Run in background (detached) with HTTP transport
	$(CONTAINER_RUNTIME) run -d --name $(CONTAINER_NAME) \
		-p $(PORT):8000 \
		-v $(KUBECONFIG):/app/kubeconfig/config:ro \
		-e RHOAI_MCP_AUTH_MODE=kubeconfig \
		-e RHOAI_MCP_KUBECONFIG_PATH=/app/kubeconfig/config \
		-e RHOAI_MCP_LOG_LEVEL=$(LOG_LEVEL) \
		$(FULL_IMAGE) --transport sse

# =============================================================================
# Management
# =============================================================================

stop: ## Stop the running container
	-$(CONTAINER_RUNTIME) stop $(CONTAINER_NAME) 2>/dev/null || true
	-$(CONTAINER_RUNTIME) rm $(CONTAINER_NAME) 2>/dev/null || true

logs: ## View container logs
	$(CONTAINER_RUNTIME) logs -f $(CONTAINER_NAME)

shell: ## Open a shell in the running container
	$(CONTAINER_RUNTIME) exec -it $(CONTAINER_NAME) /bin/bash

clean: stop ## Remove container and image
	-$(CONTAINER_RUNTIME) rmi $(FULL_IMAGE) 2>/dev/null || true

# =============================================================================
# Testing
# =============================================================================

test-health: ## Test the health endpoint
	@curl -sf http://localhost:$(PORT)/health && echo " OK" || echo "FAILED"

test-build: build ## Verify the image builds and runs
	$(CONTAINER_RUNTIME) run --rm $(FULL_IMAGE) --version

# =============================================================================
# Info
# =============================================================================

info: ## Show configuration
	@echo "IMAGE:     $(FULL_IMAGE)"
	@echo "CONTAINER: $(CONTAINER_NAME)"
	@echo "RUNTIME:   $(CONTAINER_RUNTIME)"
	@echo "PORT:      $(PORT)"
	@echo "KUBECONFIG: $(KUBECONFIG)"

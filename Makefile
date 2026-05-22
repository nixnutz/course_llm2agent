.DEFAULT_GOAL := help

.PHONY: help \
	up down ps top logs logs-all logs-init-keys logs-init-models certs-generate \
	dev-container-smoke dev-container-smoke-wrapper dev-container-smoke-clean \
	devcontainer-smoke devcontainer-smoke-wrapper devcontainer-smoke-clean \
	keys-generate keys-overwrite keys-show keys-sync litellm-recreate ollama-expose \
	phoenix-health smoke-chat smoke-embeddings state-init state-prune streamlit-run trust-certs-host \
	dev-image-build dev-image-rebuild dev-image-reset-project-venv dev-container-restart review-manual \
	ruff ruff-check

COMPOSE_DIR := container/compose
DEV_IMAGE_NAME ?= course-llm-dev:v1

help:
	@echo "Available targets:"
	@echo ""
	@echo "Docker Compose Runtime Environment (delegated to container/compose):"
	@echo "  make up                       Start compose stack"
	@echo "  make down                     Stop compose stack"
	@echo "  make ps                       Show compose status"
	@echo "  make top                      Show compose processes"
	@echo "  make logs                     Follow compose logs"
	@echo "  make logs-all                 Follow all compose logs"
	@echo "  make logs-init-keys           Follow init-keys logs"
	@echo "  make logs-init-models         Follow init-models logs"
	@echo "  make certs-generate           Generate local TLS certs"
	@echo "  make keys-generate            Create missing virtual keys"
	@echo "  make keys-overwrite           Recreate all virtual keys"
	@echo "  make keys-show                Show locally saved virtual keys"
	@echo "  make keys-sync                Sync keys into LiteLLM"
	@echo "  make litellm-recreate         Recreate LiteLLM service"
	@echo "  make ollama-expose            Recreate ollama with exposed API"
	@echo "  make phoenix-health           Check local Phoenix UI endpoint"
	@echo "  make smoke-chat               Run compose chat smoke test"
	@echo "  make smoke-embeddings         Run compose embeddings smoke test"
	@echo "  make state-init               Ensure local compose state folders/files"
	@echo "  make state-prune              Remove compose state contents"
	@echo "  make trust-certs-host         Trust generated local certs on host"
	@echo ""
	@echo "Streamlit (delegated to container/compose):"
	@echo "  make streamlit-run            Run a Streamlit app inside the dev container"
	@echo "                                Vars: STREAMLIT_FILE STREAMLIT_ADDRESS STREAMLIT_PORT"
	@echo ""
	@echo "Development Environment (delegated to container/compose):"
	@echo "  make dev-container-smoke      Run dev wrapper smoke tests"
	@echo "  make dev-container-smoke-wrapper Alias for dev-container-smoke"
	@echo "  make dev-container-smoke-clean Remove dev smoke temp artifacts"
	@echo ""
	@echo "Development Image (container/dev-image):"
	@echo "  make dev-image-build          Build dev image with repository-root context"
	@echo "  make dev-image-rebuild        Rebuild dev image without cache"
	@echo ""
	@echo "Development Container Lifecycle:"
	@echo "  make dev-container-restart    Recreate dev container (no image build)"
	@echo ""
	@echo "Review Workflow:"
	@echo "  make review-manual            Show fixed manual review checklist and context"
	@echo ""
	@echo "Code Quality (requires running dev container):"
	@echo "  make ruff-check               Run ruff lint (check only) on src/ Python files (no .ipynb)"
	@echo "  make ruff                     Run ruff lint --fix and format on src/ Python files (no .ipynb)"

up:
	$(MAKE) -C $(COMPOSE_DIR) preflight-up && $(MAKE) dev-image-build && $(MAKE) -C $(COMPOSE_DIR) up-no-preflight

down ps top logs logs-all logs-init-keys logs-init-models certs-generate \
dev-container-smoke dev-container-smoke-wrapper dev-container-smoke-clean \
keys-generate keys-overwrite keys-show keys-sync litellm-recreate ollama-expose \
phoenix-health smoke-chat smoke-embeddings state-init state-prune streamlit-run trust-certs-host ruff ruff-check:
	$(MAKE) -C $(COMPOSE_DIR) $@

# Backward-compatible aliases (deprecated naming).
devcontainer-smoke: dev-container-smoke
devcontainer-smoke-wrapper: dev-container-smoke-wrapper
devcontainer-smoke-clean: dev-container-smoke-clean

dev-image-build:
	docker build -t $(DEV_IMAGE_NAME) -f container/dev-image/Dockerfile .

dev-image-rebuild:
	$(MAKE) dev-image-reset-project-venv
	docker build --no-cache -t $(DEV_IMAGE_NAME) -f container/dev-image/Dockerfile .

dev-image-reset-project-venv:
	@if [ -d "src/.venv" ]; then \
		echo "Removing project venv at src/.venv to force fresh post-rebuild environment."; \
		rm -rf "src/.venv"; \
	else \
		echo "No project venv at src/.venv; nothing to reset."; \
	fi

dev-container-restart:
	cd $(COMPOSE_DIR) && docker compose up -d --no-deps --force-recreate dev

review-manual:
	./scripts/review-manual.sh

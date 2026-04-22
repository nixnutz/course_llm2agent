.DEFAULT_GOAL := help

.PHONY: help \
	up down ps top logs logs-all logs-init-keys logs-init-models certs-generate \
	devcontainer-smoke devcontainer-smoke-wrapper devcontainer-smoke-clean \
	keys-generate keys-overwrite keys-show keys-sync litellm-recreate ollama-expose \
	phoenix-health smoke-chat smoke-embeddings state-init state-prune trust-certs-host \
	dev-image-build dev-image-rebuild review-manual

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
	@echo "Development Environment (delegated to container/compose):"
	@echo "  make devcontainer-smoke       Run dev wrapper smoke tests"
	@echo "  make devcontainer-smoke-wrapper Alias for devcontainer-smoke"
	@echo "  make devcontainer-smoke-clean Remove dev smoke temp artifacts"
	@echo ""
	@echo "Development Image (container/dev-image):"
	@echo "  make dev-image-build          Build dev image with repository-root context"
	@echo "  make dev-image-rebuild        Rebuild dev image without cache"
	@echo ""
	@echo "Review Workflow:"
	@echo "  make review-manual            Show fixed manual review checklist and context"

up:
	$(MAKE) dev-image-build && $(MAKE) -C $(COMPOSE_DIR) up

down ps top logs logs-all logs-init-keys logs-init-models certs-generate \
devcontainer-smoke devcontainer-smoke-wrapper devcontainer-smoke-clean \
keys-generate keys-overwrite keys-show keys-sync litellm-recreate ollama-expose \
phoenix-health smoke-chat smoke-embeddings state-init state-prune trust-certs-host:
	$(MAKE) -C $(COMPOSE_DIR) $@

dev-image-build:
	docker build -t $(DEV_IMAGE_NAME) -f container/dev-image/Dockerfile .

dev-image-rebuild:
	docker build --no-cache -t $(DEV_IMAGE_NAME) -f container/dev-image/Dockerfile .

review-manual:
	./scripts/review-manual.sh

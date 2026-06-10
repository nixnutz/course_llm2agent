.DEFAULT_GOAL := help

.PHONY: help \
	up down ps top logs logs-all logs-init-keys logs-init-models certs-generate \
	dev-container-smoke dev-container-smoke-wrapper dev-container-smoke-clean \
	devcontainer-smoke devcontainer-smoke-wrapper devcontainer-smoke-clean \
	keys-generate keys-overwrite keys-show keys-sync litellm-recreate ollama-expose \
	phoenix-health smoke-chat smoke-embeddings state-init state-prune streamlit-run trust-certs-host \
	dev-image-build dev-image-rebuild dev-image-reset-project-venv dev-container-restart review-manual \
	sysbox-bash-api-smoke sysbox-bash-image-build sysbox-bash-image-rebuild sysbox-bash-service-restart sysbox-bash-sessions \
	ruff ruff-check

COMPOSE_DIR := container/compose
DEV_IMAGE_NAME ?= course-llm-dev:v1
SBASH_IMAGE_NAME ?= course-llm-sysbox-bash:dev
SBASH_EXEC_IMAGE_NAME ?= course-llm-sysbox-bash-exec:dev
SBASH_EXEC_IMAGE_ARCHIVE ?= container/compose/.state/sysbox_bash/images/sysbox-bash-exec-image.tar

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
	@echo "Sysbox Bash Image (container/sysbox-bash-image):"
	@echo "  make sysbox-bash-image-build   Build sysbox + exec images and save exec tar"
	@echo "  make sysbox-bash-image-rebuild Rebuild sysbox + exec images without cache"
	@echo ""
	@echo "Sysbox Bash Service:"
	@echo "  make sysbox-bash-api-smoke       Run Sandbox API smoke test through dev"
	@echo "  make sysbox-bash-service-restart Recreate sysbox_bash Compose service"
	@echo "  make sysbox-bash-sessions        List active sysbox_bash sessions"
	@echo ""
	@echo "Review Workflow:"
	@echo "  make review-manual            Show fixed manual review checklist and context"
	@echo ""
	@echo "Code Quality (requires running dev container):"
	@echo "  make ruff-check               Run ruff lint (check only) on src/ Python files (no .ipynb)"
	@echo "  make ruff                     Run ruff lint --fix and format on src/ Python files (no .ipynb); list modified files"

up:
	$(MAKE) -C $(COMPOSE_DIR) preflight-up && $(MAKE) dev-image-build && $(MAKE) sysbox-bash-image-build && $(MAKE) -C $(COMPOSE_DIR) up-no-preflight

down ps top logs logs-all logs-init-keys logs-init-models certs-generate \
dev-container-smoke dev-container-smoke-wrapper dev-container-smoke-clean \
keys-generate keys-overwrite keys-show keys-sync litellm-recreate ollama-expose \
phoenix-health smoke-chat smoke-embeddings state-init state-prune streamlit-run trust-certs-host ruff ruff-check:
	$(MAKE) -C $(COMPOSE_DIR) $@

sysbox-bash-api-smoke sysbox-bash-sessions:
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

sysbox-bash-image-build:
	$(MAKE) -C $(COMPOSE_DIR) state-init
	docker build -t $(SBASH_IMAGE_NAME) -f container/sysbox-bash-image/Dockerfile .
	docker build -t $(SBASH_EXEC_IMAGE_NAME) -f container/sysbox-bash-exec-image/Dockerfile .
	@$(MAKE) _sysbox-bash-exec-image-export

sysbox-bash-image-rebuild:
	$(MAKE) -C $(COMPOSE_DIR) state-init
	docker build --no-cache -t $(SBASH_IMAGE_NAME) -f container/sysbox-bash-image/Dockerfile .
	docker build --no-cache -t $(SBASH_EXEC_IMAGE_NAME) -f container/sysbox-bash-exec-image/Dockerfile .
	@$(MAKE) _sysbox-bash-exec-image-export

_sysbox-bash-exec-image-export:
	@set -eu; \
	archive="$(SBASH_EXEC_IMAGE_ARCHIVE)"; \
	dir="$$(dirname "$$archive")"; \
	tmp="$$dir/sysbox-bash-exec-image.tar.tmp"; \
	bak="$$dir/sysbox-bash-exec-image.tar.bak"; \
	mkdir -p "$$dir"; \
	docker image inspect "$(SBASH_EXEC_IMAGE_NAME)" >/dev/null; \
	rm -f "$$bak"; \
	if [ -f "$$archive" ]; then mv "$$archive" "$$bak"; fi; \
	rm -f "$$tmp"; \
	if docker save "$(SBASH_EXEC_IMAGE_NAME)" -o "$$tmp"; then \
		mv "$$tmp" "$$archive"; \
	else \
		rm -f "$$tmp"; \
		echo "ERROR: docker save failed for $(SBASH_EXEC_IMAGE_NAME)" >&2; \
		exit 1; \
	fi

sysbox-bash-service-restart:
	cd $(COMPOSE_DIR) && docker compose up -d --no-deps --force-recreate sysbox_bash

review-manual:
	./scripts/review-manual.sh

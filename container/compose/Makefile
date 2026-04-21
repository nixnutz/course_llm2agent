.DEFAULT_GOAL := help

ifneq (,$(wildcard .env))
include .env
export
endif

# Target order convention (keep .PHONY, help, and target definitions aligned):
# 1) Direct commands first: up, down, ps, top, logs
# 2) logs-* group next
# 3) All other group-action targets after that, grouped by prefix and sorted alphabetically
# 4) Single non-group targets (if any) at the end
# This is primarily for readability/discoverability and avoids accidental order drift.

.PHONY: help up down ps top logs logs-all logs-init-keys logs-init-models certs-generate devcontainer-smoke devcontainer-smoke-clean devcontainer-smoke-wrapper keys-generate keys-overwrite keys-show keys-sync litellm-recreate ollama-expose phoenix-health smoke-chat smoke-embeddings state-init state-prune trust-certs-host

CURL_TLS_FLAGS ?= -k

help:
	@echo "Available targets:"
	@echo "  Note: service 'dev' uses \`$${DEV_IMAGE_NAME:-course-llm-dev:v1}\`; run \`make dev-image-build\` at repo root before \`make up\` when needed"
	@echo "  make up                 Start stack with default secure setup"
	@echo "  make down               Stop and remove compose resources"
	@echo "  make ps                 Show compose service status"
	@echo "  make top                Show running container processes"
	@echo "  make logs               Follow all logs until litellm is healthy, then litellm-only"
	@echo "  make logs-all           Follow logs for all compose services"
	@echo "  make logs-init-keys     Follow one-shot virtual key init logs"
	@echo "  make logs-init-models   Follow one-shot model init logs"
	@echo "  make certs-generate     Generate local TLS certs via one-shot container"
	@echo "  make devcontainer-smoke Run dev wrapper smoke tests"
	@echo "  make devcontainer-smoke-wrapper Alias for devcontainer-smoke"
	@echo "  make devcontainer-smoke-clean Remove smoke test temp artifacts"
	@echo "  make keys-generate      Create missing virtual keys (dev/stage/prod/user1/user2)"
	@echo "  make keys-overwrite     Recreate all virtual keys (dev/stage/prod/user1/user2)"
	@echo "  make keys-show          Show locally saved virtual keys"
	@echo "  make keys-sync          Sync ${KEYS_LOCAL_FILE} into LiteLLM"
	@echo "  make litellm-recreate   Recreate LiteLLM service"
	@echo "  make ollama-expose      Expose Ollama API port for a running setup (recreates ollama)"
	@echo "  make phoenix-health     Check local Phoenix UI TLS endpoint"
	@echo "  make smoke-chat         Run authenticated chat completion smoke test"
	@echo "  make smoke-embeddings   Run authenticated embeddings smoke test"

up:
	$(MAKE) state-init && $(MAKE) certs-generate && docker compose up -d

down:
	docker compose down

ps:
	docker compose ps

top:
	docker compose top

logs:
	./scripts/logs-follow.sh

logs-all:
	docker compose logs -f

logs-init-keys:
	docker compose logs -f litellm_init_keys

logs-init-models:
	docker compose logs -f ollama_init_models

certs-generate:
	$(MAKE) state-init && docker compose up --no-deps --force-recreate certs_init

devcontainer-smoke:
	./tests/smoke/devcontainer_smoke_test/run.sh

devcontainer-smoke-wrapper: devcontainer-smoke

devcontainer-smoke-clean:
	rm -f "../../src/.tmp_devcontainer_smoke"

keys-generate:
	./scripts/virtual-keys.sh create

keys-overwrite:
	./scripts/virtual-keys.sh overwrite

keys-show:
	@if [ -f "${KEYS_LOCAL_FILE}" ]; then jq -r '.keys[] | "- \(.name): \(.token)"' "${KEYS_LOCAL_FILE}"; else echo "No ${KEYS_LOCAL_FILE} found. Run make keys-generate first."; fi

keys-sync:
	./scripts/virtual-keys.sh sync-from-file

litellm-recreate:
	docker compose up -d --force-recreate litellm

ollama-expose:
	docker compose -f docker-compose.yml -f docker-compose.ollama-expose.yml up -d --no-deps --force-recreate ollama

phoenix-health:
	curl $(CURL_TLS_FLAGS) -sS "https://localhost:$${PHOENIX_UI_TLS_PORT:-6006}/" >/dev/null && echo "Phoenix UI reachable on https://localhost:$${PHOENIX_UI_TLS_PORT:-6006}"

smoke-chat:
	curl $(CURL_TLS_FLAGS) -sS "https://localhost:$(LITELLM_PORT)/v1/chat/completions" \
		-H "Content-Type: application/json" \
		-H "Authorization: Bearer $(LITELLM_MASTER_KEY)" \
		-d '{"model":"ollama_chat/llama3.2:3b","messages":[{"role":"user","content":"Say hello in German."}],"temperature":0.2}'

smoke-embeddings:
	curl $(CURL_TLS_FLAGS) -sS "https://localhost:$(LITELLM_PORT)/v1/embeddings" \
		-H "Content-Type: application/json" \
		-H "Authorization: Bearer $(LITELLM_MASTER_KEY)" \
		-d '{"model":"ollama/nomic-embed-text:latest","input":"litellm + ollama MVP"}'

state-init:
	@mkdir -p ".state" ".state/postgres_data" ".state/ollama_data" ".state/certs" ".state/.tmp" ".state/keys" ".state/phoenix_data"
	@if [ ! -f ".state/.gitignore" ]; then printf '*\n!/.gitignore\n' > ".state/.gitignore"; fi
	@if [ -d "$(KEYS_LOCAL_FILE)" ]; then rm -rf "$(KEYS_LOCAL_FILE)"; fi
	@if [ ! -f "$(KEYS_LOCAL_FILE)" ]; then printf '{\n  "keys": []\n}\n' > "$(KEYS_LOCAL_FILE)"; fi

state-prune:
	docker compose down
	@mkdir -p ".state"
	@find ".state" -mindepth 1 ! -name ".gitignore" -exec rm -rf {} +

trust-certs-host:
	@if ! command -v mkcert >/dev/null 2>&1; then echo "mkcert not found on host; skipping trust step."; exit 0; fi
	@if [ ! -f ".state/certs/.caroot/rootCA.pem" ]; then echo "No generated root CA at .state/certs/.caroot/rootCA.pem. Run make certs-generate first."; exit 1; fi
	CAROOT="$(PWD)/.state/certs/.caroot" mkcert -install

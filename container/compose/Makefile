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

.PHONY: help preflight-up up up-no-preflight down ps top logs logs-all logs-init-keys logs-init-models certs-generate dev-container-smoke dev-container-smoke-clean dev-container-smoke-wrapper devcontainer-smoke devcontainer-smoke-clean devcontainer-smoke-wrapper keys-generate keys-overwrite keys-show keys-sync litellm-recreate ollama-expose phoenix-health smoke-chat smoke-embeddings state-init state-prune toxiproxy-bootstrap toxiproxy-reset trust-certs-host

CURL_TLS_FLAGS ?= -k
MIN_DOCKER_ENGINE_VERSION ?= 25.0.0
MIN_DOCKER_COMPOSE_VERSION ?= 2.20.0

help:
	@echo "Available targets:"
	@echo "  Note: service 'dev' uses \`$${DEV_IMAGE_NAME:-course-llm-dev:v1}\`; run \`make dev-image-build\` at repo root before \`make up\` when needed"
	@echo ""
	@echo "  Core Runtime:"
	@echo "    make up                    Start stack with default secure setup"
	@echo "    make down                  Stop and remove compose resources"
	@echo "    make ps                    Show compose service status"
	@echo "    make top                   Show running container processes"
	@echo ""
	@echo "  Logs:"
	@echo "    make logs                  Follow all logs until litellm_clean is healthy, then clean logs"
	@echo "    make logs-all              Follow logs for all compose services"
	@echo "    make logs-init-keys        Follow one-shot virtual key init logs"
	@echo "    make logs-init-models      Follow one-shot model init logs"
	@echo ""
	@echo "  Dev Container:"
	@echo "    make dev-container-smoke         Run dev wrapper smoke tests"
	@echo "    make dev-container-smoke-wrapper Alias for dev-container-smoke"
	@echo "    make dev-container-smoke-clean   Remove smoke test temp artifacts"
	@echo ""
	@echo "  Keys & Services:"
	@echo "    make keys-generate         Create missing virtual keys (dev/stage/prod/user1/user2)"
	@echo "    make keys-overwrite        Recreate all virtual keys (dev/stage/prod/user1/user2)"
	@echo "    make keys-show             Show locally saved virtual keys"
	@echo "    make keys-sync             Sync ${KEYS_LOCAL_FILE} into LiteLLM"
	@echo "    make litellm-recreate      Recreate both LiteLLM services"
	@echo "    make ollama-expose         Expose Ollama API port for a running setup (recreates ollama)"
	@echo ""
	@echo "  Health / Smoke:"
	@echo "    make certs-generate        Generate local TLS certs via one-shot container"
	@echo "    make phoenix-health        Check local Phoenix UI TLS endpoint"
	@echo "    make smoke-chat            Run authenticated chat completion smoke test"
	@echo "    make smoke-embeddings      Run authenticated embeddings smoke test"
	@echo ""
	@echo "  Toxiproxy:"
	@echo "    make toxiproxy-bootstrap   Ensure edge/provider proxies exist in Toxiproxy"
	@echo "    make toxiproxy-reset       Remove toxics and re-enable all proxies"
	@echo ""
	@echo "  State:"
	@echo "    make state-init            Ensure compose state folders/files exist"
	@echo "    make state-prune           Remove compose state contents"
	@echo "    make trust-certs-host      Trust generated local certs on host"

preflight-up:
	@set -eu; \
	provider="docker"; \
	if [ -n "$${DOCKER_HOST:-}" ] && printf '%s' "$${DOCKER_HOST}" | tr '[:upper:]' '[:lower:]' | grep -q 'podman'; then \
		provider="podman"; \
	fi; \
	server_platform="$$(docker version --format '{{.Server.Platform.Name}}' 2>/dev/null || true)"; \
	if [ -n "$${server_platform}" ] && printf '%s' "$${server_platform}" | tr '[:upper:]' '[:lower:]' | grep -q 'podman'; then \
		provider="podman"; \
	fi; \
	if [ "$${provider}" != "docker" ]; then \
		echo "WARNING: non-docker compose provider detected; this setup is not tested." >&2; \
		exit 0; \
	fi; \
	engine_version="$$(docker version --format '{{.Server.Version}}' 2>/dev/null || true)"; \
	if [ -z "$${engine_version}" ]; then \
		echo "ERROR: Docker server version not available. Is Docker running?" >&2; \
		exit 1; \
	fi; \
	min_engine="$(MIN_DOCKER_ENGINE_VERSION)"; \
	if [ "$$(printf '%s\n%s\n' "$${min_engine}" "$${engine_version}" | sort -V | head -n1)" != "$${min_engine}" ]; then \
		echo "ERROR: Docker Engine >= $${min_engine} required (found $${engine_version})." >&2; \
		exit 1; \
	fi; \
	compose_version_raw="$$(docker compose version --short 2>/dev/null || true)"; \
	compose_version="$${compose_version_raw#v}"; \
	if [ -z "$${compose_version}" ]; then \
		echo "ERROR: Docker Compose version not available. Is docker compose installed?" >&2; \
		exit 1; \
	fi; \
	min_compose="$(MIN_DOCKER_COMPOSE_VERSION)"; \
	if [ "$$(printf '%s\n%s\n' "$${min_compose}" "$${compose_version}" | sort -V | head -n1)" != "$${min_compose}" ]; then \
		echo "ERROR: Docker Compose >= $${min_compose} required (found $${compose_version})." >&2; \
		exit 1; \
	fi

up: preflight-up up-no-preflight

up-no-preflight:
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

dev-container-smoke:
	./tests/smoke/devcontainer_smoke_test/run.sh

dev-container-smoke-wrapper: dev-container-smoke

dev-container-smoke-clean:
	rm -f "../../src/.tmp_devcontainer_smoke"

# Backward-compatible aliases (deprecated naming).
devcontainer-smoke: dev-container-smoke
devcontainer-smoke-wrapper: dev-container-smoke-wrapper
devcontainer-smoke-clean: dev-container-smoke-clean

keys-generate:
	./scripts/virtual-keys.sh create

keys-overwrite:
	./scripts/virtual-keys.sh overwrite

keys-show:
	@if [ -f "${KEYS_LOCAL_FILE}" ]; then jq -r '.keys[] | "- \(.name): \(.token)"' "${KEYS_LOCAL_FILE}"; else echo "No ${KEYS_LOCAL_FILE} found. Run make keys-generate first."; fi

keys-sync:
	./scripts/virtual-keys.sh sync-from-file

litellm-recreate:
	docker compose up -d --force-recreate litellm_clean litellm_chaos

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

toxiproxy-bootstrap:
	TOXIPROXY_URL="http://localhost:$${TOXIPROXY_ADMIN_PORT:-8474}" \
	TOXIPROXY_EDGE_LISTEN="$${TOXIPROXY_EDGE_LISTEN:-11111}" \
	TOXIPROXY_OLLAMA_LISTEN="$${TOXIPROXY_OLLAMA_LISTEN:-11112}" \
	LITELLM_INTERNAL_PORT="$${LITELLM_INTERNAL_PORT:-4000}" \
	OLLAMA_CONTAINER_PORT="$${OLLAMA_CONTAINER_PORT:-11434}" \
	bash ./scripts/toxiproxy-bootstrap.sh

toxiproxy-reset:
	TOXIPROXY_URL="http://localhost:$${TOXIPROXY_ADMIN_PORT:-8474}" \
	bash ./scripts/toxiproxy-reset.sh

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

# liteLLM + Ollama (MVP)

Developer setup with local TLS-by-default at the edge. `ollama` hosts models, `litellm_clean` and `litellm_chaos` provide OpenAI-compatible API channels, and `phoenix` adds a lightweight local trace UI.

## What is where?

The directory layout follows a purpose-centric split with per-service subfolders:

- `docker-compose.yml`: main local stack (LiteLLM, Ollama, Postgres+pgvector, Phoenix, Caddy, helper init containers)
- `docker-compose.ollama-expose.yml`: optional override to publish Ollama API to host
- `Makefile`: primary day-to-day commands (`up`, `logs`, `smoke-*`, key management)
- `.env.example`: template for local environment values
- `config/<service>/`: read-only config files mounted into running services
  - `config/caddy/Caddyfile`: local TLS edge/proxy config for LiteLLM UI and Phoenix UI
  - `config/litellm/litellm.yaml`: LiteLLM model/provider/router configuration
- `init/<service>/`: one-shot init artifacts (SQL + scripts) consumed by init containers or Postgres' `/docker-entrypoint-initdb.d/`
  - `init/postgres/01-extensions.sql`: enables `vector` extension on first cluster init
  - `init/postgres/role-bootstrap.sh`: idempotent role/DB setup (runs every `up`)
  - `init/certs/local.sh`, `init/ollama/models.sh`, `init/keys/{virtual,validate}.sh`, `init/toxiproxy/bootstrap.sh`
- `scripts/<service>/`: host-side and `dev`-runtime helpers (Makefile callees)
  - `scripts/dev/{cmd,session,export-secrets-env}.sh`: devcontainer wrapper + secrets export
  - `scripts/keys/virtual-keys.sh`: virtual key management CLI (`make keys-*`)
  - `scripts/stack/logs-follow.sh`: cross-cutting compose log follower (`make logs`)
  - `scripts/toxiproxy/{reset,toxic}.sh`: chaos toggles
- `tests/smoke/devcontainer_smoke_test/run.sh`: smoke test for devcontainer wrapper behavior
- `.state/`: local persisted runtime data (gitignored)
- `dev-wrapper.yaml`: source of truth for devcontainer wrapper command/session contract

### Postgres init split

Two complementary mechanisms cooperate on Postgres setup:

1. **Official `/docker-entrypoint-initdb.d/` hook** (`init/postgres/01-extensions.sql`). Runs **once** when the data volume is empty (e.g. after `make state-prune`). Used here to enable the `vector` extension on the default DB. Idempotent (`CREATE EXTENSION IF NOT EXISTS`).
2. **Init container `postgres_init_identities`** (`init/postgres/role-bootstrap.sh`). Runs on **every** `compose up`. Creates LiteLLM/Phoenix roles and databases idempotently and re-applies `vector` per DB. Use this for anything that should keep working after the SQL file is changed without wiping `.state/postgres_data/`.

## Quickstart (happy path)

Learner-oriented walkthrough: [docs/getting-started.md](../../docs/getting-started.md).

```bash
cp .env.example .env
make up          # runs state-init + certs-generate, then starts the stack
make smoke-chat
```

Then open:

```bash
xdg-open "https://localhost:${LITELLM_PORT:-4000}/ui"
```

## Configuration

Compose reads variables from `.env` in this directory.
For day-to-day operations, prefer `make` targets; use raw `docker compose` for advanced/special cases.

## Technical prerequisites

- Docker Engine `>= 25.0.0` (released 2024-01-19)
- Docker Compose `>= 2.20.0` (released 2023-07-11)

`make up` enforces these minimum versions for Docker Compose runtime.
If a non-Docker compose provider is detected, `make up` prints a warning:
`WARNING: non-docker compose provider detected; this setup is not tested.`

- **Sysbox** (`sysbox-runc`) — required for the `sysbox_bash` sandbox service. `make up` runs `scripts/sysbox_bash/preflight.sh`. Install: [Nestybox Sysbox install guide](https://github.com/nestybox/sysbox/blob/master/docs/user-guide/install.md).

## Dev Runtime + Internal TLS Routing

The `dev` service uses the project dev image (`${DEV_IMAGE_NAME:-course-llm-dev:v1}`) and is isolated to enforce TLS usage via Caddy for backend access.

- Network `dev_edge`: `dev` + `caddy`
- Network `backend_core`: `caddy` + backend services (`litellm_clean`, `litellm_chaos`, `phoenix`, `postgres`, `ollama`, init jobs)
- Result: `dev` cannot directly reach backend service DNS names; backend access from `dev` goes through `caddy`

Use internal TLS endpoints from inside `dev`:

- LiteLLM clean channel: `https://caddy:${LITELLM_PORT:-4000}`
- LiteLLM chaos channel: `https://caddy:${LITELLM_CHAOS_PORT:-4001}`
- Phoenix UI: `https://caddy:${PHOENIX_UI_TLS_PORT:-6006}`

Channel semantics in this setup:
- `4000` (`litellm_clean`): direct provider path (`ollama`), intended baseline path.
- `4001` (`litellm_chaos`): edge proxy path via `toxiproxy` and provider path via `toxiproxy`.

Direct backend access from `dev` (for example `http://litellm_clean:${LITELLM_INTERNAL_PORT}`) is intentionally blocked by network segmentation.

**Exception — `sysbox_bash`:** `dev` also joins `backend_core` and receives `SBASH_BASE_URL=http://sysbox_bash:${SBASH_PORT}` for the Bash sandbox HTTP API. This is direct HTTP on the Compose network, not via Caddy. Container env uses `SBASH_*` names (not `SYSBOX_*`) because Sysbox reserves `SYSBOX_` for runtime configuration.

Sandbox API checks:

```bash
make sysbox-bash-api-smoke
make sysbox-bash-sessions
```

`sysbox-bash-api-smoke` exercises the API without LangGraph. `sysbox-bash-sessions` lists active managed inner containers through host-side Compose/Docker inspection for lab recovery visibility; it is not a Sandbox HTTP API endpoint.

The local CA is generated by `certs_init` into `./.state/certs/.caroot/rootCA.pem`.
The `dev` container imports this CA into its own trust store at startup (container-local trust only, no automatic host trust changes).

### JupyterLab URL (dev)

After `make up`, open JupyterLab from the host (substitute values from `container/compose/.env`):

```text
http://<HOST_BIND_IP>:<DEV_JUPYTER_PORT>/lab?token=<JUPYTER_TOKEN>
```

Set `JUPYTER_TOKEN` in `.env` (see `.env.example`); restart `dev` after changing it (no dev-image rebuild). Script/Dockerfile changes need `make dev-image-build` first — see `container/dev-image/README.md` → **Notebook Mode** → *Restart vs. image rebuild*.

### Notebook API key environment injection (dev)

For notebooks in `src/assorted`, the `dev` container now injects API keys into environment variables at startup:

- Source of truth: `./.state/keys/keys.local.json`
- Runtime exporter: `./scripts/dev/export-secrets-env.sh`
- Injection point: `dev` container startup before Jupyter is launched
- Restart behavior: key rotation requires restarting the `dev` container (for example `make dev-container-restart`)

Exposed variables in notebook runtime include:

- `MODEL_API_KEY_DEV`, `MODEL_API_KEY_STAGE`, `MODEL_API_KEY_PROD`, `MODEL_API_KEY_USER1`, `MODEL_API_KEY_USER2`
- `MODEL_BASE_URL_CLEAN`, `MODEL_BASE_URL_CHAOS`, `TOXIPROXY_URL` (set in `.env` — see `.env.example`)
- `PHOENIX_COLLECTOR_ENDPOINT`, `PHOENIX_APP_PROJECT_NAME` (dev compose maps the latter to `PHOENIX_PROJECT_NAME` for tracing)

No API key aliases are provided in this strict mode (`API_KEY`, `LITELLM_API_KEY`, `LITELLM_API_KEY_*` are intentionally absent).

Quick notebook check:

```python
import os
print("MODEL_API_KEY_DEV set:", bool(os.getenv("MODEL_API_KEY_DEV")))
print("MODEL_API_KEY_STAGE set:", bool(os.getenv("MODEL_API_KEY_STAGE")))
print("MODEL_BASE_URL_CLEAN:", os.getenv("MODEL_BASE_URL_CLEAN"))
print("MODEL_BASE_URL_CHAOS:", os.getenv("MODEL_BASE_URL_CHAOS"))
```

Strictness can be tuned with `DEV_KEYS_STRICT` (`1` default, fail on missing required keys; `0` warns and continues).

### Notebook imports from `src/` (dev container only)

Course notebooks under `src/assorted` may import shared modules (for example `src.reducer`). The dev service mounts only `src` at `/workspace/src`; Jupyter’s working directory is usually the notebook folder, so `from src.…` fails until the repo root is on `sys.path`.

First code cell when you need `src.*` imports (Cursor/kernel in `dev`):

```python
import sys
sys.path.insert(0, "/workspace")
```

Example: `from src.reducer.base_reader import BaseReader`

Not maintained for bare-metal clones or other layouts; use the dev container for the course.

## Devcontainer Wrapper Contract (MVP experiment)

This repository includes a compose-first wrapper experiment for command/session semantics on service `dev`.

- `./scripts/dev/cmd.sh`: one-shot execution in `dev` (state between calls is undefined)
- `./scripts/dev/session.sh`: interactive/stateful session in `dev`
- Wrapper config source of truth: `./dev-wrapper.yaml`
- Shared runtime env bootstrap: `./scripts/dev/bootstrap-env.sh`
  - Used by `dev-cmd`, `dev-session`, and container startup (`keepalive.sh`)
  - Delegates secret generation to `./scripts/dev/export-secrets-env.sh` and sources `${DEV_SECRETS_ENV_FILE:-/tmp/dev-secrets.env.sh}`
- Policy header is emitted by wrappers for traceability:
  - `mode=dev-cmd|dev-session`
  - `backend=compose`
  - `service=dev`

The wrapper commands still target the `dev` compose service with `src/` mounted at `/workspace/src`.
Direct `docker compose exec ...` remains valid for diagnostics, but it does not guarantee the wrapper/bootstrap runtime env setup.

### Optional Pylint (manual tool)

`pylint` is available in the dev runtime as an optional hygiene tool.
It is not auto-run by wrappers, Make targets, or notebook startup.
Always pass a target path explicitly when invoking it.

Project config lives in `src/.pylintrc` (explore-friendly defaults: no docstring nagging, no line-length checks, and similar).
Pylint discovers config by walking upward from the current working directory.
The score is informational only; do not optimize for 9.x vs 10.x.

#### `/workspace/src` vs `/workspace` (important)

These two invocation styles are **not equivalent**:

| Where you run | Example | Typical effect |
|---|---|---|
| `/workspace/src` | `pylint reducer/base_reader.py` | Uses `src/.pylintrc`; fewer style messages; often higher score |
| `/workspace` | `pylint src/reducer/base_reader.py` | Often misses `src/.pylintrc`; closer to pylint defaults; more messages (docstrings, import order, design hints) and often lower score |

Use `/workspace/src` as the default project run.
Use `/workspace` when you intentionally want a stricter second opinion (for example missing docstrings or import-order findings).

Shared modules under `src/reducer` use relative imports (`from .base import ...`).
Keep `src/__init__.py` and `src/reducer/__init__.py` present so pylint and runtime imports agree on package context.

#### Examples (host wrapper)

Default project run (recommended):

```bash
./scripts/dev/cmd.sh /bin/bash -lc 'cd /workspace/src && pylint reducer/base_reader.py'
./scripts/dev/cmd.sh /bin/bash -lc 'cd /workspace/src && pylint reducer'
```

Stricter exploration run (more findings, including docstrings/imports):

```bash
./scripts/dev/cmd.sh /bin/bash -lc 'cd /workspace && pylint src/reducer/base_reader.py'
```

Same project rules from `/workspace` (explicit config path):

```bash
./scripts/dev/cmd.sh pylint --rcfile=/workspace/src/.pylintrc /workspace/src/reducer/base_reader.py
```

Errors only:

```bash
./scripts/dev/cmd.sh /bin/bash -lc 'cd /workspace/src && pylint --errors-only reducer/base.py'
```

When a score looks surprisingly low, inspect details:

```bash
pylint --reports=y reducer/base_reader.py
pylint --help-msg=E0402
```

#### Ruff (lint + format)

Project config: `src/pyproject.toml` (`extend-select = ["I"]` for isort-style import sorting).

**Check only (repo root or this directory):** lint without applying fixes:

```bash
make ruff-check
```

**Lint + fix + format:**

```bash
make ruff
```

From the repository root both targets delegate to `container/compose` and run via `./scripts/dev/cmd.sh` in `/workspace/src` (`ruff check .` vs `ruff check --fix .` then `ruff format .`). Notebooks (`*.ipynb`) are excluded via `src/pyproject.toml` (`extend-exclude`).

Manual equivalent (check only):

```bash
./scripts/dev/cmd.sh ruff check .
```

**Targeted import-order checks** (inside `dev`, cwd `/workspace/src`):

```bash
# check import order only
ruff check --select I reducer/base_reader.py

# apply import fixes for one file
ruff check --select I --fix reducer/base_reader.py
```

Via host wrapper (equivalent to running in `/workspace/src`):

```bash
./scripts/dev/cmd.sh ruff check --select I reducer/base_reader.py
./scripts/dev/cmd.sh ruff check --select I --fix reducer/base_reader.py
```

```env
OLLAMA_DATA_DIR=./.state/ollama_data
KEYS_LOCAL_FILE=./.state/keys/keys.local.json
HOST_BIND_IP=127.0.0.1
DEV_JUPYTER_PORT=8888
JUPYTER_TOKEN=change_me
DEV_STREAMLIT_PORT=8501
HEALTHCHECK_INTERVAL=120s
HEALTHCHECK_INTERVAL_BOOT=3s
POSTGRES_PORT=5432
POSTGRES_LITELLM_DB=litellm
POSTGRES_LITELLM_USER=litellm
POSTGRES_LITELLM_PASSWORD=change_me
POSTGRES_PHOENIX_DB=phoenix
POSTGRES_PHOENIX_USER=phoenix
POSTGRES_PHOENIX_PASSWORD=change_me
POSTGRES_TOOLBERT_DB=toolbert
POSTGRES_TOOLBERT_USER=toolbert
POSTGRES_TOOLBERT_PASSWORD=change_me
DATABASE_URL=postgresql://${POSTGRES_LITELLM_USER}:${POSTGRES_LITELLM_PASSWORD}@postgres:${POSTGRES_PORT}/${POSTGRES_LITELLM_DB}
UI_USERNAME=admin
UI_PASSWORD=change_me
LITELLM_PLATFORM=linux/amd64
OLLAMA_CONTAINER_PORT=11434
OLLAMA_HOST_PORT=11435
LITELLM_PORT=4000
LITELLM_CHAOS_PORT=4001
LITELLM_INTERNAL_PORT=4000
LITELLM_DEFAULT_TIMEOUT=420
LITELLM_MASTER_KEY=frozenlips
OLLAMA_HOST=http://ollama:${OLLAMA_CONTAINER_PORT}
OLLAMA_MODELS=nomic-embed-text:latest llama3.2:3b
OLLAMA_INIT_MODE=pull_missing
OLLAMA_PULL_OPTIONS=
OLLAMA_RUN_OPTIONS=
OLLAMA_RUN_PROMPT=Say hello.
OLLAMA_RETRY_MAX_ATTEMPTS=0
KEYS_INIT_MODE=required
GEMINI_API_KEY=
GROQ_API_KEY=
JSON_LOGS=true
PHOENIX_PORT=6006
PHOENIX_UI_TLS_PORT=6006
PHOENIX_OTLP_GRPC_PORT=4317
PHOENIX_WORKING_DIR=/mnt/data
PHOENIX_DEFAULT_RETENTION_POLICY_DAYS=30
PHOENIX_COLLECTOR_HTTP_ENDPOINT=http://phoenix:6006/v1/traces
PHOENIX_PROJECT_NAME=litellm-proxy
PHOENIX_PROJECT_NAME_CLEAN=litellm-clean
PHOENIX_PROJECT_NAME_CHAOS=litellm-chaos
PHOENIX_API_KEY=
PHOENIX_COLLECTOR_ENDPOINT=https://caddy:6006/v1/traces
PHOENIX_APP_PROJECT_NAME=langgraph-course
MODEL_BASE_URL_CLEAN=https://caddy:4000
MODEL_BASE_URL_CHAOS=https://caddy:4001
OLLAMA_API_BASE_CLEAN=http://ollama:${OLLAMA_CONTAINER_PORT}
OLLAMA_API_BASE_CHAOS=http://toxiproxy:${TOXIPROXY_OLLAMA_LISTEN}
TOXIPROXY_ADMIN_PORT=8474
TOXIPROXY_EDGE_LISTEN=11111
TOXIPROXY_OLLAMA_LISTEN=11112
```

Model data is persisted on the host in `./.state/ollama_data` (configurable via `OLLAMA_DATA_DIR`).
Phoenix trace data is persisted in `./.state/phoenix_data`.
Phoenix SQL metadata is stored in the same Postgres server as LiteLLM, but with a dedicated
database/user pair (`POSTGRES_PHOENIX_DB`, `POSTGRES_PHOENIX_USER`). A third database
(`POSTGRES_TOOLBERT_DB`) is provisioned for course RAG / pgvector work in `dev`.
The Postgres service runs with pgvector and creates the `vector` extension idempotently in
LiteLLM, Phoenix, and Toolbert databases during `postgres_init_identities`.
LiteLLM and Phoenix are intentionally separated at config level; you can still map both to one SQL user manually if desired.
Published ports are bound to `HOST_BIND_IP` (default `127.0.0.1` for localhost-only access).
Set `HOST_BIND_IP=0.0.0.0` only if you explicitly want LAN access.
Only Caddy (TLS edge) is published by default; LiteLLM and Ollama stay private inside the Compose network.
If you want to expose Ollama, use `docker-compose.ollama-expose.yml` and set `OLLAMA_HOST_PORT`.
To keep LiteLLM UI redirects scheme-correct behind TLS, Caddy forwards `X-Forwarded-*` headers and
LiteLLM trusts proxy forwarding (`FORWARDED_ALLOW_IPS=*` in Compose).
`HEALTHCHECK_INTERVAL` is the steady-state healthcheck interval for Postgres, Ollama and LiteLLM (defaults to `120s` in examples).
TLS certificates are generated by the one-shot `certs_init` container into `./.state/certs` (self-contained flow, no mandatory host tooling).
If you do not trust the generated local CA on the host, use clients that allow untrusted local certs (for example `curl -k`).

For faster startup, services can use `HEALTHCHECK_INTERVAL_BOOT` as healthcheck `start_interval` (defaults to `3s`).
This keeps startup probes fast while preserving a quieter steady-state cadence from `HEALTHCHECK_INTERVAL`.

If you want quieter steady-state checks at the expense of slower startup detection, set `HEALTHCHECK_INTERVAL_BOOT` closer to `HEALTHCHECK_INTERVAL`.
On SELinux-enabled hosts, the bind mount uses `:z` relabeling in Compose so Ollama can write to `/root/.ollama`.
The LiteLLM config bind mount also uses `:z` so `/app/config.yaml` is readable on SELinux hosts.
Model initialization is handled by `./init/ollama/models.sh`, mounted into `ollama_init_models`.
In this MVP, successful model init is a hard prerequisite: `litellm_clean` and `litellm_chaos` start only after
`ollama_init_models` completed successfully.
By default (`OLLAMA_INIT_MODE=pull_missing`), models are only pulled if missing from local Ollama storage.
Use `OLLAMA_INIT_MODE=pull` to always refresh/check each configured model at startup.
For debug/smoke runs you can set `OLLAMA_INIT_MODE=run`, which executes
`ollama run` for each configured model. Use `OLLAMA_INIT_MODE=none` to skip init.
`OLLAMA_RUN_OPTIONS` is used for `run`.
`OLLAMA_PULL_OPTIONS` is used for `pull` and `pull_missing`.
`OLLAMA_RETRY_MAX_ATTEMPTS` controls per-model retry budget during init (`0` = unlimited retries).
Default pull set: `nomic-embed-text:latest` and `llama3.2:3b` (see `.env.example`).
Add larger models in `.env` (`OLLAMA_MODELS`) if you have RAM — for example `deepseek-r1:7b`
is listed in the commented optional line in `.env.example`.

### Ollama Runtime Tuning (CPU-friendly defaults)

This project uses explicit Ollama runtime controls to reduce local CPU churn and model swap pressure:

- `OLLAMA_DEBUG` (default `0`): enables verbose `ollama serve` logs when set to `1`.
- `OLLAMA_NUM_PARALLEL` (default `1`): limits concurrent generations per server process.
- `OLLAMA_MAX_QUEUE` (default `2`): caps queued requests before backpressure is visible.
- `OLLAMA_MAX_LOADED_MODELS` (default `1` in env examples): bounds simultaneously loaded models.
- `OLLAMA_KEEP_ALIVE` (default `1m` in local `.env`): unloads idle runners sooner to reduce post-abort residue.

Tradeoff for CPU-only machines: lower values are calmer and more stable, but can reduce burst throughput.

Runtime tuning here does not change which models are listed in `OLLAMA_MODELS`; that list lives in `.env.example` / your `.env`.

Focused runtime log checks:

```bash
docker compose logs -f --tail=300 ollama
docker compose logs -f --tail=300 litellm_clean
docker compose logs -f --tail=300 litellm_chaos
```

With `OLLAMA_DEBUG=1`, verify `ollama` logs contain debug-level server details during requests.
LiteLLM Admin UI is enabled at `https://localhost:${LITELLM_PORT:-4000}/ui` using
`UI_USERNAME` / `UI_PASSWORD` and requires the local Postgres service.
`LITELLM_DEFAULT_TIMEOUT` is applied via LiteLLM CLI `--request_timeout` (seconds) as the proxy default timeout.
In this local setup it is intentionally set to `420` seconds for long-running experiments, while queue/retry controls prevent
runaway request buildup.
`LITELLM_MASTER_KEY` is read from `.env` (single source of truth for the admin key), enables API key auth
for OpenAI-style `/v1` calls (`Authorization: Bearer <key>`), and is required for LiteLLM key management endpoints.
This repository uses `frozenlips` as a deliberately insecure local dev default; change it for any shared/non-local setup.
Gemini usage in this setup is intended for the Google AI Studio free tier (state: 04/2026).
Available Gemini models can change over time; if a configured model alias stops working, update `config/litellm/litellm.yaml`.
You can list currently available models via API:

```bash
curl "https://generativelanguage.googleapis.com/v1beta/models?key=<api_key>"
```

You can also verify availability/entitlements in your Google AI Studio web account.
Gemini requests in this setup are rate-limited/throttled in LiteLLM config to align with free-tier limits (state: 04/2026):
- `gemini-2.5-flash-lite`: `rpm: 12`, `tpm: 1000000`
- `gemini-2.5-pro`: `rpm: 2`, `tpm: 32000`
- router retry behavior: `num_retries: 2`

Gemini overload strategy in this setup: retries are intentionally conservative so overload fails fast instead of creating
large retry cascades under multi-client contention. This protects shared free-tier capacity and keeps latency more predictable.

Important: these are global provider/key limits. They apply across all connected clients sharing this LiteLLM instance
(CLI tools, apps, and agent frameworks). If one client consumes the budget, others will be throttled/retried as well.
Fair-use recommendation: keep `gemini-2.5-pro` for interactive/high-value requests and route background/batch/agent traffic
preferably to `gemini-2.5-flash-lite` to reduce contention on shared free-tier limits.

### Overload Protection (Ollama-only example scope)

This project applies overload protection **only to local Ollama models** as an explicit example scope.
Cloud provider models keep their own provider-specific behavior.

- Ollama models are configured with `max_retries: 0` in LiteLLM model config to prevent retry cascades.
- Ollama runtime queue pressure is limited via `OLLAMA_MAX_QUEUE=2`.
- Loaded model churn is bounded via `OLLAMA_MAX_LOADED_MODELS=1` for stricter local admission control.
- Idle runner lifetime is shortened with `OLLAMA_KEEP_ALIVE=1m` to reduce lingering load after aborted clients.
- Local proxy timeout budget is `LITELLM_DEFAULT_TIMEOUT=420` seconds for experimentation.

Known limitation: if a client disconnects abruptly, upstream cancellation may still be best-effort depending on
LiteLLM/Ollama internals; this setup focuses on bounding overload impact (queue + retries), not guaranteeing
instant cancellation in every path.

Streaming policy (soft; both API modes supported):

- non-streaming stays supported (`stream=false` calls are valid)
- streaming is recommended for local `ollama_chat/*` workloads
- reason: better early disconnect propagation in client timeout/abort scenarios
- reason: lower chance of long-lived zombie inference after client exits
- trade-off (agents): more chunk/event handling in client loop
- trade-off (agents): parser must detect message/block boundaries robustly
- trade-off (agents): partial/intermediate fragments need output hygiene

Model examples currently configured:
- Ollama chat: `ollama_chat/llama3.2:3b`, `ollama_chat/deepseek-coder:6.7b`, `ollama_chat/qwen2.5-coder:7b`,
  `ollama_chat/qwen2.5:1.5b`, `ollama_chat/llama3.2:1b`, `ollama_chat/llama3.1:8b`, `ollama_chat/mistral:7b`,
  `ollama_chat/mistral-nemo:12b`
- Ollama embeddings: `ollama/nomic-embed-text:latest`
- Gemini: `gemini-2.5-flash-lite`, `gemini-2.5-pro`
- Groq: `groq-llama-3.3-70b`, `groq-llama-3.1-8b-instant`
- Mistral API: `mistral-small`

Optional larger Ollama preload set (commented example in `.env.example`):
- `nomic-embed-text:latest deepseek-coder:6.7b qwen2.5-coder:7b qwen2.5:1.5b llama3.2:3b llama3.2:1b llama3.1:8b mistral:7b mistral-nemo:12b deepseek-r1:7b`
Virtual key startup sync is controlled via `KEYS_INIT_MODE`:
- `required` (default): key sync failures are treated as failures in the one-shot key init container.
- `optional`: key sync failures are logged, but the init container exits successfully.
- `off`: skip automatic virtual key startup sync.
LiteLLM container healthcheck uses `/health/readiness` (no model inference).
UI spend logs are stored in Postgres and limited by LiteLLM retention settings
(`maximum_spend_logs_retention_period: 7d`, cleanup interval `1d`).

### Data retention (lab)

| Component | Mechanism | Lab value | Notes |
|-----------|-----------|-----------|-------|
| Phoenix traces | `PHOENIX_DEFAULT_RETENTION_POLICY_DAYS` (required in `.env`) | `30d` | Only service with native trace-retention-days setting; Phoenix UI can override per project. |
| LiteLLM spend logs | `maximum_spend_logs_retention_period` in `litellm.yaml` | `7d` | Shorter on purpose because spend logs may include prompts. |
| Ollama | Model cache on disk + `OLLAMA_KEEP_ALIVE` | no age TTL | `OLLAMA_KEEP_ALIVE` unloads idle runners from RAM; it is not log/trace retention. |
| Container stdout | Docker `json-file` rotation | `10m × 3` | Global in compose logging options. |
| Full wipe | `make state-prune` | manual | Deletes `.state/*` including Postgres, Phoenix, and Ollama model cache. |

Observability and model cache data are disposable lab state. Explicit TTLs are a safety net against silent growth, while `make state-prune` remains the intentional reset path.

## Start

```bash
make up          # includes state-init + certs-generate
# Optional: trust generated local CA on host
# make trust-certs-host
```

Optional: expose Ollama API on host (still bound to `HOST_BIND_IP`):

```bash
make up
make ollama-expose
```

Open LiteLLM UI:

```bash
xdg-open "https://localhost:${LITELLM_PORT:-4000}/ui"
```

Open Phoenix UI:

```bash
xdg-open "https://localhost:${PHOENIX_UI_TLS_PORT:-6006}"
```

## Logs / Tracing

```bash
make logs
```

`make logs` follows **all compose services** while the stack is still coming up, then automatically switches to
**litellm_clean-only** logs once the `litellm_clean` service reports **healthy** (so you still see Postgres/Ollama/init output
during startup).

During the “all services” phase, logs are followed **without `--tail`**, so you do not miss early startup lines.
After `litellm_clean` becomes healthy, the follow switches to `litellm_clean` with `--tail=200` to keep the focused stream readable.

`make logs` uses `docker compose ps --format json | jq ...` when available (requires `jq`).

If you want the classic behavior (always all services):

```bash
make logs-all
```

Quick status / process view:

```bash
make ps
make top
```

Model init logs:

```bash
make logs-init-models
```

Virtual key init logs:

```bash
make logs-init-keys
```

JSON logs are enabled via `JSON_LOGS=true` (container env) and `litellm_settings.json_logs: true` in `config/litellm/litellm.yaml`.
Docker log rotation is enabled for all services via Compose (`max-size: 10m`, `max-file: 3`).
Use `make phoenix-health` for a quick local endpoint check.
Phoenix UI is served via Caddy TLS on `https://localhost:${PHOENIX_UI_TLS_PORT:-6006}`.
The direct host HTTP publish on `6006` is disabled to avoid non-TLS UI access.
If you need local OTLP HTTP ingestion from host tools, use the TLS endpoint
`https://localhost:${PHOENIX_UI_TLS_PORT:-6006}/v1/traces` (or OTLP gRPC on `${PHOENIX_OTLP_GRPC_PORT:-4317}`).

Phoenix is complementary to LiteLLM logs in this setup:
- LiteLLM logs: operational request/response and proxy behavior (`make logs`).
- Phoenix traces: application or agent execution traces via OTEL/OpenInference.

The LiteLLM proxy callback to Phoenix is enabled in `config/litellm/litellm.yaml` via
`litellm_settings.callbacks: ["arize_phoenix"]`.
For this callback, the LiteLLM container must receive:
- `PHOENIX_COLLECTOR_HTTP_ENDPOINT` (self-hosted in this compose: `http://phoenix:6006/v1/traces`)
- `PHOENIX_PROJECT_NAME` (recommended; in split-mode use distinct values for clean and chaos channels)
- `PHOENIX_API_KEY` (required for Phoenix Cloud, optional for local self-hosted)

LiteLLM does not auto-instrument all upstream client logic. Phoenix sees what clients export.

### LangGraph traces (app-side)

| Source | Phoenix project (typical) | What you see |
|--------|---------------------------|--------------|
| LiteLLM `arize_phoenix` callback | `litellm-clean` / `litellm-chaos` | Flat proxy request traces |
| App instrumentation (`src/tracing/phoenix.py`) | `langgraph-course` (`PHOENIX_APP_PROJECT_NAME`) | One root trace per `graph.ainvoke` with nested node/subgraph/LLM spans |

Course nodes call **`AsyncOpenAI`** against the LiteLLM proxy (not the `litellm` Python SDK). Use **`enable_langgraph_tracing()`** (LangChain + OpenAI OpenInference instrumentors), not `LiteLLMInstrumentor`.

Dev container: set `PHOENIX_COLLECTOR_ENDPOINT` and `PHOENIX_APP_PROJECT_NAME` in `container/compose/.env` (see `.env.example`). Use **`https://caddy:6006/v1/traces`** (not `http://` — port 6006 is TLS-only) or **`http://phoenix:6006/v1/traces`**. `enable_langgraph_tracing()` applies `/certs/.caroot/rootCA.pem` for HTTPS (same as LiteLLM). Host browser UI: `https://localhost:6006`.

**Tip:** In [`src/assorted/session5/graphtrace.ipynb`](../../src/assorted/session5/graphtrace.ipynb), run the **first code cell** before any `langgraph` / `llm_nodes` import. After experimenting in the kernel: **Restart kernel → Run All**.

**Duplicate LLM visibility is expected:** proxy callback spans may appear under `litellm-clean` while instrumented client spans appear as children under `langgraph-course` — different projects, not a bug.

Verification:

```text
make up  # rebuilds dev image when requirements.in changed
# Jupyter: session5/graphtrace.ipynb → Restart kernel → Run All
# Phoenix UI: https://localhost:6006 → project langgraph-course → one root trace with nested children (exact span names may vary)
```

Quick callback smoke flow for proxy-only traces: `make up` -> `make smoke-chat` -> Phoenix UI under the LiteLLM project name.

## Dev maintenance (minimal)

- Postgres autovacuum is enabled by default; for this standalone dev setup no manual vacuum jobs are required.
- If the local DB state is broken or too large, use the centralized state reset:

```bash
make state-prune
make up
```

- For pgvector rollouts in this local setup, `.state/postgres_data` is considered disposable.
  When switching Postgres image families (for example Alpine -> pgvector image), reset DB state and recreate:

```bash
make state-prune
make up
```

- Re-run model preload one-shot container manually when needed:

```bash
make up
```

- If preload fails, inspect the one-shot container logs:

```bash
make logs-init-models
```

## Virtual Keys (Client Separation)

Use Virtual Keys to identify clients separately in logs/spend tracking while keeping one admin master key.

- `LITELLM_MASTER_KEY` (from `.env`) = admin key (do not use for app clients).
- Virtual keys = per-client tokens used in app requests.
- This MVP intentionally supports only five reserved virtual key names in `${KEYS_LOCAL_FILE}`:
  `dev`, `stage`, `prod`, `user1`, `user2`. Any other entries are removed on sync/init.
- Deploying new keys is modeled as **replace/rotate** for those fixed names (not creating new users).
- When syncing keys into LiteLLM, `key_alias` is set to the reserved name (e.g. `dev`) so the Admin UI / log filters
  have a stable human-readable identifier (separate from the masked `key_name` LiteLLM derives from the secret).

Generate the default local client keys (`dev`, `stage`, `prod`, `user1`, `user2`):

```bash
make keys-generate
```

Sync the five reserved key pairs from `${KEYS_LOCAL_FILE}` into LiteLLM (file is authoritative for those names):

```bash
make keys-sync
```

Force rotate/recreate all five keys:

```bash
make keys-overwrite
```

Show current locally stored key map:

```bash
make keys-show
```

Generated keys are stored in `${KEYS_LOCAL_FILE}` (under `.state`, gitignored). Keep this file local only.
At startup, the one-shot `litellm_init_keys` container syncs `${KEYS_LOCAL_FILE}` automatically:
- If the file is missing, it is created with default entries (`dev`, `stage`, `prod`, `user1`, `user2`).
- If the file exists, only the reserved five entries are kept; then LiteLLM is updated to match the file.

Before `litellm_clean` starts, `litellm_keys_file_gate` validates `${KEYS_LOCAL_FILE}` (JSON + required five reserved names) and
fills in any missing reserved entries. This makes the common case safe: **file exists, LiteLLM DB keys were wiped** —
on the next successful `litellm_clean` health + init run, keys are recreated from the file contents.

If you wipe LiteLLM keys manually while the stack is already running, run:

```bash
make keys-sync
```

## Smoke checks

Ollama:

```bash
docker compose exec ollama ollama list
```

If exposed via override file, Ollama API is reachable at:

```bash
curl -s "http://localhost:${OLLAMA_HOST_PORT:-11435}/api/tags" | head
```

LiteLLM (health):

```bash
curl -k -s "https://localhost:${LITELLM_PORT:-4000}/health" | head
```

Chat completion (OpenAI-style):

```bash
make smoke-chat
```

`make smoke-chat` currently targets `ollama_chat/llama3.2:3b` in `Makefile`.

Embeddings:

```bash
make smoke-embeddings
```

Devcontainer wrapper smoke tests:

```bash
make dev-container-smoke
# or:
make dev-container-smoke-wrapper
make dev-container-smoke-clean
```

## Note on RAM usage

This MVP is **lazy / on-demand** at runtime: models are loaded into RAM/VRAM when first used by a request.
With default `OLLAMA_INIT_MODE=pull_missing`, missing models are pre-downloaded to disk at startup but not inferred.
Ballpark host RAM and cloud-model fallback: [getting-started appendix](../../docs/getting-started.md#host-ram-local-models).


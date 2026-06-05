# Dev Image (Isolated v1)

This folder contains an independent Python runtime image for development work.
It is also the runtime image for compose service `dev`.

## Scope

- Python runtime in container
- Default interactive user is `dev` (non-root)
- `sudo` is available for `dev` with `NOPASSWD`
- `venv` support
- Agent baseline dependencies from `src/requirements.in`
- `ruff` available in container baseline
- `ipykernel` available in container baseline
- `jupyterlab` available in container baseline
- LiteLLM access via OpenAPI-compatible HTTP endpoints

## Non-Goals

- No Git in container (Git stays on host)
- No changes to `container/compose` smoke-test setup
- No speculative ML package preinstalls

## Build

```bash
docker build -t course-llm-dev:v1 -f container/dev-image/Dockerfile .

# Run in detached mode; container stays alive via trap-based keepalive PID 1.
docker run -d --name course-llm-dev course-llm-dev:v1
```

Important: build from repository root context (`.`). The Dockerfile copies files from `src/` and `container/dev-image/`, which are not available when building with `container/dev-image` as context.
If you use the root `Makefile`, run `make dev-image-build` (or just `make up`, which builds it automatically).

## Keepalive Runtime

- Default container command is `/usr/local/bin/keepalive.sh`.
- The script traps `SIGINT`/`SIGTERM` and exits cleanly.
- Use `docker exec -it course-llm-dev bash` for interactive sessions as `dev`.
- Use `docker exec -it --user root course-llm-dev bash` for direct root shell (optional).

## Security Note About Sudo

`sudo` with `NOPASSWD` is enabled here for development convenience only.
In environments where an autonomous agent can execute commands, this increases risk because privilege escalation becomes trivial.
Prefer removing `sudo` (or requiring explicit approval boundaries) outside local trusted development usage.

## Quick Runtime Checks

```bash
whoami
sudo -n whoami
python --version
ruff --version
```

## Notebook Mode (compose `dev` service)

After `make up`, JupyterLab starts automatically in the `dev` container background (`keepalive.sh` → `start-notebook.sh`).

### Browser URL (from the host)

Set `HOST_BIND_IP`, `DEV_JUPYTER_PORT`, and `JUPYTER_TOKEN` in `container/compose/.env` (see `.env.example`). After `make up`, open:

```text
http://<HOST_BIND_IP>:<DEV_JUPYTER_PORT>/lab?token=<JUPYTER_TOKEN>
```

Example with defaults from `.env.example`:

```text
http://127.0.0.1:8888/lab?token=change_me
```

| Setting | `.env` variable | Example (`.env.example`) |
|--------|-----------------|---------------------------|
| Host bind | `HOST_BIND_IP` | `127.0.0.1` |
| Host port | `DEV_JUPYTER_PORT` | `8888` |
| Auth token | `JUPYTER_TOKEN` | set in `.env` (placeholder in example: `change_me`) |
| Password | — | none (`--ServerApp.password=''`) |

Compose passes `JUPYTER_TOKEN` into the `dev` container at runtime; `start-notebook.sh` (copied into the image at build time) reads that variable when Jupyter starts.

**Restart vs. image rebuild**

| What changed | What to run |
|--------------|-------------|
| `JUPYTER_TOKEN`, `DEV_JUPYTER_PORT`, or `HOST_BIND_IP` in `container/compose/.env` | `make dev-container-restart` (or `make up`) — no image rebuild |
| `src/requirements.in` (new packages) | `make dev-image-rebuild` + `make dev-container-restart` (or manual `pip install -r` in `/workspace/src/.venv`, then restart Jupyter kernel) |
| `container/dev-image/scripts/start-notebook.sh` or `container/dev-image/Dockerfile` | `make dev-image-build`, then restart `dev` — script changes are not picked up from the host mount |

Open the full URL including `?token=…` in one step. Without the token query parameter, Jupyter prompts for the token manually.

### Verify inside the container

```bash
docker compose -f container/compose/docker-compose.yml --env-file container/compose/.env exec dev jupyter server list
```

Container logs also print a startup line (token may be redacted as `...`).

The default notebook kernel is auto-registered from `/workspace/src/.venv`.

More notebook/runtime notes: `container/compose/README.md` (API keys, `src` imports).

## TLS Trust Inside `dev`

When running via compose, `./.state/certs` is mounted to `/certs` in `dev`.
At container startup, `keepalive.sh` calls `/usr/local/bin/import-local-ca.sh` to import:

- source: `/certs/.caroot/rootCA.pem`
- target: `/usr/local/share/ca-certificates/dev-local-root-ca.crt`

Then `update-ca-certificates` is executed so HTTPS calls from `dev` trust the local Caddy certificate chain.
This trust import is container-local and does not modify host trust settings.

## Spontaneous Package Installs (no rebuild)

```bash
docker compose -f container/compose/docker-compose.yml --env-file container/compose/.env exec dev bash
source /workspace/src/.venv/bin/activate
pip install <package>
```

This updates the runtime used by notebooks immediately.
Promote stable dependencies later by adding them to `src/requirements.in`.

## Requirements Split

- `src/requirements.in`: baseline agent development dependencies (`ruff`, `ipykernel`, `jupyterlab`)

## LiteLLM OpenAPI Config

Use environment variables from `.env.example`.

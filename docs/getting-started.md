# Getting started

## 1. What you are getting

You get a **lab** on your machine to develop and run **agents in Python**. You drive them
from the **`dev`** runtime (scripts, modules, or notebooks — same Python environment).
There is no end-user product UI — the lab is for building and running agent code, not
shipping a clickable app.

`make up` starts the full Compose stack, including **`dev`**. Two pillars hold the lab
together:

- **`dev` runtime** — Python, dependencies, and lab env vars inside the stack (not on the host)
- **Model access** — local models via Ollama by default; optional cloud models through LiteLLM when you add API keys

### 1.1 Prerequisites

- **Linux** — developed and tested on Linux only
- **Docker Engine** ≥ 25 and **Docker Compose** ≥ 2.20
- **Sysbox** (`sysbox-runc`) — required for `make up` because the stack includes the
  `sysbox_bash` sandbox service. Course exercises that **use** the sandbox start in
  **session 7**; sessions 1–6 do not depend on sandbox notebooks or
  `make sysbox-bash-api-smoke`.
- **Git** — clone this repository
- **Host tools** — terminal; a code editor (Cursor or VS Code recommended); a browser as fallback for JupyterLab
- **Python / ML stack** — runs inside **`dev`**, not on the host

## 2. What is in the lab

One or two sentences per piece — no wiring detail here.

| Component | Role |
|-----------|------|
| **`dev`** | Python runtime where agents and course code run; JupyterLab included as a workspace |
| **Ollama** | Local models (default path for the course) |
| **LiteLLM** | Unified OpenAI-compatible API, routing, timeouts, and logs; optional cloud models when keys are set |
| **Phoenix** | Trace observability for agent runs |
| **Postgres + pgvector** | Backing store for stack services; supports **RAG and vector search** from your Python and agent work in `dev` |
| **Caddy** | TLS inside the lab network |
| **Toxiproxy** | Network chaos for advanced experiments — skip on first run |

Ports, env vars, and stack detail: [Compose README](../container/compose/README.md).

## 3. The dev container (how you work)

The **`dev`** service is the lab’s Python runtime. It is **not** the VS Code “Dev Containers”
feature — there is no `.devcontainer/` here; it is simply the Compose service named `dev`.

**Edit on the host, run in the container.** Open `src/` in Cursor or VS Code on your machine.
The same files are what Python sees inside `dev`, because `src/` is **bind-mounted**
(`<repo>/src/` on disk = `/workspace/src/` in the container). Save on the host, rerun in
`dev` — no copy or sync step.

| On the host | Inside `dev` |
|-------------|----------------|
| Editor, `git`, `make up`, … | Python, venv, JupyterLab, lab env vars, TLS trust for API calls |

**Agents, scripts, and notebook kernels** all execute inside `dev`. A host Python on the
same folders will not have the lab API keys, base URLs, or CA — always run course code in
`dev`.

Image and runtime detail: [dev-image README](../container/dev-image/README.md).

## 4. Start the lab

From the repository root:

```bash
cp container/compose/.env.example container/compose/.env
# Edit container/compose/.env if needed (JUPYTER_TOKEN, passwords).
make up
make smoke-chat
```

**Success:** `make smoke-chat` completes without error. That checks the same model path your
agent code will use.

**First `make up` can take a long time** — images, certificates, and one-shot init jobs.
Ollama also **pulls models** on first start (`OLLAMA_INIT_MODE=pull_missing` in
`.env.example`). `make up` already runs certificate generation; no extra cert step.

**Default local chat model** for smoke tests and course work: `ollama_chat/llama3.2:3b`. That
is already the **practical floor** for this lab — slow on CPU and weak on harder prompts,
but enough for smoke checks and course demos. Most laptops will not benefit from “stepping
down” to a smaller local model.

If `llama3.2:3b` is too slow or will not run on your machine, see the
[appendix](#cloud-models-via-litellm) (RAM ballpark + cloud model setup).

Default model pull set in `.env.example`: `nomic-embed-text:latest` and `llama3.2:3b` only.
Larger models such as `deepseek-r1:7b` remain available via optional `OLLAMA_MODELS` lines in
`.env.example`.

## 5. First agent exercise — recommended (Cursor / VS Code)

**Goal:** run **agent code in Python** inside `dev`. The concrete first path is a course
notebook — same runtime as any script under `src/`.

1. Stack must be up (`make up`).
2. Connect your editor’s notebook extension to the running Jupyter server (one line — no
   Cursor-specific walkthrough here).
3. Use the Jupyter URL from [section 7](#7-services-with-a-web-ui) (full default URI there;
   change if you edited `container/compose/.env`).
4. Open [`src/assorted/session5/graphtrace.ipynb`](../src/assorted/session5/graphtrace.ipynb)
   (first-run exercise on the course parent-graph sketch). Run **cell 0 first**
   (tracing setup), then the rest top to bottom.
5. **Success:** the agent invoke completes without error.

Execution must stay in **`dev`**, not a bare host Python interpreter.

Contributor detail (dev-cmd, plans): [Editor and agent workflow](editor-and-agent-workflow.md).

## 6. First agent exercise — fallback (browser only)

Open the JupyterLab URL from [section 7](#7-services-with-a-web-ui) in your browser
(HTTP — avoids local TLS setup for the workspace). Run the same notebook as in section 5:
[`graphtrace.ipynb`](../src/assorted/session5/graphtrace.ipynb), cell 0 first.

After a successful run you can open Phoenix in the browser (section 7) to preview trace
trees — optional on first run.

## 7. Services with a web UI

Parts of the stack expose a browser UI. Default entry URLs match
[`container/compose/.env.example`](../container/compose/.env.example).

LiteLLM and Phoenix use HTTPS on localhost (local CA). If the browser warns about the
certificate, run `make trust-certs-host` (see [Compose README](../container/compose/README.md)).
After `cp …/.env.example …/.env`, they work as-is unless you changed `HOST_BIND_IP`,
`DEV_JUPYTER_PORT`, `JUPYTER_TOKEN`, or UI passwords.

| Service | Default URL (`.env.example`) | Login | What you see |
|---------|------------------------------|-------|--------------|
| **LiteLLM** | `https://localhost:4000/ui` | `admin` / `change_me` | Keys, models, proxy logs |
| **Phoenix** | `https://localhost:6006` | none (local stack) | Trace trees (e.g. `langgraph-course`) |
| **JupyterLab** | `http://127.0.0.1:8888/lab?token=change_me` | token in URL | Python workspace in `dev` |

Env mapping if you customize: `LITELLM_PORT` → LiteLLM host port; `PHOENIX_PORT` → Phoenix;
`HOST_BIND_IP` + `DEV_JUPYTER_PORT` + `JUPYTER_TOKEN` → JupyterLab; `UI_USERNAME` /
`UI_PASSWORD` → LiteLLM UI.

Internal wiring and extra ports: [Compose README](../container/compose/README.md).

## 8. Next steps

- [Course docs hub](course/README.md) — pipeline, error handling, module pointers
- [Course notebooks](../src/assorted/README.md) — sessions under `src/assorted/`
- [Compose README](../container/compose/README.md) — stack, env, Makefile targets

---

## Appendix

Extra detail for §4 — stay on this page; no need to read the Compose README first.

### Host RAM (local models)

Ballpark for the **default** pull set (`llama3.2:3b` + `nomic-embed-text`) on **CPU**
(no GPU offload):

| Host RAM | What to expect |
|----------|----------------|
| **16 GB+** | Default local path is realistic. Compose services use several GB; Ollama loads **one** model at a time (`OLLAMA_MAX_LOADED_MODELS=1` in `.env.example`). Expect slow tokens on CPU, but smoke and course demos should run. |
| **8 GB** | Tight. The stack alone can pressure memory; `llama3.2:3b` inference may swap heavily or fail. Prefer [cloud models](#cloud-models-via-litellm) rather than a smaller local model — sub-3B is not a useful course default. |
| **Disk** | ~2–3 GB for the default model files on disk (pulled once; not all loaded into RAM at once). |

Models are loaded **on first use**, not all at startup. First chat or embed request after
`make up` can still take a minute on a cold Ollama.

### Cloud models via LiteLLM

When local `llama3.2:3b` is too slow or does not run:

1. Create a provider key ([Google AI Studio](https://aistudio.google.com/apikey) for Gemini,
   [Groq console](https://console.groq.com/) for Groq — both have free tiers with limits).
2. Add to `container/compose/.env`:

   ```bash
   GEMINI_API_KEY=your_key_here
   # and/or
   GROQ_API_KEY=your_key_here
   ```

3. Reload LiteLLM so it sees the keys:

   ```bash
   make litellm-recreate
   ```

4. In your notebook or agent code, set the **LiteLLM model name** (not the raw provider
   string). Configured aliases in this repo:

   | LiteLLM `model` name | Provider | Good for |
   |----------------------|----------|----------|
   | `gemini-2.5-flash-lite` | Gemini | Default cloud choice — faster, higher free-tier quota |
   | `gemini-2.5-pro` | Gemini | Stronger, lower rate limits |
   | `groq-llama-3.1-8b-instant` | Groq | Fast small cloud model |
   | `groq-llama-3.3-70b` | Groq | Larger Groq option |

   Example in a notebook cell: `MODEL = "gemini-2.5-flash-lite"`. Calls still go through
   the same LiteLLM base URL and `MODEL_API_KEY_DEV` inside `dev` — only the model name
   changes.

5. `make smoke-chat` still checks **local** `ollama_chat/llama3.2:3b`. That is fine — your
   agent exercise proves the cloud path when invoke completes with your chosen `MODEL`.

Check the LiteLLM UI (`https://localhost:4000/ui`) if a cloud model returns auth or rate-limit
errors.

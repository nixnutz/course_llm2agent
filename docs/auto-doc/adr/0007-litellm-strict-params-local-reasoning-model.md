# 0007 - LiteLLM Drop Params, Client Compatibility, and Local Reasoning Model

- Status: Accepted
- Date: 2026-05-04
- OverheadSeconds: 0

## Context

LiteLLM can silently remove unsupported OpenAI-style parameters when `drop_params` is enabled, which hides
misconfiguration when experimenting with provider-specific options such as `reasoning_effort` mapped to Ollama.

Separately, generic chat models in the default local stack do not expose a clear separated reasoning trace suitable
for teaching and verifying the proxy path end-to-end.

**Revision (2026-05-04):** Strict `drop_params: false` improved visibility for bad parameters but caused widespread breakage with
OpenAI-compatible clients that send extra fields (for example embedding `encoding_format`) that Ollama backends reject.
`reasoning_effort` does **not** depend on `drop_params: false`; it is applied when LiteLLM supports it for the chosen
model. Compatibility-first proxy defaults were preferred over global strict mode.

**Revision (2026-06-05):** Default Ollama **pull** set trimmed for first-run RAM/disk: `nomic-embed-text:latest` +
`llama3.2:3b` only in `.env.example` / `MODELS_DEFAULT`. **`deepseek-r1:7b`** stays in LiteLLM config as an
**optional** local reasoning model (add via `OLLAMA_MODELS` when needed).

## Decision

- Set `litellm_settings.drop_params: true` in the shared LiteLLM configuration so heterogeneous OpenAI-compatible
  clients work against Ollama-backed routes without proxy 400s for dropped unsupported fields.
- Default Ollama **pull** list (`OLLAMA_MODELS` / `MODELS_DEFAULT`): **`nomic-embed-text:latest`** and
  **`llama3.2:3b`** — the practical local chat floor for this lab.
- Register **`ollama_chat/deepseek-r1:7b`** in LiteLLM for **optional** local thinking / reasoning when operators add
  `deepseek-r1:7b` to `OLLAMA_MODELS` (see commented example line in `.env.example`).
- Rely on the existing LiteLLM mapping from `reasoning_effort` to Ollama's thinking controls for reasoning-capable
  models; clients should send `reasoning_effort` via supported APIs (for example LangChain `ChatOpenAI` `model_kwargs`)
  and inspect message fields such as `reasoning_content` when present. When teaching or debugging reasoning, confirm
  behavior in responses or logs rather than relying on proxy errors for unsupported parameters.

This decision is currently in effect in production/dev workflow.

## Consequences

- OpenAI-style tooling (including embeddings calls that send `encoding_format`) is more likely to succeed through the
  proxy without client-specific workarounds.
- Unsupported parameters may be **dropped without error** when `drop_params` is enabled; validate `reasoning_effort` and
  similar knobs by inspecting model output and traces when that matters.
- First-time setup pulls only the default embed + 3B chat pair; adding `deepseek-r1:7b` (or other large models) is
  opt-in via `OLLAMA_MODELS` when disk/RAM allow.

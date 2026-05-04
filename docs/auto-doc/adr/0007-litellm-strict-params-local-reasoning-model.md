# 0007 - LiteLLM Drop Params, Client Compatibility, and Local Reasoning Model

- Status: Accepted
- Date: 2026-05-04
- OverheadSeconds: 0

## Context

LiteLLM can silently remove unsupported OpenAI-style parameters when `drop_params` is enabled, which hides
misconfiguration when experimenting with provider-specific options such as `reasoning_effort` mapped to Ollama.

Separately, generic chat models in the default local stack do not expose a clear separated reasoning trace suitable
for teaching and verifying the proxy path end-to-end.

**Revision:** Strict `drop_params: false` improved visibility for bad parameters but caused widespread breakage with
OpenAI-compatible clients that send extra fields (for example embedding `encoding_format`) that Ollama backends reject.
`reasoning_effort` does **not** depend on `drop_params: false`; it is applied when LiteLLM supports it for the chosen
model. Compatibility-first proxy defaults were preferred over global strict mode.

## Decision

- Set `litellm_settings.drop_params: true` in the shared LiteLLM configuration so heterogeneous OpenAI-compatible
  clients work against Ollama-backed routes without proxy 400s for dropped unsupported fields.
- Treat **`deepseek-r1:7b`** as the default local **thinking / reasoning** model for Compose:
  include it in default Ollama pull lists (`OLLAMA_MODELS` / `MODELS_DEFAULT` examples and scripts) and register it in
  LiteLLM as **`ollama_chat/deepseek-r1:7b`** for OpenAI-compatible clients.
- Rely on the existing LiteLLM mapping from `reasoning_effort` to Ollama's thinking controls for this model family;
  clients should send `reasoning_effort` via supported APIs (for example LangChain `ChatOpenAI` `model_kwargs`) and
  inspect message fields such as `reasoning_content` when present. When teaching or debugging reasoning, confirm
  behavior in responses or logs rather than relying on proxy errors for unsupported parameters.

This decision is currently in effect in production/dev workflow.

## Consequences

- OpenAI-style tooling (including embeddings calls that send `encoding_format`) is more likely to succeed through the
  proxy without client-specific workarounds.
- Unsupported parameters may be **dropped without error** when `drop_params` is enabled; validate `reasoning_effort` and
  similar knobs by inspecting model output and traces when that matters.
- First-time setup downloads a larger model; operators with constrained disk or CPU should trim `OLLAMA_MODELS`
  locally rather than changing the shared default contract.

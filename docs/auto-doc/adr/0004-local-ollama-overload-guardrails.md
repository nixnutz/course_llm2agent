# 0004 - Local Ollama Overload Guardrails

- Status: Accepted
- Date: 2026-04-24
- OverheadSeconds: 0

## Context

Local experimentation produced repeated timeout cascades when clients disconnected or retried aggressively while Ollama
was still processing long requests. The previous setup allowed long request lifetimes and too much queue buildup for this
workload profile.

## Decision

Apply overload guardrails for local Ollama models only:

- Set `LITELLM_DEFAULT_TIMEOUT=420` in local compose env.
- Set `OLLAMA_MAX_QUEUE=3` to reduce request backlog growth.
- Set `max_retries: 0` on local Ollama model entries in LiteLLM config.
- Keep router-level retries available for non-Ollama providers (`num_retries: 2`).

This decision is currently in effect in production/dev workflow.

## Consequences

- Local Ollama traffic fails faster under overload instead of building long retry/queue cascades.
- Cloud provider behavior remains unchanged and can be tuned independently.
- Client-disconnect cancellation remains best-effort and is tracked as a follow-up hardening area.

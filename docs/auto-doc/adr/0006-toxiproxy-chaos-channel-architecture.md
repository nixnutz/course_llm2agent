# 0006 - Define Toxiproxy Chaos Channel Architecture

- Status: Accepted
- Date: 2026-04-27
- OverheadSeconds: 0

## Context

Local chaos testing needed deterministic network-failure injection for agent traffic without breaking the clean baseline
path used for normal development and teaching workflows.

Earlier single-path wiring made it easy to accidentally apply fault injection too broadly and obscured whether failures
came from edge ingress or provider-side network links.

## Decision

Adopt a fixed dual-channel architecture for local LiteLLM traffic with explicit clean versus chaos routing semantics:

- `https://localhost:4000` is the clean channel and routes to `litellm_clean`.
- `https://localhost:4001` is the chaos channel and routes via `edge_chaos` toxiproxy to `litellm_chaos`.
- `litellm_clean` uses direct provider routing to Ollama (`OLLAMA_API_BASE_CLEAN`).
- `litellm_chaos` uses provider routing through toxiproxy (`OLLAMA_API_BASE_CHAOS` via `provider_chaos_ollama`).
- Toxiproxy proxy definitions are bootstrapped idempotently by `toxiproxy_bootstrap`.
- Phoenix tracing uses separate project labels for clean and chaos channels.

This decision is currently in effect in production/dev workflow.

## Consequences

- Clean and chaos behavior are explicit and selectable by ingress port, reducing accidental cross-impact.
- Teaching and debugging become simpler because channel intent is visible in URL and service topology.
- Toxics can be managed independently per proxy segment (edge and provider) while preserving a clean baseline path.
- Runtime footprint increases due to a second LiteLLM service and associated startup/health dependencies.

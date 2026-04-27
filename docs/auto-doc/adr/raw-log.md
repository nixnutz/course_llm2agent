# ADR Raw Log (Append-Only)

Use this file as a short collection log during implementation and experimentation.
Do not delete or rewrite past entries. Add new entries at the end only.

## Entry Format

`YYYY-MM-DD | area | decision note | evidence`

- `area`: short scope tag (for example `compose`, `agent`, `docs`, `workflow`)
- `decision note`: one sentence only
- `evidence`: commit, PR, branch, worktree, or file reference

## Example

`2026-04-22 | compose | route local ingress through caddy for TLS termination | container/compose/docker-compose.yml`

## Notes

- Keep each entry short (target: under 60 seconds to write).
- Do not add lifecycle status fields here.
- Resolve contradictions and supersessions during ADR summary maintenance before review.

2026-04-24 | compose | use healthcheck start_interval for startup probing and steady-state interval for runtime probing | container/compose/docker-compose.yml
2026-04-24 | workflow | enforce Docker Engine >= 25.0.0 and Docker Compose >= 2.20.0 in make up preflight | container/compose/Makefile
2026-04-24 | workflow | warn once to stderr when non-docker compose provider is detected because runtime is not tested | container/compose/Makefile
2026-04-24 | workflow | enforce mandatory ADR relevance check on every plan via always-applied Cursor rule | .cursor/rules/adr-plan-check.mdc
2026-04-24 | workflow | simplify ADR raw-log tail-only rule by removing duplicate checks and deferring cleanup to review | .cursor/rules/adr-raw-log-tail-only.mdc
2026-04-24 | compose | apply ollama-only overload guardrails (timeout budget, retry suppression, queue cap) to stabilize local proxy under client churn | container/compose/config/litellm.yaml
2026-04-24 | compose | tighten phase-2 local admission controls by limiting queue depth and loaded models for ollama runtime stability | container/compose/.env
2026-04-24 | compose | add phase-3 abort-path controls and observability hooks (keep_alive reduction plus abort smoke checks) | container/compose/scripts/smoke-chat-abort.sh
2026-04-24 | compose | add phase-4 soft streaming policy docs and split smoke checks for streaming vs non-streaming abort behavior | container/compose/README.md
2026-04-24 | compose | remove additional abort/streaming smoke targets to keep local workflow lightweight; rely on manual log-based verification | container/compose/Makefile
2026-04-24 | workflow | treat portable runtime control surfaces as ADR-relevant and use hybrid raw-log + ADR contract documentation | .cursor/rules/adr-plan-check.mdc
2026-04-27 | workflow | add local branch-scoped post-commit review tracking via gitignored review-status file and command pre-selection flow | .cursor/commands/review-w-auto-doc.md
2026-04-27 | workflow | add warn-only ADR hook guardrails for raw-log append-only/format and ADR required field checks | .cursor/hooks.json
2026-04-27 | compose | stage 1 implemented toxiproxy-based chaos plumbing with dedicated TLS ingress on port 4001 and bootstrap-managed edge/provider proxy endpoints | container/compose/docker-compose.yml
2026-04-27 | compose | stage 1 switched LiteLLM Ollama api_base to environment-driven routing to support provider-chaos injection via toxiproxy without per-test yaml edits | container/compose/config/litellm.yaml
2026-04-27 | workflow | stage 1 added toxiproxy helper scripts and make targets for bootstrap toxic management and reset in local dev/test workflows | container/compose/Makefile
2026-04-27 | compose | stage 2 implemented split LiteLLM services for fixed clean and chaos channels with caddy 4000 routed to litellm_clean and caddy 4001 routed via edge_chaos to litellm_chaos | container/compose/docker-compose.yml
2026-04-27 | compose | stage 2 set per-service ollama routing and phoenix project names so clean uses direct ollama and chaos uses toxiproxy provider path with isolated tracing labels | container/compose/.env
2026-04-27 | workflow | strengthen review-w-auto-doc output contract with explicit raw-log and adr-file status gates to prevent doc loss after context switches | .cursor/commands/review-w-auto-doc.md

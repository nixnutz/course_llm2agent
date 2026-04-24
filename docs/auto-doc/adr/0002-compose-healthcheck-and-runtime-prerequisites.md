# 0002 - Compose Healthcheck Semantics and Runtime Prerequisites

- Status: Accepted
- Date: 2026-04-24
- OverheadSeconds: 0

## Context

The stack produced high-volume Ollama healthcheck logs because startup probe cadence was effectively used as the permanent healthcheck interval.
At the same time, the compose configuration now depends on `start_interval`, which requires modern Docker Engine/Compose behavior to be reliable.

## Decision

Use split healthcheck timing semantics for Ollama:
- startup probing via `start_interval` (`HEALTHCHECK_INTERVAL_BOOT`)
- steady-state probing via `interval` (`HEALTHCHECK_INTERVAL`)

Treat Docker runtime versions as explicit technical prerequisites for `make up`:
- Docker Engine `>= 25.0.0`
- Docker Compose `>= 2.20.0`

If a non-Docker compose provider is detected, print a single warning to stderr and continue best-effort:
`WARNING: non-docker compose provider detected; this setup is not tested.`

## Consequences

- Lower steady-state probe noise in Ollama logs while keeping fast startup checks.
- Deterministic behavior for `start_interval`-based healthchecks.
- Faster failure with actionable messages in unsupported Docker version environments.
- Podman compatibility remains a separate follow-up scope.

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

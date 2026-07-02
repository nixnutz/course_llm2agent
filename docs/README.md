# Documentation index

Entry points for this repository, grouped by audience.

## Course (learners and implementers)

- [Course presentation](toolbert_lab.pdf) — summary deck (sessions 1–8)
- [Getting started](getting-started.md) — agent lab on Compose, `dev` runtime, first agent exercise
- [Course docs hub](course/README.md) — pipeline sketch, error handling, module pointers (sessions 1–8)
- [Course notebooks](../src/assorted/README.md) — Jupyter sessions under `src/assorted`

## Runtime and operations

- [Compose stack](../container/compose/README.md) — services, env vars, chaos channel, Phoenix
- [Dev container image](../container/dev-image/README.md) — notebook mode, restart vs rebuild
- [Root Makefile](../Makefile) — `make help` for stack and dev targets

## Contributors (editor and agents)

- [Editor and agent workflow](editor-and-agent-workflow.md) — dev-cmd, language, ADR check on plans
- [Tests and evals](../src/tests_and_evals/README.md) — pytest layers L1–L6

## Experiments (side learning, not official course scope)

- [Auto-doc overview](auto-doc/README.md) — ADR and user-value logging process
- [ADR index](auto-doc/adr/README.md) — summarized architecture decisions
- [User value log](auto-doc/value/user-value-log.md) — review-gated outcome tracking

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
2026-04-27 | compose | switch postgres services to pgvector image and enable vector extension idempotently for litellm and phoenix databases during identity init | container/compose/scripts/init-postgres-identities.sh
2026-04-27 | workflow | reorganize compose make help output into explicit grouped sections to improve command discoverability and naming consistency | container/compose/Makefile
2026-04-27 | workflow | keep dev image rebuild and dev container restart as separate root make operations and remove ambiguous combined target | Makefile
2026-04-30 | workflow | inject notebook API keys from .state keys.local.json into dev container env at startup and switch assorted notebooks to os.getenv-based API_KEY usage with restart-on-rotation semantics | container/compose/scripts/export-dev-secrets-env.sh
2026-04-30 | workflow | replace hardcoded notebook caddy endpoints with generic MODEL_BASE_URL_CLEAN and MODEL_BASE_URL_CHAOS env contract exposed to dev runtime | container/compose/.env
2026-04-30 | workflow | enforce strict pseudo-user key naming by exporting and consuming only MODEL_API_KEY_<PSEUDO_USER> variables without API_KEY or LITELLM_API_KEY aliases | container/compose/scripts/export-dev-secrets-env.sh
2026-04-30 | workflow | add FIFO-capped review skip memory contract and command integration to suppress accepted recurring findings/questions/assumptions with applied skip count reporting | .cursor/commands/review-w-auto-doc.md
2026-05-04 | compose | reorganize directory into purpose-centric layout (config/<svc>, init/<svc>, scripts/<svc>) and add postgres docker-entrypoint-initdb.d hook for vector extension | container/compose/init/postgres/01-extensions.sql
2026-05-04 | compose | disable LiteLLM drop_params so unsupported OpenAI parameters fail visibly; register ollama_chat/deepseek-r1:7b and extend default OLLAMA_MODELS pull lists for local reasoning_effort / thinking traces | docs/auto-doc/adr/0007-litellm-strict-params-local-reasoning-model.md container/compose/config/litellm/litellm.yaml container/compose/init/ollama/models.sh
2026-05-04 | compose | re-enable litellm_settings.drop_params for OpenAI-client compatibility; amend ADR 0007 (reasoning_effort does not require strict mode) | container/compose/config/litellm/litellm.yaml docs/auto-doc/adr/0007-litellm-strict-params-local-reasoning-model.md
2026-05-26 | compose | require JUPYTER_TOKEN in container/compose/.env and pass it to dev for JupyterLab host auth; document URL placeholders and restart-vs-rebuild in dev-image README | container/compose/docker-compose.yml container/compose/.env.example container/dev-image/scripts/start-notebook.sh
2026-05-26 | course | session4 LLM nodes in src/llm_nodes; TODO subgraph bridge with RunnableConfig forward and GlobalState composition | src/llm_nodes/ src/assorted/session4/langgraph.ipynb
2026-05-28 | course | introduce strict BaseState(extra=forbid), split TODO flow into todo_extract and todo_markdown subgraphs, and align session4 notebook pipeline/logging with the new flow | src/llm_nodes/ src/assorted/session4/langgraph.ipynb
2026-06-02 | workflow | add gitignored adr-plan-sidecar bridge from Plan mode to review-w-auto-doc and ADR rules without storing full plans in repo | docs/internal/adr-plan-sidecar.template.md .cursor/rules/adr-plan-check.mdc
2026-06-02 | course | split tests into tests_and_evals (tests vs evals), add pytest markers unit/smoke/eval, minimal pii_email golden-set eval scaffold; shorten log project prefix to c2a | src/tests_and_evals/ src/pyproject.toml src/logging_setup.py
2026-06-02 | course | pii_email pipeline contract: LLM returns occurrences[{span,raw}] only (no text/no dedupe), deterministic Python masking builds text via position splicing with salted E{n}_{salt} placeholders, EmailStr strip().lower() dedupe into identities, soft-fail markers (span_not_found warning/discard raw, normalization_failed error/mask with identity None, leak_suspected warning); PIIEmail state replaced (text/salt/identities/occurrences), notebook restore + tests/eval reworked | src/llm_nodes/pii_email/ src/tests_and_evals/ src/assorted/session4/langgraph.ipynb
2026-06-02 | workflow | stop auto-clearing the adr-plan-sidecar after review; clear only after explicit confirmation that ADR/raw-log work for every captured plan is done+committed, so multi-plan flows keep review context | .cursor/rules/adr-plan-check.mdc .cursor/commands/review-w-auto-doc.md docs/auto-doc/README.md docs/internal/adr-plan-sidecar.template.md
2026-06-02 | workflow | switch adr-plan-sidecar from overwrite-per-feature to append one ## plan-<n> block per finalized plan (overwrite only for unrelated features); template restructured to per-plan blocks so multi-plan context is not lost | .cursor/rules/adr-plan-check.mdc docs/auto-doc/README.md docs/internal/adr-plan-sidecar.template.md
2026-06-02 | workflow | make sidecar write the explicit closing step of plan finalization tied to the ADR-outcome check (no extra command, best-effort/not a hard gate) so it is normally captured without enforcing it | .cursor/rules/adr-plan-check.mdc docs/auto-doc/README.md
2026-06-03 | course | pii_email public contract rename (PIIEmail.emails, Occurrence.email, eval forbidden_spans) and demask_pii_emails for trusted post-graph restore | src/llm_nodes/pii_email/ src/tests_and_evals/ src/assorted/session4/langgraph.ipynb docs/auto-doc/adr/0009-pii-email-masking-pipeline.md
2026-06-03 | course | eval MUST in-test assert, SHOULD session pass-rate via pytest hooks; shared eval_collector under evals/ with xdist merge; EvalCaseResult still PII-email fields until second eval node | src/tests_and_evals/evals/ docs/auto-doc/adr/0010-eval-must-should-pytest-hooks.md
2026-06-03 | course | generalize eval_collector to node-neutral EvalCaseResult (suite/failed_checks/details/metrics, set->sorted-list normalization), gate SHOULD per suite, migrate pii_email eval, add todo_extract golden-set eval (who_placeholder_recall MUST, what/when SHOULD as LLM-as-judge placeholder); thread who/what/when vocabulary unchanged | src/tests_and_evals/evals/ docs/auto-doc/adr/0010-eval-must-should-pytest-hooks.md src/tests_and_evals/README.md

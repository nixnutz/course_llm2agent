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
2026-06-03 | course | placeholder_audit round 1: PlaceholderAllowlist in TODO subgraph state (no raw emails), bridge allowlist_from_pii_email, audit node after todo_extract/todo_markdown LLM, generic placeholder finder + allowlist gate, placeholder_violation log; failure policy deferred | src/llm_nodes/placeholder_audit/ docs/auto-doc/adr/0009-pii-email-masking-pipeline.md
2026-06-04 | course | LangGraph Phoenix trace tree via src/tracing (OpenInference LangChain+OpenAI), session5 graphtrace.ipynb, dev PHOENIX_COLLECTOR_ENDPOINT/PHOENIX_APP_PROJECT_NAME | src/tracing/ src/assorted/session5/ container/compose/
2026-06-04 | course | ParentBaseGraph + trusted demask_node after TODO subgraphs (markdown restore for tracing); ADR 0009 documents PII-in-graph compromise vs ideal system boundary | src/graphs/parent_base_graph.py src/other_nodes/demask/ docs/auto-doc/adr/0009-pii-email-masking-pipeline.md
2026-06-04 | course | ADR 0011 six-layer test scope (L1–L6 reminder model, review vs commit, L3 parent mock E2E, chaos marker); tests not required in same commit as code | docs/auto-doc/adr/0011-course-test-scope-layers.md src/tests_and_evals/ src/pyproject.toml
2026-06-04 | course | ADR 0012 course error-mode contract: Mode C default (Guard/Observe/Library tiers), always log+trace, trusted egress boundary deferred, eval L5 separate from runtime; enables L6 chaos expectations without tests yet | docs/auto-doc/adr/0012-course-error-mode-contract.md src/assorted/session5/
2026-06-05 | course | L6 parent-graph chaos exemplars: provider_chaos_ollama + edge_chaos reset_peer via build_parent_base_graph(chaos=True); Library-tier propagation per ADR 0012 | src/tests_and_evals/tests/graphs/test_parent_base_graph_chaos.py src/graphs/parent_base_graph.py src/tests_and_evals/common/toxiproxy.py
2026-06-05 | compose | trim default OLLAMA_MODELS to embed+llama3.2:3b; deepseek-r1:7b optional in LiteLLM only; amend ADR 0007 default-pull decision | container/compose/.env.example container/compose/init/ollama/models.sh docs/auto-doc/adr/0007-litellm-strict-params-local-reasoning-model.md docs/getting-started.md
2026-06-08 | course | execution scope (partial): one async flow per request (planned FastAPI: one event-loop per worker); reducer_session bound to entering OS thread (implemented); one ainvoke per request, tools in-graph not BackgroundTasks/Celery; sequential MAS/subgraphs not parallel fan-out with shared reducer; no multi-turn in-memory vault across HTTP requests without external store; multi-worker OK for independent requests only; Phoenix/reducer contextvars assume same model; dedicated ADR 0013 when API lands | src/reducer/reducer_session.py src/tracing/phoenix.py docs/auto-doc/adr/raw-log.md
2026-06-10 | course | partial rename tool_node_loop subgraph LangGraph node agent→llm_with_tools and route_after_llm_with_tools; session6 ReAct notebook prose; ToolNodeLoopAgent/get_tool_node_loop_agent_node rename deferred | src/llm_nodes/tool_node_loop/ src/assorted/session6/tool_node_basics.ipynb
2026-06-10 | compose | Sysbox Bash Slice 1+2 runtime control surface: systemd Sysbox service with inner Docker, internal-only FastAPI Sandbox HTTP API, API-owned sessions/runs, trusted optional correlation copied to metadata, script/timeout/stdout/stderr SBASH limits, no GET /sessions, read-only host inspection helper | container/sysbox-bash-image/ container/compose/ Makefile
2026-06-10 | course | Slice 3 tool_node_sysbox_bash LangGraph subgraph: bridge-owned sandbox session (start/finally end via SBASH_BASE_URL), custom run_tools from state.sandbox_session_id, bash tool schema-only for bind_tools, result_text internally with bridge map to GlobalState.todo_text, who-only finalize, policy_exhausted raises PolicyViolationError, shared tool_node_policy limits, ADR 0011 L1+L3 exemplar tests, session7 E2E smoke notebook | src/llm_nodes/tool_node_sysbox_bash/ src/llm_nodes/tool_node_policy.py src/tests_and_evals/tests/llm_nodes/tool_node_sysbox_bash/ src/assorted/session7/tool_node_sysbox.ipynb docs/auto-doc/adr/0014-tool-node-sysbox-bash-langgraph-bridge.md
2026-06-10 | compose | Slice 5 closure: summarize Slice 2 Sandbox HTTP contract as ADR 0015; stable lab limitations in sysbox service README; api-smoke + 5 unit tests verified | docs/auto-doc/adr/0015-sysbox-bash-sandbox-http-api.md container/sysbox-bash-image/README.md
2026-06-12 | course | tool_node_sysbox_bash one-shot transport-retry on exit_code=2 parse/quote stderr heuristics; Transport retry offer exempt from tool_errors; dedicated llm_fence_retry/run_fence_retry nodes; bind_tools happy path unchanged | src/llm_nodes/tool_node_sysbox_bash/ src/tests_and_evals/tests/llm_nodes/tool_node_sysbox_bash/

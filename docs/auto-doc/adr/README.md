# ADR index

Summarized architecture and implementation decisions under `docs/auto-doc/adr/`.
Raw collection log: [raw-log.md](raw-log.md). Process: [auto-doc README](../README.md).

| ADR | Title |
|-----|-------|
| [0001](0001-record-architecture-decisions.md) | Record architecture decisions as ADRs |
| [0002](0002-compose-healthcheck-and-runtime-prerequisites.md) | Compose healthcheck and runtime prerequisites |
| [0003](0003-require-adr-check-in-plan-creation.md) | Require ADR check in plan creation |
| [0004](0004-local-ollama-overload-guardrails.md) | Local Ollama overload guardrails |
| [0005](0005-define-ollama-runtime-control-surface.md) | Ollama runtime control surface |
| [0006](0006-toxiproxy-chaos-channel-architecture.md) | Toxiproxy chaos channel architecture |
| [0007](0007-litellm-strict-params-local-reasoning-model.md) | LiteLLM drop params and local reasoning models |
| [0008](0008-strict-llm-node-state-and-two-step-todo-flow.md) | Strict LLM node state and two-step TODO flow |
| [0009](0009-pii-email-masking-pipeline.md) | PII email masking pipeline (course sketch) |
| [0010](0010-eval-must-should-pytest-hooks.md) | Eval MUST/SHOULD pytest hooks |
| [0011](0011-course-test-scope-layers.md) | Course test scope layers (L1–L6) |
| [0012](0012-course-error-mode-contract.md) | Course error-mode contract (Mode C) |
| [0014](0014-tool-node-sysbox-bash-langgraph-bridge.md) | tool_node_sysbox_bash LangGraph bridge and sandbox session lifecycle |
| [0015](0015-sysbox-bash-sandbox-http-api.md) | Sysbox Bash Sandbox HTTP API and runtime control surface |

Course-facing pointers: [pipeline and nodes](../../course/pipeline-and-nodes.md),
[error handling](../../course/error-handling.md).

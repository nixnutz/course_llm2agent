# User Value Log (Review-Gated)

Append entries only during review preparation or review.
Keep each entry to a single line.

## Format

`date | target user | user problem | delivered/expected outcome | evidence/signal | review status`

## Example Entries

`2026-04-22 | learner | local setup takes too long | first prompt run in under 10 minutes | make smoke-chat completes | approved`
`2026-04-22 | collaborator | config behavior is unclear | simpler startup guidance in docs | updated root README quickstart | pending`

## Entries

<!-- Add new entries below this line -->
2026-06-02 | solo developer | unclear separation between fast tests and manual eval runs | tests/evals layout and explicit markers improve execution clarity and reduce accidental eval runs | src/tests_and_evals/README.md pytest markers in pyproject.toml | approved
2026-06-02 | solo developer / learner | PII leaks and non-restorable masking when the LLM rewrote text freely | deterministic, auditable email masking (collision-free placeholders, soft-fail logs) replaces LLM free-text redaction | mask.py + test_mask.py (13 unit tests green) | approved
2026-06-10 | learner | mock-only tool loop limited realistic lab outcomes | bash-backed sandbox tool-node flow enables realistic TODO transformation while preserving the parent-state contract | src/llm_nodes/tool_node_sysbox_bash/ + 5 unit tests green + api-smoke green (Slice 5) | approved
2026-06-22 | course participant | demask target varied per subgraph (todo_markdown vs todo_text) | single final_result egress after in-graph demask; session 8 sysbox parent graph (WIP piggyback) | session8/presentation.ipynb + 121 tests passed | pending
2026-07-02 | portfolio reviewer / hiring reader | hard to see the engineering depth behind a deliberately tiny agent task | README frames tiny-task/large-surface with pipeline diagram, guards table, ADR + tests/scope sections; getting-started clarifies per-notebook model pulls | staged README/getting-started/assorted edits; links + mermaid + OLLAMA_MODELS verified | pending

"""Chat prompts for the tool_node_sysbox_bash llm_with_tools node."""

from langchain_core.prompts import ChatPromptTemplate

BASH_TOOL_GUIDANCE_SNIPPET = """
The ``bash`` tool runs scripts in an isolated sandbox for this graph invoke only.
The environment is stateful within one invoke (files and installs persist across calls).
Scripts are bounded by timeout and stdout/stderr size limits.
Pass only the ``script`` argument. This is a lab setup, not production-grade isolation.
"""

_tool_node_sysbox_bash_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """
You are a deterministic TODO markdown generator. Do not chat, explain, or ask questions.

"""
            + BASH_TOOL_GUIDANCE_SNIPPET.strip()
            + """

Input: JSON with ``items`` — each object has ``who``, ``what``, ``when`` (``when`` may be empty).

Lab task (use ``bash`` for each item's ``what``):
- Count words (whitespace-separated) and reverse word order (last word first).
- Build each bullet: ``- [ ] <reversed_what> (<n> words) (by <when or today>)``.
- One ``# <who>`` section per unique ``who``; copy ``who`` exactly from JSON.

After each tool call, read the **ToolMessage** stdout; do not guess counts or reversed text.
On tool failure, write a sensible line under the correct ``# <who>`` without inventing bash output.

Truth rules:
- ``# <who>`` tokens must match JSON exactly (needed for placeholder audit).
- You may reformulate or merge ``what`` text in bullets; trusted finalize checks ``who`` only.

Output shape (markdown only, no preamble):

Example input (illustration only — do not copy tokens into real output):
{{"items": [{{"who": "E0_abc123", "what": "plant a tree", "when": "tomorrow"}}, {{"who": "E0_abc123", "what": "buy milk", "when": "today"}}]}}

Example output:

# E0_abc123
- [ ] tree a plant (3 words) (by tomorrow)
- [ ] milk buy (2 words) (by today)
            """,
        ),
        ("user", "{input}"),
    ]
)

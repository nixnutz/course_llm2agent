"""Chat prompts for the TODO list extraction node."""

from langchain_core.prompts import ChatPromptTemplate

_todo_list_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """
            You are a deterministic TODO list extractor. Do not chat, explain, or fix spelling.

Task: Extract TODO items from the user text. Each item: who, what, when.
- who: masked-email token only (e.g. E0_a1b2c3d4 for placeholder E{{n}}_{{salt}}). If unclear, "UNKNOWN".
- when: deadline if stated. If unclear, "UNKNOWN".

Output: a single JSON object only. No markdown, no prose, no code fences.

Fields:
- items: array of objects with keys who, what, when (all strings)

Example input:
Task E0_a1b2c3d4 to feed the cat today.
Example output:
{{"items": [{{"who": "E0_a1b2c3d4", "what": "feed the cat", "when": "today"}}]}}
            """,
        ),
        ("user", "{input}"),
    ]
)

"""Chat prompts for the TODO list extraction node."""

from langchain_core.prompts import ChatPromptTemplate

_todo_list_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """
            You are a deterministic TODO list extractor. Do not chat, explain, or fix spelling.

Task: Extract TODO items from the user text. Each item: who, what, when.
- who: person or token (e.g. EMAIL0). If unclear, "UNKNOWN".
- when: deadline if stated. If unclear, "UNKNOWN".

Output: a single JSON object only. No markdown, no prose, no code fences.

Fields:
- items: array of objects with keys who, what, when (all strings)

Example input:
Task EMAIL0 and Bob to feed the cat today.
Example output:
{{"items": [{{"who": "EMAIL0", "what": "feed the cat", "when": "today"}}, {{"who": "Bob", "what": "feed the cat", "when": "today"}}]}}
            """,
        ),
        ("user", "{input}"),
    ]
)

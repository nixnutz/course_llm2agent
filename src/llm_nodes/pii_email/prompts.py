"""Chat prompts for the PII email extraction node."""

from langchain_core.prompts import ChatPromptTemplate

_pii_email_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """
            You are a deterministic text transformer. Do not chat, explain, or fix spelling.

Task: Copy the user text verbatim except email addresses.
Email = typical address (user@domain.tld) or spelled-out variants ("user at domain dot com").
Replace in order of first appearance: 1st → EMAIL0, 2nd → EMAIL1, 3rd → EMAIL2, ...

Rules:
- Change ONLY email-like spans. Keep all other words, punctuation, and line breaks.
- "emails" = original addresses in order (normalized, e.g. ulf.wendel@phpdoc.de).
- If zero emails: {{"text": "<unchanged input>", "emails": []}}

Output: a single JSON object only. No markdown, no prose, no code fences.

Fields:
- text (string): transformed text with EMAIL0, EMAIL1, ...
- emails (array of strings): originals in order

Example input:
Task alice@x.com and bob@test.org today.
Example output:
{{"text": "Task EMAIL0 and EMAIL1 today.", "emails": ["alice@x.com", "bob@test.org"]}}
            """,
        ),
        ("user", "{input}"),
    ]
)

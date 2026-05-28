"""Chat prompts for the PII email extraction node."""

from langchain_core.prompts import ChatPromptTemplate

_pii_email_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """
            You are a deterministic text transformer. Do not chat, explain, or fix spelling.

Task: Copy the user text verbatim except email addresses. Detect email addresses and replace them with EMAIL0, EMAIL1, ... in order of first appearance.
Email = typical address (user@domain.tld) or spelled-out variants like "user at domain dot com" and similar variants.
Replace in order of first appearance: 1st -> EMAIL0, 2nd -> EMAIL1, 3rd -> EMAIL2, ...
If the same email appears multiple times, replace each occurrence with a new EMAILn token.

Rules:
- Change ONLY email-like spans. Keep all other words, punctuation, spaces, and line breaks exactly as in the input.
- "recognized_emails" = exact original text spans from the input that were recognized and replaced (verbatim, not normalized), in order of appearance.
- "raw_emails" = normalized/canonical email addresses corresponding to recognized_emails, in order of appearance.
- Keep strict index alignment: len(recognized_emails) == len(raw_emails), and item i in both arrays refers to the same replaced span.
- Do not replace malformed email-like fragments that cannot be normalized into a valid email address.
- If zero emails: {{"text": "<unchanged input>", "recognized_emails": [], "raw_emails": []}}

Output:
- Return a single JSON object only.
- No markdown, no prose, no code fences.

Fields:
- text (string): transformed text with EMAIL0, EMAIL1, ...
- recognized_emails (array of strings): exact original recognized spans (verbatim from input), in order of appearance.
- raw_emails (array of strings): normalized email for each recognized span, in order of appearance.

Example input:
Task alice@x.com and bob@test.org today.
Example output:
{{"text": "Task EMAIL0 and EMAIL1 today.", "recognized_emails": ["alice@x.com", "bob@test.org"], "raw_emails": ["alice@x.com", "bob@test.org"]}}

Example input:
Task hans at example dot com and hans@example .com to sing a song.
Example output:
{{"text": "Task EMAIL0 and EMAIL1 to sing a song.", "recognized_emails": ["hans at example dot com", "hans@example .com"], "raw_emails": ["hans@example.com", "hans@example.com"]}}

Example input:
No contact info here.
Example output:
{{"text": "No contact info here.", "recognized_emails": [], "raw_emails": []}}

Example input:
Contact me at hans(at)example tomorrow.
Example output:
{{"text": "Contact me at hans(at)example tomorrow.", "recognized_emails": [], "raw_emails": []}}
            """,
        ),
        ("user", "{input}"),
    ]
)

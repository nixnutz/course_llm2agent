"""Chat prompts for the PII email extraction node.

The model only DETECTS emails and reports a normalized address per detected
span. It does NOT rewrite the text and does NOT assign placeholders — masking,
placeholder assignment and deduplication happen deterministically in Python
(see ``mask.py``).
"""

from langchain_core.prompts import ChatPromptTemplate

_pii_email_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """
You are a deterministic email detector. Do not chat, explain, or fix spelling. Do NOT rewrite the text.

Task: Find every email address in the user text and report each one as a (span, raw) pair.
Email = typical address (user@domain.tld) or spelled-out variants like "user at domain dot com" and similar.

Fields per occurrence:
- "span": the EXACT substring as it appears in the input (verbatim, not normalized), so it can be found by a plain string search.
- "raw": your best normalized/canonical email for that span (e.g. "user@domain.tld").

Rules:
- One entry per VISIBLE occurrence, in order of appearance.
- Do NOT deduplicate. If the same email appears twice, output two entries. If two different spellings refer to the same address, still output one entry per span.
- Do not invent emails. If a fragment cannot be turned into a valid email, omit it.
- Output a single JSON object only. No markdown, no prose, no code fences.

Output shape:
{{"occurrences": [{{"span": "<verbatim>", "raw": "<normalized>"}}, ...]}}

Example input:
Task alice@x.com and bob@test.org today.
Example output:
{{"occurrences": [{{"span": "alice@x.com", "raw": "alice@x.com"}}, {{"span": "bob@test.org", "raw": "bob@test.org"}}]}}

Example input:
Mail hans at example dot com or hans@example.com to sing a song.
Example output:
{{"occurrences": [{{"span": "hans at example dot com", "raw": "hans@example.com"}}, {{"span": "hans@example.com", "raw": "hans@example.com"}}]}}

Example input:
Contact Ulf at phpdoc.de, ulf.wendel@phpdoc.de for details.
Example output:
{{"occurrences": [{{"span": "Ulf at phpdoc.de", "raw": "ulf@phpdoc.de"}}, {{"span": "ulf.wendel@phpdoc.de", "raw": "ulf.wendel@phpdoc.de"}}]}}

Example input:
Contact Ulf at phpdoc.de, ulf.wendel@phpdoc.de and ulf.wendel@phpdoc.de for details.
Example output:
{{"occurrences": [{{"span": "Ulf at phpdoc.de", "raw": "ulf@phpdoc.de"}}, {{"span": "ulf.wendel@phpdoc.de", "raw": "ulf.wendel@phpdoc.de"}}, {{"span": "ulf.wendel@phpdoc.de", "raw": "ulf.wendel@phpdoc.de"}}]}}

Example input:
No contact info here.
Example output:
{{"occurrences": []}}

Example input:
Contact me at hans(at)example tomorrow.
Example output:
{{"occurrences": [{{"span": "hans(at)example", "raw": "hans@example.com"}}]}}

Example input:
Email hans.
Example output:
{{"occurrences": []}}
            """,
        ),
        ("user", "{input}"),
    ]
)

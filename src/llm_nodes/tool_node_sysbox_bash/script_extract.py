"""Extract bash script bodies from markdown fences (transport-retry path only)."""

from __future__ import annotations

import re

_BASH_FENCE_RE = re.compile(
    r"```(?:bash|sh)\s*\n(.*?)```",
    re.DOTALL | re.IGNORECASE,
)

FENCE_RETRY_TOOL_CALL_ID = "bash-fence-retry"


def extract_bash_fence(text: str) -> str | None:
    """Return the first ```bash or ```sh fence body, or None if missing/empty."""
    match = _BASH_FENCE_RE.search(text)
    if not match:
        return None
    body = match.group(1)
    # Opening fence is ```bash\n<body>\n``` — drop the delimiter newline before ```.
    if body.endswith("\n"):
        body = body[:-1]
    return body if body.strip() else None


def has_bash_fence(text: str) -> bool:
    return extract_bash_fence(text) is not None

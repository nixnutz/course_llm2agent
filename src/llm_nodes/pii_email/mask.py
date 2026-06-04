"""Deterministic email masking pipeline (no LLM).

Course sketch — not production PII tooling. See ``README.md`` in this package
for scope and known limitations.

Input: original text + LLM occurrences ``[{"span", "raw"}, ...]``.
Output: a :class:`PIIEmail` with masked ``text``, ``salt``, ``emails`` and a
per-span audit trail in ``occurrences``.

Contract (see plan ``PII email prompt contract``):
- One placeholder ``E{n}_{salt}`` per distinct canonical email; equal
  ``raw.strip().lower()`` keys share a placeholder.
- ``salt`` is a short random hex chosen so it does not occur in the input,
  which makes every placeholder collision-free against the original text.
- Positions are resolved in the original input (cursor per span string) so
  repeated identical spans consume successive occurrences; the masked text is
  built by splicing, never by in-place ``replace`` on a mutating string.
- Soft-fail with log markers: ``span_not_found`` (warning, raw discarded),
  ``normalization_failed`` (error, span still masked with ``identity=None``),
  ``leak_suspected`` (warning, residual span/raw left in the masked text).
"""

import uuid

from pydantic import EmailStr, TypeAdapter, ValidationError

from src.logging_setup import get_logger

from .models import Occurrence, PIIEmail

logger = get_logger(__name__, __file__)

_EMAIL_ADAPTER = TypeAdapter(EmailStr)


def _make_salt(input_text: str, length: int = 8, attempts: int = 5) -> str:
    """Return a hex salt that is not a substring of ``input_text``.

    The substring check is the actual correctness guarantee; ``length`` only
    lowers the chance of needing another attempt.
    """
    for _ in range(attempts):
        candidate = uuid.uuid4().hex[:length]
        if candidate not in input_text:
            return candidate
    # Extremely unlikely fallback: full-length uuid.

    candidate = uuid.uuid4().hex
    if candidate in input_text:
        raise RuntimeError("Failed to generate a salt that is not a substring of the input text")

    return candidate


def _canonical_key(raw: str) -> str | None:
    """Return the dedupe/restore key (``raw.strip().lower()``) or ``None``.

    ``None`` means the span was recognized but is not a normalizable email.
    """
    key = raw.strip().lower()
    if not key:
        return None
    try:
        _EMAIL_ADAPTER.validate_python(key)
    except ValidationError:
        logger.warning("normalization_failed raw=%r key=%r (not a valid email)", raw, key)
        return None
    return key


def mask_pii_emails(input_text: str, raw_occurrences: list) -> PIIEmail:
    """Build a :class:`PIIEmail` from raw LLM occurrences, deterministically."""
    salt = _make_salt(input_text)

    # Step 1+2: resolve positions in the original input (cursor per span string).
    # ``skipped`` collects soft-failed spans; it is merged with accepted spans at
    # the end so the audit trail stays in reading order.
    cursors: dict[str, int] = {}
    located: list[dict] = []  # {span, raw, pos}
    skipped: list[dict] = []  # {pos, occurrence}

    for item in raw_occurrences:
        if not isinstance(item, dict):
            logger.warning("invalid occurrence=%r (not a dict)", item)
            continue
        span = str(item.get("span", ""))
        raw = str(item.get("raw", ""))

        if not span:
            logger.warning("span_not_found span=%r raw=%r (empty span)", span, raw)
            skipped.append(
                {
                    "pos": len(input_text),
                    "occurrence": Occurrence(
                        span=span, raw_llm=raw, skipped_reason="span_not_found"
                    ),
                }
            )
            continue

        start = cursors.get(span, 0)
        pos = input_text.find(span, start)
        if pos < 0:
            logger.warning("span_not_found span=%r raw=%r", span, raw)
            skipped.append(
                {
                    "pos": len(input_text),
                    "occurrence": Occurrence(
                        span=span, raw_llm=raw, skipped_reason="span_not_found"
                    ),
                }
            )
            continue

        cursors[span] = pos + len(span)
        located.append({"span": span, "raw": raw, "pos": pos})

    # Step 3: order by reading position; reject overlaps (first wins).

    located.sort(key=lambda e: e["pos"])
    accepted: list[dict] = []
    last_end = -1
    for entry in located:
        if entry["pos"] < last_end:
            logger.warning(
                "span_not_found span=%r raw=%r (overlaps earlier span)",
                entry["span"],
                entry["raw"],
            )
            skipped.append(
                {
                    "pos": entry["pos"],
                    "occurrence": Occurrence(
                        span=entry["span"], raw_llm=entry["raw"], skipped_reason="span_not_found"
                    ),
                }
            )
            continue
        accepted.append(entry)
        last_end = entry["pos"] + len(entry["span"])

    # Step 4: assign placeholders / emails in reading order.
    emails: list[str | None] = []
    key_to_index: dict[str, int] = {}
    placed: list[dict] = []  # {pos, occurrence}
    for entry in accepted:
        key = _canonical_key(entry["raw"])
        if key is None:
            index = len(emails)
            emails.append(None)
            logger.error(
                "normalization_failed span=%r raw=%r (masked, no restore)",
                entry["span"],
                entry["raw"],
            )
        elif key in key_to_index:
            index = key_to_index[key]
        else:
            index = len(emails)
            emails.append(key)
            key_to_index[key] = index

        placeholder = f"E{index}_{salt}"
        entry["placeholder"] = placeholder
        entry["key"] = key
        placed.append(
            {
                "pos": entry["pos"],
                "occurrence": Occurrence(
                    span=entry["span"],
                    raw_llm=entry["raw"],
                    email=key,
                    placeholder=placeholder,
                ),
            }
        )

    # Merge accepted + skipped audit entries in reading order (skipped spans that
    # were never located sort last via ``pos = len(input_text)``).
    occurrences: list[Occurrence] = [
        e["occurrence"] for e in sorted(placed + skipped, key=lambda e: e["pos"])
    ]

    # Step 5: build masked text via splicing (no positional drift).
    pieces: list[str] = []
    last = 0
    for entry in accepted:
        pos = entry["pos"]
        pieces.append(input_text[last:pos])
        pieces.append(entry["placeholder"])
        last = pos + len(entry["span"])
    pieces.append(input_text[last:])
    text = "".join(pieces)

    # Step 6: leak check over every masked span (incl. identity=None).
    # The ``raw`` check only applies to normalizable emails; for failed
    # normalization ``raw`` is arbitrary text and would cause false positives.
    for entry in accepted:
        if entry["span"] in text:
            logger.warning("leak_suspected span=%r still present in masked text", entry["span"])
        elif entry["key"] is not None and entry["raw"] and entry["raw"] in text:
            logger.warning("leak_suspected raw=%r still present in masked text", entry["raw"])

    return PIIEmail(text=text, salt=salt, emails=emails, occurrences=occurrences)


def demask_pii_emails(masked_text: str, pii: PIIEmail) -> str:
    """Replace ``E{n}_{salt}`` placeholders with the original email addresses.

    Only placeholders that have a non-``None`` email in ``pii.emails`` are
    restored. Placeholders whose email is ``None`` (normalization failed) are
    left as-is so downstream code can still detect them.

    Returns a new string; ``pii`` is not mutated.
    """
    result = masked_text
    for k, email in enumerate(pii.emails):
        if email is None:
            continue
        placeholder = f"E{k}_{pii.salt}"
        result = result.replace(placeholder, email)
    return result

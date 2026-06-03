"""Build ``PlaceholderAllowlist`` from masked PII state at the bridge boundary only."""

from ..pii_email.models import PIIEmail
from .models import PlaceholderAllowlist


def allowlist_from_pii_email(pii: PIIEmail) -> PlaceholderAllowlist:
    """Derive allowed ``E{n}_{salt}`` tokens from ``salt`` and index count — no email strings."""
    if not pii.salt:
        return PlaceholderAllowlist()
    return PlaceholderAllowlist(
        allowed_tokens=tuple(f"E{i}_{pii.salt}" for i in range(len(pii.emails)))
    )

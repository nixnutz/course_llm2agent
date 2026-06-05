"""Toxiproxy admin helper for L6 chaos integration tests.

Segment A (provider): ``provider_chaos_ollama`` — LiteLLM chaos → Ollama.
Segment B (edge): ``edge_chaos`` — Caddy :4001 → litellm_chaos.

Parent-graph L6 exemplars cover both segments minimally via ``reset_peer``.
"""

from __future__ import annotations

import os
import uuid

import httpx

PROXY_EDGE_CHAOS = "edge_chaos"
PROXY_PROVIDER_CHAOS_OLLAMA = "provider_chaos_ollama"


def resolve_toxiproxy_url(base_url: str | None = None) -> str:
    """Return the Toxiproxy admin URL from ``base_url`` or ``TOXIPROXY_URL`` env."""
    url = base_url or os.getenv("TOXIPROXY_URL")
    if not url:
        raise RuntimeError("Missing TOXIPROXY_URL")
    return url.rstrip("/")


class ToxiproxyAdmin:
    """HTTP client for the Toxiproxy admin API."""

    def __init__(self, base_url: str | None = None) -> None:
        self._base_url = resolve_toxiproxy_url(base_url)

    def reset(self) -> None:
        """Remove all toxics and re-enable all proxies."""
        self._post("/reset")

    def add_reset_peer(self, proxy: str, *, name: str | None = None) -> None:
        """Add a ``reset_peer`` toxic on the named proxy (downstream, toxicity 1.0)."""
        toxic_name = name or f"pytest_reset_peer_{uuid.uuid4().hex[:8]}"
        payload = {
            "name": toxic_name,
            "type": "reset_peer",
            "stream": "downstream",
            "toxicity": 1.0,
            "attributes": {},
        }
        self._post(f"/proxies/{proxy}/toxics", json=payload)

    def is_reachable(self, timeout: float = 2.0) -> bool:
        """Return True when the admin API responds to ``GET /version``."""
        try:
            with httpx.Client(timeout=timeout) as client:
                response = client.get(f"{self._base_url}/version")
                return response.is_success
        except httpx.HTTPError:
            return False

    def _post(self, path: str, *, json: dict | None = None) -> None:
        url = f"{self._base_url}{path}"
        with httpx.Client(timeout=10.0) as client:
            response = client.post(url, json=json)
        if not response.is_success:
            raise RuntimeError(
                f"Toxiproxy admin request failed: POST {path} -> {response.status_code} {response.text}"
            )

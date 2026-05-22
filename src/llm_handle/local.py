"""Cached AsyncOpenAI clients for LiteLLM (clean / chaos channels)."""

from __future__ import annotations

import os

import httpx
import openai

CA_CERT_PATH = "/certs/.caroot/rootCA.pem"
_verify_config = CA_CERT_PATH if os.path.exists(CA_CERT_PATH) else True

# One AsyncOpenAI per (base_url, api_key) for this process / Jupyter kernel.
_async_openai_clients: dict[tuple[str, str], openai.AsyncOpenAI] = {}


def _resolve_base_url(*, chaos: bool) -> str:
    if chaos:
        base_url = os.getenv("MODEL_BASE_URL_CHAOS")
        missing = "Missing MODEL_BASE_URL_CHAOS"
    else:
        base_url = os.getenv("MODEL_BASE_URL_CLEAN")
        missing = "Missing MODEL_BASE_URL_CLEAN"
    if not base_url:
        raise RuntimeError(missing)
    return base_url


def _resolve_api_key(api_key: str | None) -> str:
    if api_key is None:
        api_key = os.getenv("MODEL_API_KEY_DEV")
        if not api_key:
            raise RuntimeError("Missing MODEL_API_KEY_DEV")
    return api_key


def _create_httpx_async_client(timeout: float = 120.0) -> httpx.AsyncClient:
    return httpx.AsyncClient(verify=_verify_config, timeout=timeout)


def _create_openai_async_client(
    api_key: str, base_url: str, http_client: httpx.AsyncClient, max_retries: int = 0
) -> openai.AsyncOpenAI:
    return openai.AsyncOpenAI(
        api_key=api_key,
        base_url=base_url,
        http_client=http_client,
        max_retries=max_retries,
    )


def get_async_openai_client(api_key: str | None = None, chaos: bool = False) -> openai.AsyncOpenAI:
    """Return a cached AsyncOpenAI client for the given virtual key and channel."""
    base_url = _resolve_base_url(chaos=chaos)
    api_key = _resolve_api_key(api_key)
    cache_key = (base_url, api_key)

    cached = _async_openai_clients.get(cache_key)
    if cached is not None:
        return cached

    http_client = _create_httpx_async_client()
    client = _create_openai_async_client(api_key, base_url, http_client)
    _async_openai_clients[cache_key] = client
    return client


async def clear_cache() -> None:
    """Close cached clients and drop entries (e.g. before chaos tests or kernel restart)."""
    for client in _async_openai_clients.values():
        await client.close()
    _async_openai_clients.clear()

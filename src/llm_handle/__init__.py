"""AsyncOpenAI client access for LiteLLM (course notebooks/tests).

See ``local`` for implementation: ``get_async_openai_client`` (clean vs chaos
base URL from ``MODEL_BASE_URL_CLEAN`` / ``MODEL_BASE_URL_CHAOS``) and
``clear_cache``. Default API key when omitted: ``MODEL_API_KEY_DEV``.
"""

from .local import (
    AsyncClientProvider,
    ClientCachePolicy,
    clear_cache,
    create_httpx_async_client,
    get_async_openai_client,
    make_async_openai_client_provider,
    openai_client_context,
)

__all__ = [
    "AsyncClientProvider",
    "ClientCachePolicy",
    "clear_cache",
    "create_httpx_async_client",
    "get_async_openai_client",
    "make_async_openai_client_provider",
    "openai_client_context",
]

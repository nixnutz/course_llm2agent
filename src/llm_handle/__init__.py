"""Cached AsyncOpenAI clients for LiteLLM (course notebooks).

See ``local`` for implementation: ``get_async_openai_client`` (clean vs chaos
base URL from ``MODEL_BASE_URL_CLEAN`` / ``MODEL_BASE_URL_CHAOS``) and
``clear_cache``. Default API key when omitted: ``MODEL_API_KEY_DEV``.
"""

from .local import clear_cache, get_async_openai_client

__all__ = ["clear_cache", "get_async_openai_client"]

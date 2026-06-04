"""Phoenix OTLP setup for LangGraph + AsyncOpenAI (LiteLLM proxy) in dev/notebooks."""

from __future__ import annotations

import logging
import os
from typing import TYPE_CHECKING
from urllib.parse import urlparse

if TYPE_CHECKING:
    from opentelemetry.sdk.trace import TracerProvider

logger = logging.getLogger(__name__)

# Same trust anchor as src/llm_handle/local.py (Caddy TLS on dev_edge).
CA_CERT_PATH = "/certs/.caroot/rootCA.pem"

_tracer_provider: TracerProvider | None = None


def _require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(
            f"Missing {name} in environment. "
            "Set it in container/compose/.env (see .env.example) and restart the dev container."
        )
    return value


def _prepare_collector_endpoint(endpoint: str) -> str:
    """Validate OTLP endpoint and configure OTEL TLS for Caddy HTTPS."""
    parsed = urlparse(endpoint)
    host = (parsed.hostname or "").lower()

    if host == "caddy" and parsed.scheme == "http":
        raise RuntimeError(
            "PHOENIX_COLLECTOR_ENDPOINT must not use http://caddy:6006 — Caddy serves TLS there. "
            "Use https://caddy:6006/v1/traces (dev CA under /certs is applied automatically) or "
            "http://phoenix:6006/v1/traces on backend_core. Update container/compose/.env and "
            "restart the dev container."
        )

    if parsed.scheme == "https" and os.path.exists(CA_CERT_PATH):
        os.environ.setdefault("OTEL_EXPORTER_OTLP_TRACES_CERTIFICATE", CA_CERT_PATH)

    return endpoint


def _resolve_endpoint(endpoint: str | None) -> str:
    if endpoint:
        return _prepare_collector_endpoint(endpoint)
    return _prepare_collector_endpoint(_require_env("PHOENIX_COLLECTOR_ENDPOINT"))


def _resolve_project_name(project_name: str | None) -> str:
    if project_name:
        return project_name
    return _require_env("PHOENIX_PROJECT_NAME")


def enable_langgraph_tracing(
    project_name: str | None = None,
    *,
    endpoint: str | None = None,
    batch: bool = True,
    verbose: bool = False,
) -> TracerProvider:
    """Register Phoenix OTLP export and instrument LangGraph + OpenAI clients.

    Requires ``PHOENIX_COLLECTOR_ENDPOINT`` and ``PHOENIX_PROJECT_NAME`` in the
    environment unless passed as arguments (dev compose sets both from ``.env``).

    For ``https://caddy:...`` the dev root CA at ``CA_CERT_PATH`` is passed to the
    OTLP exporter (same trust as LiteLLM). Plain ``http://caddy:6006`` is rejected.

    ``batch`` and ``verbose`` are forwarded to ``phoenix.otel.register`` (defaults:
    batch export, no stdout banner).

    Call once per kernel **before** importing ``langgraph``, ``llm_nodes``, or
    creating ``AsyncOpenAI`` clients. After experimenting with imports manually,
    restart the kernel and run the tracing cell first.

    UI: https://localhost:6006
    """
    global _tracer_provider

    if _tracer_provider is not None:
        logger.warning("LangGraph tracing already enabled; skipping second setup")
        return _tracer_provider

    from openinference.instrumentation.langchain import LangChainInstrumentor
    from openinference.instrumentation.openai import OpenAIInstrumentor
    from phoenix.otel import register

    resolved_endpoint = _resolve_endpoint(endpoint)
    resolved_project = _resolve_project_name(project_name)

    _tracer_provider = register(
        project_name=resolved_project,
        endpoint=resolved_endpoint,
        batch=batch,
        verbose=verbose,
    )
    LangChainInstrumentor().instrument(tracer_provider=_tracer_provider)
    OpenAIInstrumentor().instrument(tracer_provider=_tracer_provider)

    logger.info(
        "LangGraph tracing enabled: project=%s endpoint=%s",
        resolved_project,
        resolved_endpoint,
    )
    return _tracer_provider


def flush_langgraph_traces(timeout_millis: int = 10_000) -> None:
    """Flush pending OTLP spans (call after ``graph.ainvoke`` in notebooks)."""
    if _tracer_provider is None:
        return
    _tracer_provider.force_flush(timeout_millis=timeout_millis)

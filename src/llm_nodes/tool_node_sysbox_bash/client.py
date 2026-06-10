"""Async HTTP client for the Sysbox Bash Sandbox API."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx
from pydantic import BaseModel, ConfigDict, Field

from src.logging_setup import get_logger

logger = get_logger(__name__, __file__)


class SandboxClientError(Exception):
    """Raised when the Sandbox API returns an error response."""

    def __init__(self, message: str, *, status_code: int | None = None, detail: Any = None):
        super().__init__(message)
        self.status_code = status_code
        self.detail = detail


class SessionCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    graph_invoke_id: str | None = None
    thread_id: str | None = None
    subgraph_name: str | None = None
    node_name: str | None = None
    caller_label: str | None = None


class SessionCreateResponse(BaseModel):
    session_id: str
    container_name: str
    container_id: str


class ExecRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    script: str = Field(..., min_length=1)
    request_id: str | None = None
    tool_round: int | None = Field(default=None, ge=0)
    tool_call_id: str | None = None
    timeout_seconds: int | None = Field(default=None, ge=1)


class ExecResponse(BaseModel):
    session_id: str
    run_id: str
    stdout: str
    stderr: str
    exit_code: int | None
    timed_out: bool
    output_limit_exceeded: bool
    elapsed_ms: int
    metadata_path: str
    metadata: dict[str, Any]


@dataclass(frozen=True)
class SessionCorrelation:
    graph_invoke_id: str | None = None
    thread_id: str | None = None
    subgraph_name: str = "tool_node_sysbox_bash"
    node_name: str = "bridge"
    caller_label: str = "langgraph.tool_node_sysbox_bash"


@dataclass(frozen=True)
class ExecCorrelation:
    request_id: str | None = None
    tool_round: int | None = None
    tool_call_id: str | None = None


class SandboxClient:
    """Thin async wrapper around the Sandbox HTTP API."""

    def __init__(self, base_url: str, *, http_client: httpx.AsyncClient | None = None):
        self._base_url = base_url.rstrip("/")
        self._owns_client = http_client is None
        self._http = http_client or httpx.AsyncClient()

    async def aclose(self) -> None:
        if self._owns_client:
            await self._http.aclose()

    async def start_session(self, *, correlation: SessionCorrelation) -> SessionCreateResponse:
        body = SessionCreateRequest(
            graph_invoke_id=correlation.graph_invoke_id,
            thread_id=correlation.thread_id,
            subgraph_name=correlation.subgraph_name,
            node_name=correlation.node_name,
            caller_label=correlation.caller_label,
        )
        return await self._request(
            "POST",
            "/sessions",
            json=body.model_dump(),
            model=SessionCreateResponse,
        )

    async def execute_in_session(
        self,
        session_id: str,
        *,
        script: str,
        correlation: ExecCorrelation,
        timeout_seconds: int,
    ) -> ExecResponse:
        body = ExecRequest(
            script=script,
            request_id=correlation.request_id,
            tool_round=correlation.tool_round,
            tool_call_id=correlation.tool_call_id,
            timeout_seconds=timeout_seconds,
        )
        http_timeout = max(timeout_seconds, 1) + 5.0
        return await self._request(
            "POST",
            f"/sessions/{session_id}/exec",
            json=body.model_dump(),
            model=ExecResponse,
            timeout=http_timeout,
        )

    async def end_session(self, session_id: str) -> None:
        try:
            await self._request("DELETE", f"/sessions/{session_id}", model=None)
        except SandboxClientError as exc:
            logger.warning("end_session best-effort failed for %s: %s", session_id, exc)

    async def _request(
        self,
        method: str,
        path: str,
        *,
        json: dict[str, Any] | None = None,
        model: type[BaseModel] | None,
        timeout: float | None = 30.0,
    ):
        url = f"{self._base_url}{path}"
        try:
            response = await self._http.request(method, url, json=json, timeout=timeout)
        except httpx.HTTPError as exc:
            raise SandboxClientError(f"HTTP request failed: {exc}") from exc
        if response.status_code >= 400:
            detail: Any
            try:
                detail = response.json()
            except ValueError:
                detail = response.text
            raise SandboxClientError(
                f"Sandbox API {method} {path} failed with {response.status_code}",
                status_code=response.status_code,
                detail=detail,
            )
        if model is None:
            return None
        return model.model_validate(response.json())

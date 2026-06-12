"""Pydantic models for the Sandbox HTTP API."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class SessionCreateRequest(BaseModel):
    """Trusted session-level correlation supplied by future LangGraph code."""

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
    # Unversioned observability supplement; keys may change. Execution contract is the
    # typed fields above. On-disk metadata.json is self-contained (includes duplicates).
    metadata: dict[str, Any]


class HealthResponse(BaseModel):
    status: str
    inner_docker: bool
    exec_image_present: bool
    exec_image_name: str
    limits: dict[str, int]

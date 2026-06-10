"""Sysbox Bash Sandbox HTTP API."""

from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse

from config import load_settings
from docker_runtime import DockerCommandError, image_present, inner_docker_available
from models import (
    ExecRequest,
    ExecResponse,
    HealthResponse,
    SessionCreateRequest,
    SessionCreateResponse,
)
from sessions import (
    ScriptTooLargeError,
    SessionManager,
    SessionNotFoundError,
    TimeoutLimitError,
)

app = FastAPI(title="sysbox_bash", version="0.2.0")
settings = load_settings()
session_manager = SessionManager(settings)


def _probe() -> HealthResponse:
    inner_docker = inner_docker_available()
    exec_image_present = image_present(settings.exec_image_name) if inner_docker else False
    healthy = inner_docker and exec_image_present
    return HealthResponse(
        status="healthy" if healthy else "unhealthy",
        inner_docker=inner_docker,
        exec_image_present=exec_image_present,
        exec_image_name=settings.exec_image_name,
        limits={
            "max_script_bytes": settings.max_script_bytes,
            "max_stdout_bytes": settings.max_stdout_bytes,
            "max_stderr_bytes": settings.max_stderr_bytes,
            "default_timeout_seconds": settings.default_timeout_seconds,
        },
    )


@app.get("/health")
def health() -> JSONResponse:
    body = _probe()
    code = 200 if body.status == "healthy" else 503
    return JSONResponse(content=body.model_dump(), status_code=code)


@app.post("/sessions")
def start_session(request: SessionCreateRequest) -> SessionCreateResponse:
    try:
        return session_manager.create_session(request)
    except DockerCommandError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/sessions/{session_id}/exec")
def execute_in_session(session_id: str, request: ExecRequest) -> ExecResponse:
    try:
        return session_manager.execute(session_id, request)
    except SessionNotFoundError as exc:
        raise HTTPException(status_code=404, detail=f"unknown session_id: {session_id}") from exc
    except ScriptTooLargeError as exc:
        raise HTTPException(status_code=413, detail=str(exc)) from exc
    except TimeoutLimitError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except DockerCommandError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.delete("/sessions/{session_id}")
def end_session(session_id: str) -> dict[str, object]:
    session_manager.delete_session(session_id)
    return {"session_id": session_id, "deleted": True}

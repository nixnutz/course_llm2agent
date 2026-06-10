"""Minimal Sandbox API skeleton — GET /health only (Slice 1)."""

from __future__ import annotations

import os
import subprocess

from fastapi import FastAPI
from fastapi.responses import JSONResponse

app = FastAPI(title="sysbox_bash", version="0.1.0")


def _exec_image_name() -> str:
    return os.environ.get("SBASH_EXEC_IMAGE_NAME", "course-llm-sysbox-bash-exec:dev")


def _probe() -> dict[str, object]:
    inner_docker = False
    exec_image_present = False
    try:
        subprocess.run(
            ["docker", "info"],
            check=True,
            capture_output=True,
            timeout=5,
        )
        inner_docker = True
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
        inner_docker = False

    if inner_docker:
        name = _exec_image_name()
        try:
            subprocess.run(
                ["docker", "image", "inspect", name],
                check=True,
                capture_output=True,
                timeout=5,
            )
            exec_image_present = True
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
            exec_image_present = False

    healthy = inner_docker and exec_image_present
    return {
        "status": "healthy" if healthy else "unhealthy",
        "inner_docker": inner_docker,
        "exec_image_present": exec_image_present,
        "exec_image_name": _exec_image_name(),
    }


@app.get("/health")
def health() -> JSONResponse:
    body = _probe()
    code = 200 if body["status"] == "healthy" else 503
    return JSONResponse(content=body, status_code=code)

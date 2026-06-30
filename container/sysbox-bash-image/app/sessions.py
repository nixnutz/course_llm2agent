"""Session and script execution management for the Sandbox API."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import secrets
import shutil
import socket
import subprocess
import time
from typing import Any

from config import Settings
from docker_runtime import (
    MANAGED_LABEL,
    SESSION_LABEL,
    container_exists,
    inspect_container_id,
    run_docker,
    terminate_sandbox_processes,
)
from models import (
    ExecRequest,
    ExecResponse,
    SessionCreateRequest,
    SessionCreateResponse,
)


SANDBOX_UID = 1001
SANDBOX_GID = 1001
TIMEOUT_EXIT_CODE = 124
OUTPUT_LIMIT_EXIT_CODE = 137
# Omitted from HTTP metadata only; still written to metadata.json for self-contained audit.
_HTTP_METADATA_OMIT = frozenset(
    {
        "session_id",
        "run_id",
        "elapsed_ms",
        "exit_code",
        "timed_out",
        "output_limit_exceeded",
    }
)


class SessionNotFoundError(RuntimeError):
    pass


class ScriptTooLargeError(RuntimeError):
    def __init__(self, actual_bytes: int, limit_bytes: int) -> None:
        super().__init__(f"script is {actual_bytes} bytes; limit is {limit_bytes}")
        self.actual_bytes = actual_bytes
        self.limit_bytes = limit_bytes


class TimeoutLimitError(RuntimeError):
    def __init__(self, requested_seconds: int, limit_seconds: int) -> None:
        super().__init__(
            "timeout_seconds may not exceed SBASH_DEFAULT_TIMEOUT_SECONDS "
            f"({limit_seconds}); requested {requested_seconds}"
        )
        self.requested_seconds = requested_seconds
        self.limit_seconds = limit_seconds


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _chown_sandbox(path: Path) -> None:
    os.chown(path, SANDBOX_UID, SANDBOX_GID)


def _read_prefix(path: Path, limit: int) -> str:
    if not path.exists():
        return ""
    with path.open("rb") as file:
        return file.read(limit).decode("utf-8", errors="replace")


def _file_size(path: Path) -> int:
    if not path.exists():
        return 0
    return path.stat().st_size


class SessionManager:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.sessions_root = Path(settings.sessions_root)

    def create_session(self, request: SessionCreateRequest) -> SessionCreateResponse:
        self.sessions_root.mkdir(parents=True, exist_ok=True)
        session_id = secrets.token_hex(16)
        session_dir = self._session_dir(session_id)
        session_dir.mkdir(parents=True, exist_ok=False)
        _chown_sandbox(session_dir)

        container_name = self._container_name(session_id)
        run_docker(
            [
                "run",
                "-d",
                "--name",
                container_name,
                "--hostname",
                container_name,
                "--network",
                self.settings.session_network_name,
                "--user",
                "root",
                "--label",
                f"{MANAGED_LABEL}=true",
                "--label",
                f"{SESSION_LABEL}={session_id}",
                "--mount",
                f"type=bind,source={session_dir},target=/sandbox/session",
                "--workdir",
                "/sandbox/session",
                self.settings.exec_image_name,
                "sleep",
                "infinity",
            ],
            timeout=30,
        )
        container_id = inspect_container_id(container_name)
        session_data = {
            "session_id": session_id,
            "container_name": container_name,
            "container_id": container_id,
            "created_at": _now(),
            "graph_invoke_id": request.graph_invoke_id,
            "thread_id": request.thread_id,
            "subgraph_name": request.subgraph_name,
            "node_name": request.node_name,
            "caller_label": request.caller_label,
        }
        _write_json(session_dir / "session.json", session_data)
        return SessionCreateResponse(
            session_id=session_id,
            container_name=container_name,
            container_id=container_id,
        )

    def execute(self, session_id: str, request: ExecRequest) -> ExecResponse:
        script_bytes = request.script.encode("utf-8")
        if len(script_bytes) > self.settings.max_script_bytes:
            raise ScriptTooLargeError(len(script_bytes), self.settings.max_script_bytes)

        timeout_seconds = request.timeout_seconds or self.settings.default_timeout_seconds
        if timeout_seconds > self.settings.default_timeout_seconds:
            raise TimeoutLimitError(
                requested_seconds=timeout_seconds,
                limit_seconds=self.settings.default_timeout_seconds,
            )

        session_data = self._load_session(session_id)
        container_name = str(session_data["container_name"])
        run_id = self._next_run_id(session_id)
        run_dir = self._session_dir(session_id) / "runs" / run_id
        run_dir.mkdir(parents=True, exist_ok=False)
        _chown_sandbox(run_dir)

        script_path = run_dir / "script.sh"
        runner_path = run_dir / "runner.sh"
        stdout_path = run_dir / "stdout.txt"
        stderr_path = run_dir / "stderr.txt"
        metadata_path = run_dir / "metadata.json"
        container_run_dir = f"/sandbox/session/runs/{run_id}"
        container_script_path = f"{container_run_dir}/script.sh"
        container_runner_path = f"{container_run_dir}/runner.sh"
        container_stdout_path = f"{container_run_dir}/stdout.txt"
        container_stderr_path = f"{container_run_dir}/stderr.txt"

        script_path.write_bytes(script_bytes)
        runner_path.write_text(
            "#!/usr/bin/env bash\n"
            "set -euo pipefail\n"
            "cd /sandbox/session\n"
            f"/bin/bash {container_script_path} > {container_stdout_path} 2> {container_stderr_path}\n",
            encoding="utf-8",
        )
        for path in (script_path, runner_path):
            path.chmod(0o755)
            _chown_sandbox(path)

        command = [
            "docker",
            "exec",
            "--user",
            "sandbox",
            "--workdir",
            "/sandbox/session",
            container_name,
            "/bin/bash",
            container_runner_path,
        ]

        created_at = _now()
        started_at = _now()
        started_monotonic = time.monotonic()
        timed_out = False
        output_limit_exceeded = False
        termination_reason = "completed"

        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        while True:
            returncode = process.poll()
            stdout_bytes = _file_size(stdout_path)
            stderr_bytes = _file_size(stderr_path)
            if (
                stdout_bytes > self.settings.max_stdout_bytes
                or stderr_bytes > self.settings.max_stderr_bytes
            ):
                output_limit_exceeded = True
                termination_reason = "output_limit_exceeded"
                terminate_sandbox_processes(container_name)
                break
            if time.monotonic() - started_monotonic > timeout_seconds:
                timed_out = True
                termination_reason = "timeout"
                terminate_sandbox_processes(container_name)
                break
            if returncode is not None:
                break
            time.sleep(0.1)

        if timed_out or output_limit_exceeded:
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
        else:
            process.wait()

        ended_at = _now()
        elapsed_ms = int((time.monotonic() - started_monotonic) * 1000)
        stdout_bytes = _file_size(stdout_path)
        stderr_bytes = _file_size(stderr_path)
        if (
            stdout_bytes > self.settings.max_stdout_bytes
            or stderr_bytes > self.settings.max_stderr_bytes
        ):
            output_limit_exceeded = True
            termination_reason = "output_limit_exceeded"

        if timed_out:
            exit_code = TIMEOUT_EXIT_CODE
        elif output_limit_exceeded:
            exit_code = OUTPUT_LIMIT_EXIT_CODE
        else:
            exit_code = process.returncode
        # Unversioned lab schema; metadata.json is the full audit record on disk.
        metadata = {
            "session_id": session_id,
            "run_id": run_id,
            "request_id": request.request_id,
            "created_at": created_at,
            "started_at": started_at,
            "ended_at": ended_at,
            "elapsed_ms": elapsed_ms,
            "graph_invoke_id": session_data.get("graph_invoke_id"),
            "thread_id": session_data.get("thread_id"),
            "subgraph_name": session_data.get("subgraph_name"),
            "node_name": session_data.get("node_name"),
            "caller_label": session_data.get("caller_label"),
            "tool_round": request.tool_round,
            "tool_call_id": request.tool_call_id,
            "inner_container_id": session_data.get("container_id"),
            "inner_container_name": container_name,
            "sandbox_service_hostname": socket.gethostname(),
            "command": command,
            "command_kind": "docker_exec_script_file",
            "script_path": str(script_path),
            "script_size_bytes": len(script_bytes),
            "script_sha256": hashlib.sha256(script_bytes).hexdigest(),
            "stdout_path": str(stdout_path),
            "stderr_path": str(stderr_path),
            "stdout_bytes": stdout_bytes,
            "stderr_bytes": stderr_bytes,
            "exit_code": exit_code,
            "timed_out": timed_out,
            "output_limit_exceeded": output_limit_exceeded,
            "termination_reason": termination_reason,
            "timeout_seconds": timeout_seconds,
            "max_script_bytes": self.settings.max_script_bytes,
            "max_stdout_bytes": self.settings.max_stdout_bytes,
            "max_stderr_bytes": self.settings.max_stderr_bytes,
        }
        _write_json(metadata_path, metadata)
        response_metadata = {
            key: value for key, value in metadata.items() if key not in _HTTP_METADATA_OMIT
        }

        return ExecResponse(
            session_id=session_id,
            run_id=run_id,
            stdout=_read_prefix(stdout_path, self.settings.max_stdout_bytes),
            stderr=_read_prefix(stderr_path, self.settings.max_stderr_bytes),
            exit_code=exit_code,
            timed_out=timed_out,
            output_limit_exceeded=output_limit_exceeded,
            elapsed_ms=elapsed_ms,
            metadata_path=str(metadata_path),
            metadata=response_metadata,
        )

    def delete_session(self, session_id: str) -> None:
        container_name = self._container_name(session_id)
        run_docker(["rm", "-f", container_name], check=False, timeout=20)
        shutil.rmtree(self._session_dir(session_id), ignore_errors=True)

    def _load_session(self, session_id: str) -> dict[str, Any]:
        session_data = self._load_session_data_if_present(session_id)
        container_name = session_data.get("container_name") or self._container_name(session_id)
        if not container_exists(str(container_name)):
            raise SessionNotFoundError(session_id)
        return session_data

    def _load_session_data_if_present(self, session_id: str) -> dict[str, Any]:
        path = self._session_dir(session_id) / "session.json"
        if not path.exists():
            return {
                "session_id": session_id,
                "container_name": self._container_name(session_id),
                "container_id": None,
            }
        return _read_json(path)

    def _next_run_id(self, session_id: str) -> str:
        runs_dir = self._session_dir(session_id) / "runs"
        runs_dir.mkdir(parents=True, exist_ok=True)
        existing = [int(path.name) for path in runs_dir.iterdir() if path.name.isdigit()]
        return str(max(existing, default=0) + 1)

    def _session_dir(self, session_id: str) -> Path:
        return self.sessions_root / session_id

    @staticmethod
    def _container_name(session_id: str) -> str:
        return f"sysbox-bash-session-{session_id}"

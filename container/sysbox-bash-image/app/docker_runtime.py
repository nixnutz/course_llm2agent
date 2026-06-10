"""Small Docker CLI wrapper for the inner Docker daemon."""

from __future__ import annotations

from dataclasses import dataclass
import subprocess


MANAGED_LABEL = "course.llm2agent.sysbox_bash.managed"
SESSION_LABEL = "course.llm2agent.sysbox_bash.session_id"


@dataclass(frozen=True)
class CommandResult:
    returncode: int
    stdout: str
    stderr: str


class DockerCommandError(RuntimeError):
    def __init__(self, command: list[str], result: CommandResult) -> None:
        super().__init__(
            f"Docker command failed ({result.returncode}): {' '.join(command)}\n"
            f"stdout={result.stdout}\nstderr={result.stderr}"
        )
        self.command = command
        self.result = result


def run_docker(args: list[str], *, check: bool = True, timeout: int = 30) -> CommandResult:
    command = ["docker", *args]
    try:
        completed = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as exc:
        result = CommandResult(
            returncode=124,
            stdout=exc.stdout or "",
            stderr=exc.stderr or "docker command timed out",
        )
        if check:
            raise DockerCommandError(command, result) from exc
        return result
    except FileNotFoundError as exc:
        result = CommandResult(returncode=127, stdout="", stderr="docker not found")
        if check:
            raise DockerCommandError(command, result) from exc
        return result

    result = CommandResult(
        returncode=completed.returncode,
        stdout=completed.stdout,
        stderr=completed.stderr,
    )
    if check and completed.returncode != 0:
        raise DockerCommandError(command, result)
    return result


def inner_docker_available() -> bool:
    return run_docker(["info"], check=False, timeout=5).returncode == 0


def image_present(image_name: str) -> bool:
    return run_docker(["image", "inspect", image_name], check=False, timeout=5).returncode == 0


def inspect_container_id(container_name: str) -> str:
    result = run_docker(
        ["container", "inspect", "--format", "{{.Id}}", container_name],
        timeout=10,
    )
    return result.stdout.strip()


def container_exists(container_name: str) -> bool:
    return (
        run_docker(
            ["container", "inspect", container_name],
            check=False,
            timeout=10,
        ).returncode
        == 0
    )


def terminate_sandbox_processes(container_name: str) -> None:
    """Best-effort cleanup for scripts running as the sandbox user."""

    run_docker(
        [
            "exec",
            container_name,
            "/bin/bash",
            "-lc",
            "pkill -TERM -u sandbox 2>/dev/null || true; "
            "sleep 1; "
            "pkill -KILL -u sandbox 2>/dev/null || true",
        ],
        check=False,
        timeout=5,
    )

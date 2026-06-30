"""Runtime configuration for the Sysbox Bash Sandbox API."""

from __future__ import annotations

from dataclasses import dataclass
import os


def _required_env(name: str) -> str:
    raw = os.environ.get(name)
    if raw is None or raw == "":
        raise RuntimeError(f"Missing required environment variable: {name}")
    return raw


DEFAULT_SESSION_NETWORK_NAME = "sbash_sessions"


def _optional_env(name: str, default: str) -> str:
    raw = os.environ.get(name)
    if raw is None or raw == "":
        return default
    return raw


def _int_from_env(name: str, *, minimum: int = 1) -> int:
    raw = _required_env(name)
    try:
        value = int(raw)
    except ValueError as exc:
        raise RuntimeError(f"{name} must be an integer, got {raw!r}") from exc
    if value < minimum:
        raise RuntimeError(f"{name} must be >= {minimum}, got {value}")
    return value


@dataclass(frozen=True)
class Settings:
    """Environment-backed settings owned by the trusted Sandbox API."""

    exec_image_name: str
    max_script_bytes: int
    max_stdout_bytes: int
    max_stderr_bytes: int
    default_timeout_seconds: int
    sessions_root: str
    session_network_name: str


def load_settings() -> Settings:
    return Settings(
        exec_image_name=_required_env("SBASH_EXEC_IMAGE_NAME"),
        max_script_bytes=_int_from_env("SBASH_MAX_SCRIPT_BYTES"),
        max_stdout_bytes=_int_from_env("SBASH_MAX_STDOUT_BYTES"),
        max_stderr_bytes=_int_from_env("SBASH_MAX_STDERR_BYTES"),
        default_timeout_seconds=_int_from_env("SBASH_DEFAULT_TIMEOUT_SECONDS"),
        sessions_root=_required_env("SBASH_SESSIONS_ROOT"),
        session_network_name=_optional_env(
            "SBASH_SESSION_NETWORK_NAME", DEFAULT_SESSION_NETWORK_NAME
        ),
    )

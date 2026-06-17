"""LiteLLM proxy callback: pace cloud model dispatches by RPM group."""

from __future__ import annotations

import asyncio
import json
import os
import time
from pathlib import Path
from typing import Any, Mapping

from litellm.integrations.custom_logger import CustomLogger


def should_bypass(model: str, bypass_prefixes: list[str]) -> bool:
    """Return True when the model alias should skip pacing (local Ollama paths)."""
    for prefix in bypass_prefixes:
        if model == prefix or model.startswith(f"{prefix}/"):
            return True
    return False


def resolve_group(
    model: str,
    groups: Mapping[str, Mapping[str, Any]],
) -> tuple[str | None, int | None]:
    """Map a LiteLLM model alias to a pacing group name and group rpm."""
    for group_name, group_cfg in groups.items():
        if model in group_cfg.get("models", []):
            return group_name, int(group_cfg["rpm"])
    return None, None


def compute_wait_seconds(now: float, last_sent: float, rpm: int) -> float:
    """Seconds to sleep before the next dispatch for the given rpm budget."""
    if rpm <= 0:
        return 0.0
    min_interval = 60.0 / rpm
    return max(0.0, last_sent + min_interval - now)


def should_pace_call_type(call_type: str) -> bool:
    """Return True for LiteLLM proxy chat-completion call types the lab uses."""
    return call_type in {"completion", "acompletion"}


def _default_config_path() -> Path:
    return Path(__file__).with_name("cloud_pacing.json")


def load_pacing_config(config_path: Path | None = None) -> dict[str, Any]:
    path = config_path or Path(
        os.environ.get("CLOUD_PACING_CONFIG", str(_default_config_path()))
    )
    with path.open(encoding="utf-8") as config_file:
        return json.load(config_file)


class _GroupState:
    """Per-group pacing state (plain class: dataclass breaks under LiteLLM dynamic import)."""

    def __init__(self, rpm: int) -> None:
        self.rpm = rpm
        self.lock = asyncio.Lock()
        self.last_sent = 0.0


class CloudPacingHandler(CustomLogger):
    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self._enabled = os.environ.get("CLOUD_PACING_ENABLED", "0") == "1"
        if config is not None:
            self._init_from_config(config)
        elif self._enabled:
            self._init_from_config(load_pacing_config())
        else:
            # Disabled services (e.g. litellm_chaos) must not fail startup on missing JSON.
            self._init_from_config({})

    def _init_from_config(self, config: dict[str, Any]) -> None:
        self._config = config
        self._default_rpm = int(config.get("default_rpm", 2))
        self._bypass_prefixes = list(config.get("bypass_prefixes", []))
        self._groups: dict[str, _GroupState] = {}
        for group_name, group_cfg in config.get("groups", {}).items():
            self._groups[group_name] = _GroupState(rpm=int(group_cfg["rpm"]))
        self._default_state = _GroupState(rpm=self._default_rpm)

    def _resolve_pacing_target(self, model: str) -> _GroupState:
        group_name, _group_rpm = resolve_group(model, self._config.get("groups", {}))
        if group_name is not None:
            return self._groups[group_name]
        return self._default_state

    async def _pace_dispatch(self, model: str) -> None:
        group_state = self._resolve_pacing_target(model)
        rpm = group_state.rpm
        if rpm <= 0:
            return

        async with group_state.lock:
            now = time.monotonic()
            wait_seconds = compute_wait_seconds(now, group_state.last_sent, rpm)
            if wait_seconds > 0:
                await asyncio.sleep(wait_seconds)
            group_state.last_sent = time.monotonic()

    async def async_pre_call_hook(
        self,
        user_api_key_dict: dict[str, Any],
        cache: Any,
        data: dict[str, Any],
        call_type: str,
    ) -> dict[str, Any]:
        if not self._enabled or not should_pace_call_type(call_type):
            return data

        model = str(data.get("model") or "")
        if not model or should_bypass(model, self._bypass_prefixes):
            return data

        await self._pace_dispatch(model)
        return data


pacing_handler_instance = CloudPacingHandler()

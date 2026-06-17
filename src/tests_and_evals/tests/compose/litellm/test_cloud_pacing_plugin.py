"""Unit tests for cloud pacing helpers loaded from compose config mount.

Requires the `dev` compose mount:
`./config/litellm:/workspace/compose-config/litellm:ro,z`
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import types
from unittest.mock import AsyncMock, patch

import pytest

_PLUGIN_PATH = Path("/workspace/compose-config/litellm/cloud_pacing_plugin.py")
_LITELLM_STUB_KEYS = (
    "litellm",
    "litellm.integrations",
    "litellm.integrations.custom_logger",
)


def _install_litellm_stubs() -> None:
    custom_logger_module = types.ModuleType("litellm.integrations.custom_logger")
    custom_logger_module.CustomLogger = type("CustomLogger", (), {})
    integrations_module = types.ModuleType("litellm.integrations")
    litellm_module = types.ModuleType("litellm")

    sys.modules["litellm"] = litellm_module
    sys.modules["litellm.integrations"] = integrations_module
    sys.modules["litellm.integrations.custom_logger"] = custom_logger_module


def _restore_sys_modules(saved: dict[str, object | None]) -> None:
    for key, previous in saved.items():
        if previous is None:
            sys.modules.pop(key, None)
        else:
            sys.modules[key] = previous  # type: ignore[assignment]


def _load_plugin_module():
    if not _PLUGIN_PATH.exists():
        pytest.fail(f"Expected plugin file at {_PLUGIN_PATH}. Is the dev mount configured?")

    spec = importlib.util.spec_from_file_location("cloud_pacing_plugin", _PLUGIN_PATH)
    if spec is None or spec.loader is None:
        pytest.fail(f"Could not load spec from {_PLUGIN_PATH}")

    saved_modules = {key: sys.modules.get(key) for key in (*_LITELLM_STUB_KEYS, spec.name)}
    try:
        _install_litellm_stubs()
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        return module
    finally:
        _restore_sys_modules(saved_modules)


@pytest.mark.unit
def test_should_bypass_matches_prefix_and_nested_path():
    plugin = _load_plugin_module()
    bypasses = ["ollama", "ollama_chat", "ollama_chat_stream"]

    assert plugin.should_bypass("ollama", bypasses)
    assert plugin.should_bypass("ollama_chat/my-model", bypasses)
    assert not plugin.should_bypass("mistral-large", bypasses)


@pytest.mark.unit
def test_resolve_group_maps_cloud_aliases():
    plugin = _load_plugin_module()
    groups = {
        "mistral": {"models": ["mistral-large", "mistral-large-old", "mistral-small"], "rpm": 2},
        "groq": {"models": ["groq-llama-3.3-70b"], "rpm": 25},
    }

    group_name, rpm = plugin.resolve_group("groq-llama-3.3-70b", groups)
    assert group_name == "groq"
    assert rpm == 25

    unknown_name, unknown_rpm = plugin.resolve_group("gemini-2.5-pro", groups)
    assert unknown_name is None
    assert unknown_rpm is None


@pytest.mark.unit
def test_mistral_aliases_share_same_group_and_rpm():
    plugin = _load_plugin_module()
    groups = {
        "mistral": {"models": ["mistral-large", "mistral-large-old", "mistral-small"], "rpm": 2},
    }

    first_name, first_rpm = plugin.resolve_group("mistral-large", groups)
    second_name, second_rpm = plugin.resolve_group("mistral-small", groups)

    assert first_name == second_name == "mistral"
    assert first_rpm == second_rpm == 2


@pytest.mark.unit
def test_compute_wait_seconds_interval_math():
    plugin = _load_plugin_module()

    # rpm=2 => one dispatch every 30 seconds.
    assert plugin.compute_wait_seconds(now=45.0, last_sent=30.0, rpm=2) == pytest.approx(15.0)
    assert plugin.compute_wait_seconds(now=60.0, last_sent=30.0, rpm=2) == pytest.approx(0.0)
    assert plugin.compute_wait_seconds(now=100.0, last_sent=90.0, rpm=0) == pytest.approx(0.0)


@pytest.mark.unit
@pytest.mark.parametrize(
    ("call_type", "expected"),
    [
        ("completion", True),
        ("acompletion", True),
        ("embedding", False),
        ("aembedding", False),
    ],
)
def test_should_pace_call_type_matrix(call_type: str, expected: bool):
    plugin = _load_plugin_module()
    assert plugin.should_pace_call_type(call_type) is expected


@pytest.mark.unit
@pytest.mark.asyncio
async def test_async_pre_call_hook_paces_acompletion():
    plugin_module = _load_plugin_module()
    config = {
        "default_rpm": 2,
        "groups": {
            "mistral": {
                "models": ["mistral-large-old"],
                "rpm": 2,
            },
        },
        "bypass_prefixes": ["ollama"],
    }
    handler = plugin_module.CloudPacingHandler(config=config)
    handler._enabled = True

    group_state = handler._groups["mistral"]
    group_state.last_sent = 100.0

    with (
        patch.object(plugin_module.time, "monotonic", side_effect=[110.0, 140.0]),
        patch.object(plugin_module.asyncio, "sleep", new_callable=AsyncMock) as sleep_mock,
    ):
        result = await handler.async_pre_call_hook(
            user_api_key_dict={},
            cache=None,
            data={"model": "mistral-large-old"},
            call_type="acompletion",
        )

    assert result == {"model": "mistral-large-old"}
    sleep_mock.assert_awaited_once_with(20.0)

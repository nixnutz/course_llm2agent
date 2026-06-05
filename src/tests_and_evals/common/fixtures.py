"""Shared fixtures for tests_and_evals (minimal baseline)."""

import os

import pytest

from src.tests_and_evals.common.toxiproxy import ToxiproxyAdmin

# Course default for smoke/chaos pytest; not env-configurable (no SMOKE_MODEL env var).
SMOKE_MODEL = "ollama_chat/llama3.2:3b"


def _skip_unless_chaos_env() -> None:
    if not os.getenv("MODEL_API_KEY_DEV") or not os.getenv("MODEL_BASE_URL_CHAOS"):
        pytest.skip("Chaos test requires MODEL_API_KEY_DEV and MODEL_BASE_URL_CHAOS")
    if not os.getenv("TOXIPROXY_URL"):
        pytest.skip("Chaos test requires TOXIPROXY_URL")
    if not ToxiproxyAdmin().is_reachable():
        pytest.skip("Chaos test requires reachable Toxiproxy admin (stack up?)")


@pytest.fixture
def get_model_for_smoke_test():
    model = SMOKE_MODEL

    # Optional guard: skip if runtime secrets/base-url are missing
    if not os.getenv("MODEL_API_KEY_DEV") or not os.getenv("MODEL_BASE_URL_CLEAN"):
        pytest.skip("Smoke test requires MODEL_API_KEY_DEV and MODEL_BASE_URL_CLEAN")

    return model


@pytest.fixture(scope="module")
def chaos_test_model():
    """Module-scoped model + env guard for L6 chaos tests and warmup."""
    _skip_unless_chaos_env()
    return SMOKE_MODEL


@pytest.fixture
def toxiproxy_admin():
    """Function-scoped Toxiproxy admin client; resets toxics after each test."""
    admin = ToxiproxyAdmin()
    yield admin
    admin.reset()

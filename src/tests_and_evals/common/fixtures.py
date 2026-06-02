"""Shared fixtures for tests_and_evals (minimal baseline)."""

import os

import pytest

_SMOKE_MODEL = "ollama_chat/llama3.2:3b"


@pytest.fixture
def get_model_for_smoke_test():
    model = os.getenv("SMOKE_MODEL", _SMOKE_MODEL)

    # Optional guard: skip if runtime secrets/base-url are missing
    if not os.getenv("MODEL_API_KEY_DEV") or not os.getenv("MODEL_BASE_URL_CLEAN"):
        pytest.skip("Smoke test requires MODEL_API_KEY_DEV and MODEL_BASE_URL_CLEAN")

    return model

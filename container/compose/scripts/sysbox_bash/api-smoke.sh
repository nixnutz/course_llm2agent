#!/usr/bin/env bash
set -euo pipefail

python - <<'PY'
import json
import os
import sys
import urllib.error
import urllib.request


BASE_URL = os.environ.get("SBASH_BASE_URL", "http://sysbox_bash:8080").rstrip("/")


def call(method, path, payload=None, expected=200):
    data = None
    headers = {}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(
        f"{BASE_URL}{path}",
        data=data,
        headers=headers,
        method=method,
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            status = response.status
            body = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        status = exc.code
        body = exc.read().decode("utf-8")

    if status != expected:
        raise AssertionError(f"{method} {path}: expected {expected}, got {status}: {body}")
    if not body:
        return {}
    return json.loads(body)


def assert_equal(actual, expected, label):
    if actual != expected:
        raise AssertionError(f"{label}: expected {expected!r}, got {actual!r}")


def assert_true(value, label):
    if not value:
        raise AssertionError(f"{label}: expected truthy value, got {value!r}")


def assert_absent(mapping, key, label):
    if key in mapping:
        raise AssertionError(f"{label}: unexpected key {key!r} present")


health = call("GET", "/health")
limits = health["limits"]
call("GET", "/sessions", expected=405)
call("POST", "/sessions", {"unknown": "field"}, expected=422)
session = None
empty_session = None
try:
    session = call(
        "POST",
        "/sessions",
        {
            "graph_invoke_id": "smoke-graph",
            "thread_id": "smoke-thread",
            "subgraph_name": "smoke-subgraph",
            "node_name": "smoke-node",
            "caller_label": "api-smoke",
        },
    )
    session_id = session["session_id"]

    result = call(
        "POST",
        f"/sessions/{session_id}/exec",
        {
            "script": "echo hello",
            "request_id": "smoke-request-1",
            "tool_round": 1,
            "tool_call_id": "smoke-tool-call",
        },
    )
    assert_equal(result["stdout"], "hello\n", "echo stdout")
    assert_equal(result["stderr"], "", "echo stderr")
    assert_equal(result["exit_code"], 0, "echo exit_code")
    assert_equal(result["metadata"]["thread_id"], "smoke-thread", "session correlation")
    assert_equal(result["metadata"]["tool_call_id"], "smoke-tool-call", "run correlation")
    assert_equal(result["metadata"]["termination_reason"], "completed", "echo termination")
    assert_absent(result["metadata"], "script", "metadata does not store script body")

    call("POST", f"/sessions/{session_id}/exec", {"script": "echo state > state.txt"})
    result = call("POST", f"/sessions/{session_id}/exec", {"script": "cat state.txt"})
    assert_equal(result["stdout"], "state\n", "same-session state")

    result = call("POST", f"/sessions/{session_id}/exec", {"script": "exit 7"})
    assert_equal(result["exit_code"], 7, "non-zero exit_code")

    result = call(
        "POST",
        f"/sessions/{session_id}/exec",
        {"script": "sleep 2", "timeout_seconds": 1},
    )
    assert_equal(result["timed_out"], True, "timeout flag")
    assert_equal(result["exit_code"], 124, "timeout exit_code")
    assert_equal(result["metadata"]["termination_reason"], "timeout", "timeout termination")
    assert_equal(result["metadata"]["timeout_seconds"], 1, "effective timeout metadata")

    call(
        "POST",
        f"/sessions/{session_id}/exec",
        {
            "script": "echo should-not-run",
            "timeout_seconds": limits["default_timeout_seconds"] + 1,
        },
        expected=422,
    )

    oversized = "# oversized\n" + ("x" * (limits["max_script_bytes"] + 1))
    oversized_error = call("POST", f"/sessions/{session_id}/exec", {"script": oversized}, expected=413)
    assert_equal(
        oversized_error["detail"]["error"],
        "script_too_large",
        "oversized script error",
    )

    stdout_limit = limits["max_stdout_bytes"]
    result = call(
        "POST",
        f"/sessions/{session_id}/exec",
        {"script": f"python -c 'print(\"x\" * {stdout_limit + 1024})'"},
    )
    assert_equal(result["output_limit_exceeded"], True, "stdout limit flag")
    assert_equal(result["exit_code"], 137, "stdout limit exit_code")
    assert_true(len(result["stdout"].encode("utf-8")) <= stdout_limit, "stdout bounded")
    assert_equal(
        result["metadata"]["termination_reason"],
        "output_limit_exceeded",
        "stdout limit termination",
    )

    stderr_limit = limits["max_stderr_bytes"]
    result = call(
        "POST",
        f"/sessions/{session_id}/exec",
        {"script": f"python -c 'import sys; sys.stderr.write(\"e\" * {stderr_limit + 1024})'"},
    )
    assert_equal(result["output_limit_exceeded"], True, "stderr limit flag")
    assert_equal(result["exit_code"], 137, "stderr limit exit_code")
    assert_true(len(result["stderr"].encode("utf-8")) <= stderr_limit, "stderr bounded")

    empty_session = call("POST", "/sessions", {})
    empty_session_id = empty_session["session_id"]
    result = call("POST", f"/sessions/{empty_session_id}/exec", {"script": "echo empty"})
    for field in (
        "graph_invoke_id",
        "thread_id",
        "subgraph_name",
        "node_name",
        "caller_label",
        "request_id",
        "tool_round",
        "tool_call_id",
    ):
        assert_equal(result["metadata"][field], None, f"omitted correlation {field}")

finally:
    if empty_session is not None:
        call("DELETE", f"/sessions/{empty_session['session_id']}")
    if session is not None:
        call("DELETE", f"/sessions/{session['session_id']}")

print("sysbox_bash API smoke passed")
PY

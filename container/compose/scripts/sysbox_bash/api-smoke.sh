#!/usr/bin/env bash
set -euo pipefail

python - <<'SMOKE_PY'
import json
import os
import socket
import sys
import urllib.error
import urllib.request
from urllib.parse import urlparse


BASE_URL = os.environ.get("SBASH_BASE_URL")
if not BASE_URL:
    raise SystemExit("Missing required environment variable: SBASH_BASE_URL")
BASE_URL = BASE_URL.rstrip("/")
_parsed_base = urlparse(BASE_URL)
API_PORT = _parsed_base.port
if API_PORT is None:
    raise SystemExit(f"SBASH_BASE_URL must include an explicit port, got {BASE_URL!r}")
BIND_IP = socket.gethostbyname("sysbox_bash")

# Log actors: dev-smoke = test runner; sysbox-api = Sandbox HTTP API; session = inner exec container.
LABEL_COL = 26
INTENT_COL = 46


def _label(name):
    return f"[{name}]".ljust(LABEL_COL)


def _log_row(name, intent="", detail=""):
    line = f"{_label(name)}{intent}"
    if detail:
        intent_field = intent.ljust(INTENT_COL) if intent else " " * INTENT_COL
        line = f"{_label(name)}{intent_field}  {detail}"
    print(line, flush=True)


def log_actor(actor, intent, detail=""):
    _log_row(actor, intent, detail)


def log_route_out(sender, receiver, intent, method, path, expected):
    _log_row(
        f"{sender} → {receiver}",
        intent,
        f"{method} {path}  (expect HTTP {expected})",
    )


def log_route_in(sender, receiver, intent, method, path, status, *, unexpected=False):
    suffix = " (unexpected)" if unexpected else ""
    _log_row(
        f"{sender} → {receiver}",
        intent,
        f"{method} {path}  HTTP {status}{suffix}",
    )


def log_section(actor, message):
    _log_row(actor, f"--- {message} ---")


def log_assert(actor, message):
    _log_row(actor, f"ok: {message}")


log_actor(
    "dev-smoke",
    "config",
    f"api_base={BASE_URL}  bind_ip={BIND_IP}  port={API_PORT}",
)
log_actor(
    "dev-smoke",
    "note",
    "session exec image is python:3.11 (name says bash); network/limit smokes use python3 in session — see exec-image README TODO",
)


def call(method, path, payload=None, expected=200, *, intent=None):
    intent_text = intent or f"{method} {path}"
    log_route_out("dev-smoke", "sysbox-api", intent_text, method, path, expected)
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
        log_route_in(
            "sysbox-api",
            "dev-smoke",
            intent_text,
            method,
            path,
            status,
            unexpected=True,
        )
        raise AssertionError(f"{method} {path}: expected {expected}, got {status}: {body}")
    log_route_in("sysbox-api", "dev-smoke", intent_text, method, path, status)
    if not body:
        return {}
    return json.loads(body)


def assert_equal(actual, expected, label):
    if actual != expected:
        raise AssertionError(f"{label}: expected {expected!r}, got {actual!r}")


def assert_true(value, label):
    if not value:
        raise AssertionError(f"{label}: expected truthy value, got {value!r}")


def assert_session_api_blocked(session_id, script, target_desc):
    log_section("dev-smoke", f"network probe (primary): {target_desc}")
    log_actor("dev-smoke", f"ask sysbox-api to exec probe script in session {session_id}")
    log_actor("session", f"run: TCP connect to {target_desc} (must fail)")
    result = call(
        "POST",
        f"/sessions/{session_id}/exec",
        {"script": script},
        intent="inject primary network probe script",
    )
    assert_equal(result["exit_code"], 0, f"{target_desc} probe exit_code")
    assert_equal(result["stdout"].strip(), "OK_API_BLOCKED", f"{target_desc} probe stdout")
    log_actor("session", f"probe stdout={result['stdout'].strip()!r}")
    log_assert("dev-smoke", f"session cannot reach {target_desc}")


def assert_session_api_blocked_supplementary(session_id, script, target_desc):
    """Fail if the API is reachable; a pass may be bind-only, not iptables proof."""
    log_section("dev-smoke", f"network probe (supplementary): {target_desc}")
    log_actor("dev-smoke", f"ask sysbox-api to exec probe script in session {session_id}")
    log_actor("session", f"run: TCP connect to {target_desc} (must fail)")
    result = call(
        "POST",
        f"/sessions/{session_id}/exec",
        {"script": script},
        intent="inject supplementary network probe script",
    )
    assert_equal(result["exit_code"], 0, f"{target_desc} probe exit_code")
    stdout = result["stdout"].strip()
    if stdout != "OK_API_BLOCKED_SUPPLEMENTARY":
        raise AssertionError(f"{target_desc} probe stdout: expected 'OK_API_BLOCKED_SUPPLEMENTARY', got {stdout!r}")
    log_actor("session", f"probe stdout={stdout!r}")
    log_actor(
        "dev-smoke",
        "note: supplementary gateway probe — block may be bind-only, not proof of iptables",
    )
    log_assert("dev-smoke", f"session cannot reach {target_desc} (supplementary)")


def assert_outbound_optional(session_id):
    log_section("dev-smoke", "network probe (optional): session outbound internet")
    log_actor("dev-smoke", f"ask sysbox-api to exec outbound probe in session {session_id}")
    log_actor("session", "run: fetch https://example.com (outbound should succeed or soft-skip)")
    script = """python3 - <<'PY'
import urllib.request

try:
    urllib.request.urlopen("https://example.com", timeout=5)
    print("OK_OUTBOUND")
except OSError:
    print("SKIP_OUTBOUND")
PY
"""
    result = call(
        "POST",
        f"/sessions/{session_id}/exec",
        {"script": script},
        intent="inject outbound probe script",
    )
    assert_equal(result["exit_code"], 0, "outbound probe exit_code")
    stdout = result["stdout"].strip()
    if stdout not in ("OK_OUTBOUND", "SKIP_OUTBOUND"):
        raise AssertionError(f"outbound probe: unexpected stdout {stdout!r}")
    log_actor("session", f"probe stdout={stdout!r}")
    log_assert("dev-smoke", f"session outbound probe -> {stdout}")


GATEWAY_BLOCK_SCRIPT = f"""python3 - <<'PY'
import socket
import struct

def default_gateway():
    with open("/proc/net/route") as handle:
        next(handle)
        for line in handle:
            parts = line.strip().split()
            if parts[1] == "00000000":
                gateway = int(parts[2], 16)
                return socket.inet_ntoa(struct.pack("<L", gateway))
    raise SystemExit("no default gateway")

def reachable(host, port, timeout=2):
    try:
        socket.create_connection((host, port), timeout=timeout).close()
        return True
    except OSError:
        return False

# Supplementary only: default gateway is not the API bind IP. A block here may
# mean nothing listens on the gateway (bind layer), not iptables alone.
host = default_gateway()
if reachable(host, {API_PORT}):
    print("FAIL_API_REACHABLE")
    raise SystemExit(1)
print("OK_API_BLOCKED_SUPPLEMENTARY")
PY
"""

BIND_BLOCK_SCRIPT = f"""python3 - <<'PY'
import socket

def reachable(host, port, timeout=2):
    try:
        socket.create_connection((host, port), timeout=timeout).close()
        return True
    except OSError:
        return False

# Primary negative check: session must not reach the API on its backend_core bind IP.
if reachable({BIND_IP!r}, {API_PORT}):
    print("FAIL_API_REACHABLE")
    raise SystemExit(1)
print("OK_API_BLOCKED")
PY
"""


def assert_absent(mapping, key, label):
    if key in mapping:
        raise AssertionError(f"{label}: unexpected key {key!r} present")


health = call("GET", "/health", intent="readiness check")
limits = health["limits"]

log_section("dev-smoke", "contract negatives")
call("GET", "/sessions", expected=405, intent="list sessions must not exist")
call("POST", "/sessions", {"unknown": "field"}, expected=422, intent="reject unknown session fields")
log_assert("dev-smoke", "contract negatives")

session = None
empty_session = None
try:
    log_section("dev-smoke", "session lifecycle")
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
        intent="create session with correlation metadata",
    )
    session_id = session["session_id"]
    log_actor("sysbox-api", "created session", f"session_id={session_id}")
    log_assert("dev-smoke", "session created")

    log_section("dev-smoke", "basic exec")
    log_actor("session", "run: echo hello")
    result = call(
        "POST",
        f"/sessions/{session_id}/exec",
        {
            "script": "echo hello",
            "request_id": "smoke-request-1",
            "tool_round": 1,
            "tool_call_id": "smoke-tool-call",
        },
        intent="echo hello with correlation metadata",
    )
    assert_equal(result["stdout"], "hello\n", "echo stdout")
    assert_equal(result["stderr"], "", "echo stderr")
    assert_equal(result["exit_code"], 0, "echo exit_code")
    assert_equal(result["metadata"]["thread_id"], "smoke-thread", "session correlation")
    assert_equal(result["metadata"]["tool_call_id"], "smoke-tool-call", "run correlation")
    assert_equal(result["metadata"]["termination_reason"], "completed", "echo termination")
    assert_absent(result["metadata"], "script", "metadata does not store script body")
    log_assert("dev-smoke", "basic exec echo hello")

    assert_session_api_blocked(session_id, BIND_BLOCK_SCRIPT, f"sysbox-api bind IP {BIND_IP}:{API_PORT}")
    assert_session_api_blocked_supplementary(
        session_id,
        GATEWAY_BLOCK_SCRIPT,
        f"inner docker0 gateway tcp:{API_PORT}",
    )
    assert_outbound_optional(session_id)

    log_section("dev-smoke", "metadata shape (local check of last exec response)")
    for field in ("session_id", "run_id", "exit_code", "timed_out", "output_limit_exceeded", "elapsed_ms"):
        assert_absent(result["metadata"], field, f"HTTP metadata omits duplicate {field}")
    log_assert("dev-smoke", "metadata shape")

    log_section("dev-smoke", "session state persistence")
    log_actor("session", "run: echo state > state.txt")
    call(
        "POST",
        f"/sessions/{session_id}/exec",
        {"script": "echo state > state.txt"},
        intent="write state.txt",
    )
    log_actor("session", "run: cat state.txt")
    result = call(
        "POST",
        f"/sessions/{session_id}/exec",
        {"script": "cat state.txt"},
        intent="read state.txt",
    )
    assert_equal(result["stdout"], "state\n", "same-session state")
    log_assert("dev-smoke", "same-session state preserved")

    log_section("dev-smoke", "exit codes")
    log_actor("session", "run: exit 7")
    result = call(
        "POST",
        f"/sessions/{session_id}/exec",
        {"script": "exit 7"},
        intent="non-zero exit",
    )
    assert_equal(result["exit_code"], 7, "non-zero exit_code")
    log_assert("dev-smoke", "non-zero exit preserved")

    log_section("dev-smoke", "timeouts")
    log_actor("session", "run: sleep 2 with timeout_seconds=1")
    result = call(
        "POST",
        f"/sessions/{session_id}/exec",
        {"script": "sleep 2", "timeout_seconds": 1},
        intent="timeout below default",
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
        intent="reject timeout above default",
    )
    log_assert("dev-smoke", "timeout rules")

    log_section("dev-smoke", "script size limit")
    oversized = "# oversized\n" + ("x" * (limits["max_script_bytes"] + 1))
    oversized_error = call(
        "POST",
        f"/sessions/{session_id}/exec",
        {"script": oversized},
        expected=413,
        intent="reject oversized script",
    )
    assert_equal(
        oversized_error["detail"]["error"],
        "script_too_large",
        "oversized script error",
    )
    log_assert("dev-smoke", "script size limit")

    log_section("dev-smoke", "stdout size limit")
    stdout_limit = limits["max_stdout_bytes"]
    log_actor("session", f"run: print {stdout_limit + 1024} bytes to stdout")
    result = call(
        "POST",
        f"/sessions/{session_id}/exec",
        {"script": f"python -c 'print(\"x\" * {stdout_limit + 1024})'"},
        intent="exceed stdout cap",
    )
    assert_equal(result["output_limit_exceeded"], True, "stdout limit flag")
    assert_equal(result["exit_code"], 137, "stdout limit exit_code")
    assert_true(len(result["stdout"].encode("utf-8")) <= stdout_limit, "stdout bounded")
    assert_equal(
        result["metadata"]["termination_reason"],
        "output_limit_exceeded",
        "stdout limit termination",
    )
    log_assert("dev-smoke", "stdout size limit")

    log_section("dev-smoke", "stderr size limit")
    stderr_limit = limits["max_stderr_bytes"]
    log_actor("session", f"run: write {stderr_limit + 1024} bytes to stderr")
    result = call(
        "POST",
        f"/sessions/{session_id}/exec",
        {"script": f"python -c 'import sys; sys.stderr.write(\"e\" * {stderr_limit + 1024})'"},
        intent="exceed stderr cap",
    )
    assert_equal(result["output_limit_exceeded"], True, "stderr limit flag")
    assert_equal(result["exit_code"], 137, "stderr limit exit_code")
    assert_true(len(result["stderr"].encode("utf-8")) <= stderr_limit, "stderr bounded")
    log_assert("dev-smoke", "stderr size limit")

    log_section("dev-smoke", "correlation metadata")
    empty_session = call("POST", "/sessions", {}, intent="create session without correlation fields")
    empty_session_id = empty_session["session_id"]
    log_actor("session", "run: echo empty")
    result = call(
        "POST",
        f"/sessions/{empty_session_id}/exec",
        {"script": "echo empty"},
        intent="exec without correlation fields",
    )
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
    log_assert("dev-smoke", "omitted correlation fields stored as null")

finally:
    log_section("dev-smoke", "cleanup")
    if empty_session is not None:
        call(
            "DELETE",
            f"/sessions/{empty_session['session_id']}",
            intent="delete empty-correlation session",
        )
    if session is not None:
        call("DELETE", f"/sessions/{session['session_id']}", intent="delete main smoke session")
    log_assert("dev-smoke", "sessions deleted")

log_actor("dev-smoke", "all checks passed")
SMOKE_PY

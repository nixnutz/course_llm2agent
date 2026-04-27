#!/usr/bin/env python3
import json
import pathlib
import re
import subprocess
import sys
from typing import List, Set


ROOT = pathlib.Path(__file__).resolve().parents[2]
RAW_LOG = pathlib.Path("docs/auto-doc/adr/raw-log.md")
ADR_DIR = pathlib.Path("docs/auto-doc/adr")
REQUIRED_SENTENCE = "This decision is currently in effect in production/dev workflow."
RAW_LOG_LINE_RE = re.compile(r"^\d{4}-\d{2}-\d{2} \| [^|]+ \| [^|]+ \| [^|]+$")


def run_git(args: List[str]) -> str:
    try:
        proc = subprocess.run(
            ["git", *args],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
    except Exception:
        return ""
    if proc.returncode != 0:
        return ""
    return proc.stdout


def changed_files() -> Set[pathlib.Path]:
    files: Set[pathlib.Path] = set()
    for args in (["diff", "--name-only"], ["diff", "--cached", "--name-only"]):
        out = run_git(args)
        for line in out.splitlines():
            line = line.strip()
            if line:
                files.add(pathlib.Path(line))
    return files


def combined_diff(path: pathlib.Path) -> str:
    return (
        run_git(["diff", "--no-color", "--unified=0", "--", str(path)])
        + "\n"
        + run_git(["diff", "--cached", "--no-color", "--unified=0", "--", str(path)])
    )


def raw_log_issues(diff_text: str) -> List[str]:
    issues: List[str] = []
    for line in diff_text.splitlines():
        if line.startswith("---") or line.startswith("+++"):
            continue
        if line.startswith("-"):
            issues.append("raw-log append-only violation (existing lines modified/deleted).")
            break

    for line in diff_text.splitlines():
        if not line.startswith("+") or line.startswith("+++"):
            continue
        content = line[1:].strip()
        if not content:
            continue
        if content.startswith("#") or content.startswith("```"):
            continue
        if " | " not in content:
            continue
        if not RAW_LOG_LINE_RE.match(content):
            issues.append(
                f"raw-log format warning: '{content}' does not match "
                "YYYY-MM-DD | area | decision note | evidence."
            )
            break
    return issues


def adr_file_issues(path: pathlib.Path) -> List[str]:
    issues: List[str] = []
    abs_path = ROOT / path
    if not abs_path.exists():
        return issues
    text = abs_path.read_text(encoding="utf-8")
    if REQUIRED_SENTENCE not in text:
        issues.append(f"{path}: missing required sentence.")
    if re.search(r"^- Status:\s+", text, flags=re.MULTILINE) is None:
        issues.append(f"{path}: missing '- Status: ...'.")
    if re.search(r"^- OverheadSeconds:\s+", text, flags=re.MULTILINE) is None:
        issues.append(f"{path}: missing '- OverheadSeconds: ...'.")
    return issues


def main() -> int:
    _ = sys.stdin.read()

    files = changed_files()
    issues: List[str] = []

    if RAW_LOG in files:
        issues.extend(raw_log_issues(combined_diff(RAW_LOG)))

    for path in sorted(files):
        if path == RAW_LOG:
            continue
        if path.parent == ADR_DIR and path.suffix == ".md":
            issues.extend(adr_file_issues(path))

    if not issues:
        print("{}")
        return 0

    additional = "[ADR Hook Guardrail | warn-only]\n- " + "\n- ".join(issues)
    print(json.dumps({"additional_context": additional}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

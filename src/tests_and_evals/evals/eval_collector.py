"""Per-process store for eval case outcomes (one list per pytest worker).

Reset at session start and merged on the controller when xdist is active; see
``tests_and_evals/evals/conftest.py``. Eval tests record outcomes; MUST is asserted
in tests, SHOULD is summarized per suite in ``pytest_sessionfinish``.

``EvalCaseResult`` is node-neutral. Each record is attributable to one ``suite``
(the eval node, e.g. ``pii_email`` / ``todo_extract``) and carries the failed
check names plus suite-specific context in ``details`` / ``metrics``. See
``docs/auto-doc/adr/0010-eval-must-should-pytest-hooks.md``.
"""

from collections.abc import Iterable
from dataclasses import dataclass, field


def _to_sorted_list(value: Iterable[str] | None) -> list[str]:
    """Normalize sets/iterables of strings to a deterministic sorted list."""
    if not value:
        return []
    return sorted(value)


@dataclass
class EvalCaseResult:
    suite: str
    case_id: str
    level: str  # MUST, SHOULD, MAY
    passed: bool = True
    failed_checks: list[str] = field(default_factory=list)
    details: dict[str, object] = field(default_factory=dict)
    metrics: dict[str, float] = field(default_factory=dict)


@dataclass
class EvalCollector:
    results: list[EvalCaseResult] = field(default_factory=list)

    def record(
        self,
        *,
        suite: str,
        case_id: str,
        level: str,
        failed_checks: Iterable[str] | None = None,
        details: dict[str, object] | None = None,
        metrics: dict[str, float] | None = None,
        passed: bool | None = None,
    ) -> None:
        checks = _to_sorted_list(failed_checks)
        normalized_details = {k: _normalize_detail(v) for k, v in (details or {}).items()}
        self.results.append(
            EvalCaseResult(
                suite=suite,
                case_id=case_id,
                level=level,
                passed=(not checks) if passed is None else passed,
                failed_checks=checks,
                details=normalized_details,
                metrics=dict(metrics or {}),
            )
        )


def _normalize_detail(value: object) -> object:
    """Normalize set values to sorted lists; leave other values untouched."""
    if isinstance(value, (set, frozenset)):
        return sorted(value)
    return value


_collector: EvalCollector | None = None


def get_eval_collector() -> EvalCollector:
    global _collector
    if _collector is None:
        _collector = EvalCollector()
    return _collector


def reset_eval_collector() -> None:
    global _collector
    _collector = None


def results_to_dicts(results: list[EvalCaseResult]) -> list[dict]:
    """Serialize for xdist ``workeroutput`` (plain dicts only)."""
    return [
        {
            "suite": r.suite,
            "case_id": r.case_id,
            "level": r.level,
            "passed": r.passed,
            "failed_checks": r.failed_checks,
            "details": r.details,
            "metrics": r.metrics,
        }
        for r in results
    ]


def results_from_dicts(items: list[dict]) -> list[EvalCaseResult]:
    return [
        EvalCaseResult(
            suite=d["suite"],
            case_id=d["case_id"],
            level=d["level"],
            passed=bool(d.get("passed", True)),
            failed_checks=list(d.get("failed_checks") or []),
            details=dict(d.get("details") or {}),
            metrics=dict(d.get("metrics") or {}),
        )
        for d in items
    ]

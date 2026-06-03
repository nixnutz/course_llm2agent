"""Per-process store for eval case outcomes (one list per pytest worker).

Reset at session start and merged on the controller when xdist is active; see
``tests_and_evals/evals/conftest.py``. Eval tests record outcomes; MUST is asserted
in tests, SHOULD is summarized in ``pytest_sessionfinish``.

``EvalCaseResult`` fields are PII-email-shaped for now; generalize when a second
eval node exists (see ``docs/auto-doc/adr/0010-eval-must-should-pytest-hooks.md``).
"""

from dataclasses import dataclass, field


@dataclass
class EvalCaseResult:
    case_id: str
    level: str  # MUST, SHOULD, MAY
    missing_emails: list[str] = field(default_factory=list)
    leaked_spans: list[str] = field(default_factory=list)
    passed: bool = True


@dataclass
class EvalCollector:
    results: list[EvalCaseResult] = field(default_factory=list)

    def record(
        self,
        *,
        case_id: str,
        level: str,
        missing_emails: list[str] | None = None,
        leaked_spans: list[str] | None = None,
    ) -> None:
        missing = sorted(missing_emails or [])
        leaked = list(leaked_spans or [])
        self.results.append(
            EvalCaseResult(
                case_id=case_id,
                level=level,
                missing_emails=missing,
                leaked_spans=leaked,
                passed=not missing and not leaked,
            )
        )


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
            "case_id": r.case_id,
            "level": r.level,
            "missing_emails": r.missing_emails,
            "leaked_spans": r.leaked_spans,
            "passed": r.passed,
        }
        for r in results
    ]


def results_from_dicts(items: list[dict]) -> list[EvalCaseResult]:
    return [
        EvalCaseResult(
            case_id=d["case_id"],
            level=d["level"],
            missing_emails=list(d.get("missing_emails") or []),
            leaked_spans=list(d.get("leaked_spans") or []),
            passed=bool(d.get("passed", True)),
        )
        for d in items
    ]

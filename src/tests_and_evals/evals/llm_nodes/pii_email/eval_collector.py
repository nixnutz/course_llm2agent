"""In-memory collector for eval case results (session-wide)."""

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
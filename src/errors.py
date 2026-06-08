"""Shared pipeline exceptions for guard-tier failures (ADR 0012).

``PipelinePreconditionError`` and ``PipelineValidationError`` subclass ``ValueError``
so existing ``except ValueError`` handlers still catch missing-input and bad-deliverable
guards.

``PolicyViolationError`` subclasses ``Exception`` only — loop/policy exhaustion is a
separate guard class. A broad ``except ValueError`` does **not** catch it; handle
``PolicyViolationError`` explicitly (or ``except Exception`` at graph boundaries).
"""


class PipelinePreconditionError(ValueError):
    """Required input or parent state is missing before a step executes."""


class PipelineValidationError(ValueError):
    """A produced deliverable fails deterministic format/schema/value checks."""


class PolicyViolationError(Exception):
    """Execution policy violated (for example exhausted tool rounds/errors with pending work).

    Not a ``ValueError`` subclass — see module docstring for catch semantics.
    """

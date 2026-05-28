"""Project logging helpers with a small, notebook-friendly API.

This module provides one central logging setup for code under `src/`:

- Console output defaults to project logs only (namespace-based filter).
- Log lines use a compact format: level + `src/`-relative file + line.
- `ProjectLogger.setLevel(...)` changes runtime level for all project loggers.
- `ProjectLogger.displayAll(...)` can temporarily include external library logs.

Typical usage in regular Python modules:

    logger = get_logger(__name__, __file__)
    logger.debug("Something happened")

Typical usage in notebooks (no reliable `__file__` there):

    logger = get_logger(__name__, "assorted/session4/langgraph.ipynb")
"""

import logging
import uuid
from pathlib import Path

_CONFIGURED: bool = False
_DISPLAY_ALL: bool = False
_PROJECT_PREFIX: str = "course_llm2agent"
_SRC_ROOT: Path = Path(__file__).resolve().parent
_RUN_ID: str = str(uuid.uuid4())


class _SelfOnlyFilter(logging.Filter):
    """Optionally allow only project loggers on console output."""

    def filter(self, record: logging.LogRecord) -> bool:
        if _DISPLAY_ALL:
            return True
        return record.name.startswith(_PROJECT_PREFIX)


class _DefaultRunIdFilter(logging.Filter):
    """Keep hook point for future per-run metadata."""

    def filter(self, record: logging.LogRecord) -> bool:
        # Keep internal run context available on records without exposing it by default.
        if not hasattr(record, "run_id"):
            record.run_id = _RUN_ID
        return True


class _RelativePathFilter(logging.Filter):
    """Add src-relative path for concise console output."""

    def filter(self, record: logging.LogRecord) -> bool:
        source_file = getattr(record, "source_file", record.pathname)
        path = Path(source_file).resolve()
        try:
            record.relpath = str(path.relative_to(_SRC_ROOT))
        except ValueError:
            record.relpath = str(source_file)
        return True


def configure_logging(level: int = logging.INFO) -> None:
    """Configure root logging once; safe to call multiple times."""
    global _CONFIGURED
    if _CONFIGURED:
        return

    root = logging.getLogger()
    root.setLevel(level)

    if not root.handlers:
        console = logging.StreamHandler()
        # To display the run id, include `%(run_id)s` in this formatter string.
        console.setFormatter(
            logging.Formatter("[%(levelname)s] [%(relpath)s:%(lineno)d] %(message)s")
        )
        console.addFilter(_DefaultRunIdFilter())
        console.addFilter(_RelativePathFilter())
        console.addFilter(_SelfOnlyFilter())
        root.addHandler(console)
    else:
        for handler in root.handlers:
            handler.addFilter(_DefaultRunIdFilter())
            handler.addFilter(_RelativePathFilter())
            handler.addFilter(_SelfOnlyFilter())

    _CONFIGURED = True


def _set_display_all(value: bool) -> None:
    """Toggle console filter between project-only and all logs."""
    global _DISPLAY_ALL
    _DISPLAY_ALL = value


def _normalize_logger_name(name: str) -> str:
    """Map logger names into the project namespace for inheritance/filtering."""
    if name.startswith(_PROJECT_PREFIX):
        return name
    return f"{_PROJECT_PREFIX}.{name}"


def _set_project_level(level: int) -> None:
    """Set effective level for all project loggers via the namespace parent.

    All project loggers are normalized under `_PROJECT_PREFIX`, so changing this
    parent logger level affects nested loggers (e.g. `src.reducer.*`) at runtime.
    """
    project_logger = logging.getLogger(_PROJECT_PREFIX)
    project_logger.setLevel(level)


def _normalize_source_file(file: str) -> str:
    """Return a stable `src/`-relative file identifier when possible.

    Accepted input forms:
    - absolute paths that include `/src/`
    - paths already relative to `src/`
    - arbitrary fallback strings (returned unchanged if no mapping is possible)
    """
    path = Path(file).resolve()
    try:
        return str(path.relative_to(_SRC_ROOT))
    except ValueError:
        marker = "/src/"
        as_posix = path.as_posix()
        if marker in as_posix:
            return as_posix.split(marker, 1)[1]
        return str(file)


class ProjectLogger:
    """Small logger wrapper used by `get_logger(...)`.

    The wrapper keeps the common logging methods (`debug`, `info`, ...) by
    delegating unknown attributes to an internal `logging.LoggerAdapter`.
    It adds two convenience controls aligned with this project:

    - `setLevel(level)`: set runtime log level for all project loggers.
    - `displayAll(value)`: toggle project-only console output vs all output.
    """

    def __init__(self, name: str, file: str, level: int | None = None):
        configure_logging(level=logging.INFO)
        if level is not None:
            _set_project_level(level)

        self._base_logger = logging.getLogger(_normalize_logger_name(name))
        # Keep children inheriting from the project namespace runtime level.
        self._base_logger.setLevel(logging.NOTSET)
        self._adapter = logging.LoggerAdapter(
            self._base_logger, extra={"source_file": _normalize_source_file(file)}
        )

    def setLevel(self, level: int) -> None:
        """Set runtime level for all project loggers.

        This is intentionally project-wide (namespace parent level), not local
        to just this single logger instance.
        """
        _set_project_level(level)

    def displayAll(self, value: bool = True) -> None:
        """Enable/disable displaying non-project logs on console.

        - `False` (default behavior): show only project logs.
        - `True`: include external library logs as well.
        """
        _set_display_all(value)

    def __getattr__(self, item):
        return getattr(self._adapter, item)


def get_logger(name: str, file: str, level: int | None = None) -> ProjectLogger:
    """Create and return a project-aware logger wrapper.

    Args:
        name: Logger name, typically `__name__`.
        file: Source file path for readable output.
            - Use `__file__` in normal Python modules.
            - Use an explicit `src/`-relative string in notebooks.
        level: Optional initial project log level to apply immediately.

    Returns:
        `ProjectLogger` wrapper with standard logging methods plus
        `setLevel(...)` and `displayAll(...)`.
    """
    return ProjectLogger(name=name, file=file, level=level)

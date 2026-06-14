"""Structured logging setup (TDD §17).

Emits JSON logs keyed by ``doc_id``/``stage``/``duration_ms`` for performance
tracing and debugging. The production stack uses ``structlog``; when it is not
installed (minimal/air-gapped image) we fall back to a stdlib ``logging``
configuration that still emits one JSON object per line, so log shape is stable
across environments.

Level, file path and format come from ``.env`` (never hardcoded).
"""

from __future__ import annotations

import json
import logging
import sys
import time
from contextlib import contextmanager
from typing import Any, Iterator

from app.config import get_settings

_CONFIGURED = False

# Attribute names the stdlib ``LogRecord`` reserves; passing any of these via
# ``logger.info(..., extra={...})`` raises ``KeyError`` at record creation. We
# rename collisions (``filename`` -> ``filename_``) so callers can use natural
# field names without knowing the stdlib's reserved set.
_RESERVED_LOGRECORD_KEYS = frozenset(
    {
        "name", "msg", "args", "levelname", "levelno", "pathname", "filename",
        "module", "exc_info", "exc_text", "stack_info", "lineno", "funcName",
        "created", "msecs", "relativeCreated", "thread", "threadName",
        "processName", "process", "message", "asctime", "taskName",
    }
)


class _SafeLogger(logging.Logger):
    """Logger that namespaces reserved keys in ``extra`` instead of raising.

    Production uses ``structlog`` (which has no such restriction); this keeps the
    stdlib fallback path from crashing when a natural field name such as
    ``filename`` collides with a built-in ``LogRecord`` attribute.
    """

    def makeRecord(self, name, level, fn, lno, msg, args, exc_info,  # noqa: D401
                   func=None, extra=None, sinfo=None):
        if extra:
            extra = {
                (f"{k}_" if k in _RESERVED_LOGRECORD_KEYS else k): v
                for k, v in extra.items()
            }
        return super().makeRecord(
            name, level, fn, lno, msg, args, exc_info, func, extra, sinfo
        )


class _JsonFormatter(logging.Formatter):
    """Minimal JSON line formatter for the stdlib fallback path."""

    def format(self, record: logging.LogRecord) -> str:  # noqa: A003
        payload: dict[str, Any] = {
            "ts": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "event": record.getMessage(),
        }
        # Attach structured extras passed via ``logger.info(msg, extra={...})``.
        for key, val in getattr(record, "__dict__", {}).items():
            if key in ("args", "msg", "levelname", "levelno", "name", "exc_info",
                       "exc_text", "stack_info", "created", "msecs", "relativeCreated",
                       "pathname", "filename", "module", "funcName", "lineno",
                       "processName", "process", "threadName", "thread", "taskName"):
                continue
            payload[key] = val
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


def configure_logging() -> None:
    """Configure process-wide logging from settings. Idempotent.

    Honours ``LOG_LEVEL``, ``LOG_FILE`` and ``LOG_FORMAT`` from the environment.
    """
    global _CONFIGURED
    if _CONFIGURED:
        return
    settings = get_settings()
    level = getattr(logging, settings.log_level.upper(), logging.INFO)

    # Ensure every logger in our tree sanitises reserved ``extra`` keys. Set the
    # class before our loggers are instantiated, and re-class any that already
    # exist (e.g. created by a prior import in the same process).
    logging.setLoggerClass(_SafeLogger)
    for lname, lobj in list(logging.Logger.manager.loggerDict.items()):
        if lname.startswith("contract_verify") and isinstance(lobj, logging.Logger):
            lobj.__class__ = _SafeLogger

    handlers: list[logging.Handler] = []
    stream = logging.StreamHandler(sys.stderr)
    handlers.append(stream)
    if settings.log_file:
        try:
            handlers.append(logging.FileHandler(settings.log_file))
        except OSError:
            # Directory may not exist on a fresh checkout; stderr still works.
            pass

    formatter: logging.Formatter
    if settings.log_format == "json":
        formatter = _JsonFormatter()
    else:
        formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s")
    for h in handlers:
        h.setFormatter(formatter)

    root = logging.getLogger("contract_verify")
    root.handlers = handlers
    root.setLevel(level)
    root.propagate = False
    _CONFIGURED = True


def get_logger(name: str = "contract_verify") -> logging.Logger:
    """Return a configured logger, configuring logging on first use.

    Args:
        name: Logger name; conventionally ``contract_verify.<module>``.
    """
    configure_logging()
    if not name.startswith("contract_verify"):
        name = f"contract_verify.{name}"
    return logging.getLogger(name)


@contextmanager
def log_stage(stage: str, doc_id: str | None = None, **fields: Any) -> Iterator[None]:
    """Context manager that logs a pipeline stage's entry and exit.

    Logs ``stage_start`` on entry and ``stage_end`` (with ``duration_ms``) on
    exit, mirroring the per-stage tracing described in TDD §17.

    Args:
        stage: Pipeline stage name (``ingest``/``extract``/``match`` ...).
        doc_id: Optional document id to correlate log lines.
        **fields: Extra structured fields to attach to both log lines.
    """
    log = get_logger("pipeline")
    extra = {"stage": stage, "doc_id": doc_id, **fields}
    log.info("stage_start", extra=extra)
    start = time.perf_counter()
    try:
        yield
    finally:
        duration_ms = round((time.perf_counter() - start) * 1000, 2)
        log.info("stage_end", extra={**extra, "duration_ms": duration_ms})

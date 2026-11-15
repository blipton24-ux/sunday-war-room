"""Structured JSON logging (structlog). Every line carries request_id / job_id when bound."""

import logging
import re
import sys
from typing import Any

import structlog

REDACTED = "[redacted]"
# ESPN's login cookies (ADR-052): never allowed in a log line, whatever put them there.
_SECRET_KEYS = frozenset({"espn_s2", "swid", "cookie", "cookies", "set-cookie", "authorization"})
_SECRET_TEXT = re.compile(r"(?i)\b(espn_s2|swid)\s*[=:]\s*[^\s;,&\"']+")


def _scrub(value: Any) -> Any:
    if isinstance(value, str):
        return _SECRET_TEXT.sub(lambda m: f"{m.group(1)}={REDACTED}", value)
    if isinstance(value, dict):
        return {
            k: REDACTED if str(k).lower() in _SECRET_KEYS else _scrub(v) for k, v in value.items()
        }
    if isinstance(value, list | tuple):
        return type(value)(_scrub(v) for v in value)
    return value


def scrub_secrets(
    _logger: Any, _method: str, event_dict: structlog.typing.EventDict
) -> structlog.typing.EventDict:
    """Blank credential values in every log line, by field name and by `espn_s2=...` text."""
    return {k: REDACTED if k.lower() in _SECRET_KEYS else _scrub(v) for k, v in event_dict.items()}


def configure_logging(level: str = "INFO", *, json: bool = True) -> None:
    logging.basicConfig(format="%(message)s", stream=sys.stdout, level=level.upper())
    renderer: structlog.typing.Processor = (
        structlog.processors.JSONRenderer() if json else structlog.dev.ConsoleRenderer()
    )
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            scrub_secrets,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.processors.format_exc_info,
            renderer,
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.getLevelName(level.upper())),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    return structlog.get_logger(name)  # type: ignore[no-any-return]

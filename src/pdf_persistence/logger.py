import json
import logging
import os
import sys
import time
from typing import Any


class JsonFormatter(logging.Formatter):
    """ADR-0007 compliant JSON log formatter."""

    def __init__(self, service: str = "pdf-persistence") -> None:
        super().__init__()
        self.service = service

    def format(self, record: logging.LogRecord) -> str:
        # RFC 3339 UTC timestamp with milliseconds
        t = time.gmtime(record.created)
        timestamp = time.strftime("%Y-%m-%dT%H:%M:%S", t) + f".{int(record.msecs):03d}Z"

        level = "WARN" if record.levelname in ("WARNING", "WARN") else record.levelname

        entry: dict[str, Any] = {
            "time": timestamp,
            "level": level,
            "service": self.service,
            "msg": record.getMessage(),
        }

        # Extra structured fields passed via extra={"fields": {...}}
        fields = getattr(record, "fields", None)
        if isinstance(fields, dict):
            entry.update(fields)

        if record.exc_info:
            entry["error"] = self.formatException(record.exc_info)

        return json.dumps(entry, ensure_ascii=False)


def setup_logging(
    raw_level: str | None = None, service: str = "pdf-persistence"
) -> str:
    """Configure root logger with ADR-0007 JsonFormatter and normalized log level."""
    if raw_level is None:
        raw_level = os.getenv("LOG_LEVEL", "INFO")

    normalized = raw_level.strip().upper()
    valid_levels = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARN": logging.WARNING,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
    }

    invalid_level = False
    if normalized not in valid_levels:
        invalid_level = True
        effective_level = logging.INFO
        effective_name = "INFO"
    else:
        effective_level = valid_levels[normalized]
        effective_name = "WARN" if normalized in ("WARN", "WARNING") else normalized

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter(service=service))

    root_logger = logging.getLogger()
    root_logger.handlers = [handler]
    root_logger.setLevel(effective_level)

    # Re-route uvicorn loggers to use the same JSON formatter and level
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        u_log = logging.getLogger(name)
        u_log.handlers = [handler]
        u_log.propagate = False
        u_log.setLevel(effective_level)

    if invalid_level:
        logger = logging.getLogger(__name__)
        logger.warning(
            "invalid log level, fallback to info",
            extra={"fields": {"invalid_level": raw_level, "default": "info"}},
        )

    return effective_name

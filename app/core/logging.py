"""
Central logging configuration.

- production  → JSON lines (stdout) — machine-parseable by Datadog / CloudWatch / Loki
- development → colored, human-readable console output

Every log record automatically carries:
  - timestamp (ISO-8601)
  - level
  - logger name  (module path)
  - message
  - request_id  (injected by RequestIDMiddleware, empty string when outside a request)
  - extra fields passed at call-site via `extra={}`
"""

import logging
import sys
from contextvars import ContextVar

import orjson

# ---------------------------------------------------------------------------
# Request-ID context  (set once per request by the middleware in main.py)
# ---------------------------------------------------------------------------
request_id_ctx: ContextVar[str] = ContextVar("request_id", default="-")


# ---------------------------------------------------------------------------
# Formatters
# ---------------------------------------------------------------------------

class _JSONFormatter(logging.Formatter):
    """Emit one JSON object per log line — ideal for log aggregation pipelines."""

    def format(self, record: logging.LogRecord) -> str:
        log: dict = {
            "ts": self.formatTime(record, "%Y-%m-%dT%H:%M:%S.%f"),
            "level": record.levelname,
            "logger": record.name,
            "request_id": request_id_ctx.get("-"),
            "msg": record.getMessage(),
        }
        if record.exc_info:
            log["exc"] = self.formatException(record.exc_info)
        # Merge any extra= fields the caller passed
        for key, val in record.__dict__.items():
            if key not in {
                "name", "msg", "args", "levelname", "levelno", "pathname",
                "filename", "module", "exc_info", "exc_text", "stack_info",
                "lineno", "funcName", "created", "msecs", "relativeCreated",
                "thread", "threadName", "processName", "process", "message",
                "taskName",
            }:
                log[key] = val
        return orjson.dumps(log).decode()


class _DevFormatter(logging.Formatter):
    """Colored, human-readable output for local development."""

    _COLORS = {
        "DEBUG":    "\033[36m",   # cyan
        "INFO":     "\033[32m",   # green
        "WARNING":  "\033[33m",   # yellow
        "ERROR":    "\033[31m",   # red
        "CRITICAL": "\033[35m",   # magenta
    }
    _RESET = "\033[0m"
    _DIM   = "\033[2m"

    def format(self, record: logging.LogRecord) -> str:
        color  = self._COLORS.get(record.levelname, "")
        rid    = request_id_ctx.get("-")
        rid_part = f" {self._DIM}[{rid}]{self._RESET}" if rid != "-" else ""
        base   = (
            f"{self._DIM}{self.formatTime(record, '%H:%M:%S')}{self._RESET} "
            f"{color}{record.levelname:<8}{self._RESET}"
            f"{rid_part} "
            f"{self._DIM}{record.name}{self._RESET} "
            f"{record.getMessage()}"
        )
        if record.exc_info:
            base += "\n" + self.formatException(record.exc_info)
        return base


# ---------------------------------------------------------------------------
# Public setup function — call once at application startup
# ---------------------------------------------------------------------------

def setup_logging(level: str = "INFO", fmt: str = "dev") -> None:
    """
    Configure the root logger.

    Args:
        level: e.g. "DEBUG", "INFO", "WARNING"
        fmt:   "json"  → _JSONFormatter  (production)
               "dev"   → _DevFormatter   (development)
    """
    formatter = _JSONFormatter() if fmt == "json" else _DevFormatter()

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    # Silence noisy third-party loggers
    for noisy in ("uvicorn.access", "sqlalchemy.engine", "httpx", "httpcore"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        handlers=[handler],
        force=True,   # override any previously installed handlers
    )

    logging.getLogger(__name__).info(
        "logging.configured level=%s fmt=%s", level, fmt
    )

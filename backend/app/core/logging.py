"""
growders.core.logging
──────────────────────
Structured logging setup.
- Development: human-readable coloured output via standard logging
- Production: JSON lines (compatible with Railway / Render log drains,
  Datadog, Grafana Loki, etc.)

Import get_logger() everywhere instead of logging.getLogger() directly
so the format is always consistent.
"""

import logging
import sys
from typing import Any

from app.core.config import get_settings

settings = get_settings()


def _configure_logging() -> None:
    level = getattr(logging, settings.log_level, logging.INFO)

    if settings.is_production:
        # JSON formatter for log aggregation services
        try:
            import json_log_formatter  # pip install json-log-formatter

            formatter = json_log_formatter.JSONFormatter()
        except ImportError:
            formatter = logging.Formatter(
                '{"time":"%(asctime)s","level":"%(levelname)s",'
                '"name":"%(name)s","message":"%(message)s"}'
            )
    else:
        formatter = logging.Formatter(
            "%(asctime)s [%(levelname)-8s] %(name)s: %(message)s",
            datefmt="%H:%M:%S",
        )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root = logging.getLogger()
    root.setLevel(level)
    root.handlers.clear()
    root.addHandler(handler)

    # Quiet noisy third-party loggers
    for noisy in ("uvicorn.access", "sqlalchemy.engine", "httpx"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


_configure_logging()


def get_logger(name: str) -> logging.Logger:
    """Return a named logger. Usage: logger = get_logger(__name__)"""
    return logging.getLogger(name)

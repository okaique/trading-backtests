import logging
import sys

import structlog


def setup_logging(level: int = logging.INFO) -> None:
    """Configure structlog/standard logging to emit JSON records."""
    logging.basicConfig(level=level, format="%(message)s", stream=sys.stdout)

    processors = [
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.JSONRenderer(),
    ]

    structlog.configure(
        processors=processors,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )


__all__ = ["setup_logging"]
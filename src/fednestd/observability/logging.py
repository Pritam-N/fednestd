from __future__ import annotations

import logging
from typing import Optional

# Lowercase so type checkers don't treat it as a constant.
_logging_configured: bool = False


def _configure_root_logger() -> None:
    """
    Configure the root logger once.

    Safe to call multiple times; subsequent calls are no-ops.
    """
    global _logging_configured
    if _logging_configured:
        return

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
    _logging_configured = True


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """
    Return a logger with basic configuration applied.

    Usage:
        from fednestd.observability.logging import get_logger
        logger = get_logger(__name__)
        logger.info("hello")
    """
    _configure_root_logger()
    return logging.getLogger(name if name is not None else "fednestd")
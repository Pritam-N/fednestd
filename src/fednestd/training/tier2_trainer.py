# src/fednestd/training/tier2_trainer.py
from __future__ import annotations

from typing import Dict, Any

try:
    from ..observability.logging import get_logger
    logger = get_logger(__name__)
except Exception:
    import logging
    logger = logging.getLogger(__name__)


def run_edge_round(config: Dict[str, Any]) -> None:
    """
    Single local round of adapters-only training on an edge node.

    Typically this will be called from federation.client.run_edge_client().
    """
    logger.info("Starting edge adapters training round with config: %s", config)

    # TODO: implement actual adapters training logic.
    pass
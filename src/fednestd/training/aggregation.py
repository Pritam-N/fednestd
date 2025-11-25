# src/fednestd/training/aggregation.py
from __future__ import annotations

from typing import Dict, Any

try:
    from ..observability.logging import get_logger
    logger = get_logger(__name__)
except Exception:
    import logging
    logger = logging.getLogger(__name__)


def run_expert_aggregation(config: Dict[str, Any]) -> None:
    """
    Aggregate expert deltas from Tier 1 and Tier 2/3 via Kafka/FedServer.

    CLI will call this. Inside here you'll:
      - Connect to Kafka (messaging/kafka_client.py).
      - Consume updates.experts.local.
      - Aggregate ΔW_experts.
      - Write updated experts back to checkpoint / registry.
    """
    logger.info("Starting expert aggregation with config: %s", config)

    # TODO: implement: create Kafka consumer, read messages, aggregate weights,
    # persist new model version, etc.
    pass
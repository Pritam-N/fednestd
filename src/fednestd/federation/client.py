# src/fednestd/federation/client.py
from __future__ import annotations

from typing import Dict, Any

try:
    from ..observability.logging import get_logger
    logger = get_logger(__name__)
except Exception:
    import logging
    logger = logging.getLogger(__name__)


def run_edge_client(config: Dict[str, Any]) -> None:
    """
    Main entrypoint for Tier 2/3 edge client.

    Responsibilities:
      - Connect to FedServer / Kafka.
      - Pull model snapshot / config.
      - Trigger local training via training.tier2_trainer.
      - Pass updates through governance.local_sidecar.
      - Publish ΔW_experts_local.
    """
    logger.info("Starting edge client with config: %s", config)

    # TODO: implement the main client loop:
    # - subscribe to control.federation_rounds
    # - on RoundStart: download model, call training.tier2_trainer.run_edge_round(config)
    # - send deltas via messaging.kafka_client
    pass
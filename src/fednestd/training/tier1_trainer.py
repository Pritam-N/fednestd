# src/fednestd/training/tier1_trainer.py
from __future__ import annotations

from typing import Dict, Any

from ..observability.logging import get_logger  # if you have one; else use logging

try:
    logger = get_logger(__name__)  # your own helper
except Exception:
    import logging
    logger = logging.getLogger(__name__)


def run_core_update(config: Dict[str, Any]) -> None:
    """
    Tier 1 core + experts training entrypoint.

    This is what the CLI will call. Inside here you'll:
      - Build the MoE model (moe_model.py).
      - Wrap with DeepSpeed.
      - Load data according to config.
      - Train core + experts.
      - Log to MLflow, update DataHub, etc.
    """
    logger.info("Starting Tier 1 core update with config: %s", config)

    # TODO: implement actual training logic
    # example structure:
    # from ..model.moe_model import build_moe_model
    # model = build_moe_model(config["model"])
    #
    # from ..model.checkpointing import load_checkpoint_if_any
    # model = load_checkpoint_if_any(model, config["checkpoint"])
    #
    # from ..training.data_loader import make_dataloader  # if you create one
    # dataloader = make_dataloader(config["data"])
    #
    # ... set up DeepSpeed, train, checkpoint, log to MLflow, etc.
    pass
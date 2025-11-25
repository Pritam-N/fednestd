# src/fednestd/networking/haprozy_config.py
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from ..observability.logging import get_logger

logger = get_logger(__name__)


def render_haproxy_config(profile: Dict[str, Any]) -> str:
    """
    Render HAProxy config from infra/config_templates/haproxy.cfg.j2
    using values from the given deployment profile.

    Expected profile structure (example):

    {
      "haproxy": {
        "fedserver_host": "fedserver.prod.local",
        "fedserver_port": 443,
        "kafka_broker": "kafka.prod.local:9092"
      }
    }
    """

    template_path = (
        Path(__file__)
        .resolve()
        .parent.parent          # -> src/fednestd
        / "infra"
        / "config_templates"
        / "haproxy.cfg.j2"
    )

    if not template_path.exists():
        raise FileNotFoundError(f"HAProxy template not found at {template_path}")

    template_text = template_path.read_text()

    hap = profile.get("haproxy", {})

    fedserver_host = hap.get("fedserver_host", "127.0.0.1")
    fedserver_port = hap.get("fedserver_port", 8080)
    kafka_broker  = hap.get("kafka_broker", "127.0.0.1:9092")

    logger.info(
        "Rendering HAProxy config with host=%s port=%s kafka=%s",
        fedserver_host,
        fedserver_port,
        kafka_broker,
    )

    # Template must use {FEDSERVER_HOST}, {FEDSERVER_PORT}, {KAFKA_BROKER}
    rendered = template_text.format(
        FEDSERVER_HOST=fedserver_host,
        FEDSERVER_PORT=fedserver_port,
        KAFKA_BROKER=kafka_broker,
    )

    return rendered
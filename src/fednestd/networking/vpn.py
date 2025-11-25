# src/fednestd/networking/vpn.py
from __future__ import annotations

from typing import Dict, Any
from pathlib import Path

try:
    from ..observability.logging import get_logger
    logger = get_logger(__name__)
except Exception:
    import logging
    logger = logging.getLogger(__name__)


def render_vpn_peer_config(profile: Dict[str, Any]) -> str:
    """
    Render VPN peer configuration from vpn_peer.conf.j2 template and profile info.
    """
    template_path = Path(__file__).parent.parent / "infra" / "config_templates" / "vpn_peer.conf.j2"
    template_text = template_path.read_text()

    vpn = profile.get("vpn", {})
    rendered = template_text.format(
        ENDPOINT=vpn.get("endpoint", "vpn.example.com:51820"),
        PUBLIC_KEY=vpn.get("public_key", "CHANGEME"),
    )

    logger.info("Rendered VPN peer config with profile: %s", vpn)
    return rendered
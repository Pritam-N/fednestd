from __future__ import annotations

from typing import TypedDict


class HAProxyProfile(TypedDict, total=False):
    fedserver_host: str
    fedserver_port: int
    kafka_broker: str


class VPNProfile(TypedDict, total=False):
    endpoint: str
    public_key: str


class DeploymentProfile(TypedDict, total=False):
    haproxy: HAProxyProfile
    vpn: VPNProfile


# Now PROFILES has a fully known type.
PROFILES: dict[str, DeploymentProfile] = {
    "dev": {
        "haproxy": {
            "fedserver_host": "fedserver.dev.local",
            "fedserver_port": 8080,
            "kafka_broker": "kafka.dev.local:9092",
        },
        "vpn": {
            "endpoint": "vpn.dev.local:51820",
            "public_key": "DEV_PUBLIC_KEY",
        },
    },
    "prod": {
        "haproxy": {
            "fedserver_host": "fedserver.prod.local",
            "fedserver_port": 443,
            "kafka_broker": "kafka.prod.local:9092",
        },
        "vpn": {
            "endpoint": "vpn.prod.local:51820",
            "public_key": "PROD_PUBLIC_KEY",
        },
    },
    "edge": {
        "vpn": {
            "endpoint": "vpn.prod.local:51820",
            "public_key": "EDGE_PUBLIC_KEY",
        }
    },
}


def load_profile(name: str) -> DeploymentProfile:
    try:
        return PROFILES[name]
    except KeyError:
        raise ValueError(f"Unknown deployment profile: {name}")
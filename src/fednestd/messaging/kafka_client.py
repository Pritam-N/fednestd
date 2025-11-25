# src/fednestd/messaging/kafka_client.py
from __future__ import annotations

from typing import Any, Dict, Iterable, Optional

from kafka import KafkaProducer, KafkaConsumer
from kafka.admin import KafkaAdminClient

from ..observability.logging import get_logger

logger = get_logger(__name__)


def get_admin_client(kafka_config: Dict[str, Any]) -> KafkaAdminClient:
    """
    Create and return a KafkaAdminClient using the given config.

    Expected kafka_config keys:
      - bootstrap_servers: str or list[str] (e.g. "localhost:9092")
      - client_id: optional, defaults to "fednestd-admin"
      - security_protocol / sasl_* if you use auth (can be added later)
    """
    bootstrap_servers = kafka_config.get("bootstrap_servers", "localhost:9092")
    client_id = kafka_config.get("client_id", "fednestd-admin")

    logger.info(
        "Creating KafkaAdminClient (bootstrap_servers=%s, client_id=%s)",
        bootstrap_servers,
        client_id,
    )

    admin = KafkaAdminClient(
        bootstrap_servers=bootstrap_servers,
        client_id=client_id,
    )
    return admin


def get_producer(kafka_config: Dict[str, Any]) -> KafkaProducer:
    """
    Create a KafkaProducer using the given config.

    Minimal expected keys:
      - bootstrap_servers
      - client_id (optional)
    """
    bootstrap_servers = kafka_config.get("bootstrap_servers", "localhost:9092")
    client_id = kafka_config.get("client_id", "fednestd-producer")

    logger.info(
        "Creating KafkaProducer (bootstrap_servers=%s, client_id=%s)",
        bootstrap_servers,
        client_id,
    )

    producer = KafkaProducer(
        bootstrap_servers=bootstrap_servers,
        client_id=client_id,
        # you can customize serializers later (value_serializer, etc.)
    )
    return producer


def get_consumer(
    kafka_config: Dict[str, Any],
    topics: Iterable[str],
    group_id: Optional[str] = None,
) -> KafkaConsumer:
    """
    Create a KafkaConsumer subscribed to the given topics.

    Minimal expected keys:
      - bootstrap_servers
      - client_id (optional)
    """
    bootstrap_servers = kafka_config.get("bootstrap_servers", "localhost:9092")
    client_id = kafka_config.get("client_id", "fednestd-consumer")

    logger.info(
        "Creating KafkaConsumer (bootstrap_servers=%s, client_id=%s, topics=%s)",
        bootstrap_servers,
        client_id,
        list(topics),
    )

    consumer = KafkaConsumer(
        bootstrap_servers=bootstrap_servers,
        client_id=client_id,
        group_id=group_id,
        enable_auto_commit=True,
        auto_offset_reset="earliest",
    )
    consumer.subscribe(list(topics))
    return consumer
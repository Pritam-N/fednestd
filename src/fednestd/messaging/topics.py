# src/fednestd/messaging/topics.py
from __future__ import annotations

from typing import Any, Dict, List

from kafka.admin import NewTopic
from kafka.errors import TopicAlreadyExistsError

from ..observability.logging import get_logger
from .kafka_client import get_admin_client

logger = get_logger(__name__)


DEFAULT_TOPICS: List[str] = [
    "control.federation_rounds",
    "updates.experts.local",
    "telemetry.edge",
    "tasks.training",
]


def bootstrap_topics(config: Dict[str, Any]) -> None:
    """
    Create required Kafka topics with appropriate partitions, replication, retention.

    Expects:

        config["kafka"] = {
            "bootstrap_servers": "localhost:9092",
            "client_id": "fednestd-admin",
            "num_partitions": 3,
            "replication_factor": 1,
            # optional: "topic_overrides": { "tasks.training": {"num_partitions": 6} }
        }
    """
    kafka_cfg = config.get("kafka", {})
    if not kafka_cfg:
        raise ValueError("bootstrap_topics: config['kafka'] is missing or empty")

    admin = get_admin_client(kafka_cfg)

    default_partitions = int(kafka_cfg.get("num_partitions", 3))
    default_replicas = int(kafka_cfg.get("replication_factor", 1))
    overrides: Dict[str, Dict[str, Any]] = kafka_cfg.get("topic_overrides", {})

    logger.info(
        "Bootstrapping topics: %s (default_partitions=%s, default_replicas=%s)",
        DEFAULT_TOPICS,
        default_partitions,
        default_replicas,
    )

    existing_topics = set(admin.list_topics())
    topics_to_create: List[NewTopic] = []

    for name in DEFAULT_TOPICS:
        if name in existing_topics:
            logger.info("Topic already exists: %s", name)
            continue

        override = overrides.get(name, {})
        num_partitions = int(override.get("num_partitions", default_partitions))
        replication_factor = int(override.get("replication_factor", default_replicas))

        logger.info(
            "Preparing topic: %s (partitions=%s, replicas=%s)",
            name,
            num_partitions,
            replication_factor,
        )

        topics_to_create.append(
            NewTopic(
                name=name,
                num_partitions=num_partitions,
                replication_factor=replication_factor,
            )
        )

    if not topics_to_create:
        logger.info("No new topics to create.")
        return

    try:
        admin.create_topics(new_topics=topics_to_create, validate_only=False)
        logger.info("Created topics: %s", [t.name for t in topics_to_create])
    except TopicAlreadyExistsError:
        # Safe to ignore if topics have been created concurrently.
        logger.warning("Some topics already existed during creation, ignoring.")
    finally:
        admin.close()
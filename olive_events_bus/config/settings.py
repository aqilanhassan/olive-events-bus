"""
Configuration settings for Olive Events Bus SDK.
"""

import os
from dataclasses import dataclass, field
from typing import Any

from olive_events_bus.exceptions import ConfigurationError


@dataclass
class EventsConfig:
    """Configuration for Olive Events Bus SDK."""

    # Kafka Configuration
    bootstrap_servers: str = field(default_factory=lambda: os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092"))
    security_protocol: str = field(default_factory=lambda: os.getenv("KAFKA_SECURITY_PROTOCOL", "PLAINTEXT"))
    sasl_mechanism: str | None = field(default_factory=lambda: os.getenv("KAFKA_SASL_MECHANISM"))
    sasl_username: str | None = field(default_factory=lambda: os.getenv("KAFKA_SASL_USERNAME"))
    sasl_password: str | None = field(default_factory=lambda: os.getenv("KAFKA_SASL_PASSWORD"))
    ssl_cafile: str | None = field(default_factory=lambda: os.getenv("KAFKA_SSL_CAFILE"))
    ssl_certfile: str | None = field(default_factory=lambda: os.getenv("KAFKA_SSL_CERTFILE"))
    ssl_keyfile: str | None = field(default_factory=lambda: os.getenv("KAFKA_SSL_KEYFILE"))

    # Producer Configuration
    producer_acks: str = field(default_factory=lambda: os.getenv("KAFKA_PRODUCER_ACKS", "all"))
    producer_max_in_flight: int = field(default_factory=lambda: int(os.getenv("KAFKA_PRODUCER_MAX_IN_FLIGHT", "5")))
    producer_batch_size: int = field(default_factory=lambda: int(os.getenv("KAFKA_PRODUCER_BATCH_SIZE", "16384")))
    producer_linger_ms: int = field(default_factory=lambda: int(os.getenv("KAFKA_PRODUCER_LINGER_MS", "10")))
    producer_compression_type: str = field(default_factory=lambda: os.getenv("KAFKA_PRODUCER_COMPRESSION", "gzip"))

    # Consumer Configuration
    consumer_auto_offset_reset: str = field(
        default_factory=lambda: os.getenv("KAFKA_CONSUMER_AUTO_OFFSET_RESET", "latest")
    )
    consumer_enable_auto_commit: bool = field(
        default_factory=lambda: os.getenv("KAFKA_CONSUMER_ENABLE_AUTO_COMMIT", "false").lower() == "true"
    )
    consumer_session_timeout_ms: int = field(
        default_factory=lambda: int(os.getenv("KAFKA_CONSUMER_SESSION_TIMEOUT_MS", "30000"))
    )
    consumer_heartbeat_interval_ms: int = field(
        default_factory=lambda: int(os.getenv("KAFKA_CONSUMER_HEARTBEAT_INTERVAL_MS", "3000"))
    )
    consumer_max_poll_records: int = field(
        default_factory=lambda: int(os.getenv("KAFKA_CONSUMER_MAX_POLL_RECORDS", "500"))
    )
    consumer_fetch_min_bytes: int = field(default_factory=lambda: int(os.getenv("KAFKA_CONSUMER_FETCH_MIN_BYTES", "1")))
    consumer_fetch_max_wait_ms: int = field(
        default_factory=lambda: int(os.getenv("KAFKA_CONSUMER_FETCH_MAX_WAIT_MS", "500"))
    )

    # Schema Registry Configuration
    schema_registry_enabled: bool = field(
        default_factory=lambda: os.getenv("SCHEMA_REGISTRY_ENABLED", "true").lower() == "true"
    )
    schema_validation_enabled: bool = field(
        default_factory=lambda: os.getenv("SCHEMA_VALIDATION_ENABLED", "true").lower() == "true"
    )

    # Retry Configuration
    max_retries: int = field(default_factory=lambda: int(os.getenv("EVENTS_MAX_RETRIES", "3")))
    retry_backoff_ms: int = field(default_factory=lambda: int(os.getenv("EVENTS_RETRY_BACKOFF_MS", "1000")))
    retry_max_backoff_ms: int = field(default_factory=lambda: int(os.getenv("EVENTS_RETRY_MAX_BACKOFF_MS", "32000")))

    # Dead Letter Queue Configuration
    dlq_enabled: bool = field(default_factory=lambda: os.getenv("DLQ_ENABLED", "true").lower() == "true")
    dlq_topic_suffix: str = field(default_factory=lambda: os.getenv("DLQ_TOPIC_SUFFIX", ".dlq"))

    # Service Configuration
    service_name: str = field(default_factory=lambda: os.getenv("SERVICE_NAME", "unknown-service"))
    service_version: str = field(default_factory=lambda: os.getenv("SERVICE_VERSION", "1.0.0"))
    environment: str = field(default_factory=lambda: os.getenv("ENVIRONMENT", "development"))

    # Observability Configuration
    logging_enabled: bool = field(default_factory=lambda: os.getenv("EVENTS_LOGGING_ENABLED", "true").lower() == "true")
    logging_level: str = field(default_factory=lambda: os.getenv("EVENTS_LOGGING_LEVEL", "INFO"))
    metrics_enabled: bool = field(default_factory=lambda: os.getenv("EVENTS_METRICS_ENABLED", "true").lower() == "true")
    tracing_enabled: bool = field(default_factory=lambda: os.getenv("EVENTS_TRACING_ENABLED", "true").lower() == "true")

    # Topic Configuration
    default_partitions: int = field(default_factory=lambda: int(os.getenv("KAFKA_DEFAULT_PARTITIONS", "3")))
    default_replication_factor: int = field(
        default_factory=lambda: int(os.getenv("KAFKA_DEFAULT_REPLICATION_FACTOR", "3"))
    )

    # Retention Configuration
    default_retention_ms: int = field(
        default_factory=lambda: int(os.getenv("KAFKA_DEFAULT_RETENTION_MS", "86400000"))  # 1 day
    )
    audit_retention_ms: int = field(
        default_factory=lambda: int(os.getenv("KAFKA_AUDIT_RETENTION_MS", "2592000000"))  # 30 days
    )

    def __post_init__(self) -> None:
        """Validate configuration after initialization."""
        if not self.bootstrap_servers:
            raise ConfigurationError.missing_bootstrap_servers()

        if not self.service_name or self.service_name == "unknown-service":
            raise ConfigurationError.missing_service_name()

        if self.max_retries < 0:
            raise ConfigurationError.invalid_max_retries()

        if self.retry_backoff_ms <= 0:
            raise ConfigurationError.invalid_retry_backoff()

        if self.default_partitions <= 0:
            raise ConfigurationError.invalid_default_partitions()

        if self.default_replication_factor <= 0:
            raise ConfigurationError.invalid_replication_factor()

    def to_producer_config(self) -> dict[str, Any]:
        """Convert to aiokafka producer configuration."""
        config = {
            "bootstrap_servers": self.bootstrap_servers,
            "security_protocol": self.security_protocol,
            "acks": self.producer_acks,
            "linger_ms": self.producer_linger_ms,
            "compression_type": self.producer_compression_type,
        }

        # Add SASL configuration if provided
        if self.sasl_mechanism:
            config["sasl_mechanism"] = self.sasl_mechanism
        if self.sasl_username:
            config["sasl_plain_username"] = self.sasl_username
        if self.sasl_password:
            config["sasl_plain_password"] = self.sasl_password

        # Add SSL configuration if provided
        if self.ssl_cafile:
            config["ssl_cafile"] = self.ssl_cafile
        if self.ssl_certfile:
            config["ssl_certfile"] = self.ssl_certfile
        if self.ssl_keyfile:
            config["ssl_keyfile"] = self.ssl_keyfile

        return config

    def to_consumer_config(self, group_id: str) -> dict[str, Any]:
        """Convert to aiokafka consumer configuration."""
        config = {
            "bootstrap_servers": self.bootstrap_servers,
            "security_protocol": self.security_protocol,
            "group_id": group_id,
            "auto_offset_reset": self.consumer_auto_offset_reset,
            "enable_auto_commit": self.consumer_enable_auto_commit,
            "session_timeout_ms": self.consumer_session_timeout_ms,
            "heartbeat_interval_ms": self.consumer_heartbeat_interval_ms,
            "max_poll_records": self.consumer_max_poll_records,
            "fetch_min_bytes": self.consumer_fetch_min_bytes,
            "fetch_max_wait_ms": self.consumer_fetch_max_wait_ms,
        }

        # Add SASL configuration if provided
        if self.sasl_mechanism:
            config["sasl_mechanism"] = self.sasl_mechanism
        if self.sasl_username:
            config["sasl_plain_username"] = self.sasl_username
        if self.sasl_password:
            config["sasl_plain_password"] = self.sasl_password

        # Add SSL configuration if provided
        if self.ssl_cafile:
            config["ssl_cafile"] = self.ssl_cafile
        if self.ssl_certfile:
            config["ssl_certfile"] = self.ssl_certfile
        if self.ssl_keyfile:
            config["ssl_keyfile"] = self.ssl_keyfile

        return config

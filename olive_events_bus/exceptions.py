"""
Custom exceptions for Olive Events Bus SDK.
"""

from typing import Any


class OliveEventsError(Exception):
    """Base exception for all Olive Events Bus errors."""

    def __init__(self, message: str, context: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.context = context or {}


class SchemaValidationError(OliveEventsError):
    """Raised when event schema validation fails."""

    def __init__(
        self,
        message: str,
        schema_path: str | None = None,
        validation_errors: list[str] | None = None,
        context: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message, context)
        self.schema_path = schema_path
        self.validation_errors = validation_errors or []


class ProducerError(OliveEventsError):
    """Raised when event production fails."""

    def __init__(
        self,
        message: str,
        topic: str | None = None,
        retry_count: int | None = None,
        context: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message, context)
        self.topic = topic
        self.retry_count = retry_count

    @classmethod
    def not_started(cls) -> "ProducerError":
        """Create error for producer not started."""
        return cls("Producer not started")

    @classmethod
    def start_failed(cls, error: Exception) -> "ProducerError":
        """Create error for failed producer start."""
        return cls(f"Failed to start producer: {error}")

    @classmethod
    def stop_failed(cls, error: Exception) -> "ProducerError":
        """Create error for failed producer stop."""
        return cls(f"Failed to stop producer: {error}")

    @classmethod
    def publish_failed_after_retries(cls, max_retries: int, error: Exception) -> "ProducerError":
        """Create error for failed publish after retries."""
        return cls(f"Failed to publish event after {max_retries} retries: {error}")

    @classmethod
    def unexpected_publish_error(cls, error: Exception) -> "ProducerError":
        """Create error for unexpected publish error."""
        return cls(f"Unexpected error publishing event: {error}")

    @classmethod
    def flush_timeout(cls, timeout: float) -> "ProducerError":
        """Create error for flush timeout."""
        return cls(f"Flush timeout after {timeout}s")

    @classmethod
    def flush_error(cls, error: Exception) -> "ProducerError":
        """Create error for flush error."""
        return cls(f"Flush error: {error}")


class ConsumerError(OliveEventsError):
    """Raised when event consumption fails."""

    def __init__(
        self,
        message: str,
        topic: str | None = None,
        consumer_group: str | None = None,
        context: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message, context)
        self.topic = topic
        self.consumer_group = consumer_group

    @classmethod
    def no_topics_specified(cls) -> "ConsumerError":
        """Create error for no topics specified."""
        return cls("No topics specified for consumer")

    @classmethod
    def aiokafka_not_available(cls) -> "ConsumerError":
        """Create error for missing aiokafka dependency."""
        return cls("aiokafka not available")

    @classmethod
    def not_started(cls) -> "ConsumerError":
        """Create error for consumer not started."""
        return cls("Consumer not started")

    @classmethod
    def start_failed(cls, error: Exception) -> "ConsumerError":
        """Create error for failed consumer start."""
        return cls(f"Failed to start consumer: {error}")

    @classmethod
    def stop_failed(cls, error: Exception) -> "ConsumerError":
        """Create error for failed consumer stop."""
        return cls(f"Failed to stop consumer: {error}")

    @classmethod
    def loop_error(cls, error: Exception) -> "ConsumerError":
        """Create error for consumer loop error."""
        return cls(f"Consumer loop error: {error}")


class ConfigurationError(OliveEventsError):
    """Raised when SDK configuration is invalid."""

    def __init__(
        self,
        message: str,
        config_key: str | None = None,
        context: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message, context)
        self.config_key = config_key

    @classmethod
    def missing_bootstrap_servers(cls) -> "ConfigurationError":
        """Create error for missing bootstrap servers."""
        return cls("KAFKA_BOOTSTRAP_SERVERS must be provided", config_key="bootstrap_servers")

    @classmethod
    def missing_service_name(cls) -> "ConfigurationError":
        """Create error for missing service name."""
        return cls("SERVICE_NAME must be provided", config_key="service_name")

    @classmethod
    def invalid_max_retries(cls) -> "ConfigurationError":
        """Create error for invalid max retries."""
        return cls("EVENTS_MAX_RETRIES must be >= 0", config_key="max_retries")

    @classmethod
    def invalid_retry_backoff(cls) -> "ConfigurationError":
        """Create error for invalid retry backoff."""
        return cls("EVENTS_RETRY_BACKOFF_MS must be > 0", config_key="retry_backoff_ms")

    @classmethod
    def invalid_default_partitions(cls) -> "ConfigurationError":
        """Create error for invalid default partitions."""
        return cls("KAFKA_DEFAULT_PARTITIONS must be > 0", config_key="default_partitions")

    @classmethod
    def invalid_replication_factor(cls) -> "ConfigurationError":
        """Create error for invalid replication factor."""
        return cls("KAFKA_DEFAULT_REPLICATION_FACTOR must be > 0", config_key="default_replication_factor")


class SchemaRegistryError(OliveEventsError):
    """Raised when schema registry operations fail."""

    def __init__(
        self,
        message: str,
        schema_name: str | None = None,
        schema_version: str | None = None,
        context: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message, context)
        self.schema_name = schema_name
        self.schema_version = schema_version


class SerializationError(OliveEventsError):
    """Raised when event serialization/deserialization fails."""

    def __init__(self, message: str, event_data: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.event_data = event_data

    @classmethod
    def serialization_failed(cls, error: Exception) -> "SerializationError":
        """Create error for failed serialization."""
        return cls(f"Failed to serialize event: {error}")


class DeserializationError(OliveEventsError):
    """Raised when event deserialization fails."""

    def __init__(self, message: str, raw_data: bytes | str | None = None) -> None:
        super().__init__(message)
        self.raw_data = raw_data

    @classmethod
    def invalid_format(cls) -> "DeserializationError":
        """Create error for invalid event format."""
        return cls("Invalid event format")

    @classmethod
    def deserialization_failed(cls, error: Exception) -> "DeserializationError":
        """Create error for failed deserialization."""
        return cls(f"Failed to deserialize event: {error}")


class DeadLetterQueueError(OliveEventsError):
    """Raised when dead letter queue operations fail."""

    def __init__(
        self,
        message: str,
        original_topic: str | None = None,
        dlq_topic: str | None = None,
        context: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message, context)
        self.original_topic = original_topic
        self.dlq_topic = dlq_topic

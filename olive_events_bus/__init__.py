"""
Olive Events Bus SDK

A comprehensive enterprise-grade Kafka SDK for the Olive workforce management platform.
Provides event-driven architecture capabilities with schema validation, observability,
and reliability patterns.
"""

__version__ = "1.0.0"

# Core event models and types
# Configuration
from .config import EventsConfig
from .consumer import EventConsumer, create_consumer, event_handler
from .events import (
    EventMetadata,
    EventPriority,
    EventType,
    OliveEvent,
    create_audit_event,
    create_employee_event,
    create_leave_event,
)

# Exceptions
from .exceptions import (
    ConfigurationError,
    ConsumerError,
    DeadLetterQueueError,
    DeserializationError,
    OliveEventsError,
    ProducerError,
    SchemaValidationError,
    SerializationError,
)

# Producer and Consumer
from .producer import EventProducer, create_producer

# Schema Registry
from .schema_registry import SchemaRegistry, get_schema_registry, validate_event_data

__all__ = [
    "ConfigurationError",
    "ConsumerError",
    "DeadLetterQueueError",
    "DeserializationError",
    "EventConsumer",
    "EventMetadata",
    "EventPriority",
    # Producer/Consumer
    "EventProducer",
    "EventType",
    # Configuration
    "EventsConfig",
    # Events
    "OliveEvent",
    # Exceptions
    "OliveEventsError",
    "ProducerError",
    # Schema Registry
    "SchemaRegistry",
    "SchemaValidationError",
    "SerializationError",
    # Version
    "__version__",
    "create_audit_event",
    "create_consumer",
    "create_employee_event",
    "create_leave_event",
    "create_producer",
    "event_handler",
    "get_schema_registry",
    "validate_event_data",
]

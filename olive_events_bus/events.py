"""
Core event models and types for Olive Events Bus SDK.
"""

import json
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any


class EventType(str, Enum):
    """Standard event types in the Olive ecosystem."""

    # Employee events
    EMPLOYEE_CREATED = "employee.created"
    EMPLOYEE_UPDATED = "employee.updated"
    EMPLOYEE_DELETED = "employee.deleted"
    EMPLOYEE_ACTIVATED = "employee.activated"
    EMPLOYEE_DEACTIVATED = "employee.deactivated"

    # Leave events (canonical dot notation)
    LEAVE_CREATED = "leave.created"
    LEAVE_UPDATED = "leave.updated"
    LEAVE_APPROVED = "leave.approved"
    LEAVE_REJECTED = "leave.rejected"
    LEAVE_CANCELLED = "leave.cancelled"

    # Client events
    CLIENT_CREATED = "client.created"
    CLIENT_UPDATED = "client.updated"
    CLIENT_DELETED = "client.deleted"
    CLIENT_ACTIVATED = "client.activated"
    CLIENT_DEACTIVATED = "client.deactivated"

    # Asset events
    ASSET_CREATED = "asset.created"
    ASSET_UPDATED = "asset.updated"
    ASSET_DELETED = "asset.deleted"
    ASSET_ASSIGNED = "asset.assigned"
    ASSET_RETURNED = "asset.returned"

    # Notification events
    NOTIFICATION_SENT = "notification.sent"
    NOTIFICATION_DELIVERED = "notification.delivered"
    NOTIFICATION_FAILED = "notification.failed"

    # System events
    SYSTEM_HEALTH_CHECK = "system.health_check"
    SYSTEM_BACKUP_COMPLETED = "system.backup_completed"
    SYSTEM_MAINTENANCE_START = "system.maintenance_start"
    SYSTEM_MAINTENANCE_END = "system.maintenance_end"

    # Audit events
    AUDIT_USER_LOGIN = "audit.user_login"
    AUDIT_USER_LOGOUT = "audit.user_logout"
    AUDIT_PERMISSION_CHANGE = "audit.permission_change"
    AUDIT_DATA_ACCESS = "audit.data_access"


class EventPriority(str, Enum):
    """Event priority levels."""

    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class EventMetadata:
    """Metadata for events."""

    source_service: str
    source_version: str
    correlation_id: str | None = None
    user_id: str | None = None
    tenant_id: str | None = None
    trace_id: str | None = None
    span_id: str | None = None
    priority: EventPriority = EventPriority.NORMAL
    tags: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert metadata to dictionary."""
        return {
            "source_service": self.source_service,
            "source_version": self.source_version,
            "correlation_id": self.correlation_id,
            "user_id": self.user_id,
            "tenant_id": self.tenant_id,
            "trace_id": self.trace_id,
            "span_id": self.span_id,
            "priority": self.priority.value,
            "tags": self.tags,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "EventMetadata":
        """Create metadata from dictionary."""
        return cls(
            source_service=data["source_service"],
            source_version=data["source_version"],
            correlation_id=data.get("correlation_id"),
            user_id=data.get("user_id"),
            tenant_id=data.get("tenant_id"),
            trace_id=data.get("trace_id"),
            span_id=data.get("span_id"),
            priority=EventPriority(data.get("priority", EventPriority.NORMAL.value)),
            tags=data.get("tags", {}),
        )


@dataclass
class OliveEvent:
    """
    Standard event structure for the Olive ecosystem.

    This is the core event class that all events in the Olive platform
    should use. It provides a consistent structure with proper metadata,
    versioning, and serialization capabilities.
    """

    event_type: EventType
    data: dict[str, Any]
    metadata: EventMetadata
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    schema_version: str = "1.0.0"

    def __post_init__(self) -> None:
        """Validate event after initialization."""
        if not self.event_type:
            msg = "event_type is required"
            raise ValueError(msg)

        if not self.data:
            msg = "data is required"
            raise ValueError(msg)

        if not self.metadata:
            msg = "metadata is required"
            raise ValueError(msg)

        # Ensure timestamp is timezone-aware
        if self.timestamp.tzinfo is None:
            self.timestamp = self.timestamp.replace(tzinfo=UTC)

    def to_dict(self) -> dict[str, Any]:
        """Convert event to dictionary for serialization."""
        return {
            "event_id": self.event_id,
            "event_type": self.event_type.value,
            "timestamp": self.timestamp.isoformat(),
            "schema_version": self.schema_version,
            "data": self.data,
            "metadata": self.metadata.to_dict(),
        }

    def to_json(self) -> str:
        """Convert event to JSON string."""
        return json.dumps(self.to_dict(), default=str)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "OliveEvent":
        """Create event from dictionary."""
        # Handle optional metadata for backward compatibility
        metadata = None
        if "metadata" in data:
            metadata = EventMetadata.from_dict(data["metadata"])
        else:
            # Create default metadata for backward compatibility
            metadata = EventMetadata(source_service="unknown", source_version="1.0.0")

        return cls(
            event_id=data["event_id"],
            event_type=EventType(data["event_type"]),
            timestamp=datetime.fromisoformat(data["timestamp"]),
            schema_version=data.get("schema_version", "1.0.0"),
            data=data["data"],
            metadata=metadata,
        )

    @classmethod
    def from_json(cls, json_str: str) -> "OliveEvent":
        """Create event from JSON string."""
        data = json.loads(json_str)
        return cls.from_dict(data)

    def with_correlation_id(self, correlation_id: str) -> "OliveEvent":
        """Create a new event with the specified correlation ID."""
        new_metadata = EventMetadata(
            source_service=self.metadata.source_service,
            source_version=self.metadata.source_version,
            correlation_id=correlation_id,
            user_id=self.metadata.user_id,
            tenant_id=self.metadata.tenant_id,
            trace_id=self.metadata.trace_id,
            span_id=self.metadata.span_id,
            priority=self.metadata.priority,
            tags=self.metadata.tags.copy(),
        )

        return OliveEvent(
            event_type=self.event_type,
            data=self.data.copy(),
            metadata=new_metadata,
            event_id=self.event_id,
            timestamp=self.timestamp,
            schema_version=self.schema_version,
        )

    def with_user_context(self, user_id: str, tenant_id: str | None = None) -> "OliveEvent":
        """Create a new event with user context."""
        new_metadata = EventMetadata(
            source_service=self.metadata.source_service,
            source_version=self.metadata.source_version,
            correlation_id=self.metadata.correlation_id,
            user_id=user_id,
            tenant_id=tenant_id or self.metadata.tenant_id,
            trace_id=self.metadata.trace_id,
            span_id=self.metadata.span_id,
            priority=self.metadata.priority,
            tags=self.metadata.tags.copy(),
        )

        return OliveEvent(
            event_type=self.event_type,
            data=self.data.copy(),
            metadata=new_metadata,
            event_id=self.event_id,
            timestamp=self.timestamp,
            schema_version=self.schema_version,
        )

    def add_tag(self, key: str, value: str) -> "OliveEvent":
        """Add a tag to the event metadata."""
        new_tags = self.metadata.tags.copy()
        new_tags[key] = value

        new_metadata = EventMetadata(
            source_service=self.metadata.source_service,
            source_version=self.metadata.source_version,
            correlation_id=self.metadata.correlation_id,
            user_id=self.metadata.user_id,
            tenant_id=self.metadata.tenant_id,
            trace_id=self.metadata.trace_id,
            span_id=self.metadata.span_id,
            priority=self.metadata.priority,
            tags=new_tags,
        )

        return OliveEvent(
            event_type=self.event_type,
            data=self.data.copy(),
            metadata=new_metadata,
            event_id=self.event_id,
            timestamp=self.timestamp,
            schema_version=self.schema_version,
        )


# Convenience functions for creating common events
def create_employee_event(
    event_type: EventType,
    employee_data: dict[str, Any],
    source_service: str,
    source_version: str,
    user_id: str | None = None,
    tenant_id: str | None = None,
    correlation_id: str | None = None,
) -> OliveEvent:
    """Create an employee-related event."""
    metadata = EventMetadata(
        source_service=source_service,
        source_version=source_version,
        correlation_id=correlation_id,
        user_id=user_id,
        tenant_id=tenant_id,
    )

    return OliveEvent(
        event_type=event_type,
        data=employee_data,
        metadata=metadata,
    )


def create_leave_event(
    event_type: EventType,
    leave_data: dict[str, Any],
    source_service: str,
    source_version: str,
    user_id: str | None = None,
    tenant_id: str | None = None,
    correlation_id: str | None = None,
) -> OliveEvent:
    """Create a leave-related event."""
    metadata = EventMetadata(
        source_service=source_service,
        source_version=source_version,
        correlation_id=correlation_id,
        user_id=user_id,
        tenant_id=tenant_id,
        priority=EventPriority.HIGH,  # Leave events are typically high priority
    )

    return OliveEvent(
        event_type=event_type,
        data=leave_data,
        metadata=metadata,
    )


def create_audit_event(
    event_type: EventType,
    audit_data: dict[str, Any],
    source_service: str,
    source_version: str,
    user_id: str | None = None,
    tenant_id: str | None = None,
) -> OliveEvent:
    """Create an audit event."""
    metadata = EventMetadata(
        source_service=source_service,
        source_version=source_version,
        user_id=user_id,
        tenant_id=tenant_id,
        priority=EventPriority.HIGH,
        tags={"category": "audit"},
    )

    return OliveEvent(
        event_type=event_type,
        data=audit_data,
        metadata=metadata,
    )

"""
Schema registry and validation for Olive Events Bus SDK.
"""

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import jsonschema
    from jsonschema import ValidationError as JsonSchemaValidationError
    from jsonschema import validate
else:
    try:
        import jsonschema
        from jsonschema import ValidationError as JsonSchemaValidationError
        from jsonschema import validate
    except ImportError:
        jsonschema = None  # type: ignore[assignment]
        JsonSchemaValidationError = Exception  # type: ignore[assignment]

        def validate(instance: Any, schema: dict[str, Any]) -> None:  # noqa: ARG001
            """Mock validation function when jsonschema is not available."""


from .events import EventType
from .exceptions import SchemaValidationError


class SchemaRegistry:
    """
    Schema registry for event validation.

    Manages JSON schemas for different event types and provides
    validation capabilities.
    """

    def __init__(self) -> None:
        """Initialize the schema registry."""
        self._schemas: dict[EventType, dict[str, Any]] = {}
        self._load_default_schemas()

    def register_schema(self, event_type: EventType, schema: dict[str, Any]) -> None:
        """Register a JSON schema for an event type."""
        if jsonschema is not None:
            # Validate that the schema itself is valid
            try:
                jsonschema.Draft7Validator.check_schema(schema)
            except Exception as e:
                msg = f"Invalid schema for {event_type.value}"
                raise SchemaValidationError(msg) from e

        self._schemas[event_type] = schema

    def get_schema(self, event_type: EventType) -> dict[str, Any] | None:
        """Get the JSON schema for an event type."""
        return self._schemas.get(event_type)

    def validate_event_data(self, event_type: EventType, data: dict[str, Any]) -> None:
        """Validate event data against its schema."""
        schema = self.get_schema(event_type)

        if schema is None:
            # No schema registered, skip validation
            return

        try:
            validate(instance=data, schema=schema)
        except JsonSchemaValidationError as e:
            msg = f"Event data validation failed for {event_type.value}"
            raise SchemaValidationError(msg) from e

    def _load_default_schemas(self) -> None:
        """Load default schemas for common event types."""
        # Employee schemas
        employee_base_schema = {
            "type": "object",
            "properties": {
                "employee_id": {"type": "string"},
                "email": {"type": "string", "format": "email"},
                "first_name": {"type": "string"},
                "last_name": {"type": "string"},
                "department": {"type": "string"},
                "position": {"type": "string"},
                "hire_date": {"type": "string", "format": "date"},
                "status": {"type": "string", "enum": ["active", "inactive", "terminated"]},
            },
            "required": ["employee_id", "email", "first_name", "last_name"],
            "additionalProperties": True,
        }

        self.register_schema(EventType.EMPLOYEE_CREATED, employee_base_schema)
        self.register_schema(EventType.EMPLOYEE_UPDATED, employee_base_schema)
        self.register_schema(
            EventType.EMPLOYEE_ACTIVATED,
            {
                "type": "object",
                "properties": {
                    "employee_id": {"type": "string"},
                    "activated_by": {"type": "string"},
                    "activation_date": {"type": "string", "format": "date-time"},
                },
                "required": ["employee_id"],
                "additionalProperties": True,
            },
        )
        self.register_schema(
            EventType.EMPLOYEE_DEACTIVATED,
            {
                "type": "object",
                "properties": {
                    "employee_id": {"type": "string"},
                    "deactivated_by": {"type": "string"},
                    "deactivation_date": {"type": "string", "format": "date-time"},
                    "reason": {"type": "string"},
                },
                "required": ["employee_id"],
                "additionalProperties": True,
            },
        )

        # Leave schemas
        leave_base_schema = {
            "type": "object",
            "properties": {
                "leave_id": {"type": "string"},
                "employee_id": {"type": "string"},
                "leave_type": {
                    "type": "string",
                    "enum": ["annual", "sick", "maternity", "paternity", "personal", "emergency"],
                },
                "start_date": {"type": "string", "format": "date"},
                "end_date": {"type": "string", "format": "date"},
                "days_requested": {"type": "number", "minimum": 0.5},
                "reason": {"type": "string"},
                "status": {"type": "string", "enum": ["pending", "approved", "rejected", "cancelled"]},
                "created_by": {"type": "string"},
                "created_at": {"type": "string", "format": "date-time"},
            },
            "required": ["leave_id", "employee_id", "leave_type", "start_date", "end_date"],
            "additionalProperties": True,
        }

        self.register_schema(EventType.LEAVE_CREATED, leave_base_schema)
        self.register_schema(EventType.LEAVE_UPDATED, leave_base_schema)
        self.register_schema(
            EventType.LEAVE_APPROVED,
            {
                "type": "object",
                "properties": {
                    "leave_id": {"type": "string"},
                    "employee_id": {"type": "string"},
                    "approved_by": {"type": "string"},
                    "approved_at": {"type": "string", "format": "date-time"},
                    "comments": {"type": "string"},
                },
                "required": ["leave_id", "employee_id", "approved_by"],
                "additionalProperties": True,
            },
        )
        self.register_schema(
            EventType.LEAVE_REJECTED,
            {
                "type": "object",
                "properties": {
                    "leave_id": {"type": "string"},
                    "employee_id": {"type": "string"},
                    "rejected_by": {"type": "string"},
                    "rejected_at": {"type": "string", "format": "date-time"},
                    "reason": {"type": "string"},
                },
                "required": ["leave_id", "employee_id", "rejected_by", "reason"],
                "additionalProperties": True,
            },
        )

        # Client schemas
        client_base_schema = {
            "type": "object",
            "properties": {
                "client_id": {"type": "string"},
                "name": {"type": "string"},
                "email": {"type": "string", "format": "email"},
                "phone": {"type": "string"},
                "address": {
                    "type": "object",
                    "properties": {
                        "street": {"type": "string"},
                        "city": {"type": "string"},
                        "state": {"type": "string"},
                        "postal_code": {"type": "string"},
                        "country": {"type": "string"},
                    },
                },
                "industry": {"type": "string"},
                "status": {"type": "string", "enum": ["active", "inactive", "prospect"]},
                "contract_start": {"type": "string", "format": "date"},
                "contract_end": {"type": "string", "format": "date"},
            },
            "required": ["client_id", "name", "email"],
            "additionalProperties": True,
        }

        self.register_schema(EventType.CLIENT_CREATED, client_base_schema)
        self.register_schema(EventType.CLIENT_UPDATED, client_base_schema)

        # Asset schemas
        asset_base_schema = {
            "type": "object",
            "properties": {
                "asset_id": {"type": "string"},
                "name": {"type": "string"},
                "type": {
                    "type": "string",
                    "enum": ["laptop", "desktop", "monitor", "phone", "tablet", "accessory", "software"],
                },
                "brand": {"type": "string"},
                "model": {"type": "string"},
                "serial_number": {"type": "string"},
                "purchase_date": {"type": "string", "format": "date"},
                "purchase_price": {"type": "number", "minimum": 0},
                "status": {"type": "string", "enum": ["available", "assigned", "maintenance", "retired"]},
                "condition": {"type": "string", "enum": ["new", "good", "fair", "poor", "broken"]},
            },
            "required": ["asset_id", "name", "type"],
            "additionalProperties": True,
        }

        self.register_schema(EventType.ASSET_CREATED, asset_base_schema)
        self.register_schema(EventType.ASSET_UPDATED, asset_base_schema)
        self.register_schema(
            EventType.ASSET_ASSIGNED,
            {
                "type": "object",
                "properties": {
                    "asset_id": {"type": "string"},
                    "employee_id": {"type": "string"},
                    "assigned_by": {"type": "string"},
                    "assigned_at": {"type": "string", "format": "date-time"},
                    "expected_return": {"type": "string", "format": "date"},
                    "notes": {"type": "string"},
                },
                "required": ["asset_id", "employee_id", "assigned_by"],
                "additionalProperties": True,
            },
        )
        self.register_schema(
            EventType.ASSET_RETURNED,
            {
                "type": "object",
                "properties": {
                    "asset_id": {"type": "string"},
                    "employee_id": {"type": "string"},
                    "returned_by": {"type": "string"},
                    "returned_at": {"type": "string", "format": "date-time"},
                    "condition": {"type": "string", "enum": ["new", "good", "fair", "poor", "broken"]},
                    "notes": {"type": "string"},
                },
                "required": ["asset_id", "employee_id", "returned_by"],
                "additionalProperties": True,
            },
        )

        # Notification schemas
        notification_schema = {
            "type": "object",
            "properties": {
                "notification_id": {"type": "string"},
                "recipient_id": {"type": "string"},
                "recipient_type": {"type": "string", "enum": ["employee", "client", "admin"]},
                "channel": {"type": "string", "enum": ["email", "sms", "push", "in_app"]},
                "subject": {"type": "string"},
                "message": {"type": "string"},
                "template_id": {"type": "string"},
                "template_data": {"type": "object"},
                "priority": {"type": "string", "enum": ["low", "normal", "high", "urgent"]},
                "sent_at": {"type": "string", "format": "date-time"},
            },
            "required": ["notification_id", "recipient_id", "channel", "message"],
            "additionalProperties": True,
        }

        self.register_schema(EventType.NOTIFICATION_SENT, notification_schema)
        self.register_schema(
            EventType.NOTIFICATION_DELIVERED,
            {
                "type": "object",
                "properties": {
                    "notification_id": {"type": "string"},
                    "delivered_at": {"type": "string", "format": "date-time"},
                    "channel": {"type": "string"},
                    "recipient_id": {"type": "string"},
                },
                "required": ["notification_id", "delivered_at", "channel"],
                "additionalProperties": True,
            },
        )
        self.register_schema(
            EventType.NOTIFICATION_FAILED,
            {
                "type": "object",
                "properties": {
                    "notification_id": {"type": "string"},
                    "failed_at": {"type": "string", "format": "date-time"},
                    "channel": {"type": "string"},
                    "recipient_id": {"type": "string"},
                    "error": {"type": "string"},
                    "retry_count": {"type": "integer", "minimum": 0},
                },
                "required": ["notification_id", "failed_at", "channel", "error"],
                "additionalProperties": True,
            },
        )

        # System event schemas
        self.register_schema(
            EventType.SYSTEM_HEALTH_CHECK,
            {
                "type": "object",
                "properties": {
                    "service_name": {"type": "string"},
                    "status": {"type": "string", "enum": ["healthy", "degraded", "unhealthy"]},
                    "timestamp": {"type": "string", "format": "date-time"},
                    "metrics": {"type": "object"},
                    "errors": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["service_name", "status", "timestamp"],
                "additionalProperties": True,
            },
        )

        # Audit event schemas
        self.register_schema(
            EventType.AUDIT_USER_LOGIN,
            {
                "type": "object",
                "properties": {
                    "user_id": {"type": "string"},
                    "username": {"type": "string"},
                    "ip_address": {"type": "string"},
                    "user_agent": {"type": "string"},
                    "login_time": {"type": "string", "format": "date-time"},
                    "success": {"type": "boolean"},
                    "failure_reason": {"type": "string"},
                },
                "required": ["user_id", "ip_address", "login_time", "success"],
                "additionalProperties": True,
            },
        )


class _SchemaRegistrySingleton:
    """Singleton holder for the schema registry."""

    _instance: SchemaRegistry | None = None

    @classmethod
    def get_instance(cls) -> SchemaRegistry:
        """Get the singleton schema registry instance."""
        if cls._instance is None:
            cls._instance = SchemaRegistry()
        return cls._instance


def get_schema_registry() -> SchemaRegistry:
    """Get the global schema registry instance."""
    return _SchemaRegistrySingleton.get_instance()


def validate_event_data(event_type: EventType, data: dict[str, Any]) -> None:
    """Validate event data using the global schema registry."""
    registry = get_schema_registry()
    registry.validate_event_data(event_type, data)

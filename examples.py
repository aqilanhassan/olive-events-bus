"""
Examples demonstrating how to use the Olive Events Bus SDK.

This file shows various usage patterns and best practices for integrating
the SDK into your Olive microservices.
"""

import asyncio
import contextlib
import logging
import traceback
from datetime import UTC, datetime

from olive_events_bus import (
    EventConsumer,
    EventMetadata,
    EventPriority,
    EventProducer,
    EventsConfig,
    EventType,
    OliveEvent,
    create_employee_event,
    create_leave_event,
    event_handler,
    get_schema_registry,
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def producer_example() -> None:
    """Example of using the EventProducer to publish events."""

    # Create configuration
    config = EventsConfig(
        service_name="olive-employees",
        service_version="1.0.0",
        bootstrap_servers="localhost:9092",
    )

    # Create producer using context manager
    async with EventProducer(config) as producer:
        # Example 1: Create and publish an employee event
        employee_event = create_employee_event(
            event_type=EventType.EMPLOYEE_CREATED,
            employee_data={
                "employee_id": "emp_123",
                "email": "john.doe@olive.com",
                "first_name": "John",
                "last_name": "Doe",
                "department": "Engineering",
                "position": "Senior Developer",
                "hire_date": "2024-01-15",
                "status": "active",
            },
            source_service="olive-employees",
            source_version="1.0.0",
            user_id="admin_001",
            tenant_id="olive_main",
        )

        await producer.publish(
            topic="employees.events",
            event=employee_event,
        )

        # Example 2: Create and publish a leave event
        leave_event = create_leave_event(
            event_type=EventType.LEAVE_CREATED,
            leave_data={
                "leave_id": "leave_456",
                "employee_id": "emp_123",
                "leave_type": "annual",
                "start_date": "2024-02-01",
                "end_date": "2024-02-05",
                "days_requested": 5,
                "reason": "Family vacation",
                "status": "pending",
                "created_by": "emp_123",
                "created_at": datetime.now(UTC).isoformat(),
            },
            source_service="olive-leaves",
            source_version="1.0.0",
            user_id="emp_123",
            tenant_id="olive_main",
        )

        await producer.publish(
            topic="leaves.events",
            event=leave_event,
            key=leave_event.data["employee_id"],  # Partition by employee
        )

        # Example 3: Publish a batch of events
        events = []
        for i in range(3):
            event = OliveEvent(
                event_type=EventType.SYSTEM_HEALTH_CHECK,
                data={
                    "service_name": f"service-{i}",
                    "status": "healthy",
                    "timestamp": datetime.now(UTC).isoformat(),
                    "metrics": {"cpu": 45.2, "memory": 67.8},
                },
                metadata=EventMetadata(
                    source_service="monitoring",
                    source_version="1.0.0",
                    priority=EventPriority.LOW,
                ),
            )
            events.append((event, f"service-{i}"))

        await producer.publish_batch(
            topic="system.health",
            events=events,
        )

        # Ensure all messages are sent
        await producer.flush()


async def consumer_example() -> None:
    """Example of using the EventConsumer to consume events."""

    # Create configuration
    config = EventsConfig(
        service_name="olive-notifications",
        service_version="1.0.0",
        bootstrap_servers="localhost:9092",
        consumer_auto_offset_reset="earliest",
    )

    # Create consumer
    consumer = EventConsumer(
        config=config,
        group_id="notifications-service",
        topics=["employees.events", "leaves.events"],
    )

    # Define event handlers
    @event_handler(EventType.EMPLOYEE_CREATED)
    async def handle_employee_created(event: OliveEvent) -> None:  # noqa: ARG001
        # Send welcome email notification
        # Simulate processing time
        await asyncio.sleep(0.1)

    @event_handler(EventType.LEAVE_CREATED)
    async def handle_leave_created(event: OliveEvent) -> None:  # noqa: ARG001
        # Notify manager about leave request
        # Simulate processing time
        await asyncio.sleep(0.1)

    # Default handler for unhandled events
    async def handle_default(event: OliveEvent) -> None:
        pass

    # Register handlers
    consumer.add_handler(EventType.EMPLOYEE_CREATED, handle_employee_created)
    consumer.add_handler(EventType.LEAVE_CREATED, handle_leave_created)
    consumer.set_default_handler(handle_default)

    # Start consumer in background
    await consumer.start_consuming()

    # Let it run for a while to process messages
    await asyncio.sleep(5)

    # Stop consumer
    await consumer.stop()


async def schema_validation_example() -> None:
    """Example of using schema validation."""

    # Get the global schema registry
    registry = get_schema_registry()

    # Example 1: Valid employee data
    valid_employee_data = {
        "employee_id": "emp_789",
        "email": "jane.smith@olive.com",
        "first_name": "Jane",
        "last_name": "Smith",
        "department": "HR",
        "position": "HR Manager",
        "hire_date": "2024-01-20",
        "status": "active",
    }

    with contextlib.suppress(Exception):
        registry.validate_event_data(EventType.EMPLOYEE_CREATED, valid_employee_data)

    # Example 2: Invalid employee data (missing required field)
    invalid_employee_data = {
        "employee_id": "emp_999",
        # Missing email field
        "first_name": "Bob",
        "last_name": "Johnson",
    }

    with contextlib.suppress(Exception):
        registry.validate_event_data(EventType.EMPLOYEE_CREATED, invalid_employee_data)

    # Example 3: Custom schema registration
    # Note: We would need to add this event type to EventType enum first
    # Custom schemas can be registered for new event types as needed


async def comprehensive_workflow_example() -> None:
    """Example showing a complete workflow with producer and consumer."""

    config = EventsConfig(
        service_name="workflow-demo",
        service_version="1.0.0",
        bootstrap_servers="localhost:9092",
    )

    # Start a consumer for leave approval workflow
    consumer = EventConsumer(
        config=config,
        group_id="leave-approval-workflow",
        topics=["leaves.events"],
    )

    @event_handler(EventType.LEAVE_CREATED)
    async def auto_approve_leave(event: OliveEvent) -> None:
        leave_data = event.data

        # Simulate approval logic
        if leave_data.get("days_requested", 0) <= 2:
            # Auto-approve short leaves
            approval_event = OliveEvent(
                event_type=EventType.LEAVE_APPROVED,
                data={
                    "leave_id": leave_data["leave_id"],
                    "employee_id": leave_data["employee_id"],
                    "approved_by": "system_auto_approver",
                    "approved_at": datetime.now(UTC).isoformat(),
                    "comments": "Auto-approved: short duration leave",
                },
                metadata=EventMetadata(
                    source_service="leave-workflow",
                    source_version="1.0.0",
                    correlation_id=event.metadata.correlation_id,
                    priority=EventPriority.HIGH,
                ),
            )

            # Publish approval event
            async with EventProducer(config) as producer:
                await producer.publish(
                    topic="leaves.events",
                    event=approval_event,
                    key=leave_data["employee_id"],
                )
        else:
            pass

    consumer.add_handler(EventType.LEAVE_CREATED, auto_approve_leave)

    # Start the workflow consumer
    await consumer.start_consuming()

    # Simulate creating some leave requests
    async with EventProducer(config) as producer:
        # Short leave - should be auto-approved
        short_leave = create_leave_event(
            event_type=EventType.LEAVE_CREATED,
            leave_data={
                "leave_id": "leave_short_001",
                "employee_id": "emp_workflow_001",
                "leave_type": "personal",
                "start_date": "2024-02-10",
                "end_date": "2024-02-11",
                "days_requested": 2,
                "reason": "Personal appointment",
                "status": "pending",
                "created_by": "emp_workflow_001",
                "created_at": datetime.now(UTC).isoformat(),
            },
            source_service="olive-leaves",
            source_version="1.0.0",
            user_id="emp_workflow_001",
        )

        await producer.publish(
            topic="leaves.events",
            event=short_leave,
        )

        # Long leave - should require manual approval
        long_leave = create_leave_event(
            event_type=EventType.LEAVE_CREATED,
            leave_data={
                "leave_id": "leave_long_001",
                "employee_id": "emp_workflow_002",
                "leave_type": "annual",
                "start_date": "2024-03-01",
                "end_date": "2024-03-15",
                "days_requested": 15,
                "reason": "Extended vacation",
                "status": "pending",
                "created_by": "emp_workflow_002",
                "created_at": datetime.now(UTC).isoformat(),
            },
            source_service="olive-leaves",
            source_version="1.0.0",
            user_id="emp_workflow_002",
        )

        await producer.publish(
            topic="leaves.events",
            event=long_leave,
        )

    # Let the workflow process
    await asyncio.sleep(3)

    await consumer.stop()


async def main() -> None:
    """Run all examples."""

    try:
        await producer_example()
        await schema_validation_example()

        # Note: Consumer examples require Kafka to be running
        # You can enable consumer_example() and comprehensive_workflow_example()

    except Exception:
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())

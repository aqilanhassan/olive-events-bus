"""
Kafka consumer implementation for Olive Events Bus SDK.
"""

import asyncio
import contextlib
from collections.abc import Awaitable, Callable
from types import TracebackType
from typing import TYPE_CHECKING, Any

try:
    import structlog

    get_logger = structlog.get_logger
except ImportError:
    import logging

    get_logger = logging.getLogger  # type: ignore[assignment]

try:
    from aiokafka import AIOKafkaConsumer
    from aiokafka.errors import KafkaError
except ImportError:
    # Graceful fallback for missing dependencies
    AIOKafkaConsumer = None  # type: ignore[assignment]
    KafkaError = Exception  # type: ignore[assignment]

if TYPE_CHECKING:
    from opentelemetry import trace
    from opentelemetry.trace import Status, StatusCode
else:
    try:
        from opentelemetry import trace
        from opentelemetry.trace import Status, StatusCode
    except ImportError:
        # Mock tracing if not available

        class MockSpan:
            def set_status(self, status: Any) -> None:
                pass

            def set_attributes(self, attrs: Any) -> None:
                pass

            def __enter__(self) -> "MockSpan":
                return self

            def __exit__(self, *args: object) -> None:
                pass

        class MockTracer:
            def start_as_current_span(self, name: str, **kwargs: Any) -> MockSpan:  # noqa: ARG002
                return MockSpan()

            def get_tracer(self, name: str) -> "MockTracer":  # noqa: ARG002
                return self

        class MockStatus:
            def __init__(self, status_code: Any, description: str = "") -> None:
                pass

        class MockStatusCode:
            OK = "OK"
            ERROR = "ERROR"

        trace = MockTracer()
        Status = MockStatus
        StatusCode = MockStatusCode

from .config import EventsConfig
from .events import EventType, OliveEvent
from .exceptions import ConsumerError, DeserializationError

logger = get_logger(__name__)
tracer = trace.get_tracer(__name__)


EventHandler = Callable[[OliveEvent], Awaitable[None]]


class EventConsumer:
    """
    High-level Kafka consumer for Olive events.

    Provides a simple interface for consuming events with built-in
    retry logic, error handling, observability, and dead letter queue support.
    """

    def __init__(
        self,
        config: EventsConfig,
        group_id: str,
        topics: list[str] | None = None,
    ) -> None:
        """Initialize the event consumer."""
        self.config = config
        self.group_id = group_id
        self.topics = topics or []
        self._consumer: Any = None  # AIOKafkaConsumer or None
        self._is_started = False
        self._handlers: dict[EventType, EventHandler] = {}
        self._default_handler: EventHandler | None = None
        self._running = False
        self._consumer_task: asyncio.Task[None] | None = None

        # Configure structured logging
        self.logger = logger.bind(
            service=config.service_name,
            component="consumer",
            group_id=group_id,
        )

    def add_handler(self, event_type: EventType, handler: EventHandler) -> None:
        """Add an event handler for a specific event type."""
        self._handlers[event_type] = handler
        self.logger.info(
            "Event handler registered",
            event_type=event_type.value,
            handler=handler.__name__,
        )

    def set_default_handler(self, handler: EventHandler) -> None:
        """Set a default handler for unhandled event types."""
        self._default_handler = handler
        self.logger.info(
            "Default event handler set",
            handler=handler.__name__,
        )

    async def start(self) -> None:
        """Start the Kafka consumer."""
        if self._is_started:
            return

        if not self.topics:
            raise ConsumerError.no_topics_specified()

        with tracer.start_as_current_span("consumer_start") as span:
            try:
                consumer_config = self.config.to_consumer_config(self.group_id)

                if AIOKafkaConsumer is None:
                    raise ConsumerError.aiokafka_not_available()  # noqa: TRY301

                self._consumer = AIOKafkaConsumer(
                    *self.topics,
                    **consumer_config,
                    value_deserializer=self._deserialize_event,
                    key_deserializer=lambda k: k.decode("utf-8") if k else None,
                )

                await self._consumer.start()
                self._is_started = True

                self.logger.info(
                    "Consumer started successfully",
                    topics=self.topics,
                    bootstrap_servers=self.config.bootstrap_servers,
                )

                span.set_status(Status(StatusCode.OK))

            except Exception as e:
                self.logger.exception(
                    "Failed to start consumer",
                    error=str(e),
                    error_type=type(e).__name__,
                )
                span.set_status(Status(StatusCode.ERROR, str(e)))
                raise ConsumerError.start_failed(e) from e

    async def stop(self) -> None:
        """Stop the Kafka consumer."""
        if not self._is_started:
            return

        with tracer.start_as_current_span("consumer_stop") as span:
            try:
                # Stop the consumer loop
                self._running = False

                # Cancel the consumer task if running
                if self._consumer_task and not self._consumer_task.done():
                    self._consumer_task.cancel()
                    with contextlib.suppress(asyncio.CancelledError):
                        await self._consumer_task

                # Stop the Kafka consumer
                if self._consumer:
                    await self._consumer.stop()

                self._is_started = False
                self._consumer = None
                self._consumer_task = None

                self.logger.info("Consumer stopped successfully")
                span.set_status(Status(StatusCode.OK))

            except Exception as e:
                self.logger.exception(
                    "Error stopping consumer",
                    error=str(e),
                    error_type=type(e).__name__,
                )
                span.set_status(Status(StatusCode.ERROR, str(e)))
                raise ConsumerError.stop_failed(e) from e

    async def run(self) -> None:
        """Run the consumer loop."""
        if not self._is_started or not self._consumer:
            raise ConsumerError.not_started()

        self._running = True
        self.logger.info("Starting consumer loop")

        try:
            async for message in self._consumer:
                if not self._running:
                    break

                await self._process_message(message)

        except asyncio.CancelledError:
            self.logger.info("Consumer loop cancelled")
            raise
        except Exception as e:
            self.logger.exception(
                "Error in consumer loop",
                error=str(e),
                error_type=type(e).__name__,
            )
            raise ConsumerError.loop_error(e) from e
        finally:
            self._running = False

    async def start_consuming(self) -> None:
        """Start consuming events in the background."""
        if self._consumer_task and not self._consumer_task.done():
            return

        await self.start()
        self._consumer_task = asyncio.create_task(self.run())

        self.logger.info("Background consumer task started")

    async def _process_message(self, message: Any) -> None:
        """Process a single Kafka message."""
        with tracer.start_as_current_span(
            "consumer_process_message",
            attributes={
                "messaging.system": "kafka",
                "messaging.destination": message.topic,
                "messaging.operation": "receive",
                "messaging.kafka.partition": message.partition,
                "messaging.kafka.offset": message.offset,
            },
        ) as span:
            try:
                event = message.value

                if not isinstance(event, OliveEvent):
                    raise DeserializationError.invalid_format()  # noqa: TRY301

                # Add message metadata to span
                span.set_attributes(
                    {
                        "messaging.message_id": event.event_id,
                        "olive.event_type": event.event_type.value,
                    }
                )

                self.logger.info(
                    "Processing event",
                    topic=message.topic,
                    partition=message.partition,
                    offset=message.offset,
                    event_id=event.event_id,
                    event_type=event.event_type.value,
                )

                # Find and execute handler
                handler = self._handlers.get(event.event_type, self._default_handler)

                if handler is None:
                    self.logger.warning(
                        "No handler found for event type",
                        event_type=event.event_type.value,
                        event_id=event.event_id,
                    )
                    return

                # Execute handler with retry logic
                await self._execute_handler_with_retry(handler, event, message)

                # Commit offset if auto-commit is disabled
                if not self.config.consumer_enable_auto_commit and self._consumer:
                    await self._consumer.commit()

                self.logger.info(
                    "Event processed successfully",
                    event_id=event.event_id,
                    event_type=event.event_type.value,
                    handler=handler.__name__,
                )

                span.set_status(Status(StatusCode.OK))

            except Exception as e:
                self.logger.exception(
                    "Error processing message",
                    topic=message.topic,
                    partition=message.partition,
                    offset=message.offset,
                    error=str(e),
                    error_type=type(e).__name__,
                )
                span.set_status(Status(StatusCode.ERROR, str(e)))

                # Send to DLQ if enabled
                if self.config.dlq_enabled:
                    await self._send_to_dlq(message, str(e))

                # Don't re-raise to avoid stopping the consumer

    async def _execute_handler_with_retry(self, handler: EventHandler, event: OliveEvent, message: Any) -> None:  # noqa: ARG002
        """Execute an event handler with retry logic."""
        retry_count = 0
        max_retries = self.config.max_retries

        while retry_count <= max_retries:
            try:
                await handler(event)
            except Exception as e:
                retry_count += 1

                if retry_count > max_retries:
                    self.logger.exception(
                        "Handler failed after retries",
                        event_id=event.event_id,
                        event_type=event.event_type.value,
                        handler=handler.__name__,
                        retry_count=retry_count,
                        error=str(e),
                        error_type=type(e).__name__,
                    )
                    raise

                # Calculate backoff delay
                delay = (
                    min(self.config.retry_backoff_ms * (2 ** (retry_count - 1)), self.config.retry_max_backoff_ms)
                    / 1000.0
                )

                self.logger.warning(
                    "Retrying handler execution",
                    event_id=event.event_id,
                    event_type=event.event_type.value,
                    handler=handler.__name__,
                    retry_count=retry_count,
                    delay_seconds=delay,
                    error=str(e),
                )

                await asyncio.sleep(delay)
            else:
                # Success case - handler executed without exception
                return

    async def _send_to_dlq(self, message: Any, error: str) -> None:
        """Send a failed message to the dead letter queue."""
        try:
            dlq_topic = f"{message.topic}{self.config.dlq_topic_suffix}"

            # Create DLQ message with error information
            {
                "original_topic": message.topic,
                "original_partition": message.partition,
                "original_offset": message.offset,
                "error": error,
                "timestamp": message.timestamp,
                "headers": dict(message.headers) if message.headers else {},
                "value": message.value.to_dict() if hasattr(message.value, "to_dict") else str(message.value),
            }

            # TODO: Implement DLQ producer
            # For now, just log the DLQ event
            self.logger.error(
                "Message sent to DLQ",
                dlq_topic=dlq_topic,
                original_topic=message.topic,
                partition=message.partition,
                offset=message.offset,
                error=error,
            )

        except Exception as e:
            self.logger.exception(
                "Failed to send message to DLQ",
                error=str(e),
                error_type=type(e).__name__,
            )

    def _deserialize_event(self, data: bytes) -> OliveEvent:
        """Deserialize event from bytes."""
        try:
            json_str = data.decode("utf-8")
            return OliveEvent.from_json(json_str)
        except Exception as e:
            raise DeserializationError.deserialization_failed(e) from e

    async def __aenter__(self) -> "EventConsumer":
        """Async context manager entry."""
        await self.start()
        return self

    async def __aexit__(
        self, exc_type: type[BaseException] | None, exc_val: BaseException | None, exc_tb: TracebackType | None
    ) -> None:
        """Async context manager exit."""
        await self.stop()


# Factory function for easy consumer creation
async def create_consumer(
    group_id: str,
    topics: list[str],
    config: EventsConfig | None = None,
) -> EventConsumer:
    """
    Create and start an event consumer.

    Args:
        group_id: Kafka consumer group ID
        topics: List of topics to subscribe to
        config: Optional configuration. If not provided, will use default config.

    Returns:
        Started EventConsumer instance
    """
    if config is None:
        config = EventsConfig()

    consumer = EventConsumer(config, group_id, topics)
    await consumer.start()
    return consumer


# Decorator for easy event handler registration
def event_handler(event_type: EventType) -> Any:
    """Decorator to mark a function as an event handler."""

    def decorator(func: EventHandler) -> EventHandler:
        func.olive_event_type = event_type  # type: ignore[attr-defined]
        return func

    return decorator

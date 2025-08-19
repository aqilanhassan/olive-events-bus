"""
Kafka producer implementation for Olive Events Bus SDK.
"""

import asyncio
from types import TracebackType
from typing import TYPE_CHECKING, Any

try:
    import structlog
except ImportError:
    import logging as structlog  # type: ignore[no-redef]

try:
    from aiokafka import AIOKafkaProducer
    from aiokafka.errors import KafkaError
except ImportError:
    # Graceful fallback for missing dependencies
    AIOKafkaProducer = None  # type: ignore[assignment]
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
from .events import OliveEvent
from .exceptions import ProducerError, SerializationError

logger = structlog.get_logger(__name__)
tracer = trace.get_tracer(__name__)


class EventProducer:
    """
    High-level Kafka producer for Olive events.

    Provides a simple interface for publishing events with built-in
    retry logic, error handling, and observability.
    """

    def __init__(self, config: EventsConfig) -> None:
        """Initialize the event producer."""
        self.config = config
        self._producer: Any = None  # AIOKafkaProducer or None
        self._is_started = False
        self._retry_attempts = 0

        # Configure structured logging
        self.logger = logger.bind(service=config.service_name, component="producer")

    async def start(self) -> None:
        """Start the Kafka producer."""
        if self._is_started:
            return

        with tracer.start_as_current_span("producer_start") as span:
            try:
                producer_config = self.config.to_producer_config()

                self._producer = AIOKafkaProducer(
                    **producer_config,
                    value_serializer=self._serialize_event,
                    key_serializer=lambda k: k.encode("utf-8") if k else None,
                )

                await self._producer.start()
                self._is_started = True

                self.logger.info(
                    "Producer started successfully",
                    bootstrap_servers=self.config.bootstrap_servers,
                )

                span.set_status(Status(StatusCode.OK))

            except Exception as e:
                self.logger.exception(
                    "Failed to start producer",
                    error=str(e),
                    error_type=type(e).__name__,
                )
                span.set_status(Status(StatusCode.ERROR, str(e)))
                raise ProducerError.start_failed(e) from e

    async def stop(self) -> None:
        """Stop the Kafka producer."""
        if not self._is_started or not self._producer:
            return

        with tracer.start_as_current_span("producer_stop") as span:
            try:
                await self._producer.stop()
                self._is_started = False
                self._producer = None

                self.logger.info("Producer stopped successfully")
                span.set_status(Status(StatusCode.OK))

            except Exception as e:
                self.logger.exception(
                    "Error stopping producer",
                    error=str(e),
                    error_type=type(e).__name__,
                )
                span.set_status(Status(StatusCode.ERROR, str(e)))
                raise ProducerError.stop_failed(e) from e

    async def publish(
        self,
        topic: str,
        event: OliveEvent,
        key: str | None = None,
        partition: int | None = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        """
        Publish an event to a Kafka topic.

        Args:
            topic: The Kafka topic to publish to
            event: The event to publish
            key: Optional partition key
            partition: Optional specific partition
            headers: Optional message headers
        """
        if not self._is_started or not self._producer:
            raise ProducerError.not_started()

        # Default key to event ID for partitioning
        if key is None:
            key = event.event_id

        # Add trace information to headers
        if headers is None:
            headers = {}

        # Add event metadata to headers
        headers.update(
            {
                "event_type": event.event_type.value,
                "event_id": event.event_id,
            }
        )

        # Add tracing headers if available
        if event.metadata.trace_id:
            headers["trace_id"] = event.metadata.trace_id
        if event.metadata.span_id:
            headers["span_id"] = event.metadata.span_id
        if event.metadata.correlation_id:
            headers["correlation_id"] = event.metadata.correlation_id

        with tracer.start_as_current_span(
            "producer_publish",
            attributes={
                "messaging.system": "kafka",
                "messaging.destination": topic,
                "messaging.operation": "publish",
                "messaging.message_id": event.event_id,
                "olive.event_type": event.event_type.value,
            },
        ) as span:
            retry_count = 0
            max_retries = self.config.max_retries

            while retry_count <= max_retries:
                try:
                    # Convert headers to bytes
                    kafka_headers = [(k, v.encode("utf-8")) for k, v in headers.items()]

                    future = await self._producer.send(
                        topic=topic,
                        value=event,
                        key=key,
                        partition=partition,
                        headers=kafka_headers,
                    )

                    record_metadata = await future

                    self.logger.info(
                        "Event published successfully",
                        topic=topic,
                        partition=record_metadata.partition,
                        offset=record_metadata.offset,
                        event_id=event.event_id,
                        event_type=event.event_type.value,
                    )

                    span.set_status(Status(StatusCode.OK))
                    span.set_attributes(
                        {
                            "messaging.kafka.partition": record_metadata.partition,
                            "messaging.kafka.offset": record_metadata.offset,
                        }
                    )
                except KafkaError as e:
                    retry_count += 1

                    if retry_count > max_retries:
                        self.logger.exception(
                            "Failed to publish event after retries",
                            topic=topic,
                            event_id=event.event_id,
                            event_type=event.event_type.value,
                            retry_count=retry_count,
                            error=str(e),
                            error_type=type(e).__name__,
                        )
                        span.set_status(Status(StatusCode.ERROR, str(e)))
                        raise ProducerError.publish_failed_after_retries(max_retries, e) from e

                    # Calculate backoff delay
                    delay = (
                        min(self.config.retry_backoff_ms * (2 ** (retry_count - 1)), self.config.retry_max_backoff_ms)
                        / 1000.0
                    )

                    self.logger.warning(
                        "Retrying event publication",
                        topic=topic,
                        event_id=event.event_id,
                        retry_count=retry_count,
                        delay_seconds=delay,
                        error=str(e),
                    )

                    await asyncio.sleep(delay)

                except Exception as e:
                    self.logger.exception(
                        "Unexpected error publishing event",
                        topic=topic,
                        event_id=event.event_id,
                        event_type=event.event_type.value,
                        error=str(e),
                        error_type=type(e).__name__,
                    )
                    span.set_status(Status(StatusCode.ERROR, str(e)))
                    raise ProducerError.unexpected_publish_error(e) from e
                else:
                    # Success case - event published successfully
                    return

    async def publish_batch(
        self,
        topic: str,
        events: list[tuple[OliveEvent, str | None]],
        headers: dict[str, str] | None = None,
    ) -> None:
        """
        Publish a batch of events to a Kafka topic.

        Args:
            topic: The Kafka topic to publish to
            events: List of (event, key) tuples
            headers: Optional message headers for all events
        """
        if not self._is_started or not self._producer:
            raise ProducerError.not_started()

        with tracer.start_as_current_span(
            "producer_publish_batch",
            attributes={
                "messaging.system": "kafka",
                "messaging.destination": topic,
                "messaging.operation": "publish",
            },
        ) as span:
            tasks = []
            for event, key in events:
                task = self.publish(topic, event, key, headers=headers)
                tasks.append(task)

            try:
                await asyncio.gather(*tasks)

                self.logger.info(
                    "Batch published successfully",
                    topic=topic,
                )

                span.set_status(Status(StatusCode.OK))

            except Exception as e:
                self.logger.exception(
                    "Failed to publish batch",
                    topic=topic,
                    error=str(e),
                    error_type=type(e).__name__,
                )
                span.set_status(Status(StatusCode.ERROR, str(e)))
                raise

    async def flush(self, timeout: float = 30.0) -> None:
        """
        Flush any pending messages.

        Args:
            timeout: Maximum time to wait for flush to complete
        """
        if not self._is_started or not self._producer:
            return

        with tracer.start_as_current_span("producer_flush") as span:
            try:
                await asyncio.wait_for(self._producer.flush(), timeout=timeout)

                self.logger.debug("Producer flush completed")
                span.set_status(Status(StatusCode.OK))

            except TimeoutError as e:
                self.logger.exception(
                    "Producer flush timeout",
                    timeout=timeout,
                )
                span.set_status(Status(StatusCode.ERROR, "Flush timeout"))
                raise ProducerError.flush_timeout(timeout) from e

            except Exception as e:
                self.logger.exception(
                    "Error during producer flush",
                    error=str(e),
                    error_type=type(e).__name__,
                )
                span.set_status(Status(StatusCode.ERROR, str(e)))
                raise ProducerError.flush_error(e) from e

    def _serialize_event(self, event: OliveEvent) -> bytes:
        """Serialize an event to bytes."""
        try:
            return event.to_json().encode("utf-8")
        except Exception as e:
            raise SerializationError.serialization_failed(e) from e

    async def __aenter__(self) -> "EventProducer":
        """Async context manager entry."""
        await self.start()
        return self

    async def __aexit__(
        self, exc_type: type[BaseException] | None, exc_val: BaseException | None, exc_tb: TracebackType | None
    ) -> None:
        """Async context manager exit."""
        await self.stop()


# Factory function for easy producer creation
async def create_producer(config: EventsConfig | None = None) -> EventProducer:
    """
    Create and start an event producer.

    Args:
        config: Optional configuration. If not provided, will use default config.

    Returns:
        Started EventProducer instance
    """
    if config is None:
        config = EventsConfig()

    producer = EventProducer(config)
    await producer.start()
    return producer

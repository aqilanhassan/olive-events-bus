# Olive Events Bus SDK

A comprehensive enterprise-grade Kafka SDK for the Olive workforce management platform. This SDK provides event-driven architecture capabilities with schema validation, observability, and reliability patterns for microservices communication.

## 🚀 Features

- **Event-Driven Architecture**: Standardized event models with rich metadata
- **Schema Validation**: Built-in JSON schema validation for event data
- **Observability**: Integrated logging, metrics, and distributed tracing
- **Reliability**: Automatic retries, dead letter queues, and error handling
- **Type Safety**: Full TypeScript-style type hints for Python 3.11+
- **Async/Await**: Modern Python async patterns for high performance
- **Enterprise Ready**: Production-grade configuration and monitoring

## 📦 Installation

```bash
pip install olive-events-bus
```

Or with Poetry:

```bash
poetry add olive-events-bus
```

## ⚡ Quick Start

### Basic Event Publishing

```python
import asyncio
from olive_events_bus import EventsConfig, EventProducer, EventType, create_employee_event

async def publish_employee_event():
    config = EventsConfig(
        service_name="my-service",
        service_version="1.0.0",
        bootstrap_servers="localhost:9092"
    )
    
    async with EventProducer(config) as producer:
        event = create_employee_event(
            event_type=EventType.EMPLOYEE_CREATED,
            employee_data={
                "employee_id": "emp_123",
                "email": "john@example.com",
                "first_name": "John",
                "last_name": "Doe",
                "department": "Engineering"
            },
            source_service="hr-service",
            source_version="1.0.0"
        )
        
        await producer.publish("employees.events", event)

asyncio.run(publish_employee_event())
```

### Event Consumption with Handlers

```python
import asyncio
from olive_events_bus import EventsConfig, EventConsumer, EventType, OliveEvent, event_handler

async def consume_events():
    config = EventsConfig(
        service_name="notification-service",
        bootstrap_servers="localhost:9092"
    )
    
    consumer = EventConsumer(
        config=config,
        group_id="notifications",
        topics=["employees.events", "leaves.events"]
    )
    
    @event_handler(EventType.EMPLOYEE_CREATED)
    async def handle_new_employee(event: OliveEvent):
        print(f"Sending welcome email to {event.data['email']}")
        # Your notification logic here
    
    @event_handler(EventType.LEAVE_CREATED) 
    async def handle_leave_request(event: OliveEvent):
        print(f"Processing leave request: {event.data['leave_id']}")
        # Your leave processing logic here
    
    consumer.add_handler(EventType.EMPLOYEE_CREATED, handle_new_employee)
    consumer.add_handler(EventType.LEAVE_CREATED, handle_leave_request)
    
    await consumer.start_consuming()
    # Consumer runs in background
    await asyncio.sleep(60)  # Run for 1 minute
    await consumer.stop()

asyncio.run(consume_events())
```

## 🏗️ Architecture

### Core Components

1. **OliveEvent**: Standardized event structure with metadata
2. **EventProducer**: High-level producer with retry logic and observability
3. **EventConsumer**: Consumer with handler registration and error handling
4. **EventsConfig**: Centralized configuration management
5. **SchemaRegistry**: JSON schema validation for event data

### Event Types

The SDK includes predefined event types for common Olive platform operations:

- **Employee Events**: `EMPLOYEE_CREATED`, `EMPLOYEE_UPDATED`, `EMPLOYEE_DELETED`
- **Leave Events**: `LEAVE_CREATED`, `LEAVE_APPROVED`, `LEAVE_REJECTED`
- **Client Events**: `CLIENT_CREATED`, `CLIENT_UPDATED`, `CLIENT_DELETED`
- **Asset Events**: `ASSET_CREATED`, `ASSET_ASSIGNED`, `ASSET_RETURNED`
- **System Events**: `SYSTEM_HEALTH_CHECK`, `SYSTEM_BACKUP_COMPLETED`
- **Audit Events**: `AUDIT_USER_LOGIN`, `AUDIT_PERMISSION_CHANGE`

## 📋 Configuration

### Environment Variables

```bash
# Kafka Configuration
KAFKA_BOOTSTRAP_SERVERS=localhost:9092
KAFKA_SECURITY_PROTOCOL=PLAINTEXT
KAFKA_SASL_MECHANISM=PLAIN
KAFKA_SASL_USERNAME=your_username
KAFKA_SASL_PASSWORD=your_password

# Service Configuration  
SERVICE_NAME=my-service
SERVICE_VERSION=1.0.0
ENVIRONMENT=production

# Producer Configuration
KAFKA_PRODUCER_ACKS=all
KAFKA_PRODUCER_RETRIES=5
KAFKA_PRODUCER_COMPRESSION=gzip

# Consumer Configuration
KAFKA_CONSUMER_AUTO_OFFSET_RESET=latest
KAFKA_CONSUMER_ENABLE_AUTO_COMMIT=false

# Retry and DLQ Configuration
EVENTS_MAX_RETRIES=3
EVENTS_RETRY_BACKOFF_MS=1000
DLQ_ENABLED=true

# Observability
EVENTS_LOGGING_ENABLED=true
EVENTS_METRICS_ENABLED=true
EVENTS_TRACING_ENABLED=true
```

### Programmatic Configuration

```python
from olive_events_bus import EventsConfig

config = EventsConfig(
    service_name="my-service",
    bootstrap_servers="localhost:9092",
    producer_acks="all",
    consumer_auto_offset_reset="earliest",
    max_retries=5,
    dlq_enabled=True,
    schema_validation_enabled=True
)
```

## 🔍 Schema Validation

The SDK includes built-in schema validation for common event types:

```python
from olive_events_bus import validate_event_data, EventType

# Validate employee data
employee_data = {
    "employee_id": "emp_123",
    "email": "john@example.com", 
    "first_name": "John",
    "last_name": "Doe"
}

try:
    validate_event_data(EventType.EMPLOYEE_CREATED, employee_data)
    print("✅ Data is valid")
except SchemaValidationError as e:
    print(f"❌ Validation failed: {e}")
```

### Custom Schema Registration

```python
from olive_events_bus import get_schema_registry

registry = get_schema_registry()

custom_schema = {
    "type": "object",
    "properties": {
        "custom_field": {"type": "string"},
        "custom_number": {"type": "number", "minimum": 0}
    },
    "required": ["custom_field"]
}

# Register for custom event type
registry.register_schema(EventType.CUSTOM_EVENT, custom_schema)
```

## 📊 Observability

### Structured Logging

The SDK uses structured logging with contextual information:

```python
# Logs include service info, event details, and processing metadata
{
    "timestamp": "2024-01-15T10:30:00Z",
    "level": "INFO", 
    "service": "notification-service",
    "component": "producer",
    "event_type": "employee.created",
    "event_id": "evt_12345",
    "message": "Event published successfully"
}
```

### Metrics and Tracing

When OpenTelemetry is configured:

- **Metrics**: Event publish/consume rates, processing latency, error rates
- **Tracing**: End-to-end event flow with spans for publish/consume operations
- **Attributes**: Event metadata, topic info, processing details

## 🛡️ Error Handling and Reliability

### Automatic Retries

```python
config = EventsConfig(
    max_retries=3,
    retry_backoff_ms=1000,
    retry_max_backoff_ms=32000
)
```

### Dead Letter Queue

Failed events are automatically sent to DLQ topics:

```python
config = EventsConfig(
    dlq_enabled=True,
    dlq_topic_suffix=".dlq"
)
```

### Exception Hierarchy

```python
from olive_events_bus import (
    OliveEventsError,          # Base exception
    ConfigurationError,        # Configuration issues
    ProducerError,            # Producer failures  
    ConsumerError,            # Consumer failures
    SerializationError,       # Event serialization issues
    SchemaValidationError     # Schema validation failures
)
```

## 🧪 Testing

Run the integration tests:

```bash
python test_integration.py
```

View comprehensive examples:

```bash
python examples.py
```

## 🤝 Integration Patterns

### FastAPI Integration

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
from olive_events_bus import EventProducer, EventsConfig

config = EventsConfig(service_name="api-service")
producer = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global producer
    producer = EventProducer(config)
    await producer.start()
    yield
    await producer.stop()

app = FastAPI(lifespan=lifespan)

@app.post("/employees")
async def create_employee(employee_data: dict):
    # Create employee in database
    # ...
    
    # Publish event
    event = create_employee_event(
        EventType.EMPLOYEE_CREATED,
        employee_data,
        "api-service",
        "1.0.0"
    )
    await producer.publish("employees.events", event)
```

### Background Task Integration

```python
import asyncio
from olive_events_bus import EventConsumer

class BackgroundConsumer:
    def __init__(self):
        self.consumer = EventConsumer(
            config=config,
            group_id="background-tasks",
            topics=["system.tasks"]
        )
        self.consumer.add_handler(EventType.TASK_CREATED, self.process_task)
    
    async def start(self):
        await self.consumer.start_consuming()
    
    async def stop(self):
        await self.consumer.stop()
    
    async def process_task(self, event: OliveEvent):
        # Process background task
        pass

# Usage
consumer = BackgroundConsumer()
await consumer.start()
```

## 📚 API Reference

### EventsConfig

Main configuration class with environment variable support.

**Key Parameters:**
- `service_name`: Your service identifier
- `bootstrap_servers`: Kafka broker addresses
- `max_retries`: Maximum retry attempts
- `dlq_enabled`: Enable dead letter queue
- `schema_validation_enabled`: Enable schema validation

### OliveEvent

Core event class with standardized structure.

**Properties:**
- `event_id`: Unique event identifier
- `event_type`: Event type from EventType enum
- `data`: Event payload data
- `metadata`: Event metadata (service, user, tenant info)
- `timestamp`: Event creation timestamp

**Methods:**
- `to_json()`: Serialize to JSON string
- `from_json()`: Deserialize from JSON string
- `with_correlation_id()`: Add correlation ID
- `with_user_context()`: Add user/tenant context
- `add_tag()`: Add metadata tag

### EventProducer

High-level producer for publishing events.

**Methods:**
- `start()`: Initialize producer
- `stop()`: Shutdown producer  
- `publish()`: Publish single event
- `publish_batch()`: Publish multiple events
- `flush()`: Wait for pending messages

### EventConsumer

High-level consumer for processing events.

**Methods:**
- `add_handler()`: Register event handler
- `set_default_handler()`: Set fallback handler
- `start()`: Initialize consumer
- `stop()`: Shutdown consumer
- `start_consuming()`: Start background processing

## 🚢 Deployment

### Docker

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
CMD ["python", "main.py"]
```

### Kubernetes

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: my-service
spec:
  template:
    spec:
      containers:
      - name: app
        image: my-service:latest
        env:
        - name: KAFKA_BOOTSTRAP_SERVERS
          value: "kafka:9092"
        - name: SERVICE_NAME
          value: "my-service"
```

## 🔧 Development

### Setup Development Environment

```bash
git clone https://github.com/olive/olive-events-bus
cd olive-events-bus
poetry install
poetry shell
```

### Run Tests

```bash
poetry run pytest
poetry run python test_integration.py
```

### Code Quality

```bash
poetry run ruff check .
poetry run mypy .
poetry run black .
```

## 📄 License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📞 Support

- **Documentation**: [Full API Documentation](https://docs.olive.com/events-bus)
- **Issues**: [GitHub Issues](https://github.com/olive/olive-events-bus/issues)
- **Discussions**: [GitHub Discussions](https://github.com/olive/olive-events-bus/discussions)
- **Slack**: #events-bus channel in Olive workspace

---

**Built with ❤️ by the Olive Platform Team**

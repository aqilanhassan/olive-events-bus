# Olive Events Bus SDK - Installation and Usage Guide

## 📦 Installing the SDK

### Option 1: Install from Local Build (Recommended for Development)

```bash
# From the olive-events-bus directory
pip install dist/olive_events_bus-1.0.0-py3-none-any.whl

# Or install in development mode
pip install -e .
```

### Option 2: Install from PyPI (When Published)

```bash
pip install olive-events-bus
```

### Option 3: Install from Git Repository

```bash
pip install git+https://github.com/your-org/olive-events-bus.git
```

## 🐳 Docker Integration

### Method 1: Copy Wheel File to Docker

Add to your `Dockerfile`:

```dockerfile
# Copy the SDK wheel file
COPY dist/olive_events_bus-1.0.0-py3-none-any.whl /tmp/

# Install the SDK
RUN pip install /tmp/olive_events_bus-1.0.0-py3-none-any.whl

# Or if you have the source code
COPY olive-events-bus/ /tmp/olive-events-bus/
RUN pip install /tmp/olive-events-bus/
```

### Method 2: Multi-stage Docker Build

```dockerfile
# Build stage
FROM python:3.13-slim as builder
COPY olive-events-bus/ /app/olive-events-bus/
WORKDIR /app/olive-events-bus
RUN pip install build && python -m build

# Runtime stage  
FROM python:3.13-slim
COPY --from=builder /app/olive-events-bus/dist/*.whl /tmp/
RUN pip install /tmp/*.whl
```

## 🏗️ Generated Files

The build process creates:

- `olive_events_bus-1.0.0-py3-none-any.whl` - Wheel distribution (recommended)
- `olive_events_bus-1.0.0.tar.gz` - Source distribution

## 🚀 Next Steps

1. Update your `pyproject.toml` or `requirements.txt`
2. Modify your `Dockerfile` to install the SDK
3. Update your application imports
4. Test the integration

The SDK is now ready to use! 🎉

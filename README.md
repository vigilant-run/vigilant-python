# Vigilant Python SDK

This is the Python SDK for the Vigilant logging platform. It is a wrapper around the [OpenTelemetry](https://opentelemetry.io/) SDK that allows you to easily use the Vigilant logging platform in your Python applications without vendor lock-in.

## Installation

```bash
pip install vigilant-py
```

## Usage

```python
from vigilant import create_logger

# Initialize the logger
logger = create_logger(
    url="log.vigilant.run:4317",
    name="my-service",
    token="your-token",
)

# Basic logging
logger.info("Hello, World!")

# Logging with attributes
logger.info("User logged in", attrs={"user_id": "123", "ip_address": "192.168.1.1"})

# Error logging
try:
    raise ValueError("Something went wrong")
except Exception as e:
    logger.error("Operation failed", error=e)
```

## Log Levels

```python
logger.debug("Debug message")
logger.info("Info message")
logger.warn("Warning message")
logger.error("Error message", error=Exception("Something went wrong"))
```

## Testing

If you want to test the SDK without sending logs to Vigilant, you can use the `create_noop_logger` function.

```python
from vigilant import create_noop_logger

logger = create_noop_logger()
logger.info("This message will not be sent to Vigilant, only printed to stdout")
```

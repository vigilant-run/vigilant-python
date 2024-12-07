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
    name="my-service",      # Your service name
    token="your-token",     # Your Vigilant API token
    url="your-url",         # Your Vigilant endpoint
    passthrough=True        # Optional: Also print to stdout
)

# Basic logging
logger.info("Hello, World!")

# Logging with attributes
logger.info("User logged in", user_id="123", ip_address="192.168.1.1")

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

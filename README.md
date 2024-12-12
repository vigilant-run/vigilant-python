# Vigilant Python SDK

This is the Python SDK for the Vigilant logging platform. It is a wrapper around the [OpenTelemetry](https://opentelemetry.io/) SDK that allows you to easily use the Vigilant logging platform in your Python applications without vendor lock-in.

## Installation

```bash
pip install vigilant-py
```

## Usage (Standard)
The standard logger is a wrapper around the OpenTelemetry logger. It allows you to log messages with attributes and metadata. The logs are sent to Vigilant and viewable in the dashboard.
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

## Usage (Autocapture)
There is an additional logger that captures stdout and stderr and logs it to Vigilant. This is allow you to capture logs without using the logger. There is no metadata or attributes attached to the logs.
```python
from vigilant import create_autocapture_logger

# Initialize the logger
logger = create_autocapture_logger(
    url="log.vigilant.run:4317",
    name="my-service",
    token="your-token",
)

# Enable autocapture
logger.enable()

# Basic logging
logger.info("Hello, World!")

# Capture stdout
print("Hello, World!")

# Error logging
try:
    raise ValueError("Something went wrong")
except Exception as e:
    print("Operation failed", error=e)
```

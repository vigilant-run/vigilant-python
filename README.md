# Vigilant Python SDK

This is the Python SDK for the Vigilant logging platform.

## Installation

```bash
pip install vigilant-py
```

## Logging Usage (Standard)
```python
from vigilant import Logger

# Initialize the logger
logger = Logger(
    name="test-python",
    endpoint="ingress.vigilant.run",
    token="tk_1234567890",
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

# Shutdown the logger
logger.shutdown()
```

## Logging Usage (Autocapture)
```python
from vigilant import Logger

# Initialize the logger
logger = Logger(
    name="test-python",
    endpoint="ingress.vigilant.run",
    token="tk_1234567890",
)

# Enable autocapture
logger.autocapture_enable()

# Capture stdout
print("Hello, World!")

# Error logging
try:
    raise ValueError("Something went wrong")
except Exception as e:
    print("Operation failed", error=e)

# Shutdown the logger
logger.shutdown()
```

## Logging Usage (Attributes)
The attributes are stored in the context of the thread. You can add, remove, and clear attributes in the context. The callbacks can be nested to create a chain of context modifications.

```python
from vigilant import Logger
from vigilant import add_attributes, remove_attributes, clear_attributes

# Create a logger
logger = Logger(
    name="test-python",
    endpoint="ingress.vigilant.run",
    token="tk_1234567890",
)

# Add multiple attributes
add_attributes({"user_id": "1", "another_user_id": "2"}, callback=lambda: {
    # Both attributes present
    print("Testing with two attributes"),
    
    # Remove one attribute
    remove_attributes(["user_id"], callback=lambda: {
        # Only another_user_id remains
        print("Testing with one attribute"),
        
        # Clear all remaining attributes
        clear_attributes(callback=lambda: {
            # No attributes present
            print("Testing without attributes")
        })
    })
})

# Shutdown the logger
logger.shutdown()
```

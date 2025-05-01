# Vigilant Python SDK

This is the Python SDK for the Vigilant logging platform.

## Installation

```bash
pip install vigilant-py
```

## Setup

You setup Vigilant by initializing the library at the start of your application.

```python
import fastapi
from vigilant import init_vigilant, VigilantUserConfig
import uvicorn

init_vigilant(
  user_config=VigilantUserConfig(
    name="backend",
    token="tk_1234567890", # Generate this from the Vigilant dashboard
  )
)

app = fastapi.FastAPI()


@app.get("/")
async def get():
  return {"message": "Hello, World!"}


if __name__ == "__main__":
  uvicorn.run(app, host="0.0.0.0", port=8000)
``` 

## Logs

You can learn more about logging in Vigilant in the [docs](https://docs.vigilant.run/logs).

```python
from vigilant import log_info, log_error, log_warn, log_debug, log_trace

def function():
  # Vigilant will automatically capture print statements as logs
  print("Hello, World!")

  # Logging with a custom message
  log_info("Hello, World!")
  log_error("An error occurred")
  log_warn("A warning occurred")
  log_debug("Some debug information")
  log_trace("A trace occurred")

  # Logging with attributes
  log_info("Hello, World!", {"route": "/"})
  log_error("An error occurred", {"error": "404"})
  log_warn("A warning occurred", {"message": "user not found"})
  log_debug("Some debug information", {"data": "batcher has run 100 times"})
  log_trace("A trace occurred", {"output": "cpu collected"})
```

## Metrics

You can learn more about metrics in Vigilant in the [docs](https://docs.vigilant.run/metrics).

```python
from vigilant import counter, gauge, histogram

def function():
  # Create a counter metric
  counter("user_login_count", 1)

  # Create a counter metric with a tag
  counter("user_login_count", 1, {"route": "/"})

  # Create a gauge metric
  gauge("active_users", 1)

  # Create a gauge metric with a tag
  gauge("active_users", 1, {"route": "/"})

  # Create a histogram metric
  histogram("request_duration", 123.4)

  # Create a histogram metric with a tag
  histogram("request_duration", 123.4, {"route": "/"})
```

# First Steps

This guide will help you get started with FastAPI Maintenance by adding the maintenance mode middleware to your FastAPI application.

## Basic Setup

Here's the simplest way to add maintenance mode to a FastAPI application:

```python
from fastapi import FastAPI
from fastapi_maintenance import MaintenanceModeMiddleware

app = FastAPI()

# Add the middleware to your FastAPI application
app.add_middleware(MaintenanceModeMiddleware)

@app.get("/")
async def root():
    return {"message": "Hello World"}
```

That's it! With just one line, your application now has maintenance mode capabilities.

## How It Works

By default, the middleware checks the `FASTAPI_MAINTENANCE_MODE` environment variable to determine if maintenance mode is active.

- When maintenance mode is not active (default), all requests function normally.
- When maintenance mode is active, all requests receive a 503 Service Unavailable response with a JSON body: `{"detail":"Service temporarily unavailable due to maintenance"}`.

## Activating Maintenance Mode

You can enable maintenance mode in several ways:

### 1. Direct Configuration
Explicitly enable maintenance mode when adding the middleware:
```python
app.add_middleware(MaintenanceModeMiddleware, enable_maintenance=True)
```

When `enable_maintenance` is set to `True` or `False`, it takes precedence over any backend state (including environment variables). This provides a programmatic way to control maintenance mode. However, note that this is part of the "global maintenance mode" check, which comes after other more specific checks in the middleware's decision chain. See [Middleware Precedence](middleware-precedence.md) for more details.

### 2. Environment Variables

To enable maintenance mode, set the `FASTAPI_MAINTENANCE_MODE` environment variable before starting your application:

```bash
# Enable maintenance mode
export FASTAPI_MAINTENANCE_MODE=1  # or "yes", "true", "on"

# Start your application
uvicorn app:app
```

To disable maintenance mode:

```bash
# Disable maintenance mode
export FASTAPI_MAINTENANCE_MODE=0  # or "no", "false", "off"

# Start your application
uvicorn app:app
```

### Testing Maintenance Mode

When maintenance mode is active, all endpoints return a 503 response:

```bash
# Make a request to your API
curl -i http://localhost:8000/

# Response (when maintenance mode is active):
# HTTP/1.1 503 Service Unavailable
# content-type: application/json
# retry-after: 3600
# ...
#
# {"detail":"Service temporarily unavailable due to maintenance"}
```

## Next Steps

While the basic setup is easy, FastAPI Maintenance offers many more features:

- Using [storage backends](./backends.md) for maintenance state
- Creating [custom backends](./custom-backends.md) for specialized storage
- Applying [route decorators](./decorators.md) for path-specific settings
- Using [context manager](./context-manager.md) for temporary maintenance
- Understanding [middleware precedence](./middleware-precedence.md) rules
- Implementing [custom exemptions](./custom-exemptions.md) for specific requests
- Creating [custom responses](./custom-responses.md) during maintenance
- Using [command line interface (CLI)](./cli.md) for managing maintenance mode
- Exploring [advanced usage](./advanced-usage.md) patterns

In the next sections, we'll explore each of these features in detail.

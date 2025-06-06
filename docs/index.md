<p align="center">
  <a href="https://msamsami.github.io/fastapi-maintenance">
    <img src="https://raw.githubusercontent.com/msamsami/fastapi-maintenance/main/docs/img/header.svg" alt="FastAPI Maintenance">
  </a>
</p>
<p align="center">
    <em>Flexible maintenance mode middleware for FastAPI applications.</em>
</p>

<p align="center">
  <a href="https://pypi.org/project/fastapi-maintenance/">
    <img src="https://img.shields.io/pypi/v/fastapi-maintenance?color=orange&label=pypi" alt="Package version">
  </a>
  <a href="https://pypi.org/project/fastapi-maintenance/">
    <img src="https://img.shields.io/badge/python-3.8%20%7C%203.9%20%7C%203.10%20%7C%203.11%20%7C%203.12%20%7C%203.13-blue" alt="Supported Python versions">
  </a>
  <a href="https://github.com/msamsami/fastapi-maintenance/actions?query=workflow%3ATest+event%3Apush+branch%3Amain" target="_blank">
    <img src="https://github.com/msamsami/fastapi-maintenance/actions/workflows/ci.yml/badge.svg?event=push&branch=main" alt="Test">
  </a>
  <a href="https://codecov.io/gh/msamsami/fastapi-maintenance" >
    <img src="https://codecov.io/gh/msamsami/fastapi-maintenance/graph/badge.svg?token=OO3XDXYCBW" alt="Coverage"/>
  </a>
  <a href="https://github.com/msamsami/fastapi-maintenance/blob/main/LICENSE">
    <img src="https://img.shields.io/github/license/msamsami/fastapi-maintenance?color=%2334D058" alt="License">
  </a>
</p>

---

**Documentation**: <a href="https://msamsami.github.io/fastapi-maintenance" target="_blank">https://msamsami.github.io/fastapi-maintenance</a>

**Source Code**: <a href="https://github.com/msamsami/fastapi-maintenance" target="_blank">https://github.com/msamsami/fastapi-maintenance</a>

---

**FastAPI Maintenance** is a lightweight middleware for [FastAPI](https://fastapi.tiangolo.com/) applications that provides a flexible way to handle **maintenance mode**.

The package provides a simple yet powerful solution to temporarily disable your API endpoints during **application maintenance states**. It ensures a smooth experience for API consumers through customizable responses and fine-grained control over which routes remain accessible. The package is designed to be easy to integrate, highly customizable, and extensible to fit various use cases.

!!! warning "Experimental Status"
    FastAPI Maintenance is currently in experimental status. Although it's actively developed and tested, the API may undergo changes between releases. Be cautious when upgrading in production environments and always review the changelog carefully.

## Features

- ⚙️ **Simple to use**: Add just a few lines of code to enable maintenance mode.
- 🔌 **Flexible state management**: Manage maintenance mode via environment variables, local files, or create your own custom backend.
- 🚦 **Per-route control**: Force maintenance mode ON/OFF for specific routes.
- 🎨 **Customizable responses**: Define your own maintenance page or custom JSON responses.
- ⏱️ **Context manager**: Temporarily enable maintenance mode for critical operations.
- 🧩 **Extensible**: Easy to extend with custom backends, handlers, and exemptions.

## Install

```bash
pip install fastapi-maintenance
```

## Quick Start

### Middleware

Add the maintenance mode middleware to your FastAPI application:

```python
from fastapi import FastAPI
from fastapi_maintenance import MaintenanceModeMiddleware

app = FastAPI()

# Add the middleware to your FastAPI application
app.add_middleware(MaintenanceModeMiddleware)

@app.get("/")
def root():
    return {"message": "Hello World"}
```

When maintenance mode is not active, endpoints function normally.

### Enabling Maintenance Mode

You can enable maintenance mode in several ways:

#### 1. Direct Configuration
Explicitly enable maintenance mode when adding the middleware:
```python
app.add_middleware(MaintenanceModeMiddleware, enable_maintenance=True)
```

#### 2. Environment Variables
Set the `FASTAPI_MAINTENANCE_MODE` environment variable before starting your application:
```bash
export FASTAPI_MAINTENANCE_MODE=1
uvicorn main:app
```

### Maintenance Response

When maintenance mode is active, all endpoints (unless explicitly exempted) will return a `503 Service Unavailable` response:
```json
{"detail":"Service temporarily unavailable due to maintenance"}
```

## Decorators

You can control maintenance mode behavior for specific routes using decorators:

```python
from fastapi import FastAPI
from fastapi_maintenance import (
    MaintenanceModeMiddleware,
    force_maintenance_mode_off,
    force_maintenance_mode_on,
)

app = FastAPI()
app.add_middleware(MaintenanceModeMiddleware)

# Always accessible, even during maintenance
@app.get("/status")
@force_maintenance_mode_off
def status():
    return {"status": "operational"}

# Always returns maintenance response
@app.get("/deprecated")
@force_maintenance_mode_on
async def deprecated_endpoint():
    return {"message": "This endpoint is deprecated"}
```

The `force_maintenance_mode_off` decorator keeps an endpoint accessible even when maintenance mode is enabled globally. Conversely, the `force_maintenance_mode_on` decorator forces an endpoint to always return the maintenance response, regardless of the global maintenance state.

## Context Manager

You can use context managers to temporarily enforce the maintenance state for specific operations:

```python
from fastapi import FastAPI
from fastapi_maintenance import (
    MaintenanceModeMiddleware,
    maintenance_mode_off,
    maintenance_mode_on,
)

app = FastAPI()
app.add_middleware(MaintenanceModeMiddleware)

@app.post("/sync")
async def sync_data():
    # Enable maintenance mode during data sync
    async with maintenance_mode_on():
        # Data sync logic here
        await perform_sync()

    # Maintenance mode is automatically disabled after the block
    return {"status": "completed"}

@app.get("/health")
def health_check():
    return {"status": "healthy"}
```

The `maintenance_mode_on` context manager temporarily enables maintenance mode for critical operations.

## License

This project is licensed under the terms of the [MIT license](https://github.com/msamsami/fastapi-maintenance/blob/main/LICENSE).

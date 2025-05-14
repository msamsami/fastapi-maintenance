<p align="center">
  <img src="https://raw.githubusercontent.com/msamsami/fastapi-maintenance/main/docs/img/logo-type.svg" alt="FastAPI Maintenance">
</p>
<p align="center">
    <em>Flexible maintenance mode middleware for FastAPI applications.</em>
</p>

<p align="center">
  <!-- <a href="https://pypi.org/project/fastapi-maintenance/">
    <img src="https://img.shields.io/pypi/v/fastapi-maintenance?color=%2334D058&label=pypi%20package" alt="Package version">
  </a> -->
  <a href="https://pypi.org/project/fastapi-maintenance/">
    <img src="https://img.shields.io/badge/python-3.8%20%7C%203.9%20%7C%203.10%20%7C%203.11%20%7C%203.12%20%7C%203.13-blue" alt="Supported Python versions">
  </a>
  <a href="https://coverage-badge.samuelcolvin.workers.dev/redirect/msamsami/fastapi-maintenance" target="_blank">
    <img src="https://coverage-badge.samuelcolvin.workers.dev/msamsami/fastapi-maintenance.svg" alt="Coverage">
  <a href="https://github.com/msamsami/fastapi-maintenance/blob/main/LICENSE">
    <img src="https://img.shields.io/github/license/msamsami/fastapi-maintenance?color=%2334D058" alt="License">
  </a>
</p>

---

**Documentation**: TBA
<!-- <a href="https://msamsami.github.io/fastapi-maintenance" target="_blank">https://msamsami.github.io/fastapi-maintenance</a> -->

**Source Code**: <a href="https://github.com/msamsami/fastapi-maintenance" target="_blank">https://github.com/msamsami/fastapi-maintenance</a>

---

**FastAPI Maintenance** is a lightweight middleware for [FastAPI](https://fastapi.tiangolo.com/) applications that provides a flexible way to handle **maintenance mode**.

The package offers a simple yet powerful solution to temporarily disable your API endpoints during maintenance windows, deployments, or system updates. It's designed to be easy to integrate, highly customizable, and extensible to fit various use cases.

The main goal of **FastAPI Maintenance** is to provide a developer-friendly way to manage **application maintenance states** while ensuring a smooth experience for API consumers through customizable responses and fine-grained control over which routes remain accessible.

The key features are:

* ⚡ **Simple to use**: Add just a few lines of code to enable maintenance mode.
* 🔌 **Pluggable storage backends**: Choose between environment variables, local files, or create your own.
* 🛠️ **Per-route control**: Force maintenance mode on/off for specific routes.
* 🎨 **Customizable responses**: Define your own maintenance page or custom JSON responses.
* 🔄 **Context managers**: Temporarily enable/disable maintenance mode for specific operations.
* 🧩 **Extensible**: Easy to extend with custom backends and callbacks.

## Installation

```bash
pip install fastapi-maintenance
```

## Quick Start

Add the maintenance mode middleware to your FastAPI application:

```python
from fastapi import FastAPI
from fastapi_maintenance import MaintenanceModeMiddleware

app = FastAPI()

app.add_middleware(MaintenanceModeMiddleware)

@app.get("/")
async def root():
    return {"message": "Hello World"}
```

By default, the middleware checks the `FASTAPI_MAINTENANCE_MODE` environment variable to see if maintenance mode is active. If it is not, the root endpoint will proceed to return its response:
```json
{"message":"Hello World"}
```

Set the environment variable before starting your application to activate the maintenance mode:
```bash
export FASTAPI_MAINTENANCE_MODE=1
uvicorn main:app
```

Now, the root endpoint will return a 503 Service Unavailable response with this error message:
```json
{"detail":"Service temporarily unavailable due to maintenance"}
```

## Using API Controls

Create endpoints to toggle maintenance mode:

```python
from fastapi import FastAPI
from fastapi_maintenance import (
    MaintenanceModeMiddleware,
    force_maintenance_mode_off,
    set_maintenance_mode,
)
from fastapi_maintenance.backends import LocalFileBackend

app = FastAPI()

app.add_middleware(
    MaintenanceModeMiddleware,
    backend=LocalFileBackend(file_path="maintenance_mode.txt"),
)

@app.get("/")
async def root():
    return {"message": "Hello World"}

@app.post("/admin/maintenance/enable")
@force_maintenance_mode_off  # This endpoint is always accessible
async def enable_maintenance():
    await set_maintenance_mode(True)
    return {"maintenance_mode": True}

@app.post("/admin/maintenance/disable")
@force_maintenance_mode_off  # This endpoint is always accessible
async def disable_maintenance():
    await set_maintenance_mode(False)
    return {"maintenance_mode": False}
```

## Exempting Routes

You can exempt specific routes from maintenance mode:

### Using Decorators

```python
from fastapi import FastAPI
from fastapi_maintenance import MaintenanceModeMiddleware, force_maintenance_mode_off

app = FastAPI()
app.add_middleware(MaintenanceModeMiddleware)

@app.get("/status")
@force_maintenance_mode_off
async def status():
    return {"status": "operational"}
```

### Using Callbacks

You can also use custom callback functions to determine which routes should be exempt:

```python
from fastapi import Request

def is_exempt(request: Request) -> bool:
    # Exempt health check endpoints
    if request.url.path.startswith("/health"):
        return True
    # Exempt requests with special header
    if request.headers.get("X-Admin-Key") == "secret-key":
        return True
    return False

app.add_middleware(
    MaintenanceModeMiddleware,
    exempt_callback=is_exempt
)
```

## Customizing Responses

You can customize the maintenance mode response:

```python
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi_maintenance import MaintenanceModeMiddleware

app = FastAPI()

async def custom_response(request: Request):
    html_content = """
    <html>
        <head>
            <title>Maintenance Mode</title>
        </head>
        <body>
            <h1>Under Maintenance</h1>
            <p>We'll be back shortly!</p>
        </body>
    </html>
    """
    return HTMLResponse(content=html_content, status_code=503)

app.add_middleware(
    MaintenanceModeMiddleware,
    response_callback=custom_response
)
```

## Context Managers for Temporary Maintenance

You can use context managers to temporarily enable/disable maintenance mode:

```python
from fastapi import FastAPI
from fastapi_maintenance import (
    MaintenanceModeMiddleware,
    maintenance_mode_on,
    maintenance_mode_off,
)

app = FastAPI()
app.add_middleware(MaintenanceModeMiddleware)

@app.post("/start-deployment")
async def start_deployment():
    # Enable maintenance mode during deployment
    async with maintenance_mode_on():
        # Deployment logic here
        await perform_deployment()

    return {"status": "deployed"}

@app.get("/check-database")
async def check_database():
    # Ensure API is accessible during database check
    async with maintenance_mode_off():
        # Database check logic
        await check_database_health()

    return {"database": "healthy"}
```

## License

This project is licensed under the terms of the MIT license.

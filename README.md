<p align="center">
  <img src="https://raw.githubusercontent.com/msamsami/fastapi-maintenance/main/docs/img/header.svg" alt="FastAPI Maintenance">
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
  <a href="https://codecov.io/gh/msamsami/fastapi-maintenance" >
    <img src="https://codecov.io/gh/msamsami/fastapi-maintenance/graph/badge.svg?token=OO3XDXYCBW" alt="Coverage"/>
  </a>
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

- **Simple to use**: Add just a few lines of code to enable maintenance mode.
- **Pluggable storage backends**: Choose between environment variables, local files, or create your own.
- **Per-route control**: Force maintenance mode on/off for specific routes.
- **Customizable responses**: Define your own maintenance page or custom JSON responses.
- **Context managers**: Temporarily enable/disable maintenance mode for specific operations.
- **Extensible**: Easy to extend with custom backends and callbacks.

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

By default, the middleware checks the `FASTAPI_MAINTENANCE_MODE` environment variable to see if maintenance mode is active. If it's not, the root endpoint will proceed to return its response:
```json
{"message":"Hello World"}
```

Set the environment variable before starting your application to activate the maintenance mode:
```bash
export FASTAPI_MAINTENANCE_MODE=1
uvicorn main:app
```

Now, the root endpoint will return a `503 Service Unavailable` response with this error message:
```json
{"detail":"Service temporarily unavailable due to maintenance"}
```

## Decorators

You can control maintenance mode behavior for specific routes using decorators:

```python
from fastapi import FastAPI
from fastapi_maintenance import MaintenanceModeMiddleware, force_maintenance_mode_off, force_maintenance_mode_on

app = FastAPI()
app.add_middleware(MaintenanceModeMiddleware)

@app.get("/status")
@force_maintenance_mode_off
async def status():
    return {"status": "operational"}  # Always accessible, even during maintenance

@app.get("/deprecated")
@force_maintenance_mode_on
async def deprecated_endpoint():
    return {"message": "This endpoint is deprecated"}  # Always returns maintenance response
```

The `force_maintenance_mode_off` decorator keeps an endpoint accessible even when maintenance mode is enabled globally. Conversely, the `force_maintenance_mode_on` decorator forces an endpoint to always return the maintenance response, regardless of the global maintenance state.

## Context Managers

You can use context managers to temporarily change the maintenance state for specific operations:

```python
from fastapi import FastAPI
from fastapi_maintenance import MaintenanceModeMiddleware, maintenance_mode_on, maintenance_mode_off

app = FastAPI()
app.add_middleware(MaintenanceModeMiddleware)

@app.post("/deploy")
async def deploy():
    # Enable maintenance mode during deployment
    async with maintenance_mode_on():
        # Deployment logic here
        await perform_deployment()

    # Maintenance mode is automatically disabled after the block
    return {"status": "deployed"}

@app.get("/health")
async def health_check():
    # Ensure API is accessible during health check
    async with maintenance_mode_off():
        # Health check logic
        status = await check_system_health()

    return {"health": status}
```

The `maintenance_mode_on` context manager temporarily enables maintenance mode for critical operations, while `maintenance_mode_off` ensures endpoints remain accessible even if maintenance mode is active globally.

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

## License

This project is licensed under the terms of the MIT license.

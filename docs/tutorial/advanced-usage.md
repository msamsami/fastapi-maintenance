# Advanced Usage

This section covers advanced usage patterns and integration scenarios for the FastAPI Maintenance package. These advanced usage patterns demonstrate how FastAPI Maintenance can be integrated into complex systems and workflows.

## Combining Multiple Features

You can combine various features of FastAPI Maintenance for sophisticated maintenance scenarios:

```python
from fastapi import FastAPI, Request, Depends
from fastapi.responses import JSONResponse
from fastapi_maintenance import (
    MaintenanceModeMiddleware,
    configure_backend,
    force_maintenance_mode_off,
    maintenance_mode_on
)

# Configure a writable backend
configure_backend("file", file_path="maintenance_mode.txt")

app = FastAPI()

# Custom response handler
async def custom_response(request: Request) -> JSONResponse:
    return JSONResponse(
        content={
            "status": "maintenance",
            "message": "We're upgrading our systems. Please try again later.",
            "estimated_completion": "30 minutes"
        },
        status_code=503,
        headers={"Retry-After": "1800"}
    )

# Custom exemption handler
def is_exempt(request: Request) -> bool:
    # Allow monitoring tools
    if request.headers.get("User-Agent", "").startswith("Monitoring"):
        return True
    return False

# Add middleware with custom handlers
app.add_middleware(
    MaintenanceModeMiddleware,
    response_handler=custom_response,
    exempt_handler=is_exempt
)

# Admin API with decorator-based exemption
@app.post("/admin/maintenance/update")
@force_maintenance_mode_off
async def update_system():
    async with maintenance_mode_on():
        # Perform system update
        await perform_update()
    return {"status": "updated"}
```

## Application Startup and Shutdown

You can use FastAPI's events to configure maintenance mode during application startup and shutdown:

```python
from fastapi import FastAPI
from fastapi_maintenance import (
    MaintenanceModeMiddleware,
    configure_backend,
    set_maintenance_mode
)

# Configure backend
configure_backend("file", file_path="maintenance_mode.txt")

app = FastAPI()
app.add_middleware(MaintenanceModeMiddleware)

@app.on_event("startup")
async def startup_event():
    # Clear any maintenance mode from previous crashes on startup
    await set_maintenance_mode(False)

@app.on_event("shutdown")
async def shutdown_event():
    # Enable maintenance mode during shutdown
    await set_maintenance_mode(True)
```

## Integration with Other Middleware

When using FastAPI Maintenance with other middleware, pay attention to the order:

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi_maintenance import MaintenanceModeMiddleware

app = FastAPI()

# Add middleware in the desired order (executed from bottom to top)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(MaintenanceModeMiddleware)

# Other middleware
# ...
```

Here, the maintenance middleware will be executed before the CORS middleware, which means maintenance responses will still have proper CORS headers.

## Dependency Injection with Maintenance Status

You can create a dependency that checks the maintenance status:

```python
from fastapi import FastAPI, Depends, HTTPException
from fastapi_maintenance import (
    MaintenanceModeMiddleware,
    get_maintenance_mode,
    configure_backend
)

configure_backend("file", file_path="maintenance_mode.txt")

app = FastAPI()
app.add_middleware(MaintenanceModeMiddleware)

async def maintenance_status():
    return await get_maintenance_mode()

async def require_maintenance_off():
    if await get_maintenance_mode():
        raise HTTPException(status_code=503, detail="Service is in maintenance mode")
    return False

@app.get("/status")
async def status(is_maintenance: bool = Depends(maintenance_status)):
    return {"maintenance_mode": is_maintenance}

@app.post("/api/important")
async def important_action(_: bool = Depends(require_maintenance_off)):
    return {"message": "Important action completed"}
```

## Custom Backends with External Services

You can create a custom backend that integrates with external services:

```python
from typing import Optional
import aiohttp
from fastapi_maintenance.backends import BaseStateBackend

class APIBackend(BaseStateBackend):
    """
    Store maintenance mode state in an external API.
    """

    def __init__(self, api_url: str, api_key: Optional[str] = None) -> None:
        self.api_url = api_url
        self._headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}

    async def get_value(self) -> bool:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{self.api_url}/maintenance", headers=self._headers) as response:
                if response.status == 200:
                    data = await response.json()
                    return self._str_to_bool(str(data.get("active", False)))
                return False

    async def set_value(self, value: bool) -> None:
        async with aiohttp.ClientSession() as session:
            await session.post(
                f"{self.api_url}/maintenance",
                json={"active": value},
                headers=self._headers
            )
```

## Monitoring Maintenance Status

You can expose an endpoint to monitor the current maintenance status:

```python
from fastapi import FastAPI
from fastapi_maintenance import (
    MaintenanceModeMiddleware,
    get_maintenance_mode,
    force_maintenance_mode_off
)

app = FastAPI()
app.add_middleware(MaintenanceModeMiddleware)

@app.get("/api/status", tags=["monitoring"])
@force_maintenance_mode_off
async def get_status():
    is_maintenance = await get_maintenance_mode()

    if is_maintenance:
        return {
            "status": "maintenance",
            "message": "System is undergoing maintenance"
        }
    else:
        return {
            "status": "operational",
            "message": "All systems operational"
        }
```

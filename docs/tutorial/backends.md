# Backend Options

FastAPI Maintenance provides flexible backend storage options for managing the maintenance mode state. This allows you to store the maintenance mode state in different ways depending on your application's needs.

## Available Backends

The package currently includes two built-in backend options:

1. **Environment Variable Backend** (default): Uses environment variables to store the maintenance mode state
2. **Local File Backend**: Uses a local file to store the maintenance mode state

## Environment Variable Backend

This is the default backend. It reads the maintenance mode state from an environment variable.

### Configuration

```python
from fastapi import FastAPI
from fastapi_maintenance import MaintenanceModeMiddleware
from fastapi_maintenance.backends import EnvVarBackend

app = FastAPI()

# Use with default environment variable name (FASTAPI_MAINTENANCE_MODE)
app.add_middleware(
    MaintenanceModeMiddleware,
    backend=EnvVarBackend()
)

# Or specify a custom environment variable name
app.add_middleware(
    MaintenanceModeMiddleware,
    backend=EnvVarBackend(var_name="MY_CUSTOM_MAINTENANCE_FLAG")
)
```

### Limitations

The environment variable backend is **read-only** at runtime. This means:

- You can only set the maintenance mode state *before* starting your application.
- Direct calls to `set_maintenance_mode()` will log a warning and have no effect.
- However, context manager `maintenance_mode_on()` **will work as expected for the duration of the context block**. They achieve this by using a temporary, in-memory override of the maintenance state. The actual environment variable is not changed. This allows you to temporarily simulate maintenance mode changes even with the environment variable backend.

Use this backend when you primarily manage maintenance mode state externally (e.g., via deployment scripts or orchestration tools) but still want the flexibility of temporary overrides within your code using context managers.

## Local File Backend

The file backend stores the maintenance mode state in a local file. This allows the state to be changed at runtime.

### Configuration

```python
from fastapi import FastAPI
from fastapi_maintenance import MaintenanceModeMiddleware
from fastapi_maintenance.backends import LocalFileBackend

app = FastAPI()

# Specify a file path to store the maintenance mode state
app.add_middleware(
    MaintenanceModeMiddleware,
    backend=LocalFileBackend(file_path="maintenance_mode.txt")
)
```

### Benefits

The local file backend provides:

- Ability to change maintenance mode state at runtime
- Persistence across application restarts
- Support for context managers and API-based control

## Configuring Backends

You can also use the `configure_backend` function to set up the default backend:

```python
from fastapi import FastAPI
from fastapi_maintenance import MaintenanceModeMiddleware, configure_backend

# Configure the default backend
configure_backend("file", file_path="maintenance_mode.txt")

app = FastAPI()

# This will use the configured default backend
app.add_middleware(MaintenanceModeMiddleware)
```

## API-Based Control

With writable backends (like the file backend), you can create endpoints to control maintenance mode:

```python
from fastapi import FastAPI
from fastapi_maintenance import (
    MaintenanceModeMiddleware,
    set_maintenance_mode,
    get_maintenance_mode,
    force_maintenance_mode_off
)
from fastapi_maintenance.backends import LocalFileBackend

app = FastAPI()
app.add_middleware(
    MaintenanceModeMiddleware,
    backend=LocalFileBackend(file_path="maintenance_mode.txt")
)

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

@app.get("/admin/maintenance/status")
@force_maintenance_mode_off  # This endpoint is always accessible
async def get_maintenance_status():
    is_active = await get_maintenance_mode()
    return {"maintenance_mode": is_active}
```

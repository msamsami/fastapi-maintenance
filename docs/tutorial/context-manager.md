# Context Manager

FastAPI Maintenance provides an async context manager that temporarily enables maintenance mode and automatically restores the previous state when done. This approach is ideal for critical tasks where you need temporary downtime without manually toggling maintenance settings, such as:

- Database migrations
- Application deployments
- Data imports or exports
- Content synchronization and updates
- System updates
- User permission and role updates
- Rolling out new features
- Temporarily disabling services during critical operations

## Basic Usage

The `maintenance_mode_on` context manager temporarily enables maintenance mode and automatically restores the previous state when exiting the context:

```python
from fastapi import FastAPI
from fastapi_maintenance import MaintenanceModeMiddleware, maintenance_mode_on

app = FastAPI()
app.add_middleware(MaintenanceModeMiddleware)

@app.post("/admin/sync")
async def sync_data():
    # Temporarily enable maintenance mode during data sync
    async with maintenance_mode_on():
        # Data sync logic here
        await perform_sync()
        # When this block finishes, maintenance mode is automatically disabled

    return {"status": "completed"}
```

## How It Works With Different Backends

The context manager works with all backend types, but behaves differently depending on the backend's characteristics:

### Local File Backend

When using a writable backend like `LocalFileBackend`, the context manager:
1. Reads the current maintenance state
2. Sets maintenance mode to ON
3. Executes your code within the context
4. Restores the original state when exiting

```python
from fastapi import FastAPI
from fastapi_maintenance import MaintenanceModeMiddleware, maintenance_mode_on
from fastapi_maintenance.backends import LocalFileBackend

app = FastAPI()
app.add_middleware(
    MaintenanceModeMiddleware,
    backend=LocalFileBackend(file_path="maintenance_mode.txt"),
)

@app.post("/admin/run-migration")
async def run_migration():
    async with maintenance_mode_on():
        # The maintenance_mode.txt file is updated to enable maintenance
        await perform_database_migration()
        # When done, the file is restored to its original state

    return {"migration": "completed"}
```

### Environment Variable Backend

When using the default environment variable backend (which is read-only), the context manager:
1. Creates a temporary in-memory override to enable maintenance mode
2. Executes your code within the context
3. Removes the override when exiting

```python
from fastapi import FastAPI
from fastapi_maintenance import MaintenanceModeMiddleware, maintenance_mode_on

# Using default environment variable backend
app = FastAPI()
app.add_middleware(MaintenanceModeMiddleware)

@app.post("/admin/update")
async def update_system():
    # Even though environment variables can't be changed at runtime,
    # this still works using an in-memory override
    async with maintenance_mode_on():
        # System enters maintenance mode
        await perform_update()
        # Maintenance mode is disabled when the context exits

    return {"update": "completed"}
```

**Note**: The environment variable itself is never modified, but the maintenance mode is still effectively enabled for the duration of the context block.

## Using With Custom Backend

You can also specify a custom backend when using the context manager:

```python
from fastapi_maintenance import maintenance_mode_on
from fastapi_maintenance.backends import LocalFileBackend

# Create a specific backend instance
custom_backend = LocalFileBackend(file_path="/path/to/custom_file.txt")

async def custom_maintenance_operation():
    # Use the specific backend with the context manager
    async with maintenance_mode_on(backend=custom_backend):
        # This only affects the custom_backend, not the globally configured one
        await perform_maintenance_tasks()
```

## Nesting Context Managers

You can nest the `maintenance_mode_on` context manager. When nesting, the innermost context will maintain the state established by the outer context:

```python
async def complex_operation():
    # Start with maintenance OFF
    assert not await get_maintenance_mode()

    async with maintenance_mode_on():
        # Now maintenance is ON
        assert await get_maintenance_mode()

        # Nested context - maintenance stays ON
        async with maintenance_mode_on():
            # Still ON
            assert await get_maintenance_mode()
            await perform_nested_task()

        # After inner context - still ON
        assert await get_maintenance_mode()

    # After outer context - back to OFF
    assert not await get_maintenance_mode()
```

The maintenance state will only be restored to its original value when all nested contexts are exited.

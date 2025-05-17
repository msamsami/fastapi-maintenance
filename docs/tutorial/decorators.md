# Route Decorators

FastAPI Maintenance provides decorators that allow you to control the maintenance mode behavior on a per-route basis. These decorators let you specify which endpoints should always be available even during maintenance or which should always be in maintenance mode.

## Available Decorators

The package includes two decorators:

1. `force_maintenance_mode_off`: Ensures an endpoint is always accessible, even when maintenance mode is active
2. `force_maintenance_mode_on`: Forces an endpoint to always return the maintenance response, regardless of the global maintenance status

## Exempting Routes from Maintenance Mode

The `force_maintenance_mode_off` decorator is useful for:

- Health check endpoints that monitoring systems rely on
- Status endpoints that report the system's maintenance state
- Admin endpoints that control the maintenance mode itself

### Example Usage

```python
from fastapi import FastAPI
from fastapi_maintenance import MaintenanceModeMiddleware, force_maintenance_mode_off

app = FastAPI()
app.add_middleware(MaintenanceModeMiddleware)

# This endpoint will always be accessible
@app.get("/health")
@force_maintenance_mode_off
async def health_check():
    return {"status": "healthy"}

# This endpoint will be affected by maintenance mode
@app.get("/users")
async def get_users():
    return {"users": ["user1", "user2"]}
```

In this example, even when maintenance mode is active, the `/health` endpoint will continue to function normally, while the `/users` endpoint will return the maintenance response.

## Forcing Maintenance Mode for Specific Routes

The `force_maintenance_mode_on` decorator is useful for:

- Endpoints that are undergoing specific maintenance
- Features that are temporarily disabled
- Routes you want to include in a staged rollout

### Example Usage

```python
from fastapi import FastAPI
from fastapi_maintenance import MaintenanceModeMiddleware, force_maintenance_mode_on

app = FastAPI()
app.add_middleware(MaintenanceModeMiddleware)

# This endpoint will always return the maintenance response
@app.get("/beta-feature")
@force_maintenance_mode_on
async def beta_feature():
    # This code will never execute when the decorator is present
    return {"feature": "beta content"}

# This endpoint will function normally (unless global maintenance is active)
@app.get("/stable-feature")
async def stable_feature():
    return {"feature": "stable content"}
```

In this example, the `/beta-feature` endpoint will always return the maintenance response, regardless of the global maintenance mode state.

## Using with Dependency Injection

The decorators work well with FastAPI's dependency injection system:

```python
from fastapi import FastAPI, Depends
from fastapi_maintenance import MaintenanceModeMiddleware, force_maintenance_mode_off

def common_parameters():
    return {"param": "value"}

app = FastAPI()
app.add_middleware(MaintenanceModeMiddleware)

@app.get("/api/admin")
@force_maintenance_mode_off
async def admin_endpoint(commons: dict = Depends(common_parameters)):
    return {"admin": True, **commons}
```

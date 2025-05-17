# Custom Backends

FastAPI Maintenance allows you to create custom backends for storing maintenance mode state. This is useful when you need to integrate with your existing infrastructure or want to use a different storage system than the default environment variable backend or local file backend.

## Creating a Custom Backend

You can create custom backends by extending the `BaseStateBackend` class. Here's an example of a Redis backend:

```python
from fastapi_maintenance.backends import BaseStateBackend
from redis.asyncio import Redis

class RedisBackend(BaseStateBackend):
    """
    Store maintenance mode state in Redis.
    """

    def __init__(self, client: Redis, key: str = "fastapi_maintenance_mode"):
        self.client = client
        self.key = key

    async def get_value(self) -> bool:
        value = await self.client.get(self.key)
        if value is None:
            return False
        return self._str_to_bool(value.decode("utf-8"))

    async def set_value(self, value: bool) -> None:
        value_str = self._bool_to_str(value)
        await self.client.set(self.key, value_str)
```

Your custom backend can use any storage system as long as it implements the `get_value` and `set_value` methods. The `BaseStateBackend` class provides helper methods like `_str_to_bool` and `_bool_to_str` to handle common conversions.

## Using Your Custom Backend

To use your custom backend, pass it to the middleware when initializing your FastAPI application:

```python
from fastapi import FastAPI
from fastapi_maintenance import MaintenanceModeMiddleware
from redis.asyncio import Redis

# Initialize your storage client
redis_client = Redis(host="localhost", port=6379, db=0)

# Create your custom backend
redis_backend = RedisBackend(redis_client)

app = FastAPI()

# Add the middleware with your custom backend
app.add_middleware(MaintenanceModeMiddleware, backend=redis_backend)
```

## Backend Requirements

Your custom backend must implement two required methods:

1. `get_value() -> bool`: Returns the current maintenance mode state
    - Should return `True` if maintenance mode is active
    - Should return `False` if maintenance mode is inactive
    - Should handle any storage-specific errors gracefully

2. `set_value(value: bool) -> None`: Sets the maintenance mode state
    - Takes a boolean value indicating the desired maintenance state
    - Should persist the value to your storage system
    - Should handle any storage-specific errors gracefully

The backend should be designed to be thread-safe and handle concurrent access appropriately, especially in production environments.

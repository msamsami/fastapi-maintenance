# Custom Exemptions

While decorators provide a simple way to exempt specific routes from maintenance mode, more complex scenarios often require custom exemption logic. The `exempt_handler` parameter of the middleware allows you to implement custom rules that can consider any aspect of the incoming request.

<details open>
<summary>Docs Bypass Maintenance</summary>

By default, FastAPI's built-in documentation endpoints (<code>/docs</code>, <code>/redoc</code>, <code>/openapi.json</code>, <code>/docs/oauth2-redirect</code>) are automatically exempted from maintenance mode to keep API documentation accessible. This built-in behavior works alongside any custom exemption handler you define.

</details>

<details open>
<summary>HTTP Error Behavior</summary>

The middleware automatically exempts requests that would result in HTTP errors (e.g., <code>404 Not Found</code>, <code>405 Method Not Allowed</code>, etc.) from maintenance mode. This ensures that when clients make requests to non-existent paths or use wrong HTTP methods, they receive the proper error response instead of a maintenance response.

</details>

## Basic Usage

Here's a simple example that exempts health check endpoints and requests with an admin key from maintenance mode:

```python
from fastapi import FastAPI, Request
from fastapi_maintenance import MaintenanceModeMiddleware

def is_exempt(request: Request) -> bool:
    # Exempt all paths starting with "/health"
    if request.url.path.startswith("/health"):
        return True

    # Exempt requests with special header
    if request.headers.get("X-Admin-Key") == "supersecret":
        return True

    return False

app = FastAPI()
app.add_middleware(
    MaintenanceModeMiddleware,
    exempt_handler=is_exempt
)

# Result during maintenance:
# ✅ /docs, /redoc, /openapi.json, /docs/oauth2-redirect (automatically exempt)
# ✅ /health/* (custom exemption)
# ✅ Requests with X-Admin-Key header (custom exemption)
# ❌ Other endpoints return 503
```

## Handler Function Requirements

The exempt handler is a function that decides whether a request should bypass maintenance mode. Here's what you need to know:

### Function Signature

The handler function must:
- Accept a single `Request` parameter from FastAPI
- Return a `bool` value
- Be either synchronous or asynchronous (both are supported)

```python
# Synchronous handler
def is_exempt(request: Request) -> bool:
    # Logic here
    return True/False

# Asynchronous handler
async def is_exempt(request: Request) -> bool:
    # Async logic here
    return True/False
```

### Return Value

The return value determines how the request is handled:
- `True`: The request bypasses maintenance mode and proceeds normally
- `False`: The request is subject to maintenance mode rules

### Execution Context

The handler runs for every request when maintenance middleware is in place, so:
- Keep it lightweight to avoid performance issues
- Handle all exceptions internally
- Avoid side effects that could impact other requests
- The handler can access any aspect of the `Request` object (headers, path, query params, etc.)

## Examples

### Role-Based Exemptions

```python
def is_exempt(request: Request) -> bool:
    # Check for admin role in JWT token
    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    try:
        payload = decode_jwt(token)
        if "admin" in payload.get("roles", []):
            return True
    except Exception:
        # Token validation failed, no exemption
        pass

    return False
```

### IP-Based Exemptions

```python
def is_exempt(request: Request) -> bool:
    # Exempt internal networks
    client_host = request.client.host if request.client else None

    # Exempt localhost and internal network
    if client_host in ["127.0.0.1", "::1"] or client_host.startswith("10."):
        return True

    return False
```

### Combining Multiple Conditions

```python
def is_exempt(request: Request) -> bool:
    # Health check endpoints are always accessible
    if request.url.path.startswith("/health"):
        return True

    # Read-only operations during partial maintenance
    if request.method in ["GET", "HEAD"] and not is_full_maintenance():
        return True

    # Admin users can access everything
    if is_admin_user(request):
        return True

    return False
```

## Async Support

The exempt handler can also be asynchronous:

```python
async def is_exempt(request: Request) -> bool:
    # Perform async operations like database queries
    user = await get_user_from_db(request.headers.get("X-User-ID"))

    if user and user.is_admin:
        return True

    return False

app.add_middleware(
    MaintenanceModeMiddleware,
    exempt_handler=is_exempt
)
```

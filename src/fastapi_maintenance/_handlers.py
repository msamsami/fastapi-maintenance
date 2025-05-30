"""
Built-in handlers for FastAPI maintenance mode.
"""

from typing import cast

from fastapi.routing import APIRoute
from starlette.requests import Request
from starlette.routing import Match


def exempt_docs_endpoints(request: Request) -> bool:
    """Exempt FastAPI's built-in documentation endpoints from maintenance mode.

    This handler exempts the following FastAPI built-in endpoints:
    - /docs - Swagger UI interactive documentation
    - /redoc - ReDoc alternative documentation
    - /openapi.json - OpenAPI schema specification
    - /docs/oauth2-redirect - OAuth2 redirect for Swagger UI

    Args:
        request: The incoming request.

    Returns:
        True if the request should be exempt from maintenance mode, False otherwise.
    """
    path = request.url.path

    # FastAPI built-in documentation endpoints
    docs_endpoints = ["/docs", "/redoc", "/openapi.json", "/docs/oauth2-redirect"]

    return path in docs_endpoints


def exempt_nonexistent_routes(request: Request) -> bool:
    """Exempt non-existent routes from maintenance mode to preserve the normal behavior (e.g. 404, 405 error).

    This handler checks if the requested path matches any defined route in the FastAPI
    application. If no route matches, it exempts the request so that FastAPI can
    return its normal error response instead of a maintenance response.

    Args:
        request: The incoming request.

    Returns:
        True if the route doesn't exist, False if it exists.
    """
    scope = {"type": "http", "path": request.url.path, "method": request.method}

    # Check if any route matches this path and method
    for route in request.app.routes:
        route = cast(APIRoute, route)
        match, _ = route.matches(scope)
        if match == Match.FULL:
            return False  # Route exists, don't exempt (apply maintenance if needed)

    # No route matched
    return True

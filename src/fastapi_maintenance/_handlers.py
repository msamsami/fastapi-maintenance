"""
Built-in handlers for FastAPI maintenance mode.
"""

from starlette.requests import Request


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

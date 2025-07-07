"""
Middleware for FastAPI maintenance mode.
"""

from __future__ import annotations

import asyncio
import re
import sys
from functools import lru_cache
from re import Pattern
from typing import Awaitable, Callable, Literal, Optional, TypeVar, Union, cast

if sys.version_info >= (3, 10):
    from typing import ParamSpec
else:
    from typing_extensions import ParamSpec

from fastapi import status
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response
from starlette.routing import Match
from starlette.types import ASGIApp

from ._constants import (
    DEFAULT_JSON_RESPONSE_CONTENT,
    FORCE_MAINTENANCE_MODE_OFF_ATTR,
    FORCE_MAINTENANCE_MODE_ON_ATTR,
)
from ._context import is_maintenance_override_ctx_active
from ._core import get_maintenance_mode, register_middleware_backend
from ._handlers import exempt_docs_endpoints
from .backends import BaseStateBackend

P = ParamSpec("P")
R = TypeVar("R")

HandlerFunction = Union[Callable[P, R], Callable[P, Awaitable[R]]]

__all__ = ["MaintenanceModeMiddleware"]


class MaintenanceModeMiddleware(BaseHTTPMiddleware):
    """Middleware for enabling maintenance mode in FastAPI applications.

    Args:
        app: The ASGI application.
        enable_maintenance: Boolean to explicitly enable (True) or disable (False) maintenance mode regardless of backend state. If specified, takes precedence over the backend's state value. Defaults to None to use the backend's state value.
        backend: Optional backend for maintenance mode state storage. Defaults to None for environment variable backend or another backend set by `configure_backend`.
        exempt_handler: Handler function (sync or async) that determines if a request should be exempt from maintenance mode. Defaults to None for no exemption.
        response_handler: Handler function (sync or async) to return a custom response during maintenance mode. Defaults to None for the default JSON response.
    """

    _FORCED_PATH_MATCH_CACHE_SIZE = 128
    _ROUTE_EXISTS_CACHE_SIZE = 128

    def __init__(
        self,
        app: ASGIApp,
        enable_maintenance: Optional[bool] = None,
        backend: Optional[BaseStateBackend] = None,
        exempt_handler: Optional[HandlerFunction[[Request], bool]] = None,
        response_handler: Optional[HandlerFunction[[Request], Response]] = None,
    ) -> None:
        super().__init__(app)
        self.enable_maintenance = enable_maintenance
        self.backend = backend
        self.exempt_handler = exempt_handler
        self.response_handler = response_handler

        register_middleware_backend(self.backend)
        self._app_routes: list[APIRoute] = []
        self._forced_on_paths: tuple[Pattern[str], ...] = ()
        self._forced_off_paths: tuple[Pattern[str], ...] = ()
        self._forced_paths_collected: bool = False
        self._cached_path_matches_patterns = lru_cache(maxsize=self._FORCED_PATH_MATCH_CACHE_SIZE)(
            self._path_matches_patterns
        )
        self._cached_route_exists = lru_cache(maxsize=self._ROUTE_EXISTS_CACHE_SIZE)(self._route_exists)

    def _collect_forced_maintenance_paths(self, routes: list[APIRoute]) -> None:
        # Clear instance-specific caches before recollection
        self._cached_path_matches_patterns.cache_clear()
        self._cached_route_exists.cache_clear()

        forced_on_paths, forced_off_paths = [], []
        for route in routes:
            if getattr(route.endpoint, "__dict__", {}).get(FORCE_MAINTENANCE_MODE_ON_ATTR, False):
                forced_on_paths.append(route.path_regex)
                continue
            if getattr(route.endpoint, "__dict__", {}).get(FORCE_MAINTENANCE_MODE_OFF_ATTR, False):
                forced_off_paths.append(route.path_regex)
        self._forced_on_paths = tuple(forced_on_paths)
        self._forced_off_paths = tuple(forced_off_paths)

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if not self._forced_paths_collected or self._app_routes != request.app.routes:
            self._app_routes = request.app.routes.copy()
            self._collect_forced_maintenance_paths(self._app_routes)
            self._forced_paths_collected = True

        # Built-in exemption: Non-existent paths/methods should return normal HTTP errors, not maintenance
        if not self._cached_route_exists(request.url.path, request.method):
            return await call_next(request)

        # 1. Highest Precedence Block: Path is explicitly forced into maintenance
        if self._is_path_forced_on(request.url.path):
            # Path forced ON implies maintenance regardless of other settings
            return await self._get_maintenance_response(request)

        # 2. Highest Precedence Allow: Path is explicitly forced out of maintenance
        if self._is_path_forced_off(request.url.path):
            # Path forced OFF implies proceeding, bypassing other maintenance checks for this path
            return await call_next(request)

        # 3. Request-Specific Exemption: The request itself is exempt from maintenance (docs, custom handlers)
        if await self._is_exempt(request):
            # Exempt requests proceed unless the path was specifically forced ON (checked above)
            return await call_next(request)

        # 4. Maintenance Override Context: Maintenance is globally forced ON via a context manager
        if is_maintenance_override_ctx_active():
            # Override context forces maintenance if not forced_off or request is exempt
            return await self._get_maintenance_response(request)

        # 5. General Maintenance Mode: Standard maintenance mode is active based on the backend
        if await self._is_maintenance_active():
            # General maintenance is active, and request was not forced_off or exempt
            return await self._get_maintenance_response(request)

        # Otherwise, continue with the request
        return await call_next(request)

    def _route_exists(self, path: str, method: str) -> bool:
        """Check if a route exists for the given path and method.

        Args:
            path: The URL path to check.
            method: The HTTP method to check.

        Returns:
            True if a route exists, False otherwise.
        """
        scope = {"type": "http", "path": path, "method": method}
        for route in self._app_routes:
            match, _ = route.matches(scope)
            if match == Match.FULL:
                return True
        return False

    async def _is_maintenance_active(self) -> bool:
        """Check if maintenance mode is active.

        Returns:
            True if maintenance mode is active, False otherwise.
        """
        if self.enable_maintenance is not None:
            return self.enable_maintenance
        return await get_maintenance_mode(self.backend)

    def _path_matches_patterns(self, path: str, patterns_type: Literal["on", "off"]) -> bool:
        """Check if a path matches forced on or off regex patterns.

        Args:
            path: The URL path to check.
            patterns_type: The type of patterns to match against, either "on" or "off".

        Returns:
            True if the path matches any of the specified patterns, False otherwise.
        """
        patterns = self._forced_on_paths if patterns_type == "on" else self._forced_off_paths
        if not patterns:
            return False
        for pattern in patterns:
            if re.fullmatch(pattern, path):
                return True
        return False

    def _is_path_forced_on(self, path: str) -> bool:
        """Check if the maintenance mode is forced on for the request's path.

        Args:
            path: The incoming request path.

        Returns:
            True if the maintenance mode is forced on for the request's path, False otherwise.
        """
        return self._cached_path_matches_patterns(path, "on")

    def _is_path_forced_off(self, path: str) -> bool:
        """Check if the maintenance mode is forced off for the request's path.

        Args:
            path: The incoming request path.

        Returns:
            True if the maintenance mode is forced off for the request's path, False otherwise.
        """
        return self._cached_path_matches_patterns(path, "off")

    async def _is_exempt(self, request: Request) -> bool:
        """Check if the request is exempt from maintenance mode.

        Args:
            request: The incoming request.

        Returns:
            True if the request is exempt, False otherwise.
        """
        # Built-in exemption: FastAPI documentation endpoints are always exempt
        if exempt_docs_endpoints(request):
            return True

        # Custom exemption handler
        if self.exempt_handler is not None:
            if asyncio.iscoroutinefunction(self.exempt_handler):
                if await self.exempt_handler(request):
                    return True
            else:
                if self.exempt_handler(request):
                    return True
        return False

    async def _get_maintenance_response(self, request: Request) -> Response:
        """Get the appropriate maintenance response.

        Args:
            request: The request object.

        Returns:
            The maintenance mode response.
        """
        if self.response_handler is not None:
            if asyncio.iscoroutinefunction(self.response_handler):
                return await cast(Callable[[Request], Awaitable[Response]], self.response_handler)(request)
            else:
                return cast(Callable[[Request], Response], self.response_handler)(request)
        else:
            return JSONResponse(
                content=DEFAULT_JSON_RESPONSE_CONTENT,
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                headers={"Retry-After": "3600"},
            )

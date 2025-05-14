"""
Middleware for FastAPI maintenance mode.
"""

from __future__ import annotations

import asyncio
import re
import sys
from typing import TYPE_CHECKING, Awaitable, Callable, Optional, TypeVar, Union, cast

if TYPE_CHECKING:
    from fastapi import Request, Response

if sys.version_info >= (3, 10):
    from typing import ParamSpec
else:
    from typing_extensions import ParamSpec

from fastapi import status
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.types import ASGIApp

from ._constants import (
    DEFAULT_JSON_CONTENT,
    FORCE_MAINTENANCE_MODE_OFF_ATTR,
    FORCE_MAINTENANCE_MODE_ON_ATTR,
)
from .backends import BaseStateBackend
from .core import get_maintenance_mode

P = ParamSpec("P")
R = TypeVar("R")

CallbackFunction = Union[Callable[P, R], Callable[P, Awaitable[R]]]

__all__ = ["MaintenanceModeMiddleware"]


class MaintenanceModeMiddleware(BaseHTTPMiddleware):
    """
    Middleware for enabling maintenance mode in FastAPI applications.
    """

    def __init__(
        self,
        app: ASGIApp,
        maintenance_mode: Optional[bool] = None,
        backend: Optional[BaseStateBackend] = None,
        exempt_callback: Optional[CallbackFunction[["Request"], bool]] = None,
        response_callback: Optional[CallbackFunction[["Request"], "Response"]] = None,
    ) -> None:
        """Initialize the maintenance mode middleware.

        Args:
            app: The ASGI application.
            maintenance_mode: Default maintenance mode state. Defaults to None to use the backend's default value.
            backend: Optional backend for state storage. Defaults to None for environment variable backend.
            exempt_callback: Callback to determine if a request is exempt from maintenance (sync or async). Defaults to None.
            response_callback: Callback to return a custom response during maintenance (sync or async). Defaults to None for the default JSON response.
        """
        super().__init__(app)
        self.maintenance_mode = maintenance_mode
        self.backend = backend
        self.exempt_callback = exempt_callback
        self.response_callback = response_callback

        self._forced_on_paths: list[re.Pattern[str]] = []
        self._forced_off_paths: list[re.Pattern[str]] = []
        self._forced_paths_collected: bool = False

    def _collect_forced_maintenance_paths(self, routes: list[APIRoute]) -> None:
        for route in routes:
            if getattr(route.endpoint, "__dict__", {}).get(FORCE_MAINTENANCE_MODE_ON_ATTR, False):
                self._forced_on_paths.append(route.path_regex)
                continue
            if getattr(route.endpoint, "__dict__", {}).get(FORCE_MAINTENANCE_MODE_OFF_ATTR, False):
                self._forced_off_paths.append(route.path_regex)

    async def dispatch(self, request: "Request", call_next: RequestResponseEndpoint) -> "Response":
        if not self._forced_paths_collected:
            self._collect_forced_maintenance_paths(request.app.routes)
            self._forced_paths_collected = True

        # If maintenance mode is forced on, return the maintenance response
        if self._is_path_forced_on(request):
            return await self._get_maintenance_response(request)

        # If maintenance mode is active, request is not exempt, and maintenance mode is not forced off for the request's path
        if (
            await self._is_maintenance_active()
            and not await self._is_exempt(request)
            and not self._is_path_forced_off(request)
        ):
            return await self._get_maintenance_response(request)

        # Otherwise, continue with the request
        return await call_next(request)

    async def _is_maintenance_active(self) -> bool:
        """Check if maintenance mode is active.

        Returns:
            True if maintenance mode is active, False otherwise.
        """
        if self.maintenance_mode is not None:
            return self.maintenance_mode
        return await get_maintenance_mode(self.backend)

    def _is_path_forced_on(self, request: "Request") -> bool:
        """Check if the maintenance mode is forced on for the request's path.

        Args:
            request: The incoming request.

        Returns:
            True if the maintenance mode is forced on for the request's path, False otherwise.
        """
        for regex_pattern in self._forced_on_paths:
            if re.fullmatch(regex_pattern, request.url.path):
                return True
        return False

    def _is_path_forced_off(self, request: "Request") -> bool:
        """Check if the maintenance mode is forced off for the request's path.

        Args:
            request: The incoming request.

        Returns:
            True if the maintenance mode is forced off for the request's path, False otherwise.
        """
        for regex_pattern in self._forced_off_paths:
            if re.fullmatch(regex_pattern, request.url.path):
                return True
        return False

    async def _is_exempt(self, request: "Request") -> bool:
        """Check if the request is exempt from maintenance mode.

        Args:
            request: The incoming request.

        Returns:
            True if the request is exempt, False otherwise.
        """
        if self.exempt_callback is not None:
            if asyncio.iscoroutinefunction(self.exempt_callback):
                if await self.exempt_callback(request):
                    return True
            else:
                if self.exempt_callback(request):
                    return True
        return False

    async def _get_maintenance_response(self, request: "Request") -> "Response":
        """Get the appropriate maintenance response.

        Args:
            request: The request object.

        Returns:
            The maintenance mode response.
        """
        if self.response_callback is not None:
            if asyncio.iscoroutinefunction(self.response_callback):
                return await cast(Callable[["Request"], Awaitable["Response"]], self.response_callback)(request)
            else:
                return cast(Callable[["Request"], "Response"], self.response_callback)(request)
        else:
            return JSONResponse(
                content=DEFAULT_JSON_CONTENT,
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                headers={"Retry-After": "3600"},
            )

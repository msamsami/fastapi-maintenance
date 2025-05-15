"""
Decorators for FastAPI routes to force maintenance mode behavior.
"""

from __future__ import annotations

import asyncio
from functools import wraps
from typing import Any, Callable

from ._constants import FORCE_MAINTENANCE_MODE_OFF_ATTR, FORCE_MAINTENANCE_MODE_ON_ATTR

RouteHandler = Callable[..., Any]

__all__ = ["force_maintenance_mode_off", "force_maintenance_mode_on"]


def force_maintenance_mode_off(func: RouteHandler) -> RouteHandler:
    """Decorator to force maintenance mode off for a specific route.

    Works with both sync and async functions.

    Args:
        func: The route handler function.

    Returns:
        A wrapped function that will always bypass maintenance mode.
    """
    is_coroutine = asyncio.iscoroutinefunction(func)

    if is_coroutine:

        @wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            return await func(*args, **kwargs)

        # Add attribute to function for middleware to check
        async_wrapper.__dict__[FORCE_MAINTENANCE_MODE_OFF_ATTR] = True
        async_wrapper.__dict__[FORCE_MAINTENANCE_MODE_ON_ATTR] = False
        return async_wrapper
    else:

        @wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            return func(*args, **kwargs)

        # Add attribute to function for middleware to check
        sync_wrapper.__dict__[FORCE_MAINTENANCE_MODE_OFF_ATTR] = True
        sync_wrapper.__dict__[FORCE_MAINTENANCE_MODE_ON_ATTR] = False
        return sync_wrapper


def force_maintenance_mode_on(func: RouteHandler) -> RouteHandler:
    """Decorator to force maintenance mode on for a specific route.

    Works with both sync and async functions.

    Args:
        func: The route handler function.

    Returns:
        A wrapped function that will always return a maintenance response.
    """
    is_coroutine = asyncio.iscoroutinefunction(func)

    if is_coroutine:

        @wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            return await func(*args, **kwargs)

        # Add attribute to function for middleware to check
        async_wrapper.__dict__[FORCE_MAINTENANCE_MODE_ON_ATTR] = True
        async_wrapper.__dict__[FORCE_MAINTENANCE_MODE_OFF_ATTR] = False
        return async_wrapper
    else:

        @wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            return func(*args, **kwargs)

        # Add attribute to function for middleware to check
        sync_wrapper.__dict__[FORCE_MAINTENANCE_MODE_ON_ATTR] = True
        sync_wrapper.__dict__[FORCE_MAINTENANCE_MODE_OFF_ATTR] = False
        return sync_wrapper

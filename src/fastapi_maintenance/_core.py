"""
Core functionality for maintenance mode.
"""

from typing import Any, Optional

from .backends import BaseStateBackend, _get_backend

_backend: Optional[BaseStateBackend] = None
"""Global variable for the default backend instance."""

_middleware_backend: Optional[BaseStateBackend] = None
"""Global variable for the backend used by the middleware."""


def register_middleware_backend(backend: Optional[BaseStateBackend]) -> None:
    """Register the backend used by the middleware.

    This allows other components such as context managers to access the backend used by the middleware.

    Args:
        backend: The backend instance used by the middleware (if provided).
    """
    global _middleware_backend
    _middleware_backend = backend


def _get_default_backend() -> BaseStateBackend:
    """Get or create the default backend instance.

    Returns:
        The default backend instance.
    """
    global _backend, _middleware_backend

    # First try to use the middleware backend if available
    if _middleware_backend is not None:
        return _middleware_backend

    # Fall back to configured backend or create default env backend
    if _backend is None:
        # Default to environment variable backend
        _backend = _get_backend("env")
    return _backend


async def get_maintenance_mode(backend: Optional[BaseStateBackend] = None) -> bool:
    """Get current maintenance mode state.

    Supported values are:
    - Truthy values (case-insensitive): '1', 'yes', 'y', 'true', 't', 'on'
    - Falsy values (case-insensitive): '0', 'no', 'n', 'false', 'f', 'off'

    Args:
        backend: Optional backend instance to use instead of the default.

    Returns:
        A boolean indicating the current maintenance mode state.
    """
    backend = backend or _get_default_backend()
    return await backend.get_value()


async def set_maintenance_mode(value: bool, backend: Optional[BaseStateBackend] = None) -> None:
    """Set maintenance mode state.

    Note: If using the default environment variable backend, this function will log a warning
    and have no effect. Environment variables are read-only at runtime.

    Args:
        value: A boolean indicating the maintenance mode state to set.
        backend: Optional backend instance to use instead of the default.
    """
    backend = backend or _get_default_backend()
    await backend.set_value(value)


def configure_backend(backend_type: str, **kwargs: Any) -> None:
    """Configure the default backend used to store and retrieve the maintenance mode state.

    Available backend types:
    - 'env': Read from environment variable (default, read-only)
    - 'file': Read/write to a file

    Args:
        backend_type: Type of backend ('env', 'file')
        **kwargs: Additional arguments to pass to the backend constructor.
            - For 'env': var_name (optional, defaults to `FASTAPI_MAINTENANCE_MODE`)
            - For 'file': file_path
    """
    global _backend
    _backend = _get_backend(backend_type, **kwargs)

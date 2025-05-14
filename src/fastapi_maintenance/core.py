"""
Core functionality for maintenance mode.
"""

from contextlib import ContextDecorator
from typing import Any, Literal, Optional

from .backends import BaseStateBackend, _get_backend

__all__ = [
    "get_maintenance_mode",
    "set_maintenance_mode",
    "configure_backend",
    "maintenance_mode_on",
    "maintenance_mode_off",
]

_backend: Optional[BaseStateBackend] = None
"""Global variable for the default backend instance."""


def _get_default_backend() -> BaseStateBackend:
    """Get or create the default backend instance.

    Returns:
        The default backend instance.
    """
    global _backend
    if _backend is None:
        # Default to environment variable backend
        _backend = _get_backend("env")
    return _backend


async def get_maintenance_mode(backend: Optional[BaseStateBackend] = None) -> bool:
    """Get current maintenance mode state.

    By default, this checks the `FASTAPI_MAINTENANCE_MODE` environment variable.
    If using the default environment backend, the supported values are:
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
    and have no effect. Environment variables are read-only at runtime. To use writable storage,
    explicitly configure a different backend using `configure_backend()`.

    Args:
        value: A boolean indicating the maintenance mode state to set.
        backend: Optional backend instance to use instead of the default (environment variable backend).
    """
    backend = backend or _get_default_backend()
    await backend.set_value(value)


def configure_backend(backend_type: str, **kwargs: Any) -> None:
    """Configure the default backend.

    Available backend types:
    - 'env': Read from environment variable (default, read-only)
    - 'file': Read/write to a file

    Args:
        backend_type: Type of backend ('env', 'file')
        **kwargs: Additional arguments to pass to the backend constructor.
            - For 'env': env_var_name (optional, defaults to `FASTAPI_MAINTENANCE_MODE`)
            - For 'file': file_path (optional)
    """
    global _backend
    _backend = _get_backend(backend_type, **kwargs)


class override_maintenance_mode(ContextDecorator):
    """
    Context manager to temporarily override maintenance mode.

    Note: If using the default environment variable backend, this will log warnings
    when trying to modify the maintenance mode state and will have no effect.
    """

    def __init__(self, value: bool, backend: Optional[BaseStateBackend] = None) -> None:
        """Initialize with the value to set during the context.

        Args:
            value: A boolean indicating the maintenance mode state to set.
            backend: Optional backend instance to use instead of the default (environment variable backend).
        """
        self.value = value
        self.backend = backend or _get_default_backend()
        self._previous_value: Optional[bool] = None

    async def __aenter__(self) -> "override_maintenance_mode":
        """
        Enter the context by saving the current state and setting the new state.
        """
        self._previous_value = await get_maintenance_mode(self.backend)
        await set_maintenance_mode(self.value, self.backend)
        return self

    async def __aexit__(self, *exc: Any) -> Literal[False]:
        """
        Exit the context by restoring the previous state.

        Returns False to ensure exceptions propagate normally and aren't suppressed.
        """
        if self._previous_value is not None:
            await set_maintenance_mode(self._previous_value, self.backend)
        return False


def maintenance_mode_on(backend: Optional[BaseStateBackend] = None) -> override_maintenance_mode:
    """Temporarily enable maintenance mode using a context manager.

    Args:
        backend: Optional backend instance to use.

    Returns:
        A context manager that enables maintenance mode.
    """
    return override_maintenance_mode(True, backend)


def maintenance_mode_off(backend: Optional[BaseStateBackend] = None) -> override_maintenance_mode:
    """Temporarily disable maintenance mode using a context manager.

    Args:
        backend: Optional backend instance to use.

    Returns:
        A context manager that disables maintenance mode.
    """
    return override_maintenance_mode(False, backend)

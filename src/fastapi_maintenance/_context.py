"""
Context managers for maintenance mode.
"""

from contextlib import ContextDecorator
from typing import Any, Literal, Optional

from ._core import _get_default_backend, get_maintenance_mode, set_maintenance_mode
from .backends import BaseStateBackend

__all__ = ["maintenance_mode_on"]


_maintenance_override_ctx_flag: bool = False
"""Internal flag that tracks whether code is currently executing within a maintenance mode override context."""


def is_maintenance_override_ctx_active() -> bool:
    """Check if a maintenance mode override context is currently in use.

    Returns:
        True if a maintenance mode override context is active, False otherwise.
    """
    global _maintenance_override_ctx_flag
    return _maintenance_override_ctx_flag


def _set_maintenance_override_ctx_flag(value: bool) -> None:
    """Set the maintenance mode override context flag.

    Args:
        value: A boolean indicating the maintenance mode state to set.
    """
    global _maintenance_override_ctx_flag
    _maintenance_override_ctx_flag = value


class override_maintenance_mode(ContextDecorator):
    """
    Context manager to temporarily override maintenance mode.

    Args:
        value: A boolean indicating the maintenance mode state to set.
        backend: Optional backend instance to use instead of the default (environment variable backend).
    """

    def __init__(self, value: bool, backend: Optional[BaseStateBackend] = None) -> None:
        self.value = value
        self.backend = backend or _get_default_backend()
        self._previous_value: Optional[bool] = None
        self._previous_override_ctx_flag: Optional[bool] = None

    async def __aenter__(self) -> "override_maintenance_mode":
        """
        Enter the context by saving the current state and setting the new state.
        """
        self._previous_value = await get_maintenance_mode(self.backend)
        await set_maintenance_mode(self.value, self.backend)
        self._previous_override_ctx_flag = is_maintenance_override_ctx_active()
        _set_maintenance_override_ctx_flag(True)
        return self

    async def __aexit__(self, *exc: Any) -> Literal[False]:
        """Exit the context by restoring the previous state.

        Returns False to ensure exceptions propagate normally and aren't suppressed.
        """
        if self._previous_value is not None:
            await set_maintenance_mode(self._previous_value, self.backend)
        if self._previous_override_ctx_flag is not None:
            _set_maintenance_override_ctx_flag(self._previous_override_ctx_flag)
        return False


def maintenance_mode_on(backend: Optional[BaseStateBackend] = None) -> override_maintenance_mode:
    """Temporarily enable maintenance mode using a context manager.

    Args:
        backend: Optional backend instance to use. If not provided, the backend registered by the middleware will be used.

    Returns:
        A context manager that enables maintenance mode.
    """
    return override_maintenance_mode(True, backend)

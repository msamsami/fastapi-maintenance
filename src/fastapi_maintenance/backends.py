"""
State storage backends for maintenance mode.
"""

import logging
import os
from abc import ABC, abstractmethod
from typing import Any, Optional

from anyio import Path, open_file

from ._constants import MAINTENANCE_MODE_ENV_VAR_NAME

logger = logging.getLogger(__name__)

__all__ = ["BaseStateBackend", "EnvVarBackend", "LocalFileBackend"]


class BaseStateBackend(ABC):
    """
    Abstract base class for maintenance mode state backends.
    """

    @staticmethod
    def _bool_to_str(value: bool) -> str:
        """
        Convert boolean value to string representation.
        """
        value_str = str(int(value))
        if value_str not in ["0", "1"]:
            raise ValueError("state value is not correct")
        return value_str

    @staticmethod
    def _str_to_bool(value: str) -> bool:
        """Convert string representation to boolean value.

        Uses Pydantic-style boolean parsing:
        - Truthy values (case-insensitive): '1', 'yes', 'y', 'true', 't', 'on'
        - Falsy values (case-insensitive): '0', 'no', 'n', 'false', 'f', 'off'
        - Empty or missing values: False
        """
        value = value.strip().lower()
        if not value:
            return False
        if value in {1, "1", "on", "t", "true", "y", "yes"}:
            return True
        elif value in {0, "0", "off", "f", "false", "n", "no"}:
            return False
        else:
            raise ValueError("state value is not correct")

    @abstractmethod
    async def get_value(self) -> bool:
        """
        Get the current maintenance mode state.
        """
        pass

    @abstractmethod
    async def set_value(self, value: bool) -> None:
        """
        Set the maintenance mode state.
        """
        pass


class EnvVarBackend(BaseStateBackend):
    """Read maintenance mode state from environment variables.

    This backend is read-only. Attempts to set values will log a warning but not change
    the environment variable. Environment variables should be set before application startup.

    Args:
        var_name: Name of the environment variable to use. Defaults to None to use `FASTAPI_MAINTENANCE_MODE`.
    """

    def __init__(self, var_name: Optional[str] = None) -> None:
        self.var_name = var_name

    @property
    def _var_name(self) -> str:
        return self.var_name or MAINTENANCE_MODE_ENV_VAR_NAME

    async def get_value(self) -> bool:
        """Get maintenance mode state from environment variable.

        Returns:
            A boolean indicating the current maintenance mode state.
        """
        value = os.environ.get(self._var_name, "")

        try:
            return self._str_to_bool(value)
        except ValueError:
            pass

        logger.warning(
            f"Invalid value '{value}' for environment variable {self._var_name}. "
            f"Expected boolean-like value. Defaulting to False."
        )
        return False

    async def set_value(self, value: bool) -> None:
        """Attempt to set maintenance mode state (not supported for environment backend).

        This method is deliberately made read-only since environment variables should not
        be modified at runtime. It will log a warning and do nothing.

        Args:
            value: Desired maintenance mode state (ignored).
        """
        logger.warning(
            f"Cannot set maintenance mode state via environment variable {self._var_name}. "
            f"Environment variables are read-only during runtime. "
            f"Set the variable before starting your application."
        )


class LocalFileBackend(BaseStateBackend):
    """Store maintenance mode state in local file system.

    Args:
        file_path: Path to the file that stores the maintenance mode state.
    """

    def __init__(self, file_path: str) -> None:
        self.file_path = file_path

    async def get_value(self) -> bool:
        """Get maintenance mode state from file.

        Returns:
            A boolean indicating the current maintenance mode state.
        """
        if not await Path(self.file_path).exists():
            await self.set_value(False)
            return False

        async with await open_file(self.file_path, "r") as f:
            content = await f.read()
            return self._str_to_bool(content)

    async def set_value(self, value: bool) -> None:
        """Set maintenance mode state in file.

        Args:
            value: A boolean indicating the maintenance mode state to set.
        """
        async with await open_file(self.file_path, "w") as f:
            await f.write(self._bool_to_str(value))


def _get_backend(backend_type: str, **kwargs: Any) -> BaseStateBackend:
    """Factory function to create backend instances.

    Args:
        backend_type: Type of backend ('env', 'file').
        **kwargs: Additional arguments to pass to the backend constructor.

    Returns:
        An instance of the requested backend.

    Raises:
        ValueError: If the backend type is not supported.
    """
    if backend_type == "env":
        return EnvVarBackend(**kwargs)
    elif backend_type == "file":
        return LocalFileBackend(**kwargs)
    else:
        raise ValueError(f"Unsupported backend type: '{backend_type}'")

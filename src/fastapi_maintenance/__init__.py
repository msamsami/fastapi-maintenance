"""FastAPI Maintenance package.

This package provides a middleware for enabling maintenance mode in FastAPI applications.
Easily toggle maintenance mode for your API with flexible configuration options and
the ability to exempt specific endpoints from maintenance status.
"""

from .core import (
    configure_backend,
    get_maintenance_mode,
    maintenance_mode_off,
    maintenance_mode_on,
    set_maintenance_mode,
)
from .decorators import force_maintenance_mode_off, force_maintenance_mode_on
from .middleware import MaintenanceModeMiddleware

__all__ = [
    "get_maintenance_mode",
    "set_maintenance_mode",
    "configure_backend",
    "force_maintenance_mode_off",
    "force_maintenance_mode_on",
    "MaintenanceModeMiddleware",
    "maintenance_mode_off",
    "maintenance_mode_on",
]

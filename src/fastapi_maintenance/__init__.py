"""FastAPI Maintenance package.

This package provides a middleware for enabling maintenance mode in FastAPI applications.
Easily toggle maintenance mode for your API with flexible configuration options and
the ability to exempt specific endpoints from maintenance status.
"""

__version__ = "0.0.5"
__author__ = "Mehdi Samsami"


from ._context import maintenance_mode_on
from ._core import configure_backend, get_maintenance_mode, set_maintenance_mode
from .decorators import force_maintenance_mode_off, force_maintenance_mode_on
from .middleware import MaintenanceModeMiddleware

__all__ = [
    "configure_backend",
    "get_maintenance_mode",
    "set_maintenance_mode",
    "force_maintenance_mode_off",
    "force_maintenance_mode_on",
    "MaintenanceModeMiddleware",
    "maintenance_mode_on",
]

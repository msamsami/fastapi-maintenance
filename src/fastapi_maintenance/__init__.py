"""FastAPI Maintenance package.

This package provides a middleware for enabling maintenance mode in FastAPI applications.
Easily toggle maintenance mode for your API with flexible configuration options and
the ability to exempt specific endpoints from maintenance status.
"""

__version__ = "0.1.0"
__author__ = "Mehdi Samsami"


from ._context import maintenance_mode_on
from ._core import get_maintenance_mode, set_maintenance_mode
from .decorators import force_maintenance_mode_off, force_maintenance_mode_on
from .middleware import MaintenanceModeMiddleware

__all__ = [
    "get_maintenance_mode",
    "set_maintenance_mode",
    "force_maintenance_mode_off",
    "force_maintenance_mode_on",
    "MaintenanceModeMiddleware",
    "maintenance_mode_on",
]

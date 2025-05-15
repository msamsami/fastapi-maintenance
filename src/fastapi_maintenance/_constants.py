"""
Internal constants for FastAPI maintenance mode.
"""

# Decorator attribute names
FORCE_MAINTENANCE_MODE_ON_ATTR = "force_maintenance_mode_on"
FORCE_MAINTENANCE_MODE_OFF_ATTR = "force_maintenance_mode_off"

# Default environment variable name
MAINTENANCE_MODE_ENV_VAR_NAME = "FASTAPI_MAINTENANCE_MODE"

# Default JSON response content
DEFAULT_JSON_RESPONSE_CONTENT = {"detail": "Service temporarily unavailable due to maintenance"}

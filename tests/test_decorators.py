import asyncio

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from fastapi_maintenance import MaintenanceModeMiddleware
from fastapi_maintenance._constants import (
    FORCE_MAINTENANCE_MODE_OFF_ATTR,
    FORCE_MAINTENANCE_MODE_ON_ATTR,
)
from fastapi_maintenance.decorators import (
    force_maintenance_mode_off,
    force_maintenance_mode_on,
)


def test_force_maintenance_mode_off_sync():
    """Test that `force_maintenance_mode_off` decorator properly sets attributes on synchronous functions."""

    @force_maintenance_mode_off
    def sync_endpoint():
        return "sync_ok"

    assert getattr(sync_endpoint, FORCE_MAINTENANCE_MODE_OFF_ATTR, False) is True
    assert getattr(sync_endpoint, FORCE_MAINTENANCE_MODE_ON_ATTR, False) is False
    assert sync_endpoint() == "sync_ok"


@pytest.mark.anyio
async def test_force_maintenance_mode_off_async():
    """Test that `force_maintenance_mode_off` decorator properly sets attributes on asynchronous functions."""

    @force_maintenance_mode_off
    async def async_endpoint():
        await asyncio.sleep(0.01)
        return "async_ok"

    assert getattr(async_endpoint, FORCE_MAINTENANCE_MODE_OFF_ATTR, False) is True
    assert getattr(async_endpoint, FORCE_MAINTENANCE_MODE_ON_ATTR, False) is False
    assert await async_endpoint() == "async_ok"


def test_force_maintenance_mode_on_sync():
    """Test that `force_maintenance_mode_on` decorator properly sets attributes on synchronous functions."""

    @force_maintenance_mode_on
    def sync_endpoint():
        return "sync_should_not_be_called"

    assert getattr(sync_endpoint, FORCE_MAINTENANCE_MODE_ON_ATTR, False) is True
    assert getattr(sync_endpoint, FORCE_MAINTENANCE_MODE_OFF_ATTR, False) is False
    assert sync_endpoint() == "sync_should_not_be_called"  # Decorator doesn't prevent call, middleware does


@pytest.mark.anyio
async def test_force_maintenance_mode_on_async():
    """Test that `force_maintenance_mode_on` decorator properly sets attributes on asynchronous functions."""

    @force_maintenance_mode_on
    async def async_endpoint():
        await asyncio.sleep(0.01)
        return "async_should_not_be_called"

    assert getattr(async_endpoint, FORCE_MAINTENANCE_MODE_ON_ATTR, False) is True
    assert getattr(async_endpoint, FORCE_MAINTENANCE_MODE_OFF_ATTR, False) is False
    assert await async_endpoint() == "async_should_not_be_called"  # Decorator doesn't prevent call, middleware does


@pytest.mark.anyio
async def test_decorators_integration_with_middleware():
    """Test that decorators correctly integrate with the `MaintenanceModeMiddleware` to control route availability."""
    app = FastAPI()

    @app.get("/forced_off")
    @force_maintenance_mode_off
    async def get_forced_off():
        return {"message": "Forced off"}

    @app.get("/forced_on")
    @force_maintenance_mode_on
    async def get_forced_on():
        return {"message": "Forced on - should not see this"}

    @app.get("/normal")
    async def get_normal():
        return {"message": "Normal"}

    # Middleware configured to be in maintenance mode by default
    app.add_middleware(MaintenanceModeMiddleware, enable_maintenance=True)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response_forced_off = await client.get("/forced_off")
        assert response_forced_off.status_code == 200
        assert response_forced_off.json() == {"message": "Forced off"}

        response_forced_on = await client.get("/forced_on")
        assert response_forced_on.status_code == 503
        assert "Service temporarily unavailable" in response_forced_on.text

        response_normal = await client.get("/normal")
        assert response_normal.status_code == 503  # Should be in maintenance
        assert "Service temporarily unavailable" in response_normal.text

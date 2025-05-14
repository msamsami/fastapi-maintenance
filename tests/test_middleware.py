import asyncio
import os
from pathlib import Path as SyncPath

import pytest
from fastapi import FastAPI, Request, Response, status
from fastapi.responses import HTMLResponse, JSONResponse
from httpx import ASGITransport, AsyncClient

from fastapi_maintenance import (
    MaintenanceModeMiddleware,
    configure_backend,
    force_maintenance_mode_off,
    force_maintenance_mode_on,
    set_maintenance_mode,
)
from fastapi_maintenance._constants import DEFAULT_JSON_RESPONSE_CONTENT
from fastapi_maintenance.backends import MAINTENANCE_MODE_ENV_VAR_NAME, LocalFileBackend
from fastapi_maintenance.core import _backend as core_backend  # For reset

CUSTOM_HTML_CONTENT = "<html><body><h1>Custom Maintenance</h1></body></html>"
CUSTOM_JSON_CONTENT = {"error": "custom_maintenance", "message": "We are down for a bit!"}


@pytest.fixture(autouse=True)
def reset_core_and_env_state():
    """Reset the core backend and environment variables to a clean state between tests."""
    original_backend = core_backend
    original_env = os.environ.copy()
    # Reset to default EnvVarBackend
    configure_backend("env")
    if MAINTENANCE_MODE_ENV_VAR_NAME in os.environ:
        del os.environ[MAINTENANCE_MODE_ENV_VAR_NAME]
    yield
    # Restore
    globals()["core_backend"] = original_backend
    # A more robust way to reset core_backend would be preferred if available
    # For now, explicitly reconfigure to ensure clean state for next test
    configure_backend("env")
    os.environ.clear()
    os.environ.update(original_env)
    if MAINTENANCE_MODE_ENV_VAR_NAME in os.environ:
        del os.environ[MAINTENANCE_MODE_ENV_VAR_NAME]


@pytest.fixture
def temp_file_path(tmp_path: SyncPath) -> str:
    """Return a temporary file path for testing middleware with file backend."""
    return str(tmp_path / "maintenance_middleware.txt")


@pytest.fixture
def app_with_middleware() -> FastAPI:
    """Create a FastAPI app with example routes for testing the middleware."""
    app = FastAPI()

    @app.get("/regular")
    async def regular_endpoint():  # pragma: no cover
        return {"message": "Hello World"}

    @app.get("/exempt_by_decorator")
    @force_maintenance_mode_off
    async def exempt_by_decorator_endpoint():
        return {"message": "Always works"}

    @app.get("/forced_on_by_decorator")
    @force_maintenance_mode_on
    async def forced_on_by_decorator_endpoint():  # pragma: no cover
        return {"message": "Should not be called"}

    return app


@pytest.mark.anyio
async def test_middleware_maintenance_mode_on_init(app_with_middleware: FastAPI):
    """Test that middleware initialized with `maintenance_mode=True` blocks regular routes."""
    app_with_middleware.add_middleware(MaintenanceModeMiddleware, maintenance_mode=True)
    async with AsyncClient(transport=ASGITransport(app=app_with_middleware), base_url="http://test") as client:
        response = await client.get("/regular")
        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
        assert response.json() == DEFAULT_JSON_RESPONSE_CONTENT


@pytest.mark.anyio
async def test_middleware_maintenance_mode_off_init(app_with_middleware: FastAPI):
    """Test that middleware initialized with `maintenance_mode=False` allows regular routes."""
    app_with_middleware.add_middleware(MaintenanceModeMiddleware, maintenance_mode=False)
    async with AsyncClient(transport=ASGITransport(app=app_with_middleware), base_url="http://test") as client:
        response = await client.get("/regular")
        assert response.status_code == status.HTTP_200_OK
        assert response.json() == {"message": "Hello World"}


@pytest.mark.anyio
async def test_middleware_env_var_backend_on(app_with_middleware: FastAPI):
    """Test that middleware with default `EnvVarBackend` respects environment variable (ON state)."""
    os.environ[MAINTENANCE_MODE_ENV_VAR_NAME] = "1"
    app_with_middleware.add_middleware(MaintenanceModeMiddleware)  # Uses default EnvVarBackend
    async with AsyncClient(transport=ASGITransport(app=app_with_middleware), base_url="http://test") as client:
        response = await client.get("/regular")
        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE


@pytest.mark.anyio
async def test_middleware_env_var_backend_off(app_with_middleware: FastAPI):
    """Test that middleware with default `EnvVarBackend` respects environment variable (OFF state)."""
    os.environ[MAINTENANCE_MODE_ENV_VAR_NAME] = "0"
    app_with_middleware.add_middleware(MaintenanceModeMiddleware)
    async with AsyncClient(transport=ASGITransport(app=app_with_middleware), base_url="http://test") as client:
        response = await client.get("/regular")
        assert response.status_code == status.HTTP_200_OK


@pytest.mark.anyio
async def test_middleware_local_file_backend_on(app_with_middleware: FastAPI, temp_file_path: str):
    """Test that middleware with `LocalFileBackend` reads state from file and responds to changes."""
    # Configure LocalFileBackend for the core functions, middleware will pick it up,
    # or pass it directly to middleware, here we test passing it to middleware.
    file_backend = LocalFileBackend(file_path=temp_file_path)
    await file_backend.set_value(True)
    app_with_middleware.add_middleware(MaintenanceModeMiddleware, backend=file_backend)

    async with AsyncClient(transport=ASGITransport(app=app_with_middleware), base_url="http://test") as client:
        response = await client.get("/regular")
        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE

    # Test changing the value dynamically
    await file_backend.set_value(False)
    async with AsyncClient(transport=ASGITransport(app=app_with_middleware), base_url="http://test") as client:
        response = await client.get("/regular")
        assert response.status_code == status.HTTP_200_OK


@pytest.mark.anyio
async def test_middleware_decorator_exemptions(app_with_middleware: FastAPI):
    """Test that decorators correctly override maintenance mode behavior for specific routes."""
    # Middleware is ON by init param
    app_with_middleware.add_middleware(MaintenanceModeMiddleware, maintenance_mode=True)
    async with AsyncClient(transport=ASGITransport(app=app_with_middleware), base_url="http://test") as client:
        # Regular endpoint should be in maintenance
        response_regular = await client.get("/regular")
        assert response_regular.status_code == status.HTTP_503_SERVICE_UNAVAILABLE

        # Endpoint decorated with @force_maintenance_mode_off should work
        response_exempt = await client.get("/exempt_by_decorator")
        assert response_exempt.status_code == status.HTTP_200_OK
        assert response_exempt.json() == {"message": "Always works"}

        # Endpoint decorated with @force_maintenance_mode_on should be in maintenance
        response_forced_on = await client.get("/forced_on_by_decorator")
        assert response_forced_on.status_code == status.HTTP_503_SERVICE_UNAVAILABLE


@pytest.mark.anyio
@pytest.mark.parametrize("is_async_callback", [False, True])
async def test_middleware_exempt_callback(app_with_middleware: FastAPI, is_async_callback: bool):
    """Test exempt_callback with both synchronous and asynchronous callback functions."""

    def sync_exempt_callback(request: Request) -> bool:
        return request.url.path == "/regular"  # Exempt only /regular

    async def async_exempt_callback(request: Request) -> bool:
        await asyncio.sleep(0.001)
        return request.url.path == "/regular"

    callback = async_exempt_callback if is_async_callback else sync_exempt_callback
    app_with_middleware.add_middleware(
        MaintenanceModeMiddleware,
        maintenance_mode=True,  # Maintenance is ON
        exempt_callback=callback,
    )

    async with AsyncClient(transport=ASGITransport(app=app_with_middleware), base_url="http://test") as client:
        # /regular is exempt by callback, should work
        response_regular = await client.get("/regular")
        assert response_regular.status_code == status.HTTP_200_OK
        assert response_regular.json() == {"message": "Hello World"}

        # /exempt_by_decorator is NOT exempt by this callback, but IS by its own decorator
        # Decorator @force_maintenance_mode_off should take precedence over general maintenance mode
        response_exempt_deco = await client.get("/exempt_by_decorator")
        assert response_exempt_deco.status_code == status.HTTP_200_OK
        assert response_exempt_deco.json() == {"message": "Always works"}


@pytest.mark.anyio
async def test_middleware_exempt_callback_path_not_exempt(app_with_middleware: FastAPI):
    """Test that `exempt_callback` returning False keeps routes in maintenance mode."""

    def exempt_nothing_callback(request: Request) -> bool:
        return False  # Nothing is exempt

    app_with_middleware.add_middleware(
        MaintenanceModeMiddleware, maintenance_mode=True, exempt_callback=exempt_nothing_callback
    )
    async with AsyncClient(transport=ASGITransport(app=app_with_middleware), base_url="http://test") as client:
        response = await client.get("/regular")
        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE


@pytest.mark.anyio
@pytest.mark.parametrize(
    "is_async_callback, response_type", [(False, "html"), (True, "html"), (False, "json"), (True, "json")]
)
async def test_middleware_custom_response_callback(
    app_with_middleware: FastAPI, is_async_callback: bool, response_type: str
):
    """Test custom response callbacks (sync/async) returning different response types (HTML/JSON)."""

    def sync_html_response(request: Request) -> Response:
        return HTMLResponse(content=CUSTOM_HTML_CONTENT, status_code=status.HTTP_503_SERVICE_UNAVAILABLE)

    async def async_html_response(request: Request) -> Response:
        await asyncio.sleep(0.001)
        return HTMLResponse(content=CUSTOM_HTML_CONTENT, status_code=status.HTTP_503_SERVICE_UNAVAILABLE)

    def sync_json_response(request: Request) -> Response:
        return JSONResponse(content=CUSTOM_JSON_CONTENT, status_code=status.HTTP_503_SERVICE_UNAVAILABLE)

    async def async_json_response(request: Request) -> Response:
        await asyncio.sleep(0.001)
        return JSONResponse(content=CUSTOM_JSON_CONTENT, status_code=status.HTTP_503_SERVICE_UNAVAILABLE)

    if response_type == "html":
        callback = async_html_response if is_async_callback else sync_html_response
        expected_content = CUSTOM_HTML_CONTENT
        expected_media_type = "text/html"
    else:  # json
        callback = async_json_response if is_async_callback else sync_json_response
        expected_content = CUSTOM_JSON_CONTENT
        expected_media_type = "application/json"

    app_with_middleware.add_middleware(
        MaintenanceModeMiddleware,
        maintenance_mode=True,  # Maintenance is ON
        response_callback=callback,
    )

    async with AsyncClient(transport=ASGITransport(app=app_with_middleware), base_url="http://test") as client:
        response = await client.get("/regular")
        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
        assert response.headers["content-type"].startswith(expected_media_type)
        if response_type == "html":
            assert response.text == expected_content
        else:
            assert response.json() == expected_content


@pytest.mark.anyio
async def test_middleware_reacts_to_core_set_maintenance_mode(app_with_middleware: FastAPI, temp_file_path: str):
    """Test that middleware reacts to changes in maintenance state when modified via core functions."""
    # Use file backend for dynamic changes
    configure_backend("file", file_path=temp_file_path)
    await set_maintenance_mode(False)  # Start with OFF

    # Middleware uses the default configured backend
    app_with_middleware.add_middleware(MaintenanceModeMiddleware)

    async with AsyncClient(transport=ASGITransport(app=app_with_middleware), base_url="http://test") as client:
        response = await client.get("/regular")
        assert response.status_code == status.HTTP_200_OK

        # Now turn maintenance mode ON using core function
        await set_maintenance_mode(True)
        response_after_on = await client.get("/regular")
        assert response_after_on.status_code == status.HTTP_503_SERVICE_UNAVAILABLE

        # Turn it OFF again
        await set_maintenance_mode(False)
        response_after_off = await client.get("/regular")
        assert response_after_off.status_code == status.HTTP_200_OK


@pytest.mark.anyio
async def test_middleware_path_regex_collection_on_init(tmp_path: SyncPath):
    """Test that decorated paths are correctly recognized by the middleware."""
    # This test verifies that decorated paths are correctly handled by the middleware
    # We'll check this through behavior instead of internal state
    app = FastAPI()

    @app.get("/p1/off")
    @force_maintenance_mode_off
    async def p1_off():
        return {"status": "off_path"}

    @app.get("/p2/on")
    @force_maintenance_mode_on
    async def p2_on():
        return {"status": "on_path"}

    @app.get("/p3/regular")
    async def p3_reg():
        return {"status": "regular_path"}

    @app.get("/p4/{item_id}/off")
    @force_maintenance_mode_off
    async def p4_off_path_param(item_id: str):
        return {"status": "off_path_param", "item_id": item_id}

    # Add the middleware properly
    app.add_middleware(MaintenanceModeMiddleware, maintenance_mode=True)

    # Test the behavior of the middleware on different paths through HTTP requests
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # This path has force_maintenance_mode_off - should be accessible
        response_p1 = await client.get("/p1/off")
        assert response_p1.status_code == status.HTTP_200_OK
        assert response_p1.json() == {"status": "off_path"}

        # This path has force_maintenance_mode_on - should be in maintenance
        response_p2 = await client.get("/p2/on")
        assert response_p2.status_code == status.HTTP_503_SERVICE_UNAVAILABLE

        # Regular path with no decorator - should be in maintenance (because maintenance_mode=True)
        response_p3 = await client.get("/p3/regular")
        assert response_p3.status_code == status.HTTP_503_SERVICE_UNAVAILABLE

        # Path with param and force_maintenance_mode_off - should be accessible
        response_p4 = await client.get("/p4/test_id/off")
        assert response_p4.status_code == status.HTTP_200_OK
        assert response_p4.json() == {"status": "off_path_param", "item_id": "test_id"}

        # Path similar to p4 but incorrect structure - should be in maintenance
        response_p4_wrong = await client.get("/p4/off")
        assert response_p4_wrong.status_code == status.HTTP_503_SERVICE_UNAVAILABLE


@pytest.mark.anyio
async def test_middleware_force_on_takes_precedence_over_exempt_callback_and_force_off_decorator(
    app_with_middleware: FastAPI,
):
    """Test that `force_maintenance_mode_on` takes precedence over `exempt_callback` and `force_maintenance_mode_off`."""
    # Scenario: Path is forced ON by decorator.
    # It also has a force_maintenance_mode_off decorator (which is contradictory, last one usually wins or it's an error)
    # And an exempt_callback would exempt it.
    # The `force_maintenance_mode_on` on the route itself should be the ultimate decider for that route.

    # Let's redefine an endpoint for this specific scenario:
    @app_with_middleware.get("/complex_force_on")
    @force_maintenance_mode_on  # Then force on (top-most decorator wins in attribute setting)
    @force_maintenance_mode_off  # Attempt to force off
    async def complex_force_on_endpoint():  # pragma: no cover
        return {"message": "Complex force on - should not be seen"}

    def always_exempt_callback(request: Request) -> bool:
        return True  # Exempts everything if it were to be checked

    # Middleware uses the app instance which now has the new route
    # Initialize middleware with general maintenance OFF, but path is forced ON
    app_with_middleware.add_middleware(
        MaintenanceModeMiddleware,
        maintenance_mode=False,  # General maintenance is OFF
        exempt_callback=always_exempt_callback,
    )

    async with AsyncClient(
        transport=ASGITransport(app=app_with_middleware), base_url="http://test"
    ) as client:  # Test with the middleware as ASGI app
        response_complex = await client.get("/complex_force_on")
        assert response_complex.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
        assert response_complex.json() == DEFAULT_JSON_RESPONSE_CONTENT
        response_regular = await client.get("/regular")
        assert response_regular.status_code == status.HTTP_200_OK

        # Regular endpoint should be fine because general maintenance is False and callback would exempt
        # but here, because the callback also exempts, and general is false, it should pass.
        # The key is that forced_on on a path overrides everything else for that path.

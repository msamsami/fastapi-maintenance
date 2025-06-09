import asyncio
import os
from pathlib import Path as SyncPath

import pytest
from fastapi import FastAPI, Request, Response, status
from fastapi.responses import HTMLResponse, JSONResponse
from httpx import ASGITransport, AsyncClient

from fastapi_maintenance import (
    MaintenanceModeMiddleware,
    force_maintenance_mode_off,
    force_maintenance_mode_on,
    maintenance_mode_on,
    set_maintenance_mode,
)
from fastapi_maintenance._constants import DEFAULT_JSON_RESPONSE_CONTENT
from fastapi_maintenance._core import _backend as core_backend  # For reset
from fastapi_maintenance._core import configure_backend
from fastapi_maintenance.backends import MAINTENANCE_MODE_ENV_VAR_NAME, LocalFileBackend

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
    async def regular_endpoint():
        return {"message": "Hello World"}

    @app.get("/exempt_by_decorator")
    @force_maintenance_mode_off
    async def exempt_by_decorator_endpoint():
        return {"message": "Always works"}

    @app.get("/forced_on_by_decorator")
    @force_maintenance_mode_on
    async def forced_on_by_decorator_endpoint():
        return {"message": "Should not be called"}

    return app


@pytest.mark.anyio
async def test_middleware_maintenance_mode_on_init(app_with_middleware: FastAPI):
    """Test that middleware initialized with `enable_maintenance=True` blocks regular routes."""
    app_with_middleware.add_middleware(MaintenanceModeMiddleware, enable_maintenance=True)
    async with AsyncClient(transport=ASGITransport(app=app_with_middleware), base_url="http://test") as client:
        response = await client.get("/regular")
        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
        assert response.json() == DEFAULT_JSON_RESPONSE_CONTENT


@pytest.mark.anyio
async def test_middleware_maintenance_mode_off_init(app_with_middleware: FastAPI):
    """Test that middleware initialized with `enable_maintenance=False` allows regular routes."""
    app_with_middleware.add_middleware(MaintenanceModeMiddleware, enable_maintenance=False)
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
    app_with_middleware.add_middleware(MaintenanceModeMiddleware, enable_maintenance=True)
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
@pytest.mark.parametrize("is_async_handler", [False, True])
async def test_middleware_exempt_handler(app_with_middleware: FastAPI, is_async_handler: bool):
    """Test exempt_handler with both synchronous and asynchronous handler functions."""

    def sync_exempt_handler(request: Request) -> bool:
        return request.url.path == "/regular"  # Exempt only /regular

    async def async_exempt_handler(request: Request) -> bool:
        await asyncio.sleep(0.001)
        return request.url.path == "/regular"

    handler = async_exempt_handler if is_async_handler else sync_exempt_handler
    app_with_middleware.add_middleware(
        MaintenanceModeMiddleware,
        enable_maintenance=True,  # Maintenance is ON
        exempt_handler=handler,
    )

    async with AsyncClient(transport=ASGITransport(app=app_with_middleware), base_url="http://test") as client:
        # /regular is exempt by handler, should work
        response_regular = await client.get("/regular")
        assert response_regular.status_code == status.HTTP_200_OK
        assert response_regular.json() == {"message": "Hello World"}

        # /exempt_by_decorator is NOT exempt by this handler, but IS by its own decorator
        # Decorator @force_maintenance_mode_off should take precedence over general maintenance mode
        response_exempt_deco = await client.get("/exempt_by_decorator")
        assert response_exempt_deco.status_code == status.HTTP_200_OK
        assert response_exempt_deco.json() == {"message": "Always works"}


@pytest.mark.anyio
async def test_middleware_exempt_handler_path_not_exempt(app_with_middleware: FastAPI):
    """Test that `exempt_handler` returning False keeps routes in maintenance mode."""

    def exempt_nothing_handler(request: Request) -> bool:
        return False  # Nothing is exempt

    app_with_middleware.add_middleware(
        MaintenanceModeMiddleware, enable_maintenance=True, exempt_handler=exempt_nothing_handler
    )
    async with AsyncClient(transport=ASGITransport(app=app_with_middleware), base_url="http://test") as client:
        response = await client.get("/regular")
        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE


@pytest.mark.anyio
@pytest.mark.parametrize(
    "is_async_handler, response_type", [(False, "html"), (True, "html"), (False, "json"), (True, "json")]
)
async def test_middleware_custom_response_handler(
    app_with_middleware: FastAPI, is_async_handler: bool, response_type: str
):
    """Test custom response handlers (sync/async) returning different response types (HTML/JSON)."""

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
        handler = async_html_response if is_async_handler else sync_html_response
        expected_content = CUSTOM_HTML_CONTENT
        expected_media_type = "text/html"
    else:  # json
        handler = async_json_response if is_async_handler else sync_json_response
        expected_content = CUSTOM_JSON_CONTENT
        expected_media_type = "application/json"

    app_with_middleware.add_middleware(
        MaintenanceModeMiddleware,
        enable_maintenance=True,  # Maintenance is ON
        response_handler=handler,
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
    file_path = str(tmp_path / "maintenance.txt")
    configure_backend("file", file_path=file_path)
    await set_maintenance_mode(True)
    app.add_middleware(MaintenanceModeMiddleware)

    # Test the behavior of the middleware on different paths through HTTP requests
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # This path has force_maintenance_mode_off - should be accessible
        response_p1 = await client.get("/p1/off")
        assert response_p1.status_code == status.HTTP_200_OK
        assert response_p1.json() == {"status": "off_path"}

        # This path has force_maintenance_mode_on - should be in maintenance
        response_p2 = await client.get("/p2/on")
        assert response_p2.status_code == status.HTTP_503_SERVICE_UNAVAILABLE

        # Regular path with no decorator - should be in maintenance (because enable_maintenance=True)
        response_p3 = await client.get("/p3/regular")
        assert response_p3.status_code == status.HTTP_503_SERVICE_UNAVAILABLE

        # Path with param and force_maintenance_mode_off - should be accessible
        response_p4 = await client.get("/p4/test_id/off")
        assert response_p4.status_code == status.HTTP_200_OK
        assert response_p4.json() == {"status": "off_path_param", "item_id": "test_id"}

        # Path similar to p4 but incorrect structure - should return 404 not found error
        response_p4_wrong = await client.get("/p4/off")
        assert response_p4_wrong.status_code == status.HTTP_404_NOT_FOUND

    # Test with maintenance off first to cover the endpoint without decorator
    await set_maintenance_mode(False)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # This path has no decorator - should be accessible
        response_p3_off = await client.get("/p3/regular")
        assert response_p3_off.status_code == status.HTTP_200_OK
        assert response_p3_off.json() == {"status": "regular_path"}


@pytest.mark.anyio
async def test_middleware_force_on_takes_precedence_over_exempt_handler_and_force_off_decorator(
    app_with_middleware: FastAPI,
):
    """Test that `force_maintenance_mode_on` takes precedence over `exempt_handler` and `force_maintenance_mode_off`."""
    # Scenario: Path is forced ON by decorator.
    # It also has a force_maintenance_mode_off decorator (which is contradictory, last one usually wins or it's an error)
    # And an exempt_handler would exempt it.
    # The `force_maintenance_mode_on` on the route itself should be the ultimate decider for that route.

    # Let's redefine an endpoint for this specific scenario:
    @app_with_middleware.get("/complex_force_on")
    @force_maintenance_mode_on  # Then force on (top-most decorator wins in attribute setting)
    @force_maintenance_mode_off  # Attempt to force off
    async def complex_force_on_endpoint():
        return {"message": "Complex force on - should not be seen"}

    def always_exempt_handler(request: Request) -> bool:
        return True  # Exempts everything if it were to be checked

    # Middleware uses the app instance which now has the new route
    # Initialize middleware with general maintenance OFF, but path is forced ON
    app_with_middleware.add_middleware(
        MaintenanceModeMiddleware,
        enable_maintenance=False,  # General maintenance is OFF
        exempt_handler=always_exempt_handler,
    )

    async with AsyncClient(
        transport=ASGITransport(app=app_with_middleware), base_url="http://test"
    ) as client:  # Test with the middleware as ASGI app
        response_complex = await client.get("/complex_force_on")
        assert response_complex.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
        assert response_complex.json() == DEFAULT_JSON_RESPONSE_CONTENT
        response_regular = await client.get("/regular")
        assert response_regular.status_code == status.HTTP_200_OK

        # Regular endpoint should be fine because general maintenance is False and handler would exempt
        # but here, because the handler also exempts, and general is false, it should pass.
        # The key is that forced_on on a path overrides everything else for that path.


@pytest.mark.anyio
async def test_context_on_vs_decorator_force_off(app_with_middleware: FastAPI, temp_file_path: str):
    """
    Test that `@force_maintenance_mode_off` overrides `maintenance_mode_on()` context.
    Precedence: @force_off (decorator, level 2) > context_on (level 4)
    """
    configure_backend("file", file_path=temp_file_path)
    await set_maintenance_mode(False)  # Global maintenance is OFF

    # Add middleware. It will use the globally configured backend (file backend)
    # as enable_maintenance is not set and no specific backend is passed to it.
    app_with_middleware.add_middleware(MaintenanceModeMiddleware)

    async with AsyncClient(transport=ASGITransport(app=app_with_middleware), base_url="http://test") as client:
        # Initial check: /exempt_by_decorator (forced_off) is OK, /regular is OK
        assert (await client.get("/exempt_by_decorator")).status_code == status.HTTP_200_OK
        assert (await client.get("/regular")).status_code == status.HTTP_200_OK

        async with maintenance_mode_on():  # Activates maintenance via file backend
            # Inside context: /exempt_by_decorator (forced_off) should still be OK
            response_exempt = await client.get("/exempt_by_decorator")
            assert response_exempt.status_code == status.HTTP_200_OK
            assert response_exempt.json() == {"message": "Always works"}

            # Inside context: /regular should be 503 due to maintenance_mode_on()
            response_regular = await client.get("/regular")
            assert response_regular.status_code == status.HTTP_503_SERVICE_UNAVAILABLE

        # After context: /regular should be OK again (state restored)
        assert (await client.get("/regular")).status_code == status.HTTP_200_OK
        # And /exempt_by_decorator should remain OK
        assert (await client.get("/exempt_by_decorator")).status_code == status.HTTP_200_OK


@pytest.mark.anyio
async def test_context_on_vs_exempt_handler(temp_file_path: str):
    """
    Test that `exempt_handler` overrides `maintenance_mode_on()` context.
    Precedence: exempt_handler (level 3) > context_on (level 4)
    """
    configure_backend("file", file_path=temp_file_path)
    await set_maintenance_mode(False)  # Global maintenance is OFF

    app = FastAPI()

    @app.get("/exempted_by_handler_rule")
    async def exempted_route_by_handler():
        return {"message": "Exempted by handler rule"}

    @app.get("/normal_for_handler_context_test")
    async def normal_route_for_handler_context():
        return {"message": "Normal for handler context test"}

    def custom_exempt_handler(request: Request) -> bool:
        return request.url.path == "/exempted_by_handler_rule"

    app.add_middleware(
        MaintenanceModeMiddleware,
        exempt_handler=custom_exempt_handler,
        # Middleware will use configured file backend for its general state
    )

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Initial check: both routes OK
        assert (await client.get("/exempted_by_handler_rule")).status_code == status.HTTP_200_OK
        assert (await client.get("/normal_for_handler_context_test")).status_code == status.HTTP_200_OK

        async with maintenance_mode_on():  # Activates maintenance via file backend
            # Inside context: /exempted_by_handler_rule should still be OK
            response_exempted = await client.get("/exempted_by_handler_rule")
            assert response_exempted.status_code == status.HTTP_200_OK
            assert response_exempted.json() == {"message": "Exempted by handler rule"}

            # Inside context: /normal_for_handler_context_test should be 503
            response_normal = await client.get("/normal_for_handler_context_test")
            assert response_normal.status_code == status.HTTP_503_SERVICE_UNAVAILABLE

        # After context: /normal_for_handler_context_test should be OK again
        assert (await client.get("/normal_for_handler_context_test")).status_code == status.HTTP_200_OK


@pytest.mark.anyio
async def test_context_on_uses_middleware_backend_implicitly(
    app_with_middleware: FastAPI, temp_file_path: str, tmp_path: SyncPath
):
    """
    Test that `maintenance_mode_on()` (with no args) uses the middleware-registered backend.
    """
    middleware_file_path = temp_file_path
    middleware_backend = LocalFileBackend(file_path=middleware_file_path)
    await middleware_backend.set_value(False)  # Middleware's backend state: OFF

    # A different backend, configured as the global fallback.
    # maintenance_mode_on() should NOT use this if middleware has its own.
    other_file_path = str(tmp_path / "other_maintenance_file.txt")
    other_backend = LocalFileBackend(file_path=other_file_path)
    await other_backend.set_value(False)  # Other backend state: OFF
    configure_backend("file", file_path=other_file_path)  # Set as global fallback

    # Add middleware, providing it with its own specific backend.
    # This action registers 'middleware_backend' via register_middleware_backend().
    app_with_middleware.add_middleware(MaintenanceModeMiddleware, backend=middleware_backend)

    async with AsyncClient(transport=ASGITransport(app=app_with_middleware), base_url="http://test") as client:
        # Initial state: all backends OFF, /regular is OK
        assert not await middleware_backend.get_value()
        assert not await other_backend.get_value()
        assert (await client.get("/regular")).status_code == status.HTTP_200_OK

        # maintenance_mode_on() called with no arguments.
        # It should pick 'middleware_backend' because the middleware registered it.
        async with maintenance_mode_on():
            assert await middleware_backend.get_value()  # Middleware's backend became ON
            assert not await other_backend.get_value()  # Global fallback backend remains OFF

            # /regular route should be 503 because middleware_backend (used by middleware) is ON
            response_regular = await client.get("/regular")
            assert response_regular.status_code == status.HTTP_503_SERVICE_UNAVAILABLE

        # After context: middleware_backend restored to OFF
        assert not await middleware_backend.get_value()
        assert not await other_backend.get_value()  # Still OFF
        assert (await client.get("/regular")).status_code == status.HTTP_200_OK


@pytest.mark.anyio
async def test_docs_endpoints_automatically_exempted():
    """Test that FastAPI's documentation endpoints are automatically exempted by default."""
    app = FastAPI()

    @app.get("/api/users")
    async def get_users():
        return {"users": ["user1", "user2"]}

    # Add middleware - docs should be exempt by default
    app.add_middleware(MaintenanceModeMiddleware, enable_maintenance=True)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Regular API endpoint should be blocked
        response = await client.get("/api/users")
        assert response.status_code == 503

        # Documentation endpoints should be automatically accessible
        docs_response = await client.get("/docs")
        assert docs_response.status_code == 200
        assert "Swagger UI" in docs_response.text

        redoc_response = await client.get("/redoc")
        assert redoc_response.status_code == 200
        assert "ReDoc" in redoc_response.text

        openapi_response = await client.get("/openapi.json")
        assert openapi_response.status_code == 200
        assert openapi_response.headers["content-type"] == "application/json"

        oauth_response = await client.get("/docs/oauth2-redirect")
        assert oauth_response.status_code == 200
        assert "OAuth2 Redirect" in oauth_response.text


@pytest.mark.anyio
async def test_custom_exempt_handler_works_with_built_in_exemptions():
    """Test that custom exempt handlers work alongside built-in docs exemptions."""
    app = FastAPI()

    @app.get("/health")
    async def health():
        return {"status": "healthy"}

    @app.get("/api/users")
    async def get_users():
        return {"users": ["user1", "user2"]}

    def custom_exempt_handler(request: Request) -> bool:
        """Custom handler that exempts health endpoints."""
        return request.url.path == "/health"

    # Use custom exemption handler alongside built-in docs exemption
    app.add_middleware(MaintenanceModeMiddleware, enable_maintenance=True, exempt_handler=custom_exempt_handler)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Regular API endpoint should be blocked
        response = await client.get("/api/users")
        assert response.status_code == 503

        # Health endpoint should be accessible (custom exemption)
        health_response = await client.get("/health")
        assert health_response.status_code == 200
        assert health_response.json() == {"status": "healthy"}

        # Documentation endpoints should still be accessible (built-in exemption)
        docs_response = await client.get("/docs")
        assert docs_response.status_code == 200
        assert "Swagger UI" in docs_response.text


@pytest.mark.anyio
async def test_async_exempt_handler_works_with_built_in_exemptions():
    """Test that async custom exempt handlers work alongside built-in docs exemptions."""
    app = FastAPI()

    @app.get("/admin/status")
    async def admin_status():
        return {"admin": "ok"}

    @app.get("/api/users")
    async def get_users():
        return {"users": ["user1", "user2"]}

    async def async_exempt_handler(request: Request) -> bool:
        """Async handler that exempts admin endpoints."""
        # Simulate async operation
        await asyncio.sleep(0.001)
        return request.url.path.startswith("/admin/")

    app.add_middleware(MaintenanceModeMiddleware, enable_maintenance=True, exempt_handler=async_exempt_handler)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Regular API endpoint should be blocked
        response = await client.get("/api/users")
        assert response.status_code == 503

        # Admin endpoint should be accessible (async custom exemption)
        admin_response = await client.get("/admin/status")
        assert admin_response.status_code == 200
        assert admin_response.json() == {"admin": "ok"}

        # Documentation endpoints should still be accessible (built-in exemption)
        docs_response = await client.get("/docs")
        assert docs_response.status_code == 200
        assert "Swagger UI" in docs_response.text


@pytest.mark.anyio
async def test_no_custom_exempt_handler_only_docs_exempted():
    """Test that when no custom exempt handler is provided, only docs are exempted."""
    app = FastAPI()

    @app.get("/health")
    async def health():
        return {"status": "healthy"}

    @app.get("/api/users")
    async def get_users():
        return {"users": ["user1", "user2"]}

    # No custom exempt handler - only built-in docs exemption
    app.add_middleware(MaintenanceModeMiddleware, enable_maintenance=True)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Regular endpoints should be blocked
        response = await client.get("/api/users")
        assert response.status_code == 503

        health_response = await client.get("/health")
        assert health_response.status_code == 503

        # Only documentation endpoints should be accessible
        docs_response = await client.get("/docs")
        assert docs_response.status_code == 200
        assert "Swagger UI" in docs_response.text


@pytest.mark.anyio
async def test_http_errors_exempt_from_maintenance():
    """Test that HTTP error responses (404, 405, etc.) are exempted from maintenance mode."""
    app = FastAPI()

    @app.get("/api/users")
    async def get_users():
        return {"users": ["user1", "user2"]}

    @app.post("/api/users")
    async def create_user():
        return {"message": "User created"}

    @app.get("/api/users/{user_id}")
    async def get_user(user_id: str):
        return {"user_id": user_id}

    @app.get("/health")
    async def health():
        return {"status": "healthy"}

    # Add middleware with maintenance enabled
    app.add_middleware(MaintenanceModeMiddleware, enable_maintenance=True)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Existing endpoints should return maintenance response
        response = await client.get("/api/users")
        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE

        response = await client.post("/api/users")
        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE

        response = await client.get("/api/users/123")
        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE

        response = await client.get("/health")
        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE

        # 404 Cases: Non-existent paths should return 404, not maintenance
        response = await client.get("/nonexistent")
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.json() == {"detail": "Not Found"}

        response = await client.get("/api/nonexistent")
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.json() == {"detail": "Not Found"}

        response = await client.get("/completely/random/path")
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.json() == {"detail": "Not Found"}

        # 405 Cases: Non-existent methods on existing paths should return 405, not maintenance
        response = await client.put("/api/users")
        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED

        response = await client.delete("/api/users/123")
        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED

        response = await client.patch("/health")
        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED

        # Additional HTTP methods that don't exist
        response = await client.options("/api/users")
        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED


@pytest.mark.anyio
async def test_method_not_allowed_exempt_from_maintenance():
    """Test comprehensive 405 Method Not Allowed cases that should be exempted from maintenance."""
    app = FastAPI()

    @app.get("/api/resource")
    async def get_resource():
        return {"data": "resource"}

    @app.post("/api/resource")
    async def create_resource():
        return {"message": "created"}

    @app.get("/api/items/{item_id}")
    async def get_item(item_id: str):
        return {"item_id": item_id}

    @app.put("/api/items/{item_id}")
    async def update_item(item_id: str):
        return {"item_id": item_id, "updated": True}

    # Add middleware with maintenance enabled
    app.add_middleware(MaintenanceModeMiddleware, enable_maintenance=True)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Existing endpoints should return maintenance response
        response = await client.get("/api/resource")
        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE

        response = await client.post("/api/resource")
        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE

        response = await client.get("/api/items/123")
        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE

        response = await client.put("/api/items/123")
        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE

        # 405 Cases: Methods that don't exist on existing paths
        response = await client.put("/api/resource")  # Only GET/POST exist
        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED

        response = await client.delete("/api/resource")  # Only GET/POST exist
        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED

        response = await client.patch("/api/resource")  # Only GET/POST exist
        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED

        response = await client.post("/api/items/123")  # Only GET/PUT exist
        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED

        response = await client.delete("/api/items/123")  # Only GET/PUT exist
        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED

        # HEAD method (should also return 405 for paths that don't support it)
        response = await client.head("/api/items/123")
        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED


@pytest.mark.anyio
async def test_http_errors_with_path_parameters():
    """Test that HTTP errors (404, 405) with path parameters are exempted from maintenance."""
    app = FastAPI()

    @app.get("/api/users/{user_id}")
    async def get_user(user_id: str):
        return {"user_id": user_id}

    @app.get("/api/users/{user_id}/posts/{post_id}")
    async def get_user_post(user_id: str, post_id: str):
        return {"user_id": user_id, "post_id": post_id}

    # Add middleware with maintenance enabled
    app.add_middleware(MaintenanceModeMiddleware, enable_maintenance=True)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Existing parameterized endpoints should return maintenance response
        response = await client.get("/api/users/123")
        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE

        response = await client.get("/api/users/123/posts/456")
        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE

        # 404 Cases: Paths that don't match parameter patterns
        response = await client.get("/api/users")  # Missing required parameter
        assert response.status_code == status.HTTP_404_NOT_FOUND

        response = await client.get("/api/users/123/posts")  # Missing required parameter
        assert response.status_code == status.HTTP_404_NOT_FOUND

        response = await client.get("/api/users/123/comments/456")  # Different resource
        assert response.status_code == status.HTTP_404_NOT_FOUND

        # 405 Cases: Correct paths but wrong methods
        response = await client.post("/api/users/123")  # Only GET exists
        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED

        response = await client.put("/api/users/123/posts/456")  # Only GET exists
        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED

        response = await client.delete("/api/users/123")  # Only GET exists
        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED


@pytest.mark.anyio
async def test_http_errors_with_custom_exempt_handler():
    """Test that HTTP errors (404, 405) are exempted even when custom exempt handler is present."""
    app = FastAPI()

    @app.get("/api/users")
    async def get_users():
        return {"users": ["user1", "user2"]}

    @app.post("/api/users")
    async def create_users():
        return {"message": "User created"}

    @app.get("/health")
    async def health():
        return {"status": "healthy"}

    def custom_exempt_handler(request: Request) -> bool:
        """Custom handler that exempts health endpoints."""
        return request.url.path == "/health"

    # Add middleware with maintenance enabled and custom exempt handler
    app.add_middleware(MaintenanceModeMiddleware, enable_maintenance=True, exempt_handler=custom_exempt_handler)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Existing endpoint not exempted by custom handler should return maintenance
        response = await client.get("/api/users")
        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE

        response = await client.post("/api/users")
        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE

        # Existing endpoint exempted by custom handler should work normally
        response = await client.get("/health")
        assert response.status_code == status.HTTP_200_OK
        assert response.json() == {"status": "healthy"}

        # 404 Cases: Non-existent paths should return 404, not maintenance
        response = await client.get("/nonexistent")
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.json() == {"detail": "Not Found"}

        # Non-existent path that would match custom exempt handler pattern should still return 404
        response = await client.get("/health/status")  # Similar to /health but doesn't exist
        assert response.status_code == status.HTTP_404_NOT_FOUND

        # 405 Cases: Wrong methods should return 405, not maintenance
        response = await client.put("/api/users")  # Only GET/POST exist
        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED

        response = await client.delete("/health")  # Only GET exists
        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED

        response = await client.patch("/api/users")  # Only GET/POST exist
        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED


@pytest.mark.anyio
async def test_http_errors_with_forced_decorators():
    """Test that HTTP errors (404, 405) are exempted even when forced decorators are used on other endpoints."""
    app = FastAPI()

    @app.get("/api/users")
    async def get_users():
        return {"users": ["user1", "user2"]}

    @app.post("/api/users")
    async def create_users():
        return {"message": "User created"}

    @app.get("/health")
    @force_maintenance_mode_off
    async def health():
        return {"status": "healthy"}

    @app.get("/admin/maintenance")
    @force_maintenance_mode_on
    async def admin_maintenance():
        return {"message": "Should not be seen"}

    # Add middleware with maintenance disabled (but forced decorators should override)
    app.add_middleware(MaintenanceModeMiddleware, enable_maintenance=False)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Regular endpoints should work (maintenance disabled)
        response = await client.get("/api/users")
        assert response.status_code == status.HTTP_200_OK

        response = await client.post("/api/users")
        assert response.status_code == status.HTTP_200_OK

        # Forced off endpoint should work
        response = await client.get("/health")
        assert response.status_code == status.HTTP_200_OK

        # Forced on endpoint should return maintenance
        response = await client.get("/admin/maintenance")
        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE

        # 404 Cases: Non-existent paths should return 404
        response = await client.get("/nonexistent")
        assert response.status_code == status.HTTP_404_NOT_FOUND

        response = await client.get("/admin/nonexistent")
        assert response.status_code == status.HTTP_404_NOT_FOUND

        # 405 Cases: Wrong methods should return 405
        response = await client.put("/api/users")  # Only GET/POST exist
        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED

        response = await client.delete("/health")  # Only GET exists
        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED

        # HTTP errors now take precedence over forced decorators (correct behavior)
        response = await client.post("/admin/maintenance")  # Only GET exists, returns 405 even though path is forced ON
        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED


@pytest.mark.anyio
async def test_http_error_behavior_consistency():
    """Test that HTTP error behavior (404, 405) is consistent between maintenance on/off states."""
    app = FastAPI()

    @app.get("/api/users")
    async def get_users():
        return {"users": ["user1", "user2"]}

    @app.post("/api/users")
    async def create_users():
        return {"message": "User created"}

    # Test with maintenance OFF first
    app.add_middleware(MaintenanceModeMiddleware, enable_maintenance=False)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Existing endpoints should work
        response = await client.get("/api/users")
        assert response.status_code == status.HTTP_200_OK

        response = await client.post("/api/users")
        assert response.status_code == status.HTTP_200_OK

        # HTTP errors when maintenance is OFF
        response_404_off = await client.get("/nonexistent")
        assert response_404_off.status_code == status.HTTP_404_NOT_FOUND
        assert response_404_off.json() == {"detail": "Not Found"}

        response_405_off = await client.put("/api/users")
        assert response_405_off.status_code == status.HTTP_405_METHOD_NOT_ALLOWED

    # Now test with maintenance ON
    app = FastAPI()

    @app.get("/api/users")
    async def get_users_maintenance_on():
        return {"users": ["user1", "user2"]}

    @app.post("/api/users")
    async def create_users_maintenance_on():
        return {"message": "User created"}

    app.add_middleware(MaintenanceModeMiddleware, enable_maintenance=True)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Existing endpoints should return maintenance
        response = await client.get("/api/users")
        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE

        response = await client.post("/api/users")
        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE

        # HTTP errors when maintenance is ON should be identical to when OFF
        response_404_on = await client.get("/nonexistent")
        assert response_404_on.status_code == status.HTTP_404_NOT_FOUND
        assert response_404_on.json() == {"detail": "Not Found"}

        response_405_on = await client.put("/api/users")
        assert response_405_on.status_code == status.HTTP_405_METHOD_NOT_ALLOWED

        # The error responses should be identical regardless of maintenance state
        assert response_404_off.json() == response_404_on.json()
        assert response_404_off.status_code == response_404_on.status_code
        assert response_405_off.status_code == response_405_on.status_code


@pytest.mark.anyio
async def test_docs_endpoints_still_exempted_with_http_error_logic():
    """Test that docs endpoints are still exempted even with the HTTP error exemption logic."""
    app = FastAPI()

    @app.get("/api/users")
    async def get_users():
        return {"users": ["user1", "user2"]}

    @app.post("/api/users")
    async def create_users():
        return {"message": "User created"}

    # Add middleware with maintenance enabled
    app.add_middleware(MaintenanceModeMiddleware, enable_maintenance=True)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Regular endpoints should return maintenance
        response = await client.get("/api/users")
        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE

        response = await client.post("/api/users")
        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE

        # Docs endpoints should still be accessible (built-in exemption takes precedence)
        docs_response = await client.get("/docs")
        assert docs_response.status_code == status.HTTP_200_OK
        assert "Swagger UI" in docs_response.text

        redoc_response = await client.get("/redoc")
        assert redoc_response.status_code == status.HTTP_200_OK
        assert "ReDoc" in redoc_response.text

        openapi_response = await client.get("/openapi.json")
        assert openapi_response.status_code == status.HTTP_200_OK

        oauth_response = await client.get("/docs/oauth2-redirect")
        assert oauth_response.status_code == status.HTTP_200_OK

        # HTTP errors should still be exempted
        response = await client.get("/nonexistent")
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.json() == {"detail": "Not Found"}

        response = await client.put("/api/users")  # Only GET/POST exist
        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED


@pytest.mark.anyio
async def test_http_errors_take_precedence_over_forced_decorators():
    """Test that HTTP errors (404, 405) take precedence over forced maintenance decorators.

    This test demonstrates the new precedence behavior where HTTP errors are checked first,
    before any forced maintenance decorators are considered.
    """
    app = FastAPI()

    @app.get("/api/forced-on")
    @force_maintenance_mode_on
    async def forced_on_endpoint():
        return {"message": "This endpoint is forced ON"}

    @app.get("/api/forced-off")
    @force_maintenance_mode_off
    async def forced_off_endpoint():
        return {"message": "This endpoint is forced OFF"}

    # Add middleware with general maintenance enabled
    app.add_middleware(MaintenanceModeMiddleware, enable_maintenance=True)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Existing endpoints behave according to their decorators
        response = await client.get("/api/forced-on")  # Forced ON
        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE

        response = await client.get("/api/forced-off")  # Forced OFF
        assert response.status_code == status.HTTP_200_OK
        assert response.json() == {"message": "This endpoint is forced OFF"}

        # HTTP errors take precedence over forced decorators
        # Non-existent path returns 404, not maintenance
        response = await client.get("/api/nonexistent")
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.json() == {"detail": "Not Found"}

        # Wrong method on forced ON path returns 405, not maintenance
        response = await client.post("/api/forced-on")  # Only GET exists
        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED

        # Wrong method on forced OFF path also returns 405
        response = await client.post("/api/forced-off")  # Only GET exists
        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED

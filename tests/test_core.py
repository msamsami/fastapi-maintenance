import os
from pathlib import Path as SyncPath

import pytest
from pytest import LogCaptureFixture

from fastapi_maintenance import (
    configure_backend,
    get_maintenance_mode,
    maintenance_mode_off,
    maintenance_mode_on,
    set_maintenance_mode,
)
from fastapi_maintenance.backends import (
    MAINTENANCE_MODE_ENV_VAR_NAME,
    MAINTENANCE_MODE_LOCAL_FILE_NAME,
    EnvVarBackend,
    LocalFileBackend,
)
from fastapi_maintenance.core import (
    _backend as core_backend,  # For inspecting internal state
)
from fastapi_maintenance.core import _get_default_backend


@pytest.fixture(autouse=True)
def reset_core_backend_and_env():
    """Reset the core backend and environment variables to a clean state between tests."""
    original_backend = core_backend
    original_env = os.environ.copy()
    try:
        # Reset to default (EnvVarBackend)
        configure_backend("env")
        # Clear any env var that might have been set by tests
        if MAINTENANCE_MODE_ENV_VAR_NAME in os.environ:
            del os.environ[MAINTENANCE_MODE_ENV_VAR_NAME]
        yield
    finally:
        # Restore original backend and environment
        globals()["_backend"] = original_backend  # type: ignore
        # This assignment to globals() might not work as expected for module-level globals.
        # A more robust way is to have a setter in the module itself or re-import, but for tests this might suffice.
        # Or, we can explicitly call configure_backend to restore if original_backend was known.
        # For simplicity, we rely on the next test's configure_backend call or explicit setup.
        os.environ.clear()
        os.environ.update(original_env)
        # Ensure subsequent tests start with a clean slate by re-configuring to env default if needed
        configure_backend("env")
        if MAINTENANCE_MODE_ENV_VAR_NAME in os.environ:
            del os.environ[MAINTENANCE_MODE_ENV_VAR_NAME]


@pytest.fixture
def temp_file_path(tmp_path: SyncPath) -> str:
    """Return a temporary file path for testing core function with file backend."""
    return str(tmp_path / "maintenance_core.txt")


@pytest.mark.anyio
async def test_get_default_backend_is_env_var_backend():
    """Test that the default backend is `EnvVarBackend` when not explicitly configured."""
    # This test relies on the initial state of core_backend being None or being reset
    # The autouse fixture should handle resetting it.
    # For this specific test, we explicitly ensure core_backend starts as None
    # to test the lazy initialization path.
    # We need to import core module to modify its _backend attribute
    import fastapi_maintenance.core

    fastapi_maintenance.core._backend = None

    backend = _get_default_backend()
    assert isinstance(backend, EnvVarBackend)
    assert backend.env_var_name is None  # It should use the default env var name
    # Also check that the module's global _backend is now set
    assert fastapi_maintenance.core._backend is backend


@pytest.mark.anyio
async def test_get_maintenance_mode_default_backend_env_var_not_set():
    """Test that `get_maintenance_mode` returns False when using the default `EnvVarBackend` and the env var is not set."""
    # Default backend is EnvVarBackend, env var not set
    assert not await get_maintenance_mode()


@pytest.mark.anyio
async def test_get_maintenance_mode_default_backend_env_var_set_true():
    """Test that `get_maintenance_mode` returns True when using the default `EnvVarBackend` and the env var is set to a truthy value."""
    os.environ[MAINTENANCE_MODE_ENV_VAR_NAME] = "1"
    assert await get_maintenance_mode()


@pytest.mark.anyio
async def test_set_maintenance_mode_default_backend_env_var_logs_warning(caplog: LogCaptureFixture):
    """Test that `set_maintenance_mode` logs a warning when using the default `EnvVarBackend`."""
    # Default backend is EnvVarBackend, which is read-only
    with caplog.at_level("WARNING"):
        await set_maintenance_mode(True)
    assert f"Cannot set maintenance mode state via environment variable {MAINTENANCE_MODE_ENV_VAR_NAME}" in caplog.text
    assert not await get_maintenance_mode()  # State should not have changed


@pytest.mark.anyio
async def test_configure_backend_file_and_set_get(temp_file_path: str):
    """Test configuring a file backend and interacting with it through get/set functions."""
    configure_backend("file", file_path=temp_file_path)
    backend = _get_default_backend()  # After configure, this should be LocalFileBackend
    assert isinstance(backend, LocalFileBackend)
    assert backend.file_path == temp_file_path

    assert not await get_maintenance_mode()  # File created with False

    await set_maintenance_mode(True)
    assert await get_maintenance_mode()
    assert SyncPath(temp_file_path).read_text() == "1"

    await set_maintenance_mode(False)
    assert not await get_maintenance_mode()
    assert SyncPath(temp_file_path).read_text() == "0"


@pytest.mark.anyio
async def test_configure_backend_file_default_name(tmp_path: SyncPath):
    """Test configuring a file backend with default file name."""
    original_cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        configure_backend("file")  # Use default file name
        backend = _get_default_backend()
        assert isinstance(backend, LocalFileBackend)
        assert backend.file_path == MAINTENANCE_MODE_LOCAL_FILE_NAME

        default_file = tmp_path / MAINTENANCE_MODE_LOCAL_FILE_NAME
        assert not await get_maintenance_mode()
        assert default_file.exists() and default_file.read_text() == "0"

        await set_maintenance_mode(True)
        assert await get_maintenance_mode()
        assert default_file.read_text() == "1"
    finally:
        os.chdir(original_cwd)


@pytest.mark.anyio
async def test_configure_backend_env_explicitly():
    """Test explicitly configuring an `EnvVarBackend` with a custom environment variable name."""
    custom_env_var = "CUSTOM_TEST_VAR"
    configure_backend("env", env_var_name=custom_env_var)
    backend = _get_default_backend()
    assert isinstance(backend, EnvVarBackend)
    assert backend.env_var_name == custom_env_var

    os.environ[custom_env_var] = "1"
    assert await get_maintenance_mode()
    del os.environ[custom_env_var]
    assert not await get_maintenance_mode()


@pytest.mark.anyio
async def test_configure_backend_invalid_type():
    """Test that `configure_backend` raises ValueError when provided an invalid backend type."""
    with pytest.raises(ValueError, match="Unsupported backend type: invalid_backend"):
        configure_backend("invalid_backend")


@pytest.mark.anyio
async def test_maintenance_mode_on_off_context_managers_with_file_backend(temp_file_path: str):
    """Test `maintenance_mode_on` and `maintenance_mode_off` context managers with file backend."""
    configure_backend("file", file_path=temp_file_path)
    assert not await get_maintenance_mode()  # Start with maintenance mode OFF

    async with maintenance_mode_on():
        assert await get_maintenance_mode()  # Inside context: ON
    assert not await get_maintenance_mode()  # Outside context: Restored to OFF

    await set_maintenance_mode(True)  # Now set to ON globally
    assert await get_maintenance_mode()

    async with maintenance_mode_off():
        assert not await get_maintenance_mode()  # Inside context: OFF
    assert await get_maintenance_mode()  # Outside context: Restored to ON

    # Test with explicit backend instance passed to context manager
    # This test ensures the global backend isn't affected if a specific one is passed.
    another_file_path = str(SyncPath(temp_file_path).parent / "another_maintenance.txt")
    specific_backend = LocalFileBackend(file_path=another_file_path)
    await specific_backend.set_value(False)  # Ensure this separate backend is off

    # Global is ON
    assert await get_maintenance_mode()
    assert not await get_maintenance_mode(specific_backend)

    async with maintenance_mode_on(backend=specific_backend):
        assert await get_maintenance_mode()  # Global unchanged (still ON)
        assert await get_maintenance_mode(specific_backend)  # Specific backend is ON
    assert await get_maintenance_mode()  # Global unchanged (still ON)
    assert not await get_maintenance_mode(specific_backend)  # Specific backend restored (OFF)

    # Test nested contexts
    await set_maintenance_mode(False)  # Global OFF
    assert not await get_maintenance_mode()
    async with maintenance_mode_on():  # Outer ON
        assert await get_maintenance_mode()
        async with maintenance_mode_off():  # Inner OFF
            assert not await get_maintenance_mode()
        assert await get_maintenance_mode()  # Back to outer ON
    assert not await get_maintenance_mode()  # Back to global OFF


@pytest.mark.anyio
async def test_maintenance_mode_context_managers_with_env_backend_logs_warnings(caplog: LogCaptureFixture):
    """Test that context managers log warnings when used with `EnvVarBackend` (which is read-only)."""
    # Default is EnvVarBackend, should log warnings when trying to set
    os.environ[MAINTENANCE_MODE_ENV_VAR_NAME] = "0"  # Start with OFF
    assert not await get_maintenance_mode()

    with caplog.at_level("WARNING"):
        async with maintenance_mode_on():
            # Attempts to set True, then read. Read will be from env var.
            assert not await get_maintenance_mode()  # Stays OFF because env var is "0"
    assert f"Cannot set maintenance mode state via environment variable {MAINTENANCE_MODE_ENV_VAR_NAME}" in caplog.text
    # Check that it tried to set True and then restore to False (original value)
    assert (
        caplog.text.count(f"Cannot set maintenance mode state via environment variable {MAINTENANCE_MODE_ENV_VAR_NAME}")
        == 2
    )

    caplog.clear()
    os.environ[MAINTENANCE_MODE_ENV_VAR_NAME] = "1"  # Start with ON
    assert await get_maintenance_mode()
    with caplog.at_level("WARNING"):
        async with maintenance_mode_off():
            assert await get_maintenance_mode()  # Stays ON because env var is "1"
    assert (
        caplog.text.count(f"Cannot set maintenance mode state via environment variable {MAINTENANCE_MODE_ENV_VAR_NAME}")
        == 2
    )


@pytest.mark.anyio
async def test_override_maintenance_mode_exception_handling(temp_file_path: str):
    """Test that context managers properly restore state even when exceptions occur."""
    configure_backend("file", file_path=temp_file_path)
    await set_maintenance_mode(False)  # Initial state: OFF

    class MyException(Exception):
        pass

    with pytest.raises(MyException):
        async with maintenance_mode_on():
            assert await get_maintenance_mode()  # Should be ON
            raise MyException("Test exception")

    # Check if state was restored despite the exception
    assert not await get_maintenance_mode()  # Should be OFF

    # Check with initial state True
    await set_maintenance_mode(True)  # Initial state: ON
    with pytest.raises(MyException):
        async with maintenance_mode_off():
            assert not await get_maintenance_mode()  # Should be OFF
            raise MyException("Test exception")
    assert await get_maintenance_mode()  # Should be ON

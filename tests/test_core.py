import os
from pathlib import Path as SyncPath

import pytest
from pytest import LogCaptureFixture

from fastapi_maintenance import get_maintenance_mode, set_maintenance_mode
from fastapi_maintenance._core import (
    _backend as core_backend,  # For inspecting internal state
)
from fastapi_maintenance._core import _get_default_backend, configure_backend
from fastapi_maintenance.backends import (
    MAINTENANCE_MODE_ENV_VAR_NAME,
    EnvVarBackend,
    LocalFileBackend,
)


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
    import fastapi_maintenance._core

    fastapi_maintenance._core._backend = None

    backend = _get_default_backend()
    assert isinstance(backend, EnvVarBackend)
    assert backend.var_name is None  # It should use the default env var name
    # Also check that the module's global _backend is now set
    assert fastapi_maintenance._core._backend is backend


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
async def test_configure_backend_file_requires_file_path(tmp_path: SyncPath):
    """Test that configuring a file backend requires a file path."""
    # The test now verifies that configure_backend("file") without file_path raises TypeError
    with pytest.raises(TypeError, match="file_path"):
        configure_backend("file")  # Should raise TypeError since file_path is now required

    # Verify that providing file_path works correctly
    file_path = str(tmp_path / "maintenance.txt")
    configure_backend("file", file_path=file_path)
    backend = _get_default_backend()
    assert isinstance(backend, LocalFileBackend)
    assert backend.file_path == file_path

    # Verify functionality still works with explicit file_path
    assert not await get_maintenance_mode()
    await set_maintenance_mode(True)
    assert await get_maintenance_mode()
    assert SyncPath(file_path).read_text() == "1"


@pytest.mark.anyio
async def test_configure_backend_env_explicitly():
    """Test explicitly configuring an `EnvVarBackend` with a custom environment variable name."""
    custom_env_var = "CUSTOM_TEST_VAR"
    configure_backend("env", var_name=custom_env_var)
    backend = _get_default_backend()
    assert isinstance(backend, EnvVarBackend)
    assert backend.var_name == custom_env_var

    os.environ[custom_env_var] = "1"
    assert await get_maintenance_mode()
    del os.environ[custom_env_var]
    assert not await get_maintenance_mode()


@pytest.mark.anyio
async def test_configure_backend_invalid_type():
    """Test that `configure_backend` raises ValueError when provided an invalid backend type."""
    with pytest.raises(ValueError, match="Unsupported backend type: 'invalid_backend'"):
        configure_backend("invalid_backend")

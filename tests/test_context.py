import asyncio
import os
from pathlib import Path as SyncPath

import pytest
from pytest import LogCaptureFixture

from fastapi_maintenance import (
    get_maintenance_mode,
    maintenance_mode_on,
    set_maintenance_mode,
)
from fastapi_maintenance._constants import MAINTENANCE_MODE_ENV_VAR_NAME
from fastapi_maintenance._context import is_maintenance_override_ctx_active
from fastapi_maintenance._core import configure_backend
from fastapi_maintenance.backends import LocalFileBackend


@pytest.fixture(autouse=True)
def reset_flag():
    """Reset the context flag for a clean state between tests."""
    from fastapi_maintenance._context import _set_maintenance_override_ctx_flag

    _set_maintenance_override_ctx_flag(False)
    yield


@pytest.fixture
def temp_file_path(tmp_path: SyncPath) -> str:
    """Return a temporary file path for testing core function with file backend."""
    return str(tmp_path / "maintenance_core.txt")


@pytest.mark.anyio
async def test_maintenance_mode_on_basic_with_file_backend(temp_file_path: str):
    """Test basic functionality of `maintenance_mode_on` context manager with file backend."""
    configure_backend("file", file_path=temp_file_path)
    assert not await get_maintenance_mode()  # Start with maintenance mode OFF
    assert not is_maintenance_override_ctx_active()  # Context flag starts inactive

    async with maintenance_mode_on():
        assert await get_maintenance_mode()  # Inside context: ON
        assert is_maintenance_override_ctx_active()  # Context flag is active

    assert not await get_maintenance_mode()  # Outside context: Restored to OFF
    assert not is_maintenance_override_ctx_active()  # Context flag back to inactive


@pytest.mark.anyio
async def test_maintenance_mode_on_with_preexisting_state(temp_file_path: str):
    """Test `maintenance_mode_on` with already enabled maintenance mode."""
    configure_backend("file", file_path=temp_file_path)
    # First set maintenance mode to ON globally
    await set_maintenance_mode(True)
    assert await get_maintenance_mode()

    # Enter context
    async with maintenance_mode_on():
        assert await get_maintenance_mode()  # Inside context: still ON

    # After context: should remain ON since that was the original state
    assert await get_maintenance_mode()


@pytest.mark.anyio
async def test_maintenance_mode_on_with_explicit_backend(temp_file_path: str):
    """Test `maintenance_mode_on` with an explicitly provided backend."""
    # Configure global backend
    configure_backend("file", file_path=temp_file_path)
    await set_maintenance_mode(True)  # Global state: ON

    # Create separate backend for context manager
    another_file_path = str(SyncPath(temp_file_path).parent / "another_maintenance.txt")
    specific_backend = LocalFileBackend(file_path=another_file_path)
    await specific_backend.set_value(False)  # Ensure specific backend is OFF

    # Global is ON, specific backend is OFF
    assert await get_maintenance_mode()
    assert not await get_maintenance_mode(specific_backend)

    # Use context with specific backend
    async with maintenance_mode_on(backend=specific_backend):
        assert await get_maintenance_mode()  # Global unchanged (still ON)
        assert await get_maintenance_mode(specific_backend)  # Specific backend is ON

    # After context: global unchanged, specific backend restored
    assert await get_maintenance_mode()  # Global unchanged (still ON)
    assert not await get_maintenance_mode(specific_backend)  # Specific backend restored (OFF)


@pytest.mark.anyio
async def test_maintenance_mode_on_nested_contexts(temp_file_path: str):
    """Test nested `maintenance_mode_on` context managers."""
    configure_backend("file", file_path=temp_file_path)
    await set_maintenance_mode(False)  # Global state: OFF
    assert not await get_maintenance_mode()

    # Enter outer context
    async with maintenance_mode_on():
        assert await get_maintenance_mode()  # Outer context: ON
        assert is_maintenance_override_ctx_active()

        # Enter inner context with same backend
        async with maintenance_mode_on():
            assert await get_maintenance_mode()  # Inner context: still ON
            assert is_maintenance_override_ctx_active()

        # After inner: still ON
        assert await get_maintenance_mode()
        assert is_maintenance_override_ctx_active()

    # After outer: restored to OFF
    assert not await get_maintenance_mode()
    assert not is_maintenance_override_ctx_active()


@pytest.mark.anyio
async def test_maintenance_mode_context_manager_with_env_backend_logs_warnings(caplog: LogCaptureFixture):
    """Test that context manager logs warnings when used with `EnvVarBackend` (which is read-only)."""
    # Configure global backend
    configure_backend("env")
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
        async with maintenance_mode_on():
            assert await get_maintenance_mode()  # Stays ON because env var is "1"
    assert (
        caplog.text.count(f"Cannot set maintenance mode state via environment variable {MAINTENANCE_MODE_ENV_VAR_NAME}")
        == 2
    )


@pytest.mark.anyio
async def test_override_maintenance_mode_exception_handling(temp_file_path: str):
    """Test that context manager properly restores state even when exceptions occur."""
    configure_backend("file", file_path=temp_file_path)
    await set_maintenance_mode(False)  # Initial state: OFF

    class MyException(Exception):
        pass

    with pytest.raises(MyException):
        async with maintenance_mode_on():
            assert await get_maintenance_mode()  # Should be ON
            assert is_maintenance_override_ctx_active()
            raise MyException("Test exception")

    # Check if state was restored despite the exception
    assert not await get_maintenance_mode()  # Should be OFF
    assert not is_maintenance_override_ctx_active()  # Flag should be reset


@pytest.mark.anyio
async def test_maintenance_mode_context_flag_directly():
    """Test the context flag is properly set/unset by the context manager."""
    # Outside of context manager, the flag should be False
    assert not is_maintenance_override_ctx_active()

    async with maintenance_mode_on():
        # Inside context manager, the flag should be True
        assert is_maintenance_override_ctx_active()

    # After context manager, the flag should be reset to False
    assert not is_maintenance_override_ctx_active()


@pytest.mark.anyio
async def test_maintenance_mode_on_with_dual_backends(temp_file_path: str):
    """Test using `maintenance_mode_on` with different backends concurrently."""
    # Set up two different backends
    main_file_path = temp_file_path
    second_file_path = str(SyncPath(temp_file_path).parent / "second_maintenance.txt")

    main_backend = LocalFileBackend(file_path=main_file_path)
    second_backend = LocalFileBackend(file_path=second_file_path)

    # Configure global backend to use main_backend
    configure_backend("file", file_path=main_file_path)

    # Set initial states
    await main_backend.set_value(False)  # Main backend OFF
    await second_backend.set_value(False)  # Second backend OFF

    # Verify initial states
    assert not await get_maintenance_mode(main_backend)  # Main backend is OFF
    assert not await get_maintenance_mode(second_backend)  # Second backend is OFF

    async with maintenance_mode_on(backend=second_backend):
        assert not await get_maintenance_mode(main_backend)  # Main backend still OFF
        assert await get_maintenance_mode(second_backend)  # Second backend now ON

        # Change main backend inside context
        await main_backend.set_value(True)  # Set main backend ON

        # Both should now be ON but for different reasons
        assert await get_maintenance_mode(main_backend)  # Main backend manually set ON
        assert await get_maintenance_mode(second_backend)  # Second backend ON via context

    # After context: main should still be ON, second back to OFF
    assert await get_maintenance_mode(main_backend)  # Main backend remains ON
    assert not await get_maintenance_mode(second_backend)  # Second backend restored to OFF


@pytest.mark.anyio
async def test_maintenance_mode_on_with_asyncio_cancel():
    """Test that context manager handles asyncio cancellation."""
    configure_backend("env")  # Use env backend for simplicity

    async def task_with_context():
        async with maintenance_mode_on():
            assert is_maintenance_override_ctx_active()
            # Wait indefinitely to allow cancellation
            await asyncio.sleep(10)

    # Start the task
    task = asyncio.create_task(task_with_context())

    # Allow a tiny bit of time for the context to start
    await asyncio.sleep(0.01)
    assert is_maintenance_override_ctx_active()  # Flag should be set

    # Cancel the task
    task.cancel()

    # Allow time for cancellation to propagate
    try:
        await task
    except asyncio.CancelledError:
        pass

    # Flag should be reset after cancellation
    assert not is_maintenance_override_ctx_active()

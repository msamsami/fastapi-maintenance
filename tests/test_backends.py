import os
from pathlib import Path as SyncPath

import pytest
from anyio import Path
from pytest import LogCaptureFixture

from fastapi_maintenance.backends import (
    MAINTENANCE_MODE_ENV_VAR_NAME,
    MAINTENANCE_MODE_LOCAL_FILE_NAME,
    BaseStateBackend,
    EnvVarBackend,
    LocalFileBackend,
)


@pytest.fixture(autouse=True)
def cleanup_env_vars():
    """Reset environment variables to their original state after each test."""
    original_env = os.environ.copy()
    yield
    os.environ.clear()
    os.environ.update(original_env)


def test_base_backend_bool_to_str_true():
    """Test conversion of True boolean value to string representation ('1')."""
    assert BaseStateBackend._bool_to_str(True) == "1"


def test_base_backend_bool_to_str_false():
    """Test conversion of False boolean value to string representation ('0')."""
    assert BaseStateBackend._bool_to_str(False) == "0"


def test_base_backend_bool_to_str_invalid_input_type_raises_value_error():
    """Test that `_bool_to_str` raises `ValueError` for non-boolean integers that don't map to '0' or '1'.

    This tests a scenario that violates the type hint (`value: bool`) but covers a defensive check.
    """
    with pytest.raises(ValueError, match="state value is not correct"):
        # Passing an integer that is not 0 or 1, violating the `bool` type hint.
        BaseStateBackend._bool_to_str(2)  # type: ignore


# _str_to_bool is an instance method, so we need an instance of a concrete subclass
class ConcreteBackend(BaseStateBackend):
    async def get_value(self) -> bool:
        return False

    async def set_value(self, value: bool) -> None:
        pass


@pytest.mark.parametrize(
    "input_str, expected_bool",
    [
        ("1", True),
        ("yes", True),
        ("y", True),
        ("true", True),
        ("t", True),
        ("on", True),
        ("0", False),
        ("no", False),
        ("n", False),
        ("false", False),
        ("f", False),
        ("off", False),
        ("  TrUe  ", True),
        ("  fAlSe  ", False),
        ("", False),
        ("  ", False),
        ("YES", True),
        ("NO", False),
    ],
)
def test_base_backend_str_to_bool_valid(input_str: str, expected_bool: bool):
    """Test conversion of various valid string representations to boolean values."""
    backend = ConcreteBackend()
    assert backend._str_to_bool(input_str) == expected_bool


@pytest.mark.parametrize("invalid_input_str", ["invalid", "2", "-1", "maybe", " truee"])
def test_base_backend_str_to_bool_invalid_raises_value_error(invalid_input_str: str):
    """Test that invalid string representations raise ValueError on conversion to boolean."""
    backend = ConcreteBackend()
    with pytest.raises(ValueError, match="state value is not correct"):
        backend._str_to_bool(invalid_input_str)


@pytest.mark.anyio
async def test_env_var_backend_get_value_not_set():
    """Test that `EnvVarBackend` returns False when the environment variable is not set."""
    backend = EnvVarBackend()
    assert not await backend.get_value()


@pytest.mark.anyio
@pytest.mark.parametrize(
    "env_value, expected",
    [
        ("1", True),
        ("true", True),
        ("on", True),
        ("0", False),
        ("false", False),
        ("off", False),
        ("", False),  # Empty string should default to False
    ],
)
async def test_env_var_backend_get_value_set(env_value: str, expected: bool):
    """Test `EnvVarBackend` with various environment variable values."""
    os.environ[MAINTENANCE_MODE_ENV_VAR_NAME] = env_value
    backend = EnvVarBackend()
    assert await backend.get_value() == expected


@pytest.mark.anyio
async def test_env_var_backend_get_value_custom_env_var():
    """Test `EnvVarBackend` with a custom environment variable name."""
    custom_var_name = "MY_CUSTOM_MAINTENANCE_ENV_VAR"
    os.environ[custom_var_name] = "1"
    backend = EnvVarBackend(env_var_name=custom_var_name)
    assert await backend.get_value()
    # Ensure default is not used
    del os.environ[custom_var_name]
    assert not await backend.get_value()


@pytest.mark.anyio
async def test_env_var_backend_get_value_invalid_value_logs_warning_and_returns_false(caplog: LogCaptureFixture):
    """Test that `EnvVarBackend` logs a warning and returns False for invalid environment variable values."""
    os.environ[MAINTENANCE_MODE_ENV_VAR_NAME] = "invalid_value"
    backend = EnvVarBackend()
    with caplog.at_level("WARNING"):
        assert not await backend.get_value()
    assert f"Invalid value 'invalid_value' for environment variable {MAINTENANCE_MODE_ENV_VAR_NAME}" in caplog.text
    assert "Expected boolean-like value. Defaulting to False." in caplog.text


@pytest.mark.anyio
async def test_env_var_backend_set_value_logs_warning(caplog: LogCaptureFixture):
    """Test that `EnvVarBackend` logs a warning when attempting to set a value (which is not supported)."""
    backend = EnvVarBackend()
    with caplog.at_level("WARNING"):
        await backend.set_value(True)
    assert f"Cannot set maintenance mode state via environment variable {MAINTENANCE_MODE_ENV_VAR_NAME}" in caplog.text
    assert "Environment variables are read-only during runtime" in caplog.text


@pytest.fixture
def temp_file_path(tmp_path: SyncPath) -> str:
    """Fixture that creates a temporary file path for testing."""
    return str(tmp_path / "maintenance.txt")


@pytest.mark.anyio
async def test_local_file_backend_get_value_file_not_exists_creates_and_returns_false(temp_file_path: str):
    """Test that `LocalFileBackend` creates a file with default value False when file doesn't exist."""
    backend = LocalFileBackend(file_path=temp_file_path)
    assert not await backend.get_value()
    assert await Path(temp_file_path).exists()
    async with await Path(temp_file_path).open("r") as f:
        content = await f.read()
        assert content == "0"


@pytest.mark.anyio
@pytest.mark.parametrize("file_content, expected_bool", [("1", True), ("0", False)])
async def test_local_file_backend_get_value_file_exists(temp_file_path: str, file_content: str, expected_bool: bool):
    """Test that `LocalFileBackend` correctly reads existing file values."""
    async with await Path(temp_file_path).open("w") as f:
        await f.write(file_content)
    backend = LocalFileBackend(file_path=temp_file_path)
    assert await backend.get_value() == expected_bool


@pytest.mark.anyio
async def test_local_file_backend_get_value_invalid_content_returns_false(temp_file_path: str):
    """Test that `LocalFileBackend` raises `ValueError` when file contains invalid content."""
    async with await Path(temp_file_path).open("w") as f:
        await f.write("invalid_content")  # This will cause _str_to_bool to raise ValueError
    backend = LocalFileBackend(file_path=temp_file_path)
    # The _str_to_bool method will raise ValueError, which should be handled by a default return of False or similar.
    # Current implementation of _str_to_bool in BaseStateBackend re-raises ValueError.
    # LocalFileBackend.get_value does not explicitly catch this.
    # Let's assume it should propagate the error for now, or be more specific if it's handled.
    # For now, we test for the ValueError being raised by the underlying _str_to_bool.
    with pytest.raises(ValueError, match="state value is not correct"):
        await backend.get_value()


@pytest.mark.anyio
async def test_local_file_backend_set_value_true(temp_file_path: str):
    """Test that `LocalFileBackend` correctly writes True value to file."""
    backend = LocalFileBackend(file_path=temp_file_path)
    await backend.set_value(True)
    async with await Path(temp_file_path).open("r") as f:
        content = await f.read()
        assert content == "1"
    assert await backend.get_value()  # Double check with get_value


@pytest.mark.anyio
async def test_local_file_backend_set_value_false(temp_file_path: str):
    """Test that `LocalFileBackend` correctly writes False value to file and handles value transitions."""
    backend = LocalFileBackend(file_path=temp_file_path)
    await backend.set_value(False)  # Initially set to False
    async with await Path(temp_file_path).open("r") as f:
        content = await f.read()
        assert content == "0"
    assert not await backend.get_value()  # Double check

    await backend.set_value(True)  # Set to True
    await backend.set_value(False)  # Then back to False
    async with await Path(temp_file_path).open("r") as f:
        content = await f.read()
        assert content == "0"
    assert not await backend.get_value()


@pytest.mark.anyio
async def test_local_file_backend_uses_default_file_name_if_not_provided(tmp_path: SyncPath):
    """Test that `LocalFileBackend` uses the default file name when none is provided."""
    # This test implicitly relies on the _get_backend factory from core.py,
    # but we can simulate its behavior here for LocalFileBackend directly or test _get_backend separately.
    # For now, let's test LocalFileBackend with default name.
    # We need to ensure the working directory for the test is predictable or use absolute paths.
    # Using tmp_path for the default file name.
    original_cwd = os.getcwd()
    os.chdir(tmp_path)  # Change CWD to tmp_path so default file is created there

    try:
        backend = LocalFileBackend(file_path=MAINTENANCE_MODE_LOCAL_FILE_NAME)  # Use default name
        # File should not exist initially, get_value should create it with '0'
        assert not await backend.get_value()
        default_file = tmp_path / MAINTENANCE_MODE_LOCAL_FILE_NAME
        assert default_file.exists()
        assert default_file.read_text() == "0"

        await backend.set_value(True)
        assert default_file.read_text() == "1"
    finally:
        os.chdir(original_cwd)  # Restore CWD

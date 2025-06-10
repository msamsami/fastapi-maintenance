"""
Unit tests for the CLI module using Typer testing approach.
"""

import os
from pathlib import Path as SyncPath
from unittest.mock import Mock, patch

import pytest
import typer
from typer.testing import CliRunner

from fastapi_maintenance import __version__
from fastapi_maintenance._constants import MAINTENANCE_MODE_ENV_VAR_NAME
from fastapi_maintenance.cli import app, main, status, version_callback


@pytest.fixture
def cli_runner():
    """Create a CliRunner instance for testing the CLI."""
    return CliRunner()


@pytest.fixture(autouse=True)
def reset_env_vars():
    """Reset environment variables to clean state between tests."""
    original_env = os.environ.copy()
    try:
        # Clear maintenance mode env var if it exists
        if MAINTENANCE_MODE_ENV_VAR_NAME in os.environ:
            del os.environ[MAINTENANCE_MODE_ENV_VAR_NAME]
        yield
    finally:
        # Restore original environment
        os.environ.clear()
        os.environ.update(original_env)


@pytest.fixture
def temp_maintenance_file(tmp_path: SyncPath) -> str:
    """Create a temporary file path for file backend testing."""
    return str(tmp_path / "maintenance_cli_test.txt")


def test_version_callback_with_true():
    """Test that version_callback prints version and exits when value is True."""
    with pytest.raises(typer.Exit):
        version_callback(True)


def test_version_callback_with_false():
    """Test that version_callback does nothing when value is False."""
    # Should not raise any exception
    version_callback(False)


def test_main_function_with_version_flag(cli_runner: CliRunner):
    """Test the main CLI with --version flag."""
    result = cli_runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert "fastapi-maintenance" in result.output
    # Should contain version number
    assert __version__ in result.output or any(char.isdigit() for char in result.output)


def test_main_function_help(cli_runner: CliRunner):
    """Test the main CLI help output."""
    result = cli_runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "🔧 Manage FastAPI maintenance mode" in result.output
    assert "status" in result.output


def test_main_function_no_args(cli_runner: CliRunner):
    """Test the main CLI with no arguments shows help."""
    result = cli_runner.invoke(app, [])
    assert result.exit_code == 0
    assert "🔧 Manage FastAPI maintenance mode" in result.output


def test_status_command_help(cli_runner: CliRunner):
    """Test the status command help output."""
    result = cli_runner.invoke(app, ["status", "--help"])
    assert result.exit_code == 0
    assert "Check the current maintenance mode status" in result.output
    assert "--backend" in result.output
    assert "--var-name" in result.output
    assert "--file-path" in result.output


@patch("fastapi_maintenance.cli.anyio.run")
@patch("fastapi_maintenance.cli.get_maintenance_mode")
def test_status_command_default_backend_off(mock_get_maintenance, mock_anyio_run, cli_runner: CliRunner):
    """Test status command with default backend when maintenance mode is OFF."""
    mock_anyio_run.return_value = False
    mock_get_maintenance.return_value = False

    result = cli_runner.invoke(app, ["status"])

    assert result.exit_code == 0
    assert "Maintenance mode is OFF" in result.output
    assert "(using default backend)" in result.output
    mock_anyio_run.assert_called_once()


@patch("fastapi_maintenance.cli.anyio.run")
@patch("fastapi_maintenance.cli.get_maintenance_mode")
def test_status_command_default_backend_on(mock_get_maintenance, mock_anyio_run, cli_runner: CliRunner):
    """Test status command with default backend when maintenance mode is ON."""
    mock_anyio_run.return_value = True
    mock_get_maintenance.return_value = True

    result = cli_runner.invoke(app, ["status"])

    assert result.exit_code == 0
    assert "Maintenance mode is ON" in result.output
    assert "(using default backend)" in result.output
    mock_anyio_run.assert_called_once()


@patch("fastapi_maintenance.cli.anyio.run")
@patch("fastapi_maintenance.cli._get_backend")
@patch("fastapi_maintenance.cli.get_maintenance_mode")
def test_status_command_env_backend_default_var(
    mock_get_maintenance, mock_get_backend, mock_anyio_run, cli_runner: CliRunner
):
    """Test status command with env backend using default variable name."""
    mock_backend = Mock()
    mock_get_backend.return_value = mock_backend
    mock_anyio_run.return_value = False
    mock_get_maintenance.return_value = False

    result = cli_runner.invoke(app, ["status", "--backend", "env"])

    assert result.exit_code == 0
    assert "Maintenance mode is OFF" in result.output
    assert f"(env: {MAINTENANCE_MODE_ENV_VAR_NAME})" in result.output
    mock_get_backend.assert_called_once_with("env", var_name=MAINTENANCE_MODE_ENV_VAR_NAME)
    mock_anyio_run.assert_called_once_with(mock_get_maintenance, mock_backend)


@patch("fastapi_maintenance.cli.anyio.run")
@patch("fastapi_maintenance.cli._get_backend")
@patch("fastapi_maintenance.cli.get_maintenance_mode")
def test_status_command_env_backend_custom_var(
    mock_get_maintenance, mock_get_backend, mock_anyio_run, cli_runner: CliRunner
):
    """Test status command with env backend using custom variable name."""
    mock_backend = Mock()
    mock_get_backend.return_value = mock_backend
    mock_anyio_run.return_value = True
    mock_get_maintenance.return_value = True
    custom_var = "CUSTOM_MAINTENANCE_VAR"

    result = cli_runner.invoke(app, ["status", "--backend", "env", "--var-name", custom_var])

    assert result.exit_code == 0
    assert "Maintenance mode is ON" in result.output
    assert f"(env: {custom_var})" in result.output
    mock_get_backend.assert_called_once_with("env", var_name=custom_var)
    mock_anyio_run.assert_called_once_with(mock_get_maintenance, mock_backend)


@patch("fastapi_maintenance.cli.anyio.run")
@patch("fastapi_maintenance.cli._get_backend")
@patch("fastapi_maintenance.cli.get_maintenance_mode")
def test_status_command_file_backend(
    mock_get_maintenance, mock_get_backend, mock_anyio_run, cli_runner: CliRunner, temp_maintenance_file: str
):
    """Test status command with file backend."""
    mock_backend = Mock()
    mock_get_backend.return_value = mock_backend
    mock_anyio_run.return_value = False
    mock_get_maintenance.return_value = False

    result = cli_runner.invoke(app, ["status", "--backend", "file", "--file-path", temp_maintenance_file])

    assert result.exit_code == 0
    assert "maintenance mode is off" in result.output.replace("\n", "").lower()
    assert temp_maintenance_file in result.output.replace("\n", "")
    mock_get_backend.assert_called_once_with("file", file_path=temp_maintenance_file)
    mock_anyio_run.assert_called_once_with(mock_get_maintenance, mock_backend)


def test_status_command_file_backend_missing_path(cli_runner: CliRunner):
    """Test status command with file backend but missing file path."""
    result = cli_runner.invoke(app, ["status", "--backend", "file"])

    assert result.exit_code == 1
    assert "ERROR: --file-path is required when --backend is 'file'" in result.output


def test_status_command_unsupported_backend(cli_runner: CliRunner):
    """Test status command with unsupported backend type."""
    result = cli_runner.invoke(app, ["status", "--backend", "invalid"])

    assert result.exit_code == 1
    assert "ERROR: Unsupported backend: invalid. Use 'env' or 'file'." in result.output


@patch("fastapi_maintenance.cli.anyio.run")
def test_status_command_keyboard_interrupt(mock_anyio_run, cli_runner: CliRunner):
    """Test status command handling KeyboardInterrupt."""
    mock_anyio_run.side_effect = KeyboardInterrupt()

    result = cli_runner.invoke(app, ["status"])

    assert result.exit_code == 1
    assert "Operation cancelled by user" in result.output


@patch("fastapi_maintenance.cli.anyio.run")
def test_status_command_generic_exception(mock_anyio_run, cli_runner: CliRunner):
    """Test status command handling generic exceptions."""
    error_message = "Something went wrong"
    mock_anyio_run.side_effect = Exception(error_message)

    result = cli_runner.invoke(app, ["status"])

    assert result.exit_code == 1
    assert f"ERROR: {error_message}" in result.output


@patch("fastapi_maintenance.cli.anyio.run")
@patch("fastapi_maintenance.cli._get_backend")
@patch("fastapi_maintenance.cli.get_maintenance_mode")
def test_status_command_exception_with_backend(
    mock_get_maintenance, mock_get_backend, mock_anyio_run, cli_runner: CliRunner
):
    """Test status command handling exceptions when using specific backend."""
    error_message = "Backend error"
    mock_backend = Mock()
    mock_get_backend.return_value = mock_backend
    mock_anyio_run.side_effect = Exception(error_message)

    result = cli_runner.invoke(app, ["status", "--backend", "env"])

    assert result.exit_code == 1
    assert f"ERROR: {error_message}" in result.output
    mock_get_backend.assert_called_once_with("env", var_name=MAINTENANCE_MODE_ENV_VAR_NAME)


def test_cli_app_properties():
    """Test CLI app configuration properties."""
    assert app.info.name == "fastapi-maintenance"
    assert app._add_completion is True
    assert app.info.no_args_is_help is True
    assert app.rich_markup_mode == "markdown"


def test_main_callback_no_version():
    """Test main callback function without version flag."""
    # Should not raise any exception
    main(version=False)


@patch("fastapi_maintenance.cli.print")
@patch("fastapi_maintenance.cli.typer.Exit")
def test_version_callback_prints_and_exits(mock_exit, mock_print):
    """Test that version_callback prints version and raises Exit."""
    mock_exit.side_effect = SystemExit()

    with pytest.raises(SystemExit):
        version_callback(True)

    mock_print.assert_called_once()
    mock_exit.assert_called_once()
    # Check that version string was printed
    print_call_args = mock_print.call_args[0][0]
    assert "fastapi-maintenance" in print_call_args


def test_status_function_directly():
    """Test calling the status function directly (not through CLI)."""
    # This tests the function signature and basic structure
    # We can't easily test the full functionality without mocking anyio.run
    # but we can test that the function exists and accepts the expected parameters
    import inspect

    sig = inspect.signature(status)
    params = list(sig.parameters.keys())
    assert "backend" in params
    assert "var_name" in params
    assert "file_path" in params


def test_status_command_all_parameters(cli_runner: CliRunner, temp_maintenance_file: str):
    """Test status command with all possible parameter combinations."""
    # Test with empty backend (should use default)
    result = cli_runner.invoke(
        app, ["status", "--backend", "", "--var-name", "TEST_VAR", "--file-path", temp_maintenance_file]
    )
    # Should use default backend and ignore other params
    assert "using default backend" in result.output


@patch("fastapi_maintenance.cli.anyio.run")
@patch("fastapi_maintenance.cli._get_backend")
@patch("fastapi_maintenance.cli.get_maintenance_mode")
def test_status_env_backend_keyboard_interrupt(
    mock_get_maintenance, mock_get_backend, mock_anyio_run, cli_runner: CliRunner
):
    """Test status command with env backend handling KeyboardInterrupt."""
    mock_backend = Mock()
    mock_get_backend.return_value = mock_backend
    mock_anyio_run.side_effect = KeyboardInterrupt()

    result = cli_runner.invoke(app, ["status", "--backend", "env"])

    assert result.exit_code == 1
    assert "Operation cancelled by user" in result.output


def test_status_command_empty_var_name(cli_runner: CliRunner):
    """Test status command with env backend and empty var name uses default."""
    with patch("fastapi_maintenance.cli.anyio.run") as mock_anyio_run:
        with patch("fastapi_maintenance.cli._get_backend") as mock_get_backend:
            with patch("fastapi_maintenance.cli.get_maintenance_mode"):
                mock_backend = Mock()
                mock_get_backend.return_value = mock_backend
                mock_anyio_run.return_value = False

                result = cli_runner.invoke(app, ["status", "--backend", "env", "--var-name", ""])

                assert result.exit_code == 0
                # Should use default env var name when empty string is provided
                assert f"(env: {MAINTENANCE_MODE_ENV_VAR_NAME})" in result.output
                mock_get_backend.assert_called_once_with("env", var_name="")

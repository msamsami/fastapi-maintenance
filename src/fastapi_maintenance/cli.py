"""
Command-line interface for FastAPI maintenance mode.
"""

import sys

import anyio
import typer
from rich import print
from rich.console import Console
from typing_extensions import Annotated

from . import __version__
from ._constants import MAINTENANCE_MODE_ENV_VAR_NAME
from ._core import get_maintenance_mode
from .backends import _get_backend

err_console = Console(stderr=True)

app = typer.Typer(name="fastapi-maintenance", add_completion=True, no_args_is_help=True, rich_markup_mode="markdown")


def version_callback(value: bool) -> None:
    """Show version and exit."""
    if value:
        print(f"fastapi-maintenance {__version__}")
        raise typer.Exit()


@app.callback(invoke_without_command=True)
def main(
    version: Annotated[
        bool, typer.Option("--version", callback=version_callback, is_eager=True, help="Show version and exit.")
    ] = False,
) -> None:
    """
    🔧 Manage FastAPI maintenance mode.

    A command-line interface for managing your FastAPI application's maintenance mode.
    """
    pass


@app.command("status")
def status(
    backend: Annotated[str, typer.Option(help="Backend to use: env or file.")] = "",
    var_name: Annotated[
        str, typer.Option(help="Environment variable name (for env backend).")
    ] = MAINTENANCE_MODE_ENV_VAR_NAME,
    file_path: Annotated[str, typer.Option(help="Path to the maintenance mode state file (for file backend).")] = "",
) -> None:
    """
    📊 Check the current maintenance mode status.

    Examples:

    * Check status using default backend:
    ```
    $ fastapi-maintenance status
    ```

    * Check status using environment variable backend:
    ```
    $ fastapi-maintenance status --backend env
    ```

    * Check status using custom environment variable:
    ```
    $ fastapi-maintenance status --backend env --var-name MY_MAINTENANCE_VAR
    ```

    * Check status using file backend:
    ```
    $ fastapi-maintenance status --backend file --file-path /tmp/maintenance.txt
    ```
    """
    try:
        if not backend:
            # No options provided, use the default backend
            status_value = anyio.run(get_maintenance_mode)
            backend_text = "[dim](using default backend)[/dim]"
        else:
            # Backend specified, create a temporary backend instance
            if backend == "file":
                if not file_path:
                    err_console.print("❌ [red]ERROR:[/red] --file-path is required when --backend is 'file'")
                    raise typer.Exit(1)
                temp_backend = _get_backend("file", file_path=file_path)
                backend_desc = f"file: {file_path}"
            elif backend == "env":
                temp_backend = _get_backend("env", var_name=var_name)
                var_display = var_name or MAINTENANCE_MODE_ENV_VAR_NAME
                backend_desc = f"env: {var_display}"
            else:
                err_console.print(
                    f"❌ [red]ERROR:[/red] Unsupported backend: [bold]{backend}[/bold]. Use 'env' or 'file'."
                )
                raise typer.Exit(1)
            status_value = anyio.run(get_maintenance_mode, temp_backend)
            backend_text = f"[dim]({backend_desc})[/dim]"

        status_icon = "🟢" if not status_value else "🔴"
        status_text = "[green]OFF[/green]" if not status_value else "[red]ON[/red]"
        print(f"{status_icon} Maintenance mode is {status_text} {backend_text}")

    except KeyboardInterrupt:
        err_console.print("\n⚠️ Operation cancelled by user")
        raise typer.Exit(1)
    except Exception as e:
        err_console.print(f"❌ [red]ERROR:[/red] {str(e)}")
        raise typer.Exit(1)


if __name__ == "__main__":
    try:
        app()
    except KeyboardInterrupt:
        sys.exit(1)

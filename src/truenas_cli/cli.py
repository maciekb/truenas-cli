"""Main CLI application entry point.

This module defines the main Typer application with global options
and registers all subcommands.
"""

import logging
import sys
import time
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.logging import RichHandler
from rich.traceback import install as install_rich_traceback

from truenas_cli import __version__
from truenas_cli.client.exceptions import (
    AuthenticationError,
    ConfigurationError,
    TrueNASError,
)
from truenas_cli.commands import config as config_commands
from truenas_cli.commands import completion as completion_commands
from truenas_cli.commands import system as system_commands
from truenas_cli.commands import pool as pool_commands
from truenas_cli.commands import dataset as dataset_commands
from truenas_cli.commands import share as share_commands

# Install rich traceback handler for better error display
install_rich_traceback(show_locals=False)

# Create console for rich output
console = Console()

# Create main Typer app
app = typer.Typer(
    name="truenas-cli",
    help="Command-line interface for managing TrueNAS SCALE appliances",
    add_completion=True,
    rich_markup_mode="rich",
    no_args_is_help=True,
)

# Add subcommands
app.add_typer(
    config_commands.app,
    name="config",
    help="Manage CLI configuration and profiles",
)
app.add_typer(
    completion_commands.app,
    name="completion",
    help="Manage shell completion",
)
app.add_typer(
    system_commands.app,
    name="system",
    help="System information and monitoring",
)
app.add_typer(
    pool_commands.app,
    name="pool",
    help="Storage pool management",
)
app.add_typer(
    dataset_commands.app,
    name="dataset",
    help="Dataset management",
)
app.add_typer(
    share_commands.app,
    name="share",
    help="NFS and SMB share management",
)


# Global state for CLI context
class CLIContext:
    """Shared context for CLI commands."""

    def __init__(
        self,
        profile: Optional[str] = None,
        output_format: str = "table",
        verbose: int = 0,
        quiet: bool = False,
        timing: bool = False,
        log_file: Optional[Path] = None,
    ):
        self.profile = profile
        self.output_format = output_format
        self.verbose = verbose
        self.quiet = quiet
        self.timing = timing
        self.log_file = log_file
        self.start_time = time.time() if timing else None


# Global callback to handle common options
@app.callback()
def main_callback(
    ctx: typer.Context,
    profile: Optional[str] = typer.Option(
        None,
        "--profile",
        "-p",
        help="Profile to use (overrides active profile)",
        envvar="TRUENAS_PROFILE",
    ),
    output_format: str = typer.Option(
        "table",
        "--output-format",
        "-o",
        help="Output format: table, json, yaml, plain",
        envvar="TRUENAS_OUTPUT_FORMAT",
    ),
    verbose: int = typer.Option(
        0,
        "--verbose",
        "-v",
        count=True,
        help="Increase verbosity (-v, -vv, -vvv for more detail)",
    ),
    quiet: bool = typer.Option(
        False,
        "--quiet",
        "-q",
        help="Suppress non-essential output",
    ),
    timing: bool = typer.Option(
        False,
        "--timing",
        help="Show operation timing information",
    ),
    log_file: Optional[Path] = typer.Option(
        None,
        "--log-file",
        help="Write logs to file",
        exists=False,
    ),
    version: Optional[bool] = typer.Option(
        None,
        "--version",
        "-V",
        help="Show version and exit",
        is_eager=True,
    ),
) -> None:
    """TrueNAS CLI - Manage TrueNAS SCALE appliances from the command line.

    Global options can be used with any command to control behavior.

    Examples:
        truenas-cli --profile production system info
        truenas-cli --output-format json system version
        truenas-cli -vv config list
        truenas-cli --timing pool list
        truenas-cli --log-file debug.log --verbose system info
    """
    if version:
        console.print(f"TrueNAS CLI version {__version__}")
        raise typer.Exit(0)

    # Configure logging based on verbosity
    if verbose == 0 and not quiet:
        log_level = logging.WARNING
    elif verbose == 1:
        log_level = logging.INFO
    elif verbose == 2:
        log_level = logging.DEBUG
    elif verbose >= 3:
        log_level = logging.DEBUG  # TRACE level simulation
    else:
        log_level = logging.ERROR

    # Setup logging handlers
    handlers = []

    # Console handler with rich formatting
    if not quiet:
        console_handler = RichHandler(
            console=console,
            show_time=verbose >= 2,
            show_path=verbose >= 3,
            rich_tracebacks=True,
        )
        console_handler.setLevel(log_level)
        handlers.append(console_handler)

    # File handler if specified
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.DEBUG)  # Always debug to file
        file_formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        file_handler.setFormatter(file_formatter)
        handlers.append(file_handler)

    # Configure root logger
    logging.basicConfig(
        level=log_level,
        format="%(message)s",
        handlers=handlers,
    )

    # Log startup info at debug level
    logger = logging.getLogger(__name__)
    logger.debug(f"TrueNAS CLI v{__version__}")
    logger.debug(f"Verbosity level: {verbose}")
    logger.debug(f"Output format: {output_format}")
    if profile:
        logger.debug(f"Profile: {profile}")

    # Store context for subcommands
    ctx.obj = CLIContext(
        profile=profile,
        output_format=output_format,
        verbose=verbose,
        quiet=quiet,
        timing=timing,
        log_file=log_file,
    )


def main() -> None:
    """Main entry point with error handling.

    This function wraps the Typer app to provide consistent error handling
    and proper exit codes for different error types.
    """
    start_time = time.time()

    try:
        app()
    except AuthenticationError as e:
        console.print(f"[bold red]Authentication Error:[/bold red] {e}")
        if hasattr(e, "__cause__") and e.__cause__:
            console.print(f"[dim]Caused by: {e.__cause__}[/dim]")
        console.print("\n[yellow]Tip:[/yellow] Check your API key with 'truenas-cli config show'")
        sys.exit(2)
    except ConfigurationError as e:
        console.print(f"[bold red]Configuration Error:[/bold red] {e}")
        console.print("\n[yellow]Tip:[/yellow] Initialize configuration with 'truenas-cli config init'")
        sys.exit(3)
    except TrueNASError as e:
        console.print(f"[bold red]TrueNAS Error:[/bold red] {e}")
        if hasattr(e, "__cause__") and e.__cause__:
            console.print(f"[dim]Caused by: {e.__cause__}[/dim]")
        sys.exit(1)
    except KeyboardInterrupt:
        console.print("\n[yellow]Operation cancelled by user[/yellow]")
        sys.exit(130)  # Standard exit code for SIGINT
    except Exception as e:
        console.print(f"[bold red]Unexpected Error:[/bold red] {e}")
        console.print("\n[dim]This is a bug. Please report it with the --verbose flag output.[/dim]")
        sys.exit(1)
    finally:
        # Show timing if requested (check if --timing was in sys.argv)
        if "--timing" in sys.argv:
            elapsed = time.time() - start_time
            console.print(f"\n[dim]Operation completed in {elapsed:.2f}s[/dim]")


if __name__ == "__main__":
    main()

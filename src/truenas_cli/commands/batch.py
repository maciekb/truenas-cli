"""Batch operations commands.

This module provides commands for executing multiple operations from
YAML or JSON configuration files with support for parallel execution.
"""

from pathlib import Path
from typing import Any

import typer
from rich.console import Console

from truenas_cli.client.base import TrueNASClient
from truenas_cli.client.exceptions import ConfigurationError
from truenas_cli.config import ConfigManager
from truenas_cli.utils.batch import BatchOperation, BatchProcessor, load_batch_file

app = typer.Typer(
    help="Execute batch operations from configuration files",
    no_args_is_help=True,
)
console = Console()


def get_client(ctx: typer.Context) -> TrueNASClient:
    """Get configured TrueNAS client from context."""
    config_mgr = ConfigManager()
    cli_ctx = ctx.obj

    try:
        _, profile, _ = config_mgr.get_profile_or_active(cli_ctx.profile)
    except ConfigurationError as e:
        console.print(f"[red]Configuration Error:[/red] {e}")
        raise typer.Exit(3) from e

    return TrueNASClient(profile=profile, verbose=cli_ctx.verbose)


def validate_batch_data(batch_data: dict[str, Any]) -> list[str]:
    """Validate batch file structure.

    Args:
        batch_data: Loaded batch file data

    Returns:
        List of validation error messages (empty if valid)
    """
    errors = []

    # Check for operations key
    if "operations" not in batch_data:
        errors.append("Batch file must contain 'operations' key")
        return errors

    operations = batch_data["operations"]

    if not isinstance(operations, list):
        errors.append("'operations' must be a list")
        return errors

    if len(operations) == 0:
        errors.append("'operations' list cannot be empty")

    # Validate each operation
    for i, op in enumerate(operations):
        op_num = i + 1

        if not isinstance(op, dict):
            errors.append(f"Operation {op_num}: must be a dictionary")
            continue

        # Check for required 'command' field
        if "command" not in op:
            errors.append(f"Operation {op_num}: missing required 'command' field")

        # Check 'args' is a dict if present
        if "args" in op and not isinstance(op["args"], dict):
            errors.append(f"Operation {op_num}: 'args' must be a dictionary")

    return errors


def execute_operation(client: TrueNASClient, operation: BatchOperation) -> Any:
    """Execute a single batch operation by calling the appropriate TrueNAS API method.

    Args:
        client: TrueNAS API client
        operation: Batch operation to execute

    Returns:
        Result of the operation (API response)

    Raises:
        ValueError: If command is not recognized or required arguments are missing
        TrueNASError: If API operation fails
    """
    command = operation.command
    args = operation.args

    # Map commands to actual API client methods
    if command == "dataset create":
        # Required: name or path
        name = args.get("name") or args.get("path")
        if not name:
            raise ValueError("dataset create requires 'name' or 'path' argument")

        # Build dataset_data dict for API
        # Default type to FILESYSTEM if not specified (matches dataset CLI behavior)
        dataset_data: dict[str, Any] = {
            "name": name,
            "type": args.get("type", "FILESYSTEM"),
        }

        # Add optional parameters if provided
        if "compression" in args:
            dataset_data["compression"] = args["compression"]
        if "comments" in args:
            dataset_data["comments"] = args["comments"]

        return client.create_dataset(dataset_data)

    elif command == "dataset list":
        # Optional: pool filter
        filters = None
        if "pool" in args:
            filters = {"pool": args["pool"]}
        return client.get_datasets(filters=filters)

    elif command == "snapshot create":
        dataset = args.get("dataset")
        snapshot_name = args.get("snapshot_name")
        if not dataset or not snapshot_name:
            raise ValueError(
                "snapshot create requires 'dataset' and 'snapshot_name' arguments"
            )

        recursive = args.get("recursive", False)
        vmware_sync = args.get("vmware_sync", False)
        properties = args.get("properties")

        return client.create_snapshot(
            dataset=dataset,
            snapshot_name=snapshot_name,
            recursive=recursive,
            vmware_sync=vmware_sync,
            properties=properties,
        )

    elif command == "snapshot delete":
        snapshot_id = args.get("snapshot_id") or args.get("snapshot")
        if not snapshot_id:
            raise ValueError("snapshot delete requires 'snapshot_id' or 'snapshot' argument")

        defer = args.get("defer", False)
        recursive = args.get("recursive", False)

        return client.delete_snapshot(
            snapshot_id=snapshot_id,
            defer=defer,
            recursive=recursive,
        )

    elif command == "snapshot list":
        dataset = args.get("dataset")
        return client.list_snapshots(dataset=dataset)

    elif command == "pool list":
        return client.get_pools()

    else:
        raise ValueError(
            f"Unknown command: '{command}'. "
            f"Supported commands: dataset create, dataset list, snapshot create, "
            f"snapshot delete, snapshot list, pool list"
        )


@app.command()
def execute(
    ctx: typer.Context,
    file: Path = typer.Argument(
        ...,
        help="Path to batch operations file (YAML or JSON)",
        exists=True,
        readable=True,
    ),
    parallel: bool = typer.Option(
        False,
        "--parallel",
        help="Execute operations in parallel",
    ),
    workers: int = typer.Option(
        4,
        "--workers",
        help="Number of parallel workers (used with --parallel)",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Validate and show operations without executing",
    ),
    stop_on_error: bool = typer.Option(
        False,
        "--stop-on-error",
        help="Stop processing if an error occurs",
    ),
) -> None:
    """Execute batch operations from a configuration file.

    The batch file should be in YAML or JSON format with an 'operations' list.
    Each operation specifies a 'command' and optional 'args' dictionary.

    Examples:
        truenas-cli batch execute operations.yaml
        truenas-cli batch execute operations.yaml --parallel --workers 8
        truenas-cli batch execute operations.yaml --dry-run
        truenas-cli batch execute operations.yaml --stop-on-error

    Batch file format (YAML):
        operations:
          - id: create_dataset_1
            command: dataset create
            args:
              path: tank/data
              compression: lz4

          - id: create_snapshot
            command: snapshot create
            args:
              dataset: tank/data
              snapshot_name: backup-2025-01-15
    """
    # Validate incompatible options
    if parallel and stop_on_error:
        console.print(
            "[red]Error:[/red] --stop-on-error cannot be used with --parallel\n"
            "[yellow]Reason:[/yellow] In parallel mode, all operations are submitted "
            "simultaneously and cannot be cancelled mid-execution.\n"
            "[cyan]Suggestion:[/cyan] Use sequential mode (remove --parallel) if you "
            "need to stop on first error."
        )
        raise typer.Exit(1)

    # Load batch file
    try:
        operations = load_batch_file(file)
    except Exception as e:
        console.print(f"[red]Error loading batch file:[/red] {e}")
        raise typer.Exit(1) from e

    # Show operations summary
    console.print(f"\n[bold]Batch operations:[/bold] {len(operations)} operation(s)")

    if dry_run:
        console.print("\n[yellow]Dry run mode - operations will not be executed[/yellow]\n")
        for i, op in enumerate(operations, 1):
            console.print(f"  {i}. [cyan]{op.command}[/cyan]")
            if op.args:
                for key, value in op.args.items():
                    console.print(f"     - {key}: {value}")
        return

    # Get client
    client = get_client(ctx)

    # Create executor function that uses the client
    def executor(operation: BatchOperation) -> Any:
        return execute_operation(client, operation)

    # Execute operations
    try:
        processor = BatchProcessor(
            operations=operations,
            executor=executor,
            parallel=parallel,
            max_workers=workers,
            console=console,
        )

        results = processor.execute(stop_on_error=stop_on_error)

        # Print summary
        processor.print_summary(results)

        # Exit with error code if any operations failed
        failed_count = sum(1 for r in results if not r.success)
        if failed_count > 0:
            raise typer.Exit(1)

    except Exception as e:
        console.print(f"\n[red]Execution error:[/red] {e}")
        raise typer.Exit(1) from e


@app.command()
def validate(
    file: Path = typer.Argument(
        ...,
        help="Path to batch operations file (YAML or JSON)",
        exists=True,
        readable=True,
    ),
) -> None:
    """Validate a batch operations file without executing.

    Checks file syntax and structure for errors.

    Examples:
        truenas-cli batch validate operations.yaml
        truenas-cli batch validate operations.json
    """
    try:
        # Load and validate
        operations = load_batch_file(file)

        # Load raw data for additional validation
        import json

        import yaml

        content = file.read_text()
        if file.suffix in [".yaml", ".yml"]:
            batch_data = yaml.safe_load(content)
        else:
            batch_data = json.loads(content)

        # Validate structure
        errors = validate_batch_data(batch_data)

        if errors:
            console.print("[red]Validation failed:[/red]\n")
            for error in errors:
                console.print(f"  - {error}")
            raise typer.Exit(1)

        # Success
        console.print(f"[green]✓[/green] Batch file is valid ({len(operations)} operations)\n")

        # Show operations summary
        for i, op in enumerate(operations, 1):
            op_id = op.id or f"op_{i}"
            console.print(f"  {i}. [cyan]{op_id}[/cyan]: {op.command}")

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1) from e


@app.command("create-sample")
def create_sample(
    output_file: Path = typer.Argument(
        Path("batch-operations.yaml"),
        help="Output file path",
    ),
    format: str = typer.Option(
        "yaml",
        "--format",
        "-f",
        help="Output format: yaml or json",
    ),
) -> None:
    """Create a sample batch operations file.

    This creates a template file demonstrating the batch file format.

    Examples:
        truenas-cli batch create-sample
        truenas-cli batch create-sample operations.yaml
        truenas-cli batch create-sample operations.json --format json
    """
    from truenas_cli.utils.batch import create_sample_batch_file

    try:
        create_sample_batch_file(output_file, format=format)
        console.print(f"[green]✓[/green] Created sample batch file: {output_file}")

        # Show the content
        console.print("\n[cyan]File contents:[/cyan]\n")
        console.print(output_file.read_text())

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1) from e

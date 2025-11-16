"""Dataset management commands.

This module provides commands for managing ZFS datasets including
listing, creation, deletion, and property management.
"""


import typer
from rich.console import Console

from truenas_cli.client.base import TrueNASClient
from truenas_cli.client.exceptions import ConfigurationError, TrueNASError
from truenas_cli.config import ConfigManager
from truenas_cli.utils.formatters import (
    format_bytes,
    format_json_output,
    format_key_value_output,
    output_data,
)

app = typer.Typer(
    help="Dataset management",
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
        raise typer.Exit(3)

    return TrueNASClient(profile=profile, verbose=cli_ctx.verbose)


@app.command("list")
def list_datasets(
    ctx: typer.Context,
    pool_name: str | None = typer.Argument(None, help="Filter by pool name"),
) -> None:
    """List all datasets, optionally filtered by pool.

    Shows all ZFS datasets with their properties including size, compression, and mount points.

    Examples:
        truenas-cli dataset list
        truenas-cli dataset list tank
        truenas-cli --output-format json dataset list
    """
    client = get_client(ctx)
    cli_ctx = ctx.obj

    try:
        # Get all datasets
        datasets = client.get_datasets()

        # Filter by pool if specified
        if pool_name:
            datasets = [d for d in datasets if d.get("pool") == pool_name or d.get("id", "").startswith(f"{pool_name}/")]

        if not datasets:
            if pool_name:
                console.print(f"[yellow]No datasets found in pool '{pool_name}'[/yellow]")
            else:
                console.print("[yellow]No datasets found[/yellow]")
            return

        # Prepare table columns
        table_columns = [
            {"key": "id", "header": "Path", "style": "cyan bold"},
            {"key": "type", "header": "Type", "style": ""},
            {"key": "used_value", "header": "Used", "style": "", "format": "bytes"},
            {"key": "available_value", "header": "Available", "style": "", "format": "bytes"},
            {"key": "compression", "header": "Compression", "style": "dim"},
            {"key": "mountpoint", "header": "Mount Point", "style": "dim"},
        ]

        plain_columns = ["id", "type", "used_value", "available_value", "compression", "mountpoint"]

        # Extract nested values for display
        for ds in datasets:
            # Handle nested 'used' and 'available' which might be dicts
            if isinstance(ds.get("used"), dict):
                ds["used_value"] = ds["used"].get("parsed", 0)
            else:
                ds["used_value"] = ds.get("used", 0)

            if isinstance(ds.get("available"), dict):
                ds["available_value"] = ds["available"].get("parsed", 0)
            else:
                ds["available_value"] = ds.get("available", 0)

            # Handle compression which is also a dict with 'value' field
            if isinstance(ds.get("compression"), dict):
                ds["compression"] = ds["compression"].get("value", "N/A")
            elif ds.get("compression") is None:
                ds["compression"] = "N/A"

        output_data(
            datasets,
            output_format=cli_ctx.output_format,
            table_columns=table_columns,
            plain_columns=plain_columns,
            title=f"Datasets{f' in pool {pool_name}' if pool_name else ''}",
        )

    except TrueNASError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


@app.command("create", no_args_is_help=True)
def create_dataset(
    ctx: typer.Context,
    path: str = typer.Argument(..., help="Dataset path (e.g., tank/mydataset)"),
    compression: str | None = typer.Option(None, "--compression", "-c", help="Compression algorithm (lz4, gzip, zstd)"),
    quota: str | None = typer.Option(None, "--quota", "-q", help="Quota (e.g., 100G, 1T)"),
    recordsize: str | None = typer.Option(None, "--recordsize", "-r", help="Record size (e.g., 128K, 1M)"),
    dedup: str | None = typer.Option(None, "--dedup", help="Deduplication (on, off, verify)"),
) -> None:
    """Create a new dataset.

    Creates a ZFS dataset with specified properties. The path should include
    the pool name followed by the dataset name (e.g., tank/mydataset).

    Examples:
        truenas-cli dataset create tank/mydata
        truenas-cli dataset create tank/mydata --compression lz4
        truenas-cli dataset create tank/mydata --quota 100G
        truenas-cli dataset create tank/mydata --compression zstd --recordsize 1M
    """
    client = get_client(ctx)
    cli_ctx = ctx.obj

    try:
        # Parse path into pool and dataset name
        parts = path.split("/", 1)
        if len(parts) < 2:
            console.print(f"[red]Error:[/red] Invalid dataset path '{path}'")
            console.print("[yellow]Format:[/yellow] pool_name/dataset_name (e.g., tank/mydataset)")
            raise typer.Exit(1)

        # Build dataset configuration
        dataset_config = {
            "name": path,
            "type": "FILESYSTEM",
        }

        # Add optional properties
        if compression:
            dataset_config["compression"] = compression.upper()

        if quota:
            dataset_config["quota"] = quota

        if recordsize:
            dataset_config["recordsize"] = recordsize

        if dedup:
            dataset_config["deduplication"] = dedup.upper()

        # Create dataset
        result = client.create_dataset(dataset_config)

        if cli_ctx.output_format == "json":
            format_json_output(result)
        else:
            console.print(f"[green]Dataset '{path}' created successfully[/green]")

            # Show created dataset properties
            if isinstance(result, dict):
                summary = {
                    "path": result.get("id", path),
                    "type": result.get("type", "FILESYSTEM"),
                    "compression": result.get("compression", "inherited"),
                    "mountpoint": result.get("mountpoint", "N/A"),
                }
                format_key_value_output(summary, title="Created Dataset")

    except TrueNASError as e:
        console.print(f"[red]Error:[/red] {e}")
        if "already exists" in str(e).lower():
            console.print(f"[yellow]Tip:[/yellow] Dataset '{path}' already exists")
        raise typer.Exit(1)


@app.command("delete", no_args_is_help=True)
def delete_dataset(
    ctx: typer.Context,
    path: str = typer.Argument(..., help="Dataset path to delete"),
    recursive: bool = typer.Option(False, "--recursive", "-r", help="Delete recursively"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
) -> None:
    """Delete a dataset.

    Deletes a ZFS dataset. Use with caution as this operation cannot be undone.

    Examples:
        truenas-cli dataset delete tank/mydata
        truenas-cli dataset delete tank/mydata --recursive
        truenas-cli dataset delete tank/mydata --yes
    """
    client = get_client(ctx)
    cli_ctx = ctx.obj

    try:
        # Get dataset info first to confirm it exists
        try:
            dataset = client.get_dataset(path)
        except TrueNASError:
            console.print(f"[red]Error:[/red] Dataset '{path}' not found")
            raise typer.Exit(1)

        # Confirmation prompt unless --yes flag is used
        if not yes:
            console.print(f"[yellow]Warning:[/yellow] You are about to delete dataset '{path}'")
            if recursive:
                console.print("[yellow]This will delete all child datasets as well[/yellow]")
            console.print("[red]This operation cannot be undone![/red]")

            confirm = typer.confirm("Are you sure you want to continue?")
            if not confirm:
                console.print("[yellow]Operation cancelled[/yellow]")
                raise typer.Exit(0)

        # Delete dataset
        result = client.delete_dataset(path, recursive=recursive)

        if cli_ctx.output_format == "json":
            format_json_output({"status": "deleted", "path": path})
        else:
            console.print(f"[green]Dataset '{path}' deleted successfully[/green]")

    except TrueNASError as e:
        console.print(f"[red]Error:[/red] {e}")
        if "has children" in str(e).lower():
            console.print("[yellow]Tip:[/yellow] Use --recursive to delete child datasets")
        raise typer.Exit(1)


@app.command("set", no_args_is_help=True)
def set_dataset_property(
    ctx: typer.Context,
    path: str = typer.Argument(..., help="Dataset path"),
    property_name: str = typer.Argument(..., help="Property name (e.g., compression, quota)"),
    value: str = typer.Argument(..., help="Property value"),
) -> None:
    """Modify dataset properties.

    Updates a specific property of a dataset.

    Examples:
        truenas-cli dataset set tank/mydata compression lz4
        truenas-cli dataset set tank/mydata quota 100G
        truenas-cli dataset set tank/mydata recordsize 1M
        truenas-cli dataset set tank/mydata readonly on
    """
    client = get_client(ctx)
    cli_ctx = ctx.obj

    try:
        # Build update config
        update_config = {
            property_name: value
        }

        # Update dataset
        result = client.update_dataset(path, update_config)

        if cli_ctx.output_format == "json":
            format_json_output(result)
        else:
            console.print(f"[green]Property '{property_name}' set to '{value}' for dataset '{path}'[/green]")

    except TrueNASError as e:
        console.print(f"[red]Error:[/red] {e}")
        if "not found" in str(e).lower():
            console.print(f"[yellow]Tip:[/yellow] Dataset '{path}' does not exist")
        raise typer.Exit(1)


@app.command("info", no_args_is_help=True)
def dataset_info(
    ctx: typer.Context,
    path: str = typer.Argument(..., help="Dataset path"),
) -> None:
    """Show detailed information about a dataset.

    Displays comprehensive information about dataset properties and usage.

    Examples:
        truenas-cli dataset info tank/mydata
        truenas-cli --output-format json dataset info tank/mydata
    """
    client = get_client(ctx)
    cli_ctx = ctx.obj

    try:
        dataset = client.get_dataset(path)

        if cli_ctx.output_format == "json":
            format_json_output(dataset)
        else:
            # Extract key information
            summary = {
                "path": dataset.get("id", path),
                "type": dataset.get("type"),
                "pool": dataset.get("pool"),
                "mountpoint": dataset.get("mountpoint"),
            }

            # Handle nested values
            if isinstance(dataset.get("used"), dict):
                summary["used"] = format_bytes(dataset["used"].get("parsed", 0))
            else:
                summary["used"] = format_bytes(dataset.get("used", 0))

            if isinstance(dataset.get("available"), dict):
                summary["available"] = format_bytes(dataset["available"].get("parsed", 0))
            else:
                summary["available"] = format_bytes(dataset.get("available", 0))

            # Add other properties
            summary["compression"] = dataset.get("compression", "N/A")
            summary["compressratio"] = dataset.get("compressratio", "N/A")
            summary["readonly"] = dataset.get("readonly", False)

            if dataset.get("quota"):
                if isinstance(dataset["quota"], dict):
                    summary["quota"] = format_bytes(dataset["quota"].get("parsed", 0))
                else:
                    summary["quota"] = str(dataset["quota"])

            if dataset.get("encryption"):
                summary["encryption"] = dataset.get("encryption")
                summary["key_loaded"] = dataset.get("key_loaded", False)

            format_key_value_output(summary, title=f"Dataset Information: {path}")

    except TrueNASError as e:
        console.print(f"[red]Error:[/red] {e}")
        if "not found" in str(e).lower():
            console.print(f"[yellow]Tip:[/yellow] Dataset '{path}' does not exist")
        raise typer.Exit(1)

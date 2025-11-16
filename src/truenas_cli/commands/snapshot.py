"""Snapshot management commands.

This module provides commands for managing ZFS snapshots including
listing, creation, deletion, cloning, and rollback operations.
"""

from datetime import datetime

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
    help="Manage ZFS snapshots",
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


def parse_snapshot_name(snapshot_full: str) -> tuple[str, str]:
    """Parse snapshot name into dataset and snapshot parts.

    Args:
        snapshot_full: Full snapshot name (dataset@snapshot)

    Returns:
        Tuple of (dataset, snapshot_name)

    Raises:
        ValueError: If snapshot name format is invalid
    """
    if "@" not in snapshot_full:
        raise ValueError(
            f"Invalid snapshot format: '{snapshot_full}'. Expected format: dataset@snapshot_name"
        )

    parts = snapshot_full.split("@", 1)
    return parts[0], parts[1]


@app.command("list")
def list_snapshots(
    ctx: typer.Context,
    dataset: str | None = typer.Argument(
        None, help="Filter snapshots by dataset name"
    ),
) -> None:
    """List ZFS snapshots.

    Shows all ZFS snapshots with their properties including creation time,
    space used, and referenced data. Optionally filter by dataset.

    Examples:
        truenas-cli snapshot list
        truenas-cli snapshot list tank/data
        truenas-cli --output-format json snapshot list
    """
    client = get_client(ctx)
    cli_ctx = ctx.obj

    try:
        # Get snapshots
        snapshots = client.list_snapshots(dataset=dataset)

        if not snapshots:
            if dataset:
                console.print(
                    f"[yellow]No snapshots found for dataset '{dataset}'[/yellow]"
                )
            else:
                console.print("[yellow]No snapshots found[/yellow]")
            return

        # Prepare table columns
        table_columns = [
            {"key": "name", "header": "Snapshot", "style": "cyan bold"},
            {"key": "dataset", "header": "Dataset", "style": ""},
            {"key": "created", "header": "Created", "style": "dim"},
            {"key": "used_value", "header": "Used", "style": "", "format": "bytes"},
            {
                "key": "referenced_value",
                "header": "Referenced",
                "style": "",
                "format": "bytes",
            },
        ]

        plain_columns = ["name", "dataset", "created", "used_value", "referenced_value"]

        # Extract nested values for display
        for snap in snapshots:
            # Extract dataset name if not present
            if not snap.get("dataset") and "@" in snap.get("name", ""):
                snap["dataset"] = snap["name"].split("@")[0]

            # Format creation time
            if isinstance(snap.get("creation"), dict):
                creation_value = snap["creation"].get("$date")
                if creation_value:
                    try:
                        dt = datetime.fromtimestamp(creation_value / 1000)
                        snap["created"] = dt.strftime("%Y-%m-%d %H:%M:%S")
                    except Exception:
                        snap["created"] = "N/A"
                else:
                    snap["created"] = "N/A"
            else:
                snap["created"] = snap.get("creation", "N/A")

            # Handle nested 'used' and 'referenced'
            if isinstance(snap.get("used"), dict):
                snap["used_value"] = snap["used"].get("parsed", 0)
            else:
                snap["used_value"] = snap.get("used", 0)

            if isinstance(snap.get("referenced"), dict):
                snap["referenced_value"] = snap["referenced"].get("parsed", 0)
            else:
                snap["referenced_value"] = snap.get("referenced", 0)

        output_data(
            snapshots,
            output_format=cli_ctx.output_format,
            table_columns=table_columns,
            plain_columns=plain_columns,
            title=f"Snapshots{f' for {dataset}' if dataset else ''}",
        )

    except TrueNASError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


@app.command("create", no_args_is_help=True)
def create_snapshot(
    ctx: typer.Context,
    snapshot: str = typer.Argument(
        ..., help="Snapshot name in format: dataset@snapshot_name"
    ),
    recursive: bool = typer.Option(
        False, "--recursive", "-r", help="Create recursive snapshot of all children"
    ),
    vmware_sync: bool = typer.Option(
        False, "--vmware-sync", help="Sync with VMware before creating snapshot"
    ),
) -> None:
    """Create a new ZFS snapshot.

    Creates a snapshot of a dataset. The snapshot name must be in the format
    dataset@snapshot_name (e.g., tank/data@backup-2025-01-15).

    Examples:
        truenas-cli snapshot create tank/data@backup-2025-01-15
        truenas-cli snapshot create tank/data@daily --recursive
        truenas-cli snapshot create tank/vmware@pre-update --vmware-sync
    """
    client = get_client(ctx)
    cli_ctx = ctx.obj

    try:
        # Parse snapshot name
        try:
            dataset, snapshot_name = parse_snapshot_name(snapshot)
        except ValueError as e:
            console.print(f"[red]Error:[/red] {e}")
            raise typer.Exit(1)

        # Create snapshot
        result = client.create_snapshot(
            dataset=dataset,
            snapshot_name=snapshot_name,
            recursive=recursive,
            vmware_sync=vmware_sync,
        )

        if cli_ctx.output_format == "json":
            format_json_output(result)
        else:
            console.print(f"[green]Snapshot '{snapshot}' created successfully[/green]")

            # Show created snapshot properties
            if isinstance(result, dict):
                summary = {
                    "snapshot": result.get("name", snapshot),
                    "dataset": result.get("dataset", dataset),
                }
                if recursive:
                    summary["type"] = "Recursive"
                format_key_value_output(summary, title="Created Snapshot")

    except TrueNASError as e:
        console.print(f"[red]Error:[/red] {e}")
        if "already exists" in str(e).lower():
            console.print(f"[yellow]Tip:[/yellow] Snapshot '{snapshot}' already exists")
        raise typer.Exit(1)


@app.command("delete", no_args_is_help=True)
def delete_snapshot(
    ctx: typer.Context,
    snapshot: str = typer.Argument(
        ..., help="Snapshot name in format: dataset@snapshot_name"
    ),
    recursive: bool = typer.Option(
        False, "--recursive", "-r", help="Recursively destroy dependent clones"
    ),
    defer: bool = typer.Option(
        False, "--defer", help="Defer deletion of snapshot"
    ),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
) -> None:
    """Delete a ZFS snapshot.

    Deletes a snapshot. Use with caution as this operation cannot be undone.
    If the snapshot has dependent clones, use --recursive to delete them as well.

    Examples:
        truenas-cli snapshot delete tank/data@backup-2025-01-15
        truenas-cli snapshot delete tank/data@old --yes
        truenas-cli snapshot delete tank/data@snap --recursive
    """
    client = get_client(ctx)
    cli_ctx = ctx.obj

    try:
        # Validate snapshot format
        try:
            dataset, snapshot_name = parse_snapshot_name(snapshot)
        except ValueError as e:
            console.print(f"[red]Error:[/red] {e}")
            raise typer.Exit(1)

        # Confirmation prompt unless --yes flag is used
        if not yes:
            console.print(
                f"[yellow]Warning:[/yellow] You are about to delete snapshot '{snapshot}'"
            )
            if recursive:
                console.print(
                    "[yellow]This will also delete all dependent clones[/yellow]"
                )
            console.print("[red]This operation cannot be undone![/red]")

            confirm = typer.confirm("Are you sure you want to continue?")
            if not confirm:
                console.print("[yellow]Operation cancelled[/yellow]")
                raise typer.Exit(0)

        # Delete snapshot
        client.delete_snapshot(
            snapshot_id=snapshot, defer=defer, recursive=recursive
        )

        if cli_ctx.output_format == "json":
            format_json_output({"status": "deleted", "snapshot": snapshot})
        else:
            console.print(f"[green]Snapshot '{snapshot}' deleted successfully[/green]")

    except TrueNASError as e:
        console.print(f"[red]Error:[/red] {e}")
        if "has dependent clones" in str(e).lower() or "has clones" in str(e).lower():
            console.print(
                "[yellow]Tip:[/yellow] Use --recursive to delete dependent clones"
            )
        raise typer.Exit(1)


@app.command("rollback", no_args_is_help=True)
def rollback_snapshot(
    ctx: typer.Context,
    snapshot: str = typer.Argument(
        ..., help="Snapshot name in format: dataset@snapshot_name"
    ),
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="Force unmount and rollback (DESTRUCTIVE)",
    ),
    recursive: bool = typer.Option(
        False,
        "--recursive",
        "-r",
        help="Destroy more recent snapshots and clones (DESTRUCTIVE)",
    ),
) -> None:
    """Rollback a dataset to a snapshot state.

    DESTRUCTIVE OPERATION: Rolling back to a snapshot will destroy all changes
    made to the dataset after the snapshot was created. This includes:
    - All newer snapshots will be destroyed
    - All uncommitted data changes will be lost
    - Any clones created from newer snapshots will be destroyed (with --recursive)

    This operation requires explicit confirmation and the --force flag.

    Examples:
        truenas-cli snapshot rollback tank/data@backup-2025-01-15 --force
        truenas-cli snapshot rollback tank/data@last-good --force --recursive
    """
    client = get_client(ctx)
    cli_ctx = ctx.obj

    try:
        # Validate snapshot format
        try:
            dataset, snapshot_name = parse_snapshot_name(snapshot)
        except ValueError as e:
            console.print(f"[red]Error:[/red] {e}")
            raise typer.Exit(1)

        # Safety check: require --force flag
        if not force:
            console.print(
                "[red]Error:[/red] Rollback is a destructive operation and requires the --force flag"
            )
            console.print(
                "[yellow]Tip:[/yellow] Use --force to confirm you want to rollback"
            )
            raise typer.Exit(1)

        # Show warning and require confirmation
        console.print("[bold red]!!! DESTRUCTIVE OPERATION WARNING !!![/bold red]")
        console.print(
            f"\n[yellow]You are about to rollback dataset '{dataset}' to snapshot '{snapshot_name}'[/yellow]\n"
        )
        console.print("[red]This will:[/red]")
        console.print("  - Destroy all changes made after this snapshot")
        console.print("  - Delete all newer snapshots")
        if recursive:
            console.print("  - Destroy all dependent clones")
        console.print("\n[bold red]THIS CANNOT BE UNDONE![/bold red]\n")

        confirm = typer.confirm(
            "Are you absolutely sure you want to proceed with rollback?"
        )
        if not confirm:
            console.print("[yellow]Operation cancelled[/yellow]")
            raise typer.Exit(0)

        # Double confirmation for extra safety
        double_confirm = typer.confirm(
            "Final confirmation - rollback will DESTROY all newer data. Continue?"
        )
        if not double_confirm:
            console.print("[yellow]Operation cancelled[/yellow]")
            raise typer.Exit(0)

        # Perform rollback
        client.rollback_snapshot(
            snapshot_id=snapshot, force=force, recursive=recursive
        )

        if cli_ctx.output_format == "json":
            format_json_output({"status": "rolled_back", "snapshot": snapshot})
        else:
            console.print(
                f"[green]Successfully rolled back to snapshot '{snapshot}'[/green]"
            )

    except TrueNASError as e:
        console.print(f"[red]Error:[/red] {e}")
        if "more recent snapshots" in str(e).lower():
            console.print(
                "[yellow]Tip:[/yellow] Use --recursive to destroy newer snapshots"
            )
        raise typer.Exit(1)


@app.command("clone", no_args_is_help=True)
def clone_snapshot(
    ctx: typer.Context,
    snapshot: str = typer.Argument(
        ..., help="Source snapshot name in format: dataset@snapshot_name"
    ),
    target: str = typer.Argument(..., help="Target dataset name for the clone"),
) -> None:
    """Clone a snapshot to create a new dataset.

    Creates a new dataset as a clone of an existing snapshot. The cloned dataset
    will initially share all data with the snapshot, using copy-on-write to
    minimize storage usage.

    Examples:
        truenas-cli snapshot clone tank/data@backup-2025-01-15 tank/data-restore
        truenas-cli snapshot clone tank/vm@pre-update tank/vm-test
    """
    client = get_client(ctx)
    cli_ctx = ctx.obj

    try:
        # Validate snapshot format
        try:
            dataset, snapshot_name = parse_snapshot_name(snapshot)
        except ValueError as e:
            console.print(f"[red]Error:[/red] {e}")
            raise typer.Exit(1)

        # Validate target dataset name
        if "@" in target:
            console.print(
                "[red]Error:[/red] Target cannot be a snapshot (remove @ from target name)"
            )
            raise typer.Exit(1)

        # Clone snapshot
        result = client.clone_snapshot(snapshot_id=snapshot, target_dataset=target)

        if cli_ctx.output_format == "json":
            format_json_output(result)
        else:
            console.print(
                f"[green]Successfully cloned '{snapshot}' to '{target}'[/green]"
            )

            # Show clone information
            if isinstance(result, dict):
                summary = {
                    "source_snapshot": snapshot,
                    "cloned_dataset": target,
                }
                format_key_value_output(summary, title="Clone Created")

    except TrueNASError as e:
        console.print(f"[red]Error:[/red] {e}")
        if "already exists" in str(e).lower():
            console.print(
                f"[yellow]Tip:[/yellow] Target dataset '{target}' already exists"
            )
        raise typer.Exit(1)


@app.command("info", no_args_is_help=True)
def snapshot_info(
    ctx: typer.Context,
    snapshot: str = typer.Argument(
        ..., help="Snapshot name in format: dataset@snapshot_name"
    ),
) -> None:
    """Show detailed information about a snapshot.

    Displays comprehensive information about a snapshot including creation time,
    space usage, and properties.

    Examples:
        truenas-cli snapshot info tank/data@backup-2025-01-15
        truenas-cli --output-format json snapshot info tank/data@daily
    """
    client = get_client(ctx)
    cli_ctx = ctx.obj

    try:
        # Validate snapshot format
        try:
            dataset, snapshot_name = parse_snapshot_name(snapshot)
        except ValueError as e:
            console.print(f"[red]Error:[/red] {e}")
            raise typer.Exit(1)

        # Get snapshot info
        snap = client.get_snapshot(snapshot)

        if cli_ctx.output_format == "json":
            format_json_output(snap)
        else:
            # Extract key information
            summary = {
                "snapshot": snap.get("name", snapshot),
                "dataset": snap.get("dataset", dataset),
                "type": snap.get("type", "N/A"),
            }

            # Format creation time
            if isinstance(snap.get("creation"), dict):
                creation_value = snap["creation"].get("$date")
                if creation_value:
                    try:
                        dt = datetime.fromtimestamp(creation_value / 1000)
                        summary["created"] = dt.strftime("%Y-%m-%d %H:%M:%S")
                    except Exception:
                        summary["created"] = "N/A"
            else:
                summary["created"] = snap.get("creation", "N/A")

            # Handle nested values
            if isinstance(snap.get("used"), dict):
                summary["used"] = format_bytes(snap["used"].get("parsed", 0))
            else:
                summary["used"] = format_bytes(snap.get("used", 0))

            if isinstance(snap.get("referenced"), dict):
                summary["referenced"] = format_bytes(snap["referenced"].get("parsed", 0))
            else:
                summary["referenced"] = format_bytes(snap.get("referenced", 0))

            # Add createtxg if available
            if snap.get("createtxg"):
                summary["createtxg"] = snap["createtxg"]

            format_key_value_output(summary, title=f"Snapshot Information: {snapshot}")

    except TrueNASError as e:
        console.print(f"[red]Error:[/red] {e}")
        if "not found" in str(e).lower():
            console.print(
                f"[yellow]Tip:[/yellow] Snapshot '{snapshot}' does not exist"
            )
        raise typer.Exit(1)

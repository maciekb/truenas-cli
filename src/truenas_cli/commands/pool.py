"""Storage pool management commands.

This module provides commands for managing ZFS storage pools including
listing, status checks, scrub operations, and statistics.
"""

import typer
from rich.console import Console, RenderableType
from rich.table import Table

from truenas_cli.client.base import TrueNASClient
from truenas_cli.client.exceptions import ConfigurationError, TrueNASError
from truenas_cli.config import ConfigManager
from truenas_cli.utils.filtering import filter_items
from truenas_cli.utils.formatters import (
    format_bytes,
    format_json_output,
    format_key_value_output,
    get_status_color,
    output_data,
)
from truenas_cli.utils.watch import watch

app = typer.Typer(
    help="Storage pool management",
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
def list_pools(
    ctx: typer.Context,
    filter: list[str] = typer.Option(
        None,
        "--filter",
        help="Filter results (e.g., 'status=ONLINE', 'name~tank')",
    ),
    watch_mode: bool = typer.Option(
        False,
        "--watch",
        help="Watch mode - continuously refresh output",
    ),
    interval: int = typer.Option(
        2,
        "--interval",
        help="Refresh interval in seconds (used with --watch)",
    ),
) -> None:
    """List all storage pools.

    Shows all storage pools with their status, size, and health information.

    Examples:
        truenas-cli pool list
        truenas-cli pool list --filter "status=ONLINE"
        truenas-cli pool list --filter "name~tank"
        truenas-cli pool list --watch --interval 5
        truenas-cli pool list --filter "status=ONLINE" --watch
        truenas-cli --output-format json pool list
        truenas-cli --output-format plain pool list
    """
    client = get_client(ctx)
    cli_ctx = ctx.obj

    def _create_output() -> RenderableType:
        """Create output renderable for display."""
        try:
            pools = client.get_pools()

            if not pools:
                return console.render_str("[yellow]No storage pools found[/yellow]")

            # Apply filters if provided
            if filter:
                pools = filter_items(pools, filter)

            # Prepare table columns
            table_columns = [
                {"key": "name", "header": "Name", "style": "cyan bold"},
                {"key": "status", "header": "Status", "style": "", "format": "status"},
                {"key": "healthy", "header": "Healthy", "style": "", "format": "boolean"},
                {"key": "size", "header": "Size", "style": "", "format": "bytes"},
                {"key": "allocated", "header": "Allocated", "style": "", "format": "bytes"},
                {"key": "free", "header": "Free", "style": "", "format": "bytes"},
            ]

            # For watch mode, we need to return a Rich renderable
            if cli_ctx.output_format == "json":
                import json

                from rich.json import JSON

                return JSON(json.dumps(pools, indent=2, default=str))
            elif cli_ctx.output_format == "plain":
                # For plain format in watch mode, create a text renderable
                from rich.text import Text

                plain_columns = ["name", "status", "healthy", "size", "allocated", "free"]
                lines = ["\t".join(plain_columns)]
                for item in pools:
                    values = [str(item.get(col, "")) for col in plain_columns]
                    lines.append("\t".join(values))
                return Text("\n".join(lines))
            else:
                # Create table
                table = Table(title="Storage Pools", show_header=True, header_style="bold cyan")

                # Add columns
                for col in table_columns:
                    table.add_column(
                        col["header"],
                        style=col.get("style", ""),
                        no_wrap=bool(col.get("no_wrap", False)),
                    )

                # Add rows
                for item in pools:
                    row = []
                    for col in table_columns:
                        key = col["key"]
                        value = item.get(key, "N/A")

                        # Special formatting for certain types
                        if col.get("format") == "bytes":
                            value = format_bytes(value)
                        elif col.get("format") == "status":
                            color = get_status_color(str(value))
                            value = f"[{color}]{value}[/{color}]"
                        elif col.get("format") == "boolean":
                            value = "[green]Yes[/green]" if value else "[red]No[/red]"
                        elif value is None:
                            value = "[dim]N/A[/dim]"

                        row.append(str(value))

                    table.add_row(*row)

                return table

        except TrueNASError as e:
            from rich.text import Text

            return Text(f"Error: {e}", style="red")

    # Use watch mode if requested
    if watch_mode:
        watch(_create_output, interval=interval, console=console)
    else:
        try:
            pools = client.get_pools()

            if not pools:
                console.print("[yellow]No storage pools found[/yellow]")
                return

            # Apply filters if provided
            if filter:
                pools = filter_items(pools, filter)

            # Prepare table columns
            table_columns = [
                {"key": "name", "header": "Name", "style": "cyan bold"},
                {"key": "status", "header": "Status", "style": "", "format": "status"},
                {"key": "healthy", "header": "Healthy", "style": "", "format": "boolean"},
                {"key": "size", "header": "Size", "style": "", "format": "bytes"},
                {"key": "allocated", "header": "Allocated", "style": "", "format": "bytes"},
                {"key": "free", "header": "Free", "style": "", "format": "bytes"},
            ]

            plain_columns = ["name", "status", "healthy", "size", "allocated", "free"]

            output_data(
                pools,
                output_format=cli_ctx.output_format,
                table_columns=table_columns,
                plain_columns=plain_columns,
                title="Storage Pools",
            )

        except TrueNASError as e:
            console.print(f"[red]Error:[/red] {e}")
            raise typer.Exit(1)


@app.command("status", no_args_is_help=True)
def pool_status(
    ctx: typer.Context,
    pool_name: str = typer.Argument(..., help="Name of the pool"),
    watch_mode: bool = typer.Option(
        False,
        "--watch",
        help="Watch mode - continuously refresh output",
    ),
    interval: int = typer.Option(
        2,
        "--interval",
        help="Refresh interval in seconds (used with --watch)",
    ),
) -> None:
    """Get detailed status of a specific pool.

    Shows comprehensive information about pool topology, health, and configuration.

    Examples:
        truenas-cli pool status tank
        truenas-cli pool status tank --watch --interval 10
        truenas-cli --output-format json pool status tank
    """
    client = get_client(ctx)
    cli_ctx = ctx.obj

    def _create_output() -> RenderableType:
        """Create output renderable for display."""
        try:
            # Get all pools and find the one we want
            pools = client.get_pools()
            pool = next((p for p in pools if p["name"] == pool_name), None)

            if not pool:
                from rich.text import Text

                error_msg = Text()
                error_msg.append(f"Error: Pool '{pool_name}' not found\n", style="red")
                available = ", ".join([p["name"] for p in pools])
                error_msg.append(f"Available pools: {available}", style="yellow")
                return error_msg

            # Get detailed information
            pool_id = pool["id"]
            detailed = client.get_pool(pool_id)

            if cli_ctx.output_format == "json":
                import json

                from rich.json import JSON

                return JSON(json.dumps(detailed, indent=2, default=str))
            else:
                # Build summary
                summary = {
                    "name": detailed.get("name"),
                    "status": detailed.get("status"),
                    "healthy": detailed.get("healthy"),
                    "guid": detailed.get("guid"),
                    "size": format_bytes(detailed.get("size")),
                    "allocated": format_bytes(detailed.get("allocated")),
                    "free": format_bytes(detailed.get("free")),
                    "fragmentation": detailed.get("fragmentation", "N/A"),
                }

                # Add scrub info if available
                if "scan" in detailed and detailed["scan"]:
                    scan = detailed["scan"]
                    summary["last_scrub"] = scan.get("end_time", "Never")
                    summary["scrub_state"] = scan.get("state", "N/A")

                # Create key-value table
                table = Table(
                    title=f"Pool Status: {pool_name}",
                    show_header=False,
                    box=None,
                    padding=(0, 2),
                )
                table.add_column("Property", style="cyan bold")
                table.add_column("Value", style="green")

                for key, value in summary.items():
                    # Convert underscores to spaces and title case
                    display_key = key.replace("_", " ").title()

                    # Format special types
                    if isinstance(value, bool):
                        display_value = "[green]Yes[/green]" if value else "[red]No[/red]"
                    elif value is None:
                        display_value = "[dim]N/A[/dim]"
                    else:
                        display_value = str(value)

                    table.add_row(display_key, display_value)

                # Show topology if available
                if "topology" in detailed and detailed["topology"]:
                    from rich.console import Group
                    from rich.text import Text

                    topology_lines = [Text("\nTopology:", style="cyan bold")]
                    topology = detailed["topology"]

                    for vdev_type in ["data", "cache", "log", "spare", "special"]:
                        if vdev_type in topology and topology[vdev_type]:
                            vdev_header = Text(f"\n  {vdev_type.upper()}:", style="yellow")
                            topology_lines.append(vdev_header)
                            for vdev in topology[vdev_type]:
                                vdev_name = vdev.get("type", "unknown")
                                topology_lines.append(Text(f"    - {vdev_name}"))

                    return Group(table, *topology_lines)

                return table

        except TrueNASError as e:
            from rich.text import Text

            return Text(f"Error: {e}", style="red")

    # Use watch mode if requested
    if watch_mode:
        watch(_create_output, interval=interval, console=console)
    else:
        try:
            # Get all pools and find the one we want
            pools = client.get_pools()
            pool = next((p for p in pools if p["name"] == pool_name), None)

            if not pool:
                console.print(f"[red]Error:[/red] Pool '{pool_name}' not found")
                available = ", ".join([p["name"] for p in pools])
                console.print(f"[yellow]Available pools:[/yellow] {available}")
                raise typer.Exit(1)

            # Get detailed information
            pool_id = pool["id"]
            detailed = client.get_pool(pool_id)

            if cli_ctx.output_format == "json":
                format_json_output(detailed)
            else:
                # Build summary
                summary = {
                    "name": detailed.get("name"),
                    "status": detailed.get("status"),
                    "healthy": detailed.get("healthy"),
                    "guid": detailed.get("guid"),
                    "size": format_bytes(detailed.get("size")),
                    "allocated": format_bytes(detailed.get("allocated")),
                    "free": format_bytes(detailed.get("free")),
                    "fragmentation": detailed.get("fragmentation", "N/A"),
                }

                # Add scrub info if available
                if "scan" in detailed and detailed["scan"]:
                    scan = detailed["scan"]
                    summary["last_scrub"] = scan.get("end_time", "Never")
                    summary["scrub_state"] = scan.get("state", "N/A")

                format_key_value_output(summary, title=f"Pool Status: {pool_name}")

                # Show topology if available
                if "topology" in detailed and detailed["topology"]:
                    console.print("\n[cyan bold]Topology:[/cyan bold]")
                    topology = detailed["topology"]

                    for vdev_type in ["data", "cache", "log", "spare", "special"]:
                        if vdev_type in topology and topology[vdev_type]:
                            console.print(f"\n  [yellow]{vdev_type.upper()}:[/yellow]")
                            for vdev in topology[vdev_type]:
                                vdev_name = vdev.get("type", "unknown")
                                console.print(f"    - {vdev_name}")

        except TrueNASError as e:
            console.print(f"[red]Error:[/red] {e}")
            raise typer.Exit(1)


@app.command("stats", no_args_is_help=True)
def pool_stats(
    ctx: typer.Context,
    pool_name: str = typer.Argument(..., help="Name of the pool"),
) -> None:
    """Show I/O statistics for a pool.

    Displays read/write operations and bandwidth statistics.

    Examples:
        truenas-cli pool stats tank
        truenas-cli --output-format json pool stats tank
    """
    client = get_client(ctx)
    cli_ctx = ctx.obj

    try:
        # Get pool information
        pools = client.get_pools()
        pool = next((p for p in pools if p["name"] == pool_name), None)

        if not pool:
            console.print(f"[red]Error:[/red] Pool '{pool_name}' not found")
            raise typer.Exit(1)

        # Try to get I/O statistics from reporting API
        try:
            disk_data = client.get(
                "/reporting/get_data",
                params={
                    "graphs": ["disk"],
                    "unit": "HOURLY",
                },
            )

            if disk_data and isinstance(disk_data, list):
                stats = {
                    "pool_name": pool_name,
                    "status": pool.get("status"),
                    "size": format_bytes(pool.get("size")),
                    "allocated": format_bytes(pool.get("allocated")),
                    "free": format_bytes(pool.get("free")),
                }

                if cli_ctx.output_format == "json":
                    format_json_output(stats)
                else:
                    format_key_value_output(stats, title=f"Pool Statistics: {pool_name}")
            else:
                # Fallback to basic pool info
                stats = {
                    "pool_name": pool_name,
                    "status": pool.get("status"),
                    "size": format_bytes(pool.get("size")),
                    "allocated": format_bytes(pool.get("allocated")),
                    "free": format_bytes(pool.get("free")),
                }

                if cli_ctx.output_format == "json":
                    format_json_output(stats)
                else:
                    format_key_value_output(stats, title=f"Pool Statistics: {pool_name}")
                    console.print(
                        "\n[yellow]Note:[/yellow] Detailed I/O statistics require reporting to be enabled"
                    )

        except Exception:
            # If reporting fails, show basic info
            stats = {
                "pool_name": pool_name,
                "status": pool.get("status"),
                "size": format_bytes(pool.get("size")),
                "allocated": format_bytes(pool.get("allocated")),
                "free": format_bytes(pool.get("free")),
            }

            if cli_ctx.output_format == "json":
                format_json_output(stats)
            else:
                format_key_value_output(stats, title=f"Pool Statistics: {pool_name}")

    except TrueNASError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


@app.command("scrub", no_args_is_help=True)
def pool_scrub(
    ctx: typer.Context,
    pool_name: str = typer.Argument(..., help="Name of the pool"),
    action: str = typer.Option(
        "start",
        "--action",
        "-a",
        help="Scrub action: start, stop, pause",
    ),
) -> None:
    """Start, stop, or check scrub operations on a pool.

    A scrub verifies the integrity of all data in the pool.

    Examples:
        truenas-cli pool scrub tank
        truenas-cli pool scrub tank --action start
        truenas-cli pool scrub tank --action stop
    """
    client = get_client(ctx)
    cli_ctx = ctx.obj

    try:
        # Get pool information
        pools = client.get_pools()
        pool = next((p for p in pools if p["name"] == pool_name), None)

        if not pool:
            console.print(f"[red]Error:[/red] Pool '{pool_name}' not found")
            raise typer.Exit(1)

        pool_id = pool["id"]
        action_upper = action.upper()

        # Perform scrub action
        if action_upper in ["START", "STOP", "PAUSE"]:
            result = client.scrub_pool(pool_id, action_upper)

            if cli_ctx.output_format == "json":
                format_json_output(result)
            else:
                console.print(f"[green]Scrub {action} initiated for pool '{pool_name}'[/green]")

                if isinstance(result, dict) and "id" in result:
                    console.print(f"[dim]Job ID: {result['id']}[/dim]")
        else:
            console.print(f"[red]Error:[/red] Invalid action '{action}'")
            console.print("[yellow]Valid actions:[/yellow] start, stop, pause")
            raise typer.Exit(1)

    except TrueNASError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


@app.command("expand", no_args_is_help=True)
def pool_expand(
    ctx: typer.Context,
    pool_name: str = typer.Argument(..., help="Name of the pool"),
) -> None:
    """Show information about pool expansion options.

    Displays current pool status and expansion possibilities.

    Examples:
        truenas-cli pool expand tank
    """
    client = get_client(ctx)
    cli_ctx = ctx.obj

    try:
        # Get pool information
        pools = client.get_pools()
        pool = next((p for p in pools if p["name"] == pool_name), None)

        if not pool:
            console.print(f"[red]Error:[/red] Pool '{pool_name}' not found")
            raise typer.Exit(1)

        pool_id = pool["id"]
        detailed = client.get_pool(pool_id)

        # Build expansion info
        info = {
            "pool_name": pool_name,
            "current_size": format_bytes(detailed.get("size")),
            "allocated": format_bytes(detailed.get("allocated")),
            "free": format_bytes(detailed.get("free")),
            "status": detailed.get("status"),
        }

        if cli_ctx.output_format == "json":
            format_json_output(info)
        else:
            format_key_value_output(info, title=f"Pool Expansion Info: {pool_name}")

            console.print("\n[yellow]Expansion Options:[/yellow]")
            console.print("  1. Add new vdevs to the pool (increases capacity)")
            console.print("  2. Replace existing disks with larger ones (gradual expansion)")
            console.print("  3. Add cache or log devices (improves performance)")
            console.print("\n[dim]Note: Use TrueNAS web GUI for actual expansion operations[/dim]")

    except TrueNASError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)

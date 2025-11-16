"""System information and management commands.

This module provides commands for querying system information,
status, and performing system-level operations.
"""

import json
from typing import Any

import typer
from rich.console import Console
from rich.json import JSON

from truenas_cli.client.base import TrueNASClient
from truenas_cli.client.exceptions import ConfigurationError, TrueNASError
from truenas_cli.config import ConfigManager

app = typer.Typer(
    help="System information and management",
    no_args_is_help=True,
)
console = Console()


def get_client(ctx: typer.Context) -> TrueNASClient:
    """Get configured TrueNAS client from context.

    Args:
        ctx: Typer context with CLIContext object

    Returns:
        Configured TrueNASClient

    Raises:
        ConfigurationError: If configuration is missing or invalid
    """
    config_mgr = ConfigManager()
    cli_ctx = ctx.obj

    try:
        _, profile, _ = config_mgr.get_profile_or_active(cli_ctx.profile)
    except ConfigurationError as e:
        console.print(f"[red]Configuration Error:[/red] {e}")
        raise typer.Exit(3)

    return TrueNASClient(profile=profile, verbose=cli_ctx.verbose)


def format_output(data: Any, output_format: str) -> None:
    """Format and print output based on requested format.

    Args:
        data: Data to output
        output_format: Format type (table, json, yaml)
    """
    from truenas_cli.utils.formatters import format_json_output, format_key_value_output

    if output_format == "json":
        # Pretty print JSON
        format_json_output(data)
    elif output_format == "yaml":
        # Simple YAML-like output
        import yaml
        try:
            console.print(yaml.dump(data, default_flow_style=False))
        except ImportError:
            # Fallback to JSON if PyYAML not installed
            format_json_output(data)
    else:
        # Default: pretty print dict/list using centralized formatter
        if isinstance(data, dict):
            format_key_value_output(data)
        else:
            console.print(data)


@app.command("info")
def system_info(ctx: typer.Context) -> None:
    """Get system information.

    Displays general information about the TrueNAS system including
    hostname, version, uptime, and hardware details.

    Examples:
        truenas-cli system info
        truenas-cli --output-format json system info
        truenas-cli --profile production system info
    """
    client = get_client(ctx)
    cli_ctx = ctx.obj

    try:
        # Make API request
        data = client.get("/system/info")

        # Format and display output
        format_output(data, cli_ctx.output_format)

    except TrueNASError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


@app.command("version")
def system_version(ctx: typer.Context) -> None:
    """Get TrueNAS version information.

    Shows the TrueNAS version string and whether it's a stable release.

    Examples:
        truenas-cli system version
        truenas-cli --output-format json system version
    """
    client = get_client(ctx)
    cli_ctx = ctx.obj

    try:
        # Make API request
        data = client.get("/system/version")

        # Format and display output
        format_output(data, cli_ctx.output_format)

    except TrueNASError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


@app.command("state")
def system_state(ctx: typer.Context) -> None:
    """Get system state information.

    Shows the current state of the system.

    Examples:
        truenas-cli system state
    """
    client = get_client(ctx)
    cli_ctx = ctx.obj

    try:
        # Make API request
        data = client.get("/system/state")

        # Format and display output
        format_output(data, cli_ctx.output_format)

    except TrueNASError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


@app.command("boot-id")
def boot_id(ctx: typer.Context) -> None:
    """Get system boot ID.

    Returns a unique identifier for the current boot session.

    Examples:
        truenas-cli system boot-id
    """
    client = get_client(ctx)
    cli_ctx = ctx.obj

    try:
        # Make API request
        data = client.get("/system/boot_id")

        # Simple output for this one
        if cli_ctx.output_format == "json":
            console.print(JSON(json.dumps({"boot_id": data}, indent=2)))
        else:
            console.print(f"[cyan]Boot ID:[/cyan] {data}")

    except TrueNASError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


@app.command("health")
def system_health(ctx: typer.Context) -> None:
    """Check overall system health status.

    Displays the system health status and any critical issues.

    Examples:
        truenas-cli system health
        truenas-cli --output-format json system health
    """
    client = get_client(ctx)
    cli_ctx = ctx.obj

    try:
        # Note: TrueNAS doesn't have a single /system/health endpoint
        # We combine multiple indicators for overall health
        from truenas_cli.utils.formatters import format_json_output, format_key_value_output

        # Get system state and info
        state = client.get("/system/state")
        info = client.get("/system/info")

        # Build health summary
        health_data = {
            "status": "HEALTHY" if state == "READY" else state,
            "state": state,
            "hostname": info.get("hostname", "unknown"),
            "version": info.get("version", "unknown"),
            "uptime_seconds": info.get("uptime_seconds", 0),
        }

        # Check for alerts
        try:
            alerts = client.get("/alert/list")
            critical_alerts = [a for a in alerts if a.get("level") == "CRITICAL"]
            warning_alerts = [a for a in alerts if a.get("level") == "WARNING"]

            health_data["critical_alerts"] = len(critical_alerts)
            health_data["warning_alerts"] = len(warning_alerts)

            if critical_alerts:
                health_data["status"] = "CRITICAL"
            elif warning_alerts:
                health_data["status"] = "WARNING"
        except Exception:
            pass  # Alerts endpoint might not be available

        # Format output
        if cli_ctx.output_format == "json":
            format_json_output(health_data)
        else:
            # Color-code status
            status = health_data["status"]
            if status == "HEALTHY" or status == "READY":
                status_display = f"[green]{status}[/green]"
            elif status == "WARNING":
                status_display = f"[yellow]{status}[/yellow]"
            else:
                status_display = f"[red]{status}[/red]"

            health_data["status"] = status_display
            format_key_value_output(health_data, title="System Health")

    except TrueNASError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


@app.command("stats")
def system_stats(ctx: typer.Context) -> None:
    """Show system resource usage statistics.

    Displays CPU, memory, and network statistics.

    Examples:
        truenas-cli system stats
        truenas-cli --output-format json system stats
    """
    client = get_client(ctx)
    cli_ctx = ctx.obj

    try:
        from truenas_cli.utils.formatters import (
            format_bytes,
            format_json_output,
            format_key_value_output,
        )

        # Get system info for uptime and memory
        info = client.get("/system/info")

        # Build stats summary
        stats_data = {
            "hostname": info.get("hostname", "unknown"),
            "uptime_seconds": info.get("uptime_seconds", 0),
            "uptime_formatted": f"{int(info.get('uptime_seconds', 0) / 3600)} hours",
        }

        # Try to get more detailed stats from reporting API
        try:
            # Get CPU stats (last 5 minutes average)
            cpu_data = client.get("/reporting/get_data", params={
                "graphs": ["cpu"],
                "unit": "HOURLY",
            })
            if cpu_data and isinstance(cpu_data, list) and len(cpu_data) > 0:
                cpu_info = cpu_data[0]
                if "aggregations" in cpu_info and "mean" in cpu_info["aggregations"]:
                    # CPU usage is (100 - idle)
                    idle = cpu_info["aggregations"]["mean"][-1]  # idle is last value
                    stats_data["cpu_usage_percent"] = f"{100 - idle:.1f}"

            # Get memory stats
            memory_data = client.get("/reporting/get_data", params={
                "graphs": ["memory"],
                "unit": "HOURLY",
            })
            if memory_data and isinstance(memory_data, list) and len(memory_data) > 0:
                mem_info = memory_data[0]
                if "aggregations" in mem_info and "mean" in mem_info["aggregations"]:
                    # Memory values are in bytes
                    free_mem = mem_info["aggregations"]["mean"][0]
                    # Estimate total memory
                    stats_data["memory_free"] = format_bytes(int(free_mem))
        except Exception:
            # Reporting API might not be available or configured
            pass

        # Format output
        if cli_ctx.output_format == "json":
            format_json_output(stats_data)
        else:
            format_key_value_output(stats_data, title="System Statistics")

    except TrueNASError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


@app.command("alerts")
def system_alerts(ctx: typer.Context) -> None:
    """List active system alerts and warnings.

    Displays all active alerts with their severity levels.

    Examples:
        truenas-cli system alerts
        truenas-cli --output-format json system alerts
        truenas-cli --output-format plain system alerts
    """
    client = get_client(ctx)
    cli_ctx = ctx.obj

    try:
        from truenas_cli.utils.formatters import output_data

        # Get alerts
        alerts = client.get("/alert/list")

        if not alerts:
            console.print("[green]No active alerts[/green]")
            return

        # Prepare table columns
        table_columns = [
            {"key": "level", "header": "Level", "style": "", "format": "status"},
            {"key": "formatted", "header": "Message", "style": ""},
            {"key": "datetime", "header": "Time", "style": "dim"},
        ]

        plain_columns = ["level", "formatted", "datetime"]

        # Format output
        output_data(
            alerts,
            output_format=cli_ctx.output_format,
            table_columns=table_columns,
            plain_columns=plain_columns,
            title=f"System Alerts ({len(alerts)} active)",
        )

    except TrueNASError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)

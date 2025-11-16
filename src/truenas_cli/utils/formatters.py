"""Output formatting utilities for TrueNAS CLI.

This module provides consistent formatting functions for displaying data
in table, JSON, and plain text formats across all commands.
"""

import json
from typing import Any

from rich.console import Console
from rich.json import JSON
from rich.table import Table

from truenas_cli.utils.datetime import format_datetime, format_uptime, is_datetime_field

console = Console()


def format_bytes(bytes_value: int | None) -> str:
    """Format bytes into human-readable format.

    Args:
        bytes_value: Size in bytes

    Returns:
        Human-readable string (e.g., "1.5 GB")
    """
    if bytes_value is None:
        return "N/A"

    if bytes_value == 0:
        return "0 B"

    units = ["B", "KB", "MB", "GB", "TB", "PB"]
    unit_index = 0
    size = float(bytes_value)

    while size >= 1024.0 and unit_index < len(units) - 1:
        size /= 1024.0
        unit_index += 1

    if unit_index == 0:
        return f"{int(size)} {units[unit_index]}"
    else:
        return f"{size:.2f} {units[unit_index]}"


def format_percentage(numerator: int | None, denominator: int | None) -> str:
    """Format a percentage from numerator and denominator.

    Args:
        numerator: Numerator value
        denominator: Denominator value

    Returns:
        Percentage string (e.g., "75.5%")
    """
    if numerator is None or denominator is None or denominator == 0:
        return "N/A"

    percentage = (numerator / denominator) * 100
    return f"{percentage:.1f}%"


def get_status_color(status: str) -> str:
    """Get Rich color for a status string.

    Args:
        status: Status string (e.g., "ONLINE", "DEGRADED", "ERROR")

    Returns:
        Rich color name
    """
    status_upper = status.upper()

    # Health/success states
    if status_upper in ["ONLINE", "HEALTHY", "OK", "SUCCESS", "UP", "ACTIVE", "RUNNING"]:
        return "green"

    # Warning states
    if status_upper in ["DEGRADED", "WARNING", "WARN", "PARTIAL"]:
        return "yellow"

    # Error/critical states
    if status_upper in ["OFFLINE", "ERROR", "CRITICAL", "FAILED", "DOWN", "FAULTED", "UNAVAIL"]:
        return "red"

    # Unknown/info states
    return "blue"


def format_table_output(
    data: list[dict[str, Any]],
    columns: list[dict[str, str]],
    title: str | None = None,
) -> None:
    """Format and display data as a Rich table.

    Args:
        data: List of dictionaries to display
        columns: Column definitions with 'key', 'header', and optional 'style'
        title: Optional table title
    """
    table = Table(title=title, show_header=True, header_style="bold cyan")

    # Add columns
    for col in columns:
        table.add_column(
            col["header"],
            style=col.get("style", ""),
            no_wrap=col.get("no_wrap", False),
        )

    # Add rows
    for item in data:
        row = []
        for col in columns:
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
            elif col.get("format") == "datetime":
                # Explicit datetime formatting
                value = format_datetime(value, format_type="human")
            elif is_datetime_field(key, value):
                # Auto-detect datetime fields
                value = format_datetime(value, format_type="human")
            elif value is None:
                value = "[dim]N/A[/dim]"

            row.append(str(value))

        table.add_row(*row)

    console.print(table)


def format_key_value_output(
    data: dict[str, Any],
    title: str | None = None,
) -> None:
    """Format and display data as a key-value table.

    Args:
        data: Dictionary to display
        title: Optional table title
    """
    table = Table(title=title, show_header=False, box=None, padding=(0, 2))
    table.add_column("Property", style="cyan bold")
    table.add_column("Value", style="green")

    for key, value in data.items():
        # Convert underscores to spaces and title case
        display_key = key.replace("_", " ").title()

        # Format special types
        if isinstance(value, bool):
            display_value = "[green]Yes[/green]" if value else "[red]No[/red]"
        elif is_datetime_field(key, value):
            # Auto-detect and format datetime fields
            display_value = format_datetime(value, format_type="human")
        elif key.lower() == 'uptime_seconds':
            # Special handling for uptime
            display_value = format_uptime(value)
        elif isinstance(value, (dict, list)):
            # Check if it's an unformatted datetime (shouldn't happen after above check)
            if isinstance(value, dict) and '$date' in value:
                display_value = format_datetime(value, format_type="human")
            # Check if it's a ZFS property dict with 'value' field
            elif isinstance(value, dict) and 'value' in value:
                # Extract the human-readable value from ZFS property
                display_value = str(value['value'])
            else:
                display_value = json.dumps(value, indent=2)
        elif value is None:
            display_value = "[dim]N/A[/dim]"
        else:
            display_value = str(value)

        table.add_row(display_key, display_value)

    console.print(table)


def format_json_output(data: Any) -> None:
    """Format and display data as JSON.

    Args:
        data: Data to display as JSON
    """
    console.print(JSON(json.dumps(data, indent=2, default=str)))


def format_plain_output(
    data: list[dict[str, Any]],
    columns: list[str],
    delimiter: str = "\t",
) -> None:
    """Format and display data as plain text (TSV by default).

    Args:
        data: List of dictionaries to display
        columns: Column keys to include
        delimiter: Field delimiter (default: tab)
    """
    # Print header
    print(delimiter.join(columns))

    # Print rows
    for item in data:
        values = []
        for col in columns:
            value = item.get(col, "")

            # Format datetime fields
            if is_datetime_field(col, value):
                value = format_datetime(value, format_type="iso")
            # Convert complex types to simple strings
            elif isinstance(value, dict) and '$date' in value:
                # Fallback for undetected datetime fields
                value = format_datetime(value, format_type="iso")
            elif isinstance(value, (dict, list)):
                value = json.dumps(value)
            elif value is None:
                value = ""

            values.append(str(value))

        print(delimiter.join(values))


def output_data(
    data: Any,
    output_format: str = "table",
    table_columns: list[dict[str, str]] | None = None,
    plain_columns: list[str] | None = None,
    title: str | None = None,
) -> None:
    """Universal output function that handles all formats.

    Args:
        data: Data to output (dict, list of dicts, or other)
        output_format: Output format (table, json, plain)
        table_columns: Column definitions for table format
        plain_columns: Column keys for plain format
        title: Optional title for table output
    """
    if output_format == "json":
        format_json_output(data)
    elif output_format == "plain":
        if isinstance(data, list) and plain_columns:
            format_plain_output(data, plain_columns)
        elif isinstance(data, dict):
            # For single dict, output as key=value lines
            for key, value in data.items():
                print(f"{key}={value}")
        else:
            print(str(data))
    else:  # table (default)
        if isinstance(data, list) and table_columns:
            format_table_output(data, table_columns, title)
        elif isinstance(data, dict):
            format_key_value_output(data, title)
        else:
            console.print(data)

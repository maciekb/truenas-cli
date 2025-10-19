from __future__ import annotations

import argparse
import json
from typing import Any, Dict, List, Optional

from truenas_client import TrueNASClient

from ..core import format_size, run_command
from .base import CommandGroup


def _extract_temperature(value: Any) -> Optional[float]:
    """Parse a temperature value (possibly within a dict) into Celsius."""

    if isinstance(value, dict):
        for key in ("temperature", "current", "value"):
            extracted = _extract_temperature(value.get(key))
            if extracted is not None:
                return extracted
        return None

    if isinstance(value, (int, float)):
        return float(value)

    if isinstance(value, str):
        stripped = value.strip().replace("°C", "")
        try:
            return float(stripped)
        except ValueError:
            return None

    return None


def _format_temperature(disk: Dict[str, Any], temperature_entry: Optional[Any]) -> str:
    """Resolve temperature from disk.temperatures mapping or disk fields."""

    temp = None
    critical = None

    if isinstance(temperature_entry, list):
        if temperature_entry:
            temp = temperature_entry[0]
        if len(temperature_entry) > 1:
            critical = temperature_entry[1]
    elif isinstance(temperature_entry, dict):
        temp = _extract_temperature(temperature_entry.get("temperature"))
        critical = _extract_temperature(temperature_entry.get("critical"))
    else:
        temp = _extract_temperature(temperature_entry)

    if temp is None:
        temp = _extract_temperature(disk.get("temp")) or _extract_temperature(
            disk.get("temperature")
        )

    if temp is None:
        return "Unknown"

    base = (
        f"{temp:.1f}°C" if abs(temp - round(temp)) > 1e-2 else f"{int(round(temp))}°C"
    )
    if critical is not None:
        crit_display = (
            f"{critical:.1f}°C"
            if abs(critical - round(critical)) > 1e-2
            else f"{int(round(critical))}°C"
        )
        base = f"{base} (crit {crit_display})"

    return base


def _derive_status(
    disk: Dict[str, Any],
    temperature_entry: Optional[Any],
) -> str:
    """Derive a user-friendly status using documented disk fields."""

    temp = None
    critical = None

    if isinstance(temperature_entry, list):
        if temperature_entry:
            temp = _extract_temperature(temperature_entry[0])
        if len(temperature_entry) > 1:
            critical = _extract_temperature(temperature_entry[1])
    elif isinstance(temperature_entry, dict):
        temp = _extract_temperature(temperature_entry.get("temperature"))
        critical = _extract_temperature(temperature_entry.get("critical"))
    else:
        temp = _extract_temperature(temperature_entry)

    if temp is None:
        temp = _extract_temperature(disk.get("temp")) or _extract_temperature(
            disk.get("temperature")
        )

    temperature_state = None
    if temp is not None and critical is not None and temp >= critical:
        temperature_state = "Critical temperature"
    elif temp is not None:
        if temp >= 55:
            temperature_state = "Hot"
        elif temp >= 45:
            temperature_state = "Warm"

    if disk.get("expiretime"):
        base = "Expired"
        if temperature_state:
            base = f"{temperature_state}, expired"
        return base

    pool = disk.get("pool")
    if temperature_state and pool:
        return f"{temperature_state} (pool {pool})"
    if temperature_state:
        return temperature_state
    if pool:
        return f"In pool ({pool})"

    return "Available"


class DiskCommands(CommandGroup):
    """Disk operations (``disk.*`` API)."""

    name = "disk"

    def register_commands(
        self,
        subparsers: argparse._SubParsersAction,
        parent_parser: argparse.ArgumentParser,
    ) -> None:
        """Register disk subcommands."""
        # List disks
        list_parser = self.add_command(
            subparsers,
            "list",
            "List disks (disk.query)",
            _cmd_disk_list,
            parent_parser=parent_parser,
        )
        self.add_optional_argument(
            list_parser,
            "--full",
            "full",
            "Show all available fields",
            action="store_true",
        )

        # Health check
        health_parser = self.add_command(
            subparsers,
            "health",
            "Get disk health information (disk.query)",
            _cmd_disk_health,
            parent_parser=parent_parser,
        )
        health_parser.add_argument("disk", help="Disk name (e.g., sda)")


async def _cmd_disk_list(args):
    async def handler(client: TrueNASClient):
        disks = await client.get_disks()
        disk_names: List[str] = []
        for disk in disks:
            name = disk.get("name")
            if isinstance(name, str):
                disk_names.append(name)

        temperatures: Dict[str, Any] = {}
        if disk_names:
            try:
                temperatures = await client.get_disk_temperatures(
                    disk_names, include_thresholds=True
                )
            except Exception:
                temperatures = {}

        if args.json:
            print(json.dumps(disks, indent=2))
            return

        print("\n=== Disks ===")
        if not disks:
            print("No disks found.")
            return

        for disk in disks:
            name = disk.get("name", "Unknown")
            size_str = format_size(disk.get("size"))
            temp_entry = temperatures.get(name, {})
            status = _derive_status(disk, temp_entry)
            temp_str = _format_temperature(disk, temp_entry)

            print(f"\nDisk: {name}")
            print(f"  Size: {size_str}")
            print(f"  Status: {status}")
            print(f"  Temperature: {temp_str}")

            if args.full:
                # Show all available fields
                excluded_keys = {"name", "size", "model", "serial"}
                for key, value in sorted(disk.items()):
                    if key not in excluded_keys:
                        if isinstance(value, bool):
                            value = "Yes" if value else "No"
                        elif isinstance(value, dict):
                            value = json.dumps(value)
                        elif isinstance(value, list):
                            value = ", ".join(map(str, value)) if value else "None"
                        print(f"  {key}: {value}")

    await run_command(args, handler)


async def _cmd_disk_health(args):
    async def handler(client: TrueNASClient):
        disk = await client.get_disk(args.disk)
        temp_mapping = {}
        try:
            temp_mapping = await client.get_disk_temperatures(
                [args.disk], include_thresholds=True
            )
        except Exception:
            temp_mapping = {}

        if args.json:
            print(json.dumps(disk, indent=2))
            return

        print(f"\n=== Disk: {disk.get('name')} ===")
        print(f"Status: {_derive_status(disk, temp_mapping.get(args.disk))}")
        temp_str = _format_temperature(disk, temp_mapping.get(args.disk))
        print(f"Temperature: {temp_str}")
        print(f"Size: {format_size(disk.get('size'))}")
        print(f"Model: {disk.get('model')}")
        print(f"Serial: {disk.get('serial')}")

    await run_command(args, handler)


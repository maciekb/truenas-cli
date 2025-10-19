"""Storage pool operations (pool.* API)."""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from typing import Any, Dict, List, Optional, Sequence

from truenas_client import TrueNASClient

from ..core import format_size, run_command, safe_get
from .base import CommandGroup


class PoolCommands(CommandGroup):
    """Storage pool operations (``pool.*`` API)."""

    name = "pool"

    def register_commands(
        self,
        subparsers: argparse._SubParsersAction,
        parent_parser: argparse.ArgumentParser,
    ) -> None:
        """Register pool subcommands."""
        # List pools
        list_parser = self.add_command(
            subparsers,
            "list",
            "List storage pools (pool.query)",
            _cmd_pool_list,
            parent_parser=parent_parser,
        )
        self.add_optional_argument(
            list_parser,
            "--full",
            "full",
            "Show all available fields",
            action="store_true",
        )

        # Get pool info
        info_parser = self.add_command(
            subparsers,
            "info",
            "Get pool information (pool.query)",
            _cmd_pool_info,
            parent_parser=parent_parser,
        )
        self.add_required_argument(
            info_parser,
            "pool",
            "Pool name",
        )

        # Create pool
        create_parser = self.add_command(
            subparsers,
            "create",
            "Create a new storage pool (pool.create)",
            _cmd_pool_create,
            parent_parser=parent_parser,
        )
        self.add_required_argument(
            create_parser,
            "name",
            "Pool name",
        )
        self.add_required_argument(
            create_parser,
            "disks",
            "Disk names/identifiers (comma-separated)",
        )
        self.add_optional_argument(
            create_parser,
            "--vdev-type",
            "vdev_type",
            "Virtual device type: stripe, mirror, raidz, raidz2, raidz3 (default: stripe)",
            default="stripe",
        )
        self.add_optional_argument(
            create_parser,
            "--encryption",
            "encryption",
            "Enable encryption (yes/no)",
            default="no",
        )
        self.add_optional_argument(
            create_parser,
            "--encryption-key",
            "encryption_key",
            "Encryption key (required if encryption=yes)",
        )

        # Import pool
        import_parser = self.add_command(
            subparsers,
            "import",
            "Import an existing pool (pool.import_find)",
            _cmd_pool_import,
            parent_parser=parent_parser,
        )
        self.add_required_argument(
            import_parser,
            "name",
            "Pool name to import",
        )
        self.add_optional_argument(
            import_parser,
            "--guid",
            "guid",
            "Pool GUID (optional)",
        )

        # Export pool
        export_parser = self.add_command(
            subparsers,
            "export",
            "Export a pool (pool.export)",
            _cmd_pool_export,
            parent_parser=parent_parser,
        )
        self.add_required_argument(
            export_parser,
            "pool",
            "Pool name to export",
        )
        self.add_optional_argument(
            export_parser,
            "--force",
            "force",
            "Force export even if in use",
            action="store_true",
        )

        # Delete pool
        delete_parser = self.add_command(
            subparsers,
            "delete",
            "Delete a pool (pool.delete)",
            _cmd_pool_delete,
            parent_parser=parent_parser,
        )
        self.add_required_argument(
            delete_parser,
            "pool",
            "Pool name to delete",
        )
        self.add_optional_argument(
            delete_parser,
            "--force",
            "force",
            "Force deletion without confirmation",
            action="store_true",
        )
        self.add_optional_argument(
            delete_parser,
            "--remove-data",
            "remove_data",
            "Remove all data from disks",
            action="store_true",
        )

        parents = [parent_parser] if parent_parser else []

        # Scrub maintenance commands
        scrub_parser = subparsers.add_parser(
            "scrub",
            help="Manage pool scrub schedules",
            parents=parents,
        )
        scrub_parser.set_defaults(
            func=_cmd_pool_scrub_root,
            _scrub_parser=scrub_parser,
        )
        scrub_subparsers = scrub_parser.add_subparsers(dest="scrub_command")

        scrub_list_parser = scrub_subparsers.add_parser(
            "list",
            help="List scrub schedules (pool.scrub.query)",
            parents=parents,
        )
        scrub_list_parser.set_defaults(func=_cmd_pool_scrub_list)
        scrub_list_parser.add_argument(
            "--pool",
            help="Filter by pool name",
        )

        scrub_run_parser = scrub_subparsers.add_parser(
            "run",
            help="Trigger a pool scrub (pool.scrub.run)",
            parents=parents,
        )
        scrub_run_parser.set_defaults(func=_cmd_pool_scrub_run)
        scrub_run_parser.add_argument(
            "pool",
            help="Pool name to scrub",
        )
        scrub_run_parser.add_argument(
            "--threshold",
            type=int,
            help="Override threshold days before automatic scrub (default: 35)",
        )

        scrub_update_parser = scrub_subparsers.add_parser(
            "update",
            help="Update scrub schedule (pool.scrub.update)",
            parents=parents,
        )
        scrub_update_parser.set_defaults(func=_cmd_pool_scrub_update)
        scrub_update_parser.add_argument(
            "scrub_id",
            type=int,
            help="Scrub schedule ID",
        )
        scrub_update_parser.add_argument(
            "--threshold",
            type=int,
            help="Days before scrub runs automatically",
        )
        scrub_update_parser.add_argument(
            "--description",
            help="Optional description for the schedule",
        )
        scrub_update_parser.add_argument(
            "--schedule",
            help="Cron-style schedule (minute hour dom month dow)",
        )
        toggle_group = scrub_update_parser.add_mutually_exclusive_group()
        toggle_group.add_argument(
            "--enable",
            action="store_true",
            dest="enable",
            help="Enable the scrub schedule",
        )
        toggle_group.add_argument(
            "--disable",
            action="store_true",
            dest="disable",
            help="Disable the scrub schedule",
        )

        scrub_delete_parser = scrub_subparsers.add_parser(
            "delete",
            help="Delete scrub schedule (pool.scrub.delete)",
            parents=parents,
        )
        scrub_delete_parser.set_defaults(func=_cmd_pool_scrub_delete)
        scrub_delete_parser.add_argument(
            "scrub_id",
            type=int,
            help="Scrub schedule ID",
        )

        # Resilver configuration commands
        resilver_parser = subparsers.add_parser(
            "resilver",
            help="Manage resilver priority window",
            parents=parents,
        )
        resilver_parser.set_defaults(
            func=_cmd_pool_resilver_root,
            _resilver_parser=resilver_parser,
        )
        resilver_sub = resilver_parser.add_subparsers(dest="resilver_command")

        resilver_status_parser = resilver_sub.add_parser(
            "status",
            help="Show resilver configuration (pool.resilver.config)",
            parents=parents,
        )
        resilver_status_parser.set_defaults(func=_cmd_pool_resilver_status)

        resilver_update_parser = resilver_sub.add_parser(
            "update",
            help="Update resilver window (pool.resilver.update)",
            parents=parents,
        )
        resilver_update_parser.set_defaults(func=_cmd_pool_resilver_update)
        resilver_update_parser.add_argument(
            "--begin",
            help="Window start time (HH:MM, 24h)",
        )
        resilver_update_parser.add_argument(
            "--end",
            help="Window end time (HH:MM, 24h)",
        )
        resilver_update_parser.add_argument(
            "--weekday",
            help="Comma-separated weekdays (1=Mon .. 7=Sun)",
        )
        toggle_resilver = resilver_update_parser.add_mutually_exclusive_group()
        toggle_resilver.add_argument(
            "--enable",
            action="store_true",
            dest="enable",
            help="Enable the resilver window",
        )
        toggle_resilver.add_argument(
            "--disable",
            action="store_true",
            dest="disable",
            help="Disable the resilver window",
        )


async def _cmd_pool_list(args):
    async def handler(client: TrueNASClient):
        pools = await client.get_pools()

        if args.json:
            print(json.dumps(pools, indent=2))
            return

        print("\n=== Storage Pools ===")
        if not pools:
            print("No pools found.")
            return

        for pool in pools:
            print(f"\nPool: {pool.get('name')}")
            print(f"  Status: {pool.get('status')}")
            for key in ["size", "allocated", "free"]:
                str_key = f"{key}_str"
                val = pool.get(str_key) or pool.get(key)
                formatted = format_size(val)
                print(f"  {key.capitalize()}: {formatted}")

            if args.full:
                # Show all available fields
                excluded_keys = {
                    "name",
                    "status",
                    "size",
                    "allocated",
                    "free",
                    "size_str",
                    "allocated_str",
                    "free_str",
                }
                for key, value in sorted(pool.items()):
                    if key not in excluded_keys:
                        if isinstance(value, bool):
                            value = "Yes" if value else "No"
                        elif isinstance(value, dict):
                            value = json.dumps(value)
                        elif isinstance(value, list):
                            value = ", ".join(map(str, value)) if value else "None"
                        print(f"  {key}: {value}")

    await run_command(args, handler)


async def _cmd_pool_info(args):
    async def handler(client: TrueNASClient):
        pool = await client.get_pool(args.pool)

        if args.json:
            print(json.dumps(pool, indent=2))
            return

        print(f"\n=== Pool: {pool.get('name')} ===")
        print(f"Status: {pool.get('status')}")

        for key in ["size", "allocated", "free"]:
            str_key = f"{key}_str"
            val = pool.get(str_key) or pool.get(key)
            formatted = format_size(val)
            print(f"{key.capitalize()}: {formatted}")

        health = safe_get(pool, "health")
        if health is not None:
            print(f"Healthy: {health}")

    await run_command(args, handler)


async def _cmd_pool_create(args):
    """Handle ``pool create`` using ``pool.create``."""

    async def handler(client: TrueNASClient):
        disk_list = [d.strip() for d in args.disks.split(",")]

        # Build vdevs structure
        vdevs = []
        if args.vdev_type == "stripe":
            vdevs = [{"type": "disk", "disks": disk_list}]
        else:
            vdevs = [{"type": args.vdev_type, "disks": disk_list}]

        pool_params = {
            "name": args.name,
            "vdevs": vdevs,
        }

        if args.encryption and args.encryption.lower() == "yes":
            if not args.encryption_key:
                print("Error: --encryption-key required when encryption is enabled")
                return
            pool_params["encryption"] = True
            pool_params["encryption_key"] = args.encryption_key

        print(f"Creating pool '{args.name}' with {args.vdev_type} vdev...")
        result = await client.call("pool.create", [pool_params])

        if args.json:
            print(json.dumps(result, indent=2))
            return

        print(f"Pool '{args.name}' created successfully")

    await run_command(args, handler)


async def _cmd_pool_import(args):
    """Handle ``pool import`` using ``pool.import_find``."""

    async def handler(client: TrueNASClient, _args=args):
        print(f"Searching for pool '{_args.name}'...")

        # Find available pools to import
        available_pools = await client.call("pool.import_find", [])

        if _args.json:
            print(json.dumps(available_pools, indent=2))
            return

        # Search for matching pool
        matching_pool = None
        for pool in available_pools:
            if pool.get("name") == _args.name or (
                _args.guid and pool.get("guid") == _args.guid
            ):
                matching_pool = pool
                break

        if not matching_pool:
            print(f"Pool '{_args.name}' not found")
            return

        print(f"Found pool '{_args.name}' (guid: {matching_pool.get('guid')})")
        print("Importing pool...")

        import_params = {"name": _args.name}
        result = await client.call("pool.import_pool", [import_params])

        print(f"Pool '{_args.name}' imported successfully")

    await run_command(args, handler)


async def _cmd_pool_export(args):
    """Handle ``pool export`` using ``pool.export``."""

    async def handler(client: TrueNASClient):
        print(f"Exporting pool '{args.pool}'...")

        export_params = {
            "pool": args.pool,
            "force": args.force,
        }

        result = await client.call("pool.export", [export_params])

        if args.json:
            print(json.dumps(result, indent=2))
            return

        print(f"Pool '{args.pool}' exported successfully")

    await run_command(args, handler)


async def _cmd_pool_delete(args):
    """Handle ``pool delete`` using ``pool.delete``."""

    async def handler(client: TrueNASClient):
        if not args.force:
            print(f"WARNING: Deleting pool '{args.pool}' will erase all data!")
            response = input("Continue? [yes/no]: ")
            if response.lower() != "yes":
                print("Cancelled")
                return

        print(f"Deleting pool '{args.pool}'...")

        delete_params = {
            "pool": args.pool,
            "force": args.force,
            "remove_data": args.remove_data,
        }

        result = await client.call("pool.delete", [delete_params])

        if args.json:
            print(json.dumps(result, indent=2))
            return

        print(f"Pool '{args.pool}' deleted successfully")

    await run_command(args, handler)


def _format_timestamp(value: Any) -> str:
    """Render timestamp values from various formats."""
    if value is None:
        return "N/A"

    if isinstance(value, dict):
        if "$date" in value and isinstance(value["$date"], (int, float)):
            return _format_timestamp(value["$date"])
        parsed = value.get("parsed")
        if isinstance(parsed, dict):
            return _format_timestamp(parsed.get("$date"))
        return json.dumps(value)

    if isinstance(value, (int, float)):
        dt = datetime.fromtimestamp(value / 1000 if value > 1e12 else value)
        return dt.isoformat(sep=" ", timespec="seconds")

    if isinstance(value, str):
        try:
            dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
            localized = dt.astimezone() if dt.tzinfo else dt
            return localized.isoformat(sep=" ", timespec="seconds")
        except ValueError:
            return value

    return str(value)


def _scrub_pool_name(scrub: Dict[str, Any]) -> str:
    """Derive pool name from scrub entry."""
    direct_name = safe_get(scrub, "pool_name")
    if direct_name:
        return str(direct_name)

    pool_entry = safe_get(scrub, "pool")
    if isinstance(pool_entry, dict):
        name = safe_get(pool_entry, "name")
        if name:
            return str(name)
        identifier = safe_get(pool_entry, "id")
        if identifier is not None:
            return f"#{identifier}"
    if isinstance(pool_entry, (str, int)):
        return str(pool_entry)
    return "Unknown"


def _format_scrub_schedule(schedule: Optional[Dict[str, Any]]) -> str:
    """Format cron-style scrub schedule."""
    if not isinstance(schedule, dict):
        return "N/A"
    fields = [
        str(schedule.get("minute", "*")),
        str(schedule.get("hour", "*")),
        str(schedule.get("dom", "*")),
        str(schedule.get("month", "*")),
        str(schedule.get("dow", "*")),
    ]
    return " ".join(fields)


def _parse_cron_schedule(expr: str) -> Dict[str, str]:
    """Parse space-separated cron schedule expression."""
    parts = expr.split()
    if len(parts) != 5:
        raise ValueError(
            "Schedule must contain five space-separated fields "
            "(minute hour day-of-month month day-of-week)."
        )
    keys = ["minute", "hour", "dom", "month", "dow"]
    return {key: part for key, part in zip(keys, parts)}


def _parse_weekday_list(value: str) -> List[int]:
    """Parse comma-separated weekday values."""
    weekdays: List[int] = []
    for chunk in value.split(","):
        stripped = chunk.strip()
        if not stripped:
            continue
        number = int(stripped)
        if number < 0 or number > 7:
            raise ValueError("Weekday values must be between 0 and 7.")
        weekdays.append(number)
    if not weekdays:
        raise ValueError("At least one weekday must be provided.")
    return weekdays


async def _cmd_pool_scrub_root(args: argparse.Namespace) -> None:
    """Handle ``pool scrub`` root without subcommand."""

    parser = getattr(args, "_scrub_parser", None)
    if isinstance(parser, argparse.ArgumentParser):
        parser.print_help()
    else:
        print("Specify a scrub subcommand. Use --help for available options.")


async def _cmd_pool_scrub_list(args: argparse.Namespace) -> None:
    """List configured scrub schedules."""

    async def handler(client: TrueNASClient) -> None:
        scrubs = await client.get_pool_scrubs()

        if args.pool:
            requested = args.pool.lower()
            scrubs = [
                entry
                for entry in scrubs
                if _scrub_pool_name(entry).lower() == requested
            ]

        if args.json:
            print(json.dumps(scrubs, indent=2))
            return

        print("\n=== Pool Scrub Schedules ===")
        if not scrubs:
            if args.pool:
                print(f"No scrub schedules found for pool '{args.pool}'.")
            else:
                print("No scrub schedules configured.")
            return

        for scrub in scrubs:
            schedule_id = safe_get(scrub, "id", "N/A")
            pool_name = _scrub_pool_name(scrub)
            enabled = safe_get(scrub, "enabled", False)
            threshold = safe_get(scrub, "threshold")
            description = safe_get(scrub, "description")
            last_run = _format_timestamp(safe_get(scrub, "last_run"))
            next_run = _format_timestamp(safe_get(scrub, "next_run"))
            schedule = _format_scrub_schedule(safe_get(scrub, "schedule", {}))

            icon = "✓" if enabled else "✗"
            print(f"\n[{schedule_id}] {pool_name} {icon}")
            if threshold is not None:
                print(f"  Threshold: {threshold} day(s)")
            print(f"  Enabled: {'Yes' if enabled else 'No'}")
            print(f"  Schedule: {schedule}")
            if description:
                print(f"  Description: {description}")
            if last_run != "N/A":
                print(f"  Last Run: {last_run}")
            if next_run != "N/A":
                print(f"  Next Run: {next_run}")

    await run_command(args, handler)


async def _cmd_pool_scrub_run(args: argparse.Namespace) -> None:
    """Trigger a scrub run."""

    async def handler(client: TrueNASClient) -> None:
        threshold = args.threshold
        print(f"Requesting scrub for pool '{args.pool}'...")
        result = await client.run_pool_scrub(
            args.pool,
            threshold=threshold,
        )

        if args.json:
            print(
                json.dumps(
                    {
                        "pool": args.pool,
                        "threshold": threshold,
                        "result": result,
                    },
                    indent=2,
                )
            )
            return

        print(f"✓ Scrub request submitted for pool '{args.pool}'")

    await run_command(args, handler)


async def _cmd_pool_scrub_update(args: argparse.Namespace) -> None:
    """Update scrub schedule settings."""

    async def handler(client: TrueNASClient) -> None:
        payload: Dict[str, Any] = {}

        if args.threshold is not None:
            payload["threshold"] = args.threshold
        if args.description:
            payload["description"] = args.description
        if args.schedule:
            payload["schedule"] = _parse_cron_schedule(args.schedule)
        if args.enable:
            payload["enabled"] = True
        elif args.disable:
            payload["enabled"] = False

        if not payload:
            raise ValueError("No update parameters provided.")

        result = await client.update_pool_scrub(args.scrub_id, **payload)

        if args.json:
            print(json.dumps(result, indent=2))
            return

        print(f"✓ Scrub schedule {args.scrub_id} updated")

    await run_command(args, handler)


async def _cmd_pool_scrub_delete(args: argparse.Namespace) -> None:
    """Delete a scrub schedule."""

    async def handler(client: TrueNASClient) -> None:
        print(f"Deleting scrub schedule {args.scrub_id}...")
        result = await client.delete_pool_scrub(args.scrub_id)

        if args.json:
            print(json.dumps({"deleted": bool(result), "id": args.scrub_id}, indent=2))
            return

        print(f"✓ Scrub schedule {args.scrub_id} deleted")

    await run_command(args, handler)


async def _cmd_pool_resilver_root(args: argparse.Namespace) -> None:
    """Handle ``pool resilver`` root without subcommand."""

    parser = getattr(args, "_resilver_parser", None)
    if isinstance(parser, argparse.ArgumentParser):
        parser.print_help()
    else:
        print("Specify a resilver subcommand. Use --help for available options.")


async def _cmd_pool_resilver_status(args: argparse.Namespace) -> None:
    """Display resilver configuration."""

    async def handler(client: TrueNASClient) -> None:
        config = await client.get_resilver_config()

        if args.json:
            print(json.dumps(config, indent=2))
            return

        enabled = safe_get(config, "enabled", True)
        begin = safe_get(config, "begin", "18:00")
        end = safe_get(config, "end", "09:00")
        weekday = safe_get(config, "weekday", list(range(1, 8)))

        print("\n=== Resilver Priority Window ===")
        print(f"Enabled: {'Yes' if enabled else 'No'}")
        print(f"Begin: {begin}")
        print(f"End: {end}")
        if isinstance(weekday, Sequence):
            weekday_str = ", ".join(map(str, weekday))
            print(f"Weekdays: {weekday_str}")
        identifier = safe_get(config, "id")
        if identifier is not None:
            print(f"ID: {identifier}")

    await run_command(args, handler)


async def _cmd_pool_resilver_update(args: argparse.Namespace) -> None:
    """Update resilver priority configuration."""

    async def handler(client: TrueNASClient) -> None:
        payload: Dict[str, Any] = {}

        if args.begin:
            payload["begin"] = args.begin
        if args.end:
            payload["end"] = args.end
        if args.weekday:
            payload["weekday"] = _parse_weekday_list(args.weekday)
        if args.enable:
            payload["enabled"] = True
        elif args.disable:
            payload["enabled"] = False

        if not payload:
            raise ValueError("No update parameters provided.")

        result = await client.update_resilver_config(**payload)

        if args.json:
            print(json.dumps(result, indent=2))
            return

        print("✓ Resilver configuration updated")

    await run_command(args, handler)

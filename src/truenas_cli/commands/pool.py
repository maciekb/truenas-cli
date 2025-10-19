"""Storage pool operations (pool.* API)."""

from __future__ import annotations

import argparse
import json

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

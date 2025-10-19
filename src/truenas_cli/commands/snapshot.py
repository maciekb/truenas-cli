from __future__ import annotations

import argparse
import json

from truenas_client import TrueNASClient

from ..core import format_size, run_command
from .base import CommandGroup


class SnapshotCommands(CommandGroup):
    """Snapshot operations (``pool.snapshot`` namespace)."""

    name = "snapshot"

    def register_commands(
        self,
        subparsers: argparse._SubParsersAction,
        parent_parser: argparse.ArgumentParser,
    ) -> None:
        """Register snapshot subcommands."""
        # List snapshots
        list_parser = self.add_command(
            subparsers,
            "list",
            "List snapshots (pool.snapshot.query)",
            _cmd_snapshot_list,
            parent_parser=parent_parser,
        )
        self.add_optional_argument(
            list_parser,
            ["-d", "--dataset"],
            "dataset",
            "Dataset name (optional filter)",
        )
        self.add_optional_argument(
            list_parser,
            "--full",
            "full",
            "Show all available fields",
            action="store_true",
        )

        # Create snapshot
        create_parser = self.add_command(
            subparsers,
            "create",
            "Create snapshot (pool.snapshot.create)",
            _cmd_snapshot_create,
            parent_parser=parent_parser,
        )
        self.add_optional_argument(
            create_parser,
            ["-d", "--dataset"],
            "dataset",
            "Dataset name",
            required=True,
        )
        self.add_optional_argument(
            create_parser,
            ["-n", "--name"],
            "name",
            "Snapshot name",
            required=True,
        )
        self.add_optional_argument(
            create_parser,
            "--recursive",
            "recursive",
            "Create recursive snapshot (optional)",
            action="store_true",
        )

        # Delete snapshots
        delete_parser = self.add_command(
            subparsers,
            "delete",
            "Delete snapshot(s) (pool.snapshot.delete)",
            _cmd_snapshot_delete,
            parent_parser=parent_parser,
        )
        delete_parser.add_argument(
            "snapshots",
            nargs="+",
            type=str,
            help="Snapshot path(s) to delete (e.g., tank/data@daily)",
        )
        self.add_optional_argument(
            delete_parser,
            ["-f", "--force"],
            "force",
            "Force delete without confirmation",
            action="store_true",
        )

        # Rollback to snapshot
        rollback_parser = self.add_command(
            subparsers,
            "rollback",
            "Rollback to snapshot (pool.dataset.snapshot_rollback)",
            _cmd_snapshot_rollback,
            parent_parser=parent_parser,
        )
        self.add_required_argument(
            rollback_parser,
            "snapshot",
            "Snapshot path (e.g., tank/data@daily)",
        )
        self.add_optional_argument(
            rollback_parser,
            ["-f", "--force"],
            "force",
            "Force rollback without confirmation",
            action="store_true",
        )
        self.add_optional_argument(
            rollback_parser,
            ["-r", "--recursive"],
            "recursive",
            "Recursively rollback child datasets",
            action="store_true",
        )


async def _cmd_snapshot_list(args):
    async def handler(client: TrueNASClient):
        snapshots = await client.get_snapshots(args.dataset if args.dataset else None)

        if args.json:
            print(json.dumps(snapshots, indent=2))
            return

        print("\n=== Snapshots ===")
        if not snapshots:
            print("No snapshots found.")
            return

        for snap in snapshots:
            snap_name = snap.get("name", "N/A")
            creation = snap.get("creation", "N/A")
            used = snap.get("used")

            print(f"\nSnapshot: {snap_name}")
            print(f"  Created: {creation}")
            print(f"  Used: {format_size(used)}")

            if args.full:
                # Show all available fields
                excluded_keys = {"name", "creation", "used"}
                for key, value in sorted(snap.items()):
                    if key not in excluded_keys:
                        if isinstance(value, bool):
                            value = "Yes" if value else "No"
                        elif isinstance(value, dict):
                            value = json.dumps(value)
                        elif isinstance(value, list):
                            value = ", ".join(map(str, value)) if value else "None"
                        print(f"  {key}: {value}")

    await run_command(args, handler)


async def _cmd_snapshot_create(args):
    async def handler(client: TrueNASClient):
        payload = {
            "dataset_name": args.dataset,
            "snapshot_name": args.name,
        }
        if args.recursive:
            payload["recursive"] = True

        snapshot = await client.create_snapshot(**payload)

        if args.json:
            print(json.dumps(snapshot, indent=2))
            return

        print(f"✓ Snapshot created: {args.dataset}@{args.name}")

    await run_command(args, handler)


async def _cmd_snapshot_delete(args):
    async def handler(client: TrueNASClient):
        snapshots = list(args.snapshots)

        if not args.force:
            count = len(snapshots)
            names = ", ".join(snapshots)
            confirm = input(f"Delete {count} snapshot(s): {names}? (yes/no): ")
            if confirm.lower() != "yes":
                print("Cancelled.")
                return

        results = []
        errors = []

        for snapshot in snapshots:
            try:
                await client.delete_snapshot(snapshot)
                results.append(snapshot)
            except Exception as exc:
                errors.append({"snapshot": snapshot, "error": str(exc)})

        if args.json:
            print(
                json.dumps(
                    {"deleted": results, "errors": errors or None},
                    indent=2,
                )
            )
            if errors:
                raise SystemExit(1)
            return

        if results:
            print(f"✓ Deleted {len(results)} snapshot(s):")
            for snap in results:
                print(f"  • {snap}")

        if errors:
            print(f"\n✗ Failed to delete {len(errors)} snapshot(s):")
            for err in errors:
                print(f"  • {err['snapshot']}: {err['error']}")
            raise SystemExit(1)

    await run_command(args, handler)


async def _cmd_snapshot_rollback(args):
    """Handle ``snapshot rollback`` using ``pool.dataset.snapshot_rollback``."""

    async def handler(client: TrueNASClient):
        snapshot_name = args.snapshot

        if "@" not in snapshot_name:
            print(
                "Error: Invalid snapshot path. Use format: dataset@snapshot (e.g., tank/data@daily)"
            )
            return

        if not args.force:
            confirm = input(
                f"WARNING: Rolling back to snapshot '{snapshot_name}' will discard "
                f"all changes made after this snapshot. Continue? (yes/no): "
            )
            if confirm.lower() != "yes":
                print("Cancelled.")
                return

        print(f"Rolling back to snapshot '{snapshot_name}'...")

        rollback_params = {
            "recursive": args.recursive,
        }

        result = await client.call(
            "pool.dataset.snapshot_rollback", [snapshot_name, rollback_params]
        )

        if args.json:
            print(json.dumps(result, indent=2))
            return

        print(f"✓ Successfully rolled back to snapshot '{snapshot_name}'")

    await run_command(args, handler)

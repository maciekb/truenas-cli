from __future__ import annotations

import argparse
import json

from truenas_client import TrueNASClient

from ..core import run_command, safe_get
from .base import CommandGroup


class NFSCommands(CommandGroup):
    """NFS share operations (``sharing.nfs`` API)."""

    name = "nfs"

    def register_commands(
        self,
        subparsers: argparse._SubParsersAction,
        parent_parser: argparse.ArgumentParser,
    ) -> None:
        """Register NFS subcommands."""
        # List shares
        list_parser = self.add_command(
            subparsers,
            "list",
            "List NFS shares (sharing.nfs.query)",
            _cmd_nfs_list,
            parent_parser=parent_parser,
        )
        self.add_optional_argument(
            list_parser,
            "--full",
            "full",
            "Show all available fields",
            action="store_true",
        )

        # Create share
        create_parser = self.add_command(
            subparsers,
            "create",
            "Create NFS share (sharing.nfs.create)",
            _cmd_nfs_create,
            parent_parser=parent_parser,
        )
        self.add_optional_argument(
            create_parser, "-p", "pool", "Pool name", required=True
        )
        self.add_optional_argument(
            create_parser, "-d", "dataset", "Dataset name", required=True
        )
        self.add_optional_argument(
            create_parser, "-c", "comment", "Share comment (optional)"
        )

        # Delete shares
        delete_parser = self.add_command(
            subparsers,
            "delete",
            "Delete NFS share(s) (sharing.nfs.delete)",
            _cmd_nfs_delete,
            parent_parser=parent_parser,
        )
        delete_parser.add_argument(
            "ids",
            nargs="+",
            type=int,
            help="NFS share ID(s) to delete",
        )
        delete_parser.add_argument(
            "-f",
            "--force",
            action="store_true",
            help="Force delete without confirmation",
        )


async def _cmd_nfs_list(args):
    async def handler(client: TrueNASClient):
        shares = await client.get_nfs_shares()

        if args.json:
            print(json.dumps(shares, indent=2))
            return

        print("\n=== NFS Shares ===")
        if not shares:
            print("No NFS shares found.")
            return

        for share in shares:
            share_id = safe_get(share, "id", "N/A")
            path = safe_get(share, "path", "N/A")
            print(f"\nShare: {path}")
            print(f"  ID: {share_id}")

            if args.full:
                # Show all available fields
                for key, value in sorted(share.items()):
                    if key not in ("id", "path"):
                        if isinstance(value, bool):
                            value = "Yes" if value else "No"
                        elif isinstance(value, list):
                            value = ", ".join(map(str, value)) if value else "None"
                        print(f"  {key}: {value}")
            else:
                # Show selected fields only
                # Read-only status
                ro = safe_get(share, "ro")
                print(f"  Read-only: {'Yes' if ro else 'No'}")

                # Networks (if not all)
                networks = safe_get(share, "networks", [])
                if networks and networks != ["*"]:
                    formatted_networks = (
                        ", ".join(networks)
                        if isinstance(networks, list)
                        else str(networks)
                    )
                    print(f"  Networks: {formatted_networks}")

                # Comment (if present)
                comment = safe_get(share, "comment")
                if comment:
                    print(f"  Comment: {comment}")

    await run_command(args, handler)


async def _cmd_nfs_create(args):
    async def handler(client: TrueNASClient):
        dataset_name = f"{args.pool}/{args.dataset}"
        dataset_path = f"/mnt/{dataset_name}"

        print(f"\n=== Creating NFS Share for '{dataset_path}' ===\n")

        print("Step 1: Ensuring dataset exists (pool.dataset.create)...")
        try:
            dataset = await client.create_dataset(
                name=dataset_name,
                dataset_type="FILESYSTEM",
            )
            print(f"  ✓ Dataset created: {safe_get(dataset, 'name', dataset_name)}")
            print(f"  Mount path: {safe_get(dataset, 'mountpoint', dataset_path)}")
        except ValueError:
            print("  ℹ Dataset already exists")

        print("\nStep 2: Ensuring NFS service availability (service.*)...")
        try:
            service = await client.ensure_nfs_service_running()
            print(f"  ✓ NFS service state: {safe_get(service, 'state', 'UNKNOWN')}")
        except Exception as exc:
            print(f"  ⚠️  Could not verify NFS service: {exc}")

        print("\nStep 3: Creating NFS share (sharing.nfs.create)...")
        share = None
        if await client.nfs_share_exists_for_path(dataset_path):
            print("  ℹ NFS share for this path already exists")
            shares = await client.get_nfs_shares()
            share = next(
                (s for s in shares if safe_get(s, "path") == dataset_path), None
            )
        else:
            share = await client.create_nfs_share(
                path=dataset_path,
                comment=args.comment or "",
            )

        if args.json:
            print(json.dumps(share or {}, indent=2))
        else:
            if share:
                print("  ✓ NFS share ready")
                if safe_get(share, "id"):
                    print(f"  ID: {safe_get(share, 'id')}")
                share_paths = safe_get(share, "paths")
                if share_paths:
                    print(f"  Paths: {', '.join(share_paths)}")
                else:
                    print(f"  Path: {dataset_path}")
            else:
                print("  ✓ NFS share creation completed")
                print(f"  Path: {dataset_path}")

            print("\n=== NFS Share Ready ===")
            print(f"Share path: {dataset_path}")
            print(f"Mount point: /mnt/{dataset_name}")

    await run_command(args, handler)


async def _cmd_nfs_delete(args):
    async def handler(client: TrueNASClient):
        share_ids = list(args.ids)

        if not args.force:
            count = len(share_ids)
            names = ", ".join(map(str, share_ids))
            confirm = input(f"Delete {count} NFS share(s): {names}? (yes/no): ")
            if confirm.lower() != "yes":
                print("Cancelled.")
                return

        results = []
        errors = []

        for share_id in share_ids:
            try:
                await client.delete_nfs_share(share_id)
                results.append(share_id)
            except Exception as exc:
                errors.append({"id": share_id, "error": str(exc)})

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
            print(f"✓ Deleted {len(results)} NFS share(s):")
            for share_id in results:
                print(f"  • ID: {share_id}")

        if errors:
            print(f"\n✗ Failed to delete {len(errors)} NFS share(s):")
            for err in errors:
                print(f"  • ID {err['id']}: {err['error']}")
            raise SystemExit(1)

    await run_command(args, handler)

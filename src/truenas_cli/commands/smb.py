"""SMB share operations (sharing.smb API)."""

from __future__ import annotations

import argparse
import json
from argparse import Namespace

from truenas_client import TrueNASClient

from ..core import run_command, safe_get
from .base import CommandGroup


class SMBCommands(CommandGroup):
    """SMB share operations (``sharing.smb`` API)."""

    name = "smb"

    def register_commands(
        self,
        subparsers: argparse._SubParsersAction,
        parent_parser: argparse.ArgumentParser,
    ) -> None:
        """Register SMB subcommands."""
        # List presets
        self.add_command(
            subparsers,
            "list-presets",
            "List SMB presets (sharing.smb.presets)",
            _cmd_smb_list_presets,
            parent_parser=parent_parser,
        )

        # List shares
        list_parser = self.add_command(
            subparsers,
            "list",
            "List SMB shares (sharing.smb.query)",
            _cmd_smb_list_shares,
            parent_parser=parent_parser,
        )
        self.add_optional_argument(
            list_parser,
            ["-F", "--full"],
            "full",
            "Show all available fields",
            action="store_true",
        )

        # Create share
        create_parser = self.add_command(
            subparsers,
            "create",
            "Create SMB share (sharing.smb.create)",
            _cmd_smb_create,
            parent_parser=parent_parser,
        )
        self.add_optional_argument(
            create_parser,
            ["-p", "--pool"],
            "pool",
            "Pool name",
            required=True,
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
            ["-s", "--share"],
            "share",
            "Share name",
            required=True,
        )
        self.add_optional_argument(
            create_parser,
            ["-c", "--comment"],
            "comment",
            "Share comment (optional)",
        )
        self.add_optional_argument(
            create_parser,
            "--preset",
            "preset",
            "Use preset (e.g., DEFAULT_SHARE)",
        )

        # Delete shares
        delete_parser = self.add_command(
            subparsers,
            "delete",
            "Delete SMB share(s) (sharing.smb.delete)",
            _cmd_smb_delete,
            parent_parser=parent_parser,
        )
        delete_parser.add_argument(
            "ids",
            nargs="+",
            type=int,
            help="SMB share ID(s) to delete",
        )
        delete_parser.add_argument(
            "-f",
            "--force",
            action="store_true",
            help="Force delete without confirmation",
        )


async def _cmd_smb_list_presets(args: Namespace) -> None:
    async def handler(client: TrueNASClient):
        presets = await client.get_smb_presets()

        if args.json:
            print(json.dumps(presets, indent=2))
            return

        print("\n=== Available SMB Share Presets ===\n")
        for preset_name, config in presets.items():
            print(f"{preset_name}:")
            for key, value in config.items():
                print(f"  {key}: {value}")
            print()

    await run_command(args, handler)


async def _cmd_smb_list_shares(args: Namespace) -> None:
    async def handler(client: TrueNASClient):
        shares = await client.get_smb_shares()

        if args.json:
            print(json.dumps(shares, indent=2))
            return

        print("\n=== SMB Shares ===")
        if not shares:
            print("No SMB shares found.")
            return

        for share in shares:
            share_name = share.get("name", "N/A")
            share_id = share.get("id", "N/A")
            path = share.get("path", "N/A")
            enabled = share.get("enabled", False)
            comment = share.get("comment")

            print(f"\nShare: {share_name}")
            print(f"  ID: {share_id}")
            print(f"  Path: {path}")
            print(f"  Enabled: {'Yes' if enabled else 'No'}")

            if args.full:
                # Show all available fields
                for key, value in sorted(share.items()):
                    if key not in ("name", "id", "path", "enabled", "comment"):
                        if isinstance(value, bool):
                            value = "Yes" if value else "No"
                        elif isinstance(value, list):
                            value = ", ".join(map(str, value)) if value else "None"
                        elif isinstance(value, dict):
                            value = json.dumps(value)
                        print(f"  {key}: {value}")
            else:
                # Comment (if present)
                if comment:
                    print(f"  Comment: {comment}")

    await run_command(args, handler)


async def _cmd_smb_create(args: Namespace) -> None:
    async def handler(client: TrueNASClient):
        full_dataset_name = f"{args.pool}/{args.dataset}"
        dataset_mount_path = f"/mnt/{full_dataset_name}"

        print(f"\n=== Creating SMB Share '{args.share}' ===\n")
        print(f"Step 1: Ensuring dataset '{full_dataset_name}' exists...")

        try:
            dataset = await client.create_dataset(
                name=full_dataset_name,
                dataset_type="FILESYSTEM",
            )
            print(
                f"  ✓ Dataset created: {safe_get(dataset, 'name', full_dataset_name)}"
            )
            print(
                f"  Mount path: {safe_get(dataset, 'mountpoint', dataset_mount_path)}"
            )
        except ValueError:
            dataset = await client.get_dataset(full_dataset_name)
            print("  ℹ Dataset already exists")
            print(
                f"  Mount path: {safe_get(dataset, 'mountpoint', dataset_mount_path)}"
            )

        print("\nStep 2: Ensuring SMB service availability (service.*)...")
        try:
            service = await client.ensure_smb_service_running()
            print(f"  ✓ SMB service state: {safe_get(service, 'state', 'UNKNOWN')}")
        except Exception as exc:
            print(f"  ⚠️  Could not verify SMB service: {exc}")

        print(f"\nStep 3: Creating SMB share '{args.share}' (sharing.smb.create)...")
        if args.preset:
            print(f"  Using preset: {args.preset}")
            smb_share = await client.create_smb_share_with_preset(
                path=dataset_mount_path,
                name=args.share,
                preset=args.preset,
                comment=args.comment or "",
                enabled=True,
            )
        else:
            smb_share = await client.create_smb_share(
                path=dataset_mount_path,
                name=args.share,
                comment=args.comment or "",
                enabled=True,
            )

        if smb_share:
            print(f"  ✓ SMB share created: {safe_get(smb_share, 'name', args.share)}")
            if safe_get(smb_share, "id"):
                print(f"  Share ID: {safe_get(smb_share, 'id')}")
            print(f"  Path: {safe_get(smb_share, 'path', dataset_mount_path)}")
            print(f"  Enabled: {safe_get(smb_share, 'enabled', True)}")
        else:
            print(f"  ✓ SMB share created: {args.share}")
            print(f"  Path: {dataset_mount_path}")

        print("\n=== SMB Share Ready! ===")
        print(f"Share name: \\\\{client.host}\\{args.share}")
        print(f"Local path: {dataset_mount_path}")

    await run_command(args, handler)


async def _cmd_smb_delete(args: Namespace) -> None:
    async def handler(client: TrueNASClient):
        share_ids = list(args.ids)

        if not args.force:
            count = len(share_ids)
            names = ", ".join(map(str, share_ids))
            confirm = input(f"Delete {count} SMB share(s): {names}? (yes/no): ")
            if confirm.lower() != "yes":
                print("Cancelled.")
                return

        results = []
        errors = []

        for share_id in share_ids:
            try:
                await client.delete_smb_share(share_id)
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
            print(f"✓ Deleted {len(results)} SMB share(s):")
            for share_id in results:
                print(f"  • ID: {share_id}")

        if errors:
            print(f"\n✗ Failed to delete {len(errors)} SMB share(s):")
            for err in errors:
                print(f"  • ID {err['id']}: {err['error']}")
            raise SystemExit(1)

    await run_command(args, handler)

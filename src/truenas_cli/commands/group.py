"""Group management operations (group.* API)."""

from __future__ import annotations

import argparse
import json

from truenas_client import TrueNASClient

from ..core import run_command
from .base import CommandGroup


class GroupCommands(CommandGroup):
    """Group management operations (``group.*`` API)."""

    name = "group"

    def register_commands(
        self,
        subparsers: argparse._SubParsersAction,
        parent_parser: argparse.ArgumentParser,
    ) -> None:
        """Register group subcommands."""
        # List groups
        list_parser = self.add_command(
            subparsers,
            "list",
            "List all groups (group.query)",
            _cmd_group_list,
            parent_parser=parent_parser,
        )
        self.add_optional_argument(
            list_parser,
            "--full",
            "full",
            "Show all available fields",
            action="store_true",
        )

        # Get group info
        info_parser = self.add_command(
            subparsers,
            "info",
            "Get group details (group.get_instance)",
            _cmd_group_info,
            parent_parser=parent_parser,
        )
        self.add_required_argument(
            info_parser,
            "group_id",
            "Group ID",
            type=int,
        )

        # Create group
        create_parser = self.add_command(
            subparsers,
            "create",
            "Create a new group (group.create)",
            _cmd_group_create,
            parent_parser=parent_parser,
        )
        self.add_required_argument(
            create_parser,
            "name",
            "Group name",
        )
        self.add_optional_argument(
            create_parser,
            "--gid",
            "gid",
            "Group ID (auto-assigned if not provided)",
            type=int,
        )
        self.add_optional_argument(
            create_parser,
            "--smb",
            "smb",
            "Enable SMB access",
            action="store_true",
        )

        # Update group
        update_parser = self.add_command(
            subparsers,
            "update",
            "Update a group (group.update)",
            _cmd_group_update,
            parent_parser=parent_parser,
        )
        self.add_required_argument(
            update_parser,
            "group_id",
            "Group ID",
            type=int,
        )
        self.add_optional_argument(
            update_parser,
            "--name",
            "name",
            "New group name",
        )
        self.add_optional_argument(
            update_parser,
            "--smb",
            "smb",
            "Enable/disable SMB access (true/false)",
        )

        # Delete group
        delete_parser = self.add_command(
            subparsers,
            "delete",
            "Delete a group (group.delete)",
            _cmd_group_delete,
            parent_parser=parent_parser,
        )
        self.add_required_argument(
            delete_parser,
            "group_id",
            "Group ID",
            type=int,
        )


async def _cmd_group_list(args):
    """Handle ``group list`` command."""

    async def handler(client: TrueNASClient):
        groups = await client.get_groups()

        if args.json:
            print(json.dumps(groups, indent=2))
            return

        print("\n=== Groups ===")
        if not groups:
            print("No groups found.")
            return

        for group in groups:
            gid = group.get("gid", "N/A")
            name = group.get("group", "N/A")
            builtin = group.get("builtin", False)

            builtin_marker = " (builtin)" if builtin else ""
            print(f"\n[{gid}] {name}{builtin_marker}")

            if args.full:
                # Show members
                if group.get("users"):
                    users = group["users"]
                    if users:
                        print(f"  Members: {', '.join(map(str, users))}")

                # Show SMB status
                if group.get("smb"):
                    print("  SMB: Enabled")

                # Show sudo commands
                if group.get("sudo_commands"):
                    cmds = group["sudo_commands"]
                    if cmds:
                        print(f"  Sudo Commands: {', '.join(cmds)}")

    await run_command(args, handler)


async def _cmd_group_info(args):
    """Handle ``group info`` command."""

    async def handler(client: TrueNASClient):
        group = await client.get_group(args.group_id)

        if args.json:
            print(json.dumps(group, indent=2))
            return

        gid = group.get("gid", "N/A")
        name = group.get("group", "N/A")
        builtin = group.get("builtin", False)

        print(f"\n=== Group: {name} (GID {gid}) ===")

        if builtin:
            print("Type: Built-in system group")

        # Members
        if group.get("users"):
            users = group["users"]
            if users:
                print(f"Members: {', '.join(map(str, users))}")
            else:
                print("Members: None")
        else:
            print("Members: None")

        # SMB
        if group.get("smb"):
            print("SMB Access: Enabled")
        else:
            print("SMB Access: Disabled")

        # Sudo commands
        if group.get("sudo_commands"):
            cmds = group["sudo_commands"]
            if cmds:
                print("\nSudo Commands:")
                for cmd in cmds:
                    print(f"  - {cmd}")

        if group.get("sudo_commands_nopasswd"):
            cmds = group["sudo_commands_nopasswd"]
            if cmds:
                print("\nSudo Commands (no password):")
                for cmd in cmds:
                    print(f"  - {cmd}")

    await run_command(args, handler)


async def _cmd_group_create(args):
    """Handle ``group create`` command."""

    async def handler(client: TrueNASClient):
        kwargs = {}

        if args.smb:
            kwargs["smb"] = True

        print(f"Creating group: {args.name}...")

        group = await client.create_group(args.name, args.gid, **kwargs)

        if args.json:
            print(json.dumps(group, indent=2))
            return

        gid = group.get("gid", "N/A")
        print(f"✓ Group '{args.name}' created successfully (GID {gid})")

    await run_command(args, handler)


async def _cmd_group_update(args):
    """Handle ``group update`` command."""

    async def handler(client: TrueNASClient):
        kwargs = {}

        if args.name:
            kwargs["name"] = args.name

        if args.smb is not None:
            kwargs["smb"] = args.smb.lower() in ("true", "yes", "1")

        if not kwargs:
            print("Error: No update parameters provided")
            return

        print(f"Updating group ID {args.group_id}...")

        group = await client.update_group(args.group_id, **kwargs)

        if args.json:
            print(json.dumps(group, indent=2))
            return

        print(f"✓ Group ID {args.group_id} updated successfully")

    await run_command(args, handler)


async def _cmd_group_delete(args):
    """Handle ``group delete`` command."""

    async def handler(client: TrueNASClient):
        print(f"Deleting group ID {args.group_id}...")

        result = await client.delete_group(args.group_id)

        if args.json:
            print(json.dumps({"success": result}, indent=2))
            return

        print(f"✓ Group ID {args.group_id} deleted successfully")

    await run_command(args, handler)

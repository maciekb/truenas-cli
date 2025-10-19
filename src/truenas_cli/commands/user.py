"""User management operations (user.* API)."""

from __future__ import annotations

import argparse
import json

from truenas_client import TrueNASClient

from ..core import run_command
from .base import CommandGroup


class UserCommands(CommandGroup):
    """User management operations (``user.*`` API)."""

    name = "user"

    def register_commands(
        self,
        subparsers: argparse._SubParsersAction,
        parent_parser: argparse.ArgumentParser,
    ) -> None:
        """Register user subcommands."""
        # List users
        list_parser = self.add_command(
            subparsers,
            "list",
            "List all users (user.query)",
            _cmd_user_list,
            parent_parser=parent_parser,
        )
        self.add_optional_argument(
            list_parser,
            "--full",
            "full",
            "Show all available fields",
            action="store_true",
        )

        # Get user info
        info_parser = self.add_command(
            subparsers,
            "info",
            "Get user details (user.get_instance)",
            _cmd_user_info,
            parent_parser=parent_parser,
        )
        self.add_required_argument(
            info_parser,
            "user_id",
            "User ID",
            type=int,
        )

        # Create user
        create_parser = self.add_command(
            subparsers,
            "create",
            "Create a new user (user.create)",
            _cmd_user_create,
            parent_parser=parent_parser,
        )
        self.add_required_argument(
            create_parser,
            "username",
            "Username (login name)",
        )
        self.add_required_argument(
            create_parser,
            "full_name",
            "Full name",
        )
        self.add_optional_argument(
            create_parser,
            "--user-password",
            "password",
            "User password",
        )
        self.add_optional_argument(
            create_parser,
            "--uid",
            "uid",
            "User ID (auto-assigned if not provided)",
            type=int,
        )
        self.add_optional_argument(
            create_parser,
            "--group",
            "group",
            "Primary group ID",
            type=int,
        )
        self.add_optional_argument(
            create_parser,
            "--home",
            "home",
            "Home directory path",
        )
        self.add_optional_argument(
            create_parser,
            "--shell",
            "shell",
            "Shell path (e.g., /bin/bash)",
        )
        self.add_optional_argument(
            create_parser,
            "--email",
            "email",
            "Email address",
        )

        # Delete user
        delete_parser = self.add_command(
            subparsers,
            "delete",
            "Delete a user (user.delete)",
            _cmd_user_delete,
            parent_parser=parent_parser,
        )
        self.add_required_argument(
            delete_parser,
            "user_id",
            "User ID",
            type=int,
        )
        self.add_optional_argument(
            delete_parser,
            "--delete-group",
            "delete_group",
            "Also delete the user's primary group",
            action="store_true",
        )

        # Set password
        password_parser = self.add_command(
            subparsers,
            "set-password",
            "Set user password (user.set_password)",
            _cmd_user_set_password,
            parent_parser=parent_parser,
        )
        self.add_required_argument(
            password_parser,
            "user_id",
            "User ID",
            type=int,
        )
        self.add_required_argument(
            password_parser,
            "password",
            "New password",
        )

        # Shell choices
        self.add_command(
            subparsers,
            "shells",
            "List available shells (user.shell_choices)",
            _cmd_user_shells,
            parent_parser=parent_parser,
        )


async def _cmd_user_list(args):
    """Handle ``user list`` command."""

    async def handler(client: TrueNASClient):
        users = await client.get_users()

        if args.json:
            print(json.dumps(users, indent=2))
            return

        print("\n=== Users ===")
        if not users:
            print("No users found.")
            return

        for user in users:
            uid = user.get("uid", "N/A")
            username = user.get("username", "N/A")
            full_name = user.get("full_name", "")
            home = user.get("home", "")

            print(f"\n[{uid}] {username}")
            if full_name:
                print(f"  Name: {full_name}")

            if args.full:
                if home:
                    print(f"  Home: {home}")
                if user.get("shell"):
                    print(f"  Shell: {user['shell']}")
                if user.get("email"):
                    print(f"  Email: {user['email']}")
                if user.get("group"):
                    print(f"  Primary Group: {user['group']['bsdgrp_group']}")
                if user.get("groups"):
                    group_names = [g for g in user["groups"]]
                    if group_names:
                        print(f"  Groups: {', '.join(map(str, group_names))}")

    await run_command(args, handler)


async def _cmd_user_info(args):
    """Handle ``user info`` command."""

    async def handler(client: TrueNASClient):
        user = await client.get_user(args.user_id)

        if args.json:
            print(json.dumps(user, indent=2))
            return

        uid = user.get("uid", "N/A")
        username = user.get("username", "N/A")
        full_name = user.get("full_name", "")

        print(f"\n=== User: {username} (UID {uid}) ===")
        if full_name:
            print(f"Full Name: {full_name}")

        if user.get("home"):
            print(f"Home Directory: {user['home']}")
        if user.get("shell"):
            print(f"Shell: {user['shell']}")
        if user.get("email"):
            print(f"Email: {user['email']}")

        # Primary group
        if user.get("group"):
            group_data = user["group"]
            if isinstance(group_data, dict):
                group_name = group_data.get("bsdgrp_group", "N/A")
                group_gid = group_data.get("bsdgrp_gid", "N/A")
                print(f"Primary Group: {group_name} (GID {group_gid})")

        # Additional groups
        if user.get("groups"):
            groups = user["groups"]
            if groups:
                print(f"Additional Groups: {', '.join(map(str, groups))}")

        # Flags
        if user.get("password_disabled"):
            print("Password: Disabled")
        if user.get("ssh_password_enabled"):
            print("SSH Password Auth: Enabled")
        if user.get("locked"):
            print("Account: Locked")

    await run_command(args, handler)


async def _cmd_user_create(args):
    """Handle ``user create`` command."""

    async def handler(client: TrueNASClient):
        kwargs = {}

        if args.uid is not None:
            kwargs["uid"] = args.uid
        if args.group is not None:
            kwargs["group"] = args.group
        if args.home:
            kwargs["home"] = args.home
        if args.shell:
            kwargs["shell"] = args.shell
        if args.email:
            kwargs["email"] = args.email

        print(f"Creating user: {args.username}...")

        user = await client.create_user(
            args.username, args.full_name, args.password, **kwargs
        )

        if args.json:
            print(json.dumps(user, indent=2))
            return

        uid = user.get("uid", "N/A")
        print(f"✓ User '{args.username}' created successfully (UID {uid})")

    await run_command(args, handler)


async def _cmd_user_delete(args):
    """Handle ``user delete`` command."""

    async def handler(client: TrueNASClient):
        print(f"Deleting user ID {args.user_id}...")

        result = await client.delete_user(args.user_id, args.delete_group)

        if args.json:
            print(json.dumps({"success": result}, indent=2))
            return

        print(f"✓ User ID {args.user_id} deleted successfully")
        if args.delete_group:
            print("  Primary group also deleted")

    await run_command(args, handler)


async def _cmd_user_set_password(args):
    """Handle ``user set-password`` command."""

    async def handler(client: TrueNASClient):
        print(f"Setting password for user ID {args.user_id}...")

        result = await client.set_user_password(args.user_id, args.password)

        if args.json:
            print(json.dumps({"success": result}, indent=2))
            return

        print(f"✓ Password set successfully for user ID {args.user_id}")

    await run_command(args, handler)


async def _cmd_user_shells(args):
    """Handle ``user shells`` command."""

    async def handler(client: TrueNASClient):
        shells = await client.get_shell_choices()

        if args.json:
            print(json.dumps(shells, indent=2))
            return

        print("\n=== Available Shells ===")
        for shell in shells:
            print(f"  {shell}")

    await run_command(args, handler)

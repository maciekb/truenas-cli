"""Application/Container operations (app.* API) - TrueNAS SCALE."""

from __future__ import annotations

import argparse
import json

from truenas_client import TrueNASClient

from ..core import run_command
from .base import CommandGroup


class AppCommands(CommandGroup):
    """Application/Container operations (``app.*`` API)."""

    name = "app"

    def register_commands(
        self,
        subparsers: argparse._SubParsersAction,
        parent_parser: argparse.ArgumentParser,
    ) -> None:
        """Register app subcommands."""
        # List apps
        list_parser = self.add_command(
            subparsers,
            "list",
            "List installed applications (app.query)",
            _cmd_app_list,
            parent_parser=parent_parser,
        )
        self.add_optional_argument(
            list_parser,
            ["-F", "--full"],
            "full",
            "Show all available fields",
            action="store_true",
        )

        # Get app info
        info_parser = self.add_command(
            subparsers,
            "info",
            "Get application details (app.get_instance)",
            _cmd_app_info,
            parent_parser=parent_parser,
        )
        self.add_required_argument(
            info_parser,
            "app_name",
            "Application name",
        )

        # List available apps
        self.add_command(
            subparsers,
            "available",
            "List available applications from catalog (app.available)",
            _cmd_app_available,
            parent_parser=parent_parser,
        )

        # List categories
        self.add_command(
            subparsers,
            "categories",
            "List application categories (app.categories)",
            _cmd_app_categories,
            parent_parser=parent_parser,
        )

        # Start app
        start_parser = self.add_command(
            subparsers,
            "start",
            "Start an application (app.start)",
            _cmd_app_start,
            parent_parser=parent_parser,
        )
        self.add_required_argument(
            start_parser,
            "app_name",
            "Application name",
        )

        # Stop app
        stop_parser = self.add_command(
            subparsers,
            "stop",
            "Stop an application (app.stop)",
            _cmd_app_stop,
            parent_parser=parent_parser,
        )
        self.add_required_argument(
            stop_parser,
            "app_name",
            "Application name",
        )

        # Delete app
        delete_parser = self.add_command(
            subparsers,
            "delete",
            "Delete/uninstall an application (app.delete)",
            _cmd_app_delete,
            parent_parser=parent_parser,
        )
        self.add_required_argument(
            delete_parser,
            "app_name",
            "Application name",
        )

        # Redeploy app
        redeploy_parser = self.add_command(
            subparsers,
            "redeploy",
            "Redeploy an application (app.redeploy)",
            _cmd_app_redeploy,
            parent_parser=parent_parser,
        )
        self.add_required_argument(
            redeploy_parser,
            "app_name",
            "Application name",
        )

        # Upgrade app
        upgrade_parser = self.add_command(
            subparsers,
            "upgrade",
            "Upgrade an application (app.upgrade)",
            _cmd_app_upgrade,
            parent_parser=parent_parser,
        )
        self.add_required_argument(
            upgrade_parser,
            "app_name",
            "Application name",
        )
        self.add_optional_argument(
            upgrade_parser,
            "--version",
            "version",
            "Target version (default: latest)",
        )

        # Get config
        self.add_command(
            subparsers,
            "config",
            "Get applications configuration (app.config)",
            _cmd_app_config,
            parent_parser=parent_parser,
        )

        # List images
        images_parser = self.add_command(
            subparsers,
            "images",
            "List Docker images (app.image.query)",
            _cmd_app_images,
            parent_parser=parent_parser,
        )
        self.add_optional_argument(
            images_parser,
            ["-F", "--full"],
            "full",
            "Show all available fields",
            action="store_true",
        )


async def _cmd_app_list(args: argparse.Namespace) -> None:
    """Handle ``app list`` command."""

    async def handler(client: TrueNASClient) -> None:
        apps = await client.get_apps()

        if args.json:
            print(json.dumps(apps, indent=2))
            return

        print("\n=== Installed Applications ===")
        if not apps:
            print("No applications installed.")
            return

        for app in apps:
            name = app.get("name", "N/A")
            state = app.get("state", "UNKNOWN")
            version = app.get("version", "N/A")

            # State indicator (terminal-safe)
            state_icon = {
                "RUNNING": "[✓]",
                "STOPPED": "[■]",
                "DEPLOYING": "[...]",
                "CRASHED": "[✗]",
            }.get(state, "[?]")

            print(f"\n{state_icon} {name}")
            print(f"  State: {state}")
            print(f"  Version: {version}")

            if args.full:
                # Show additional details
                if app.get("metadata"):
                    metadata = app["metadata"]
                    if metadata.get("train"):
                        print(f"  Train: {metadata['train']}")
                if app.get("human_version"):
                    print(f"  App Version: {app['human_version']}")
                if app.get("active_workloads"):
                    workloads = app["active_workloads"]
                    containers = workloads.get("container_details", [])
                    if containers:
                        print(f"  Containers: {len(containers)}")

    await run_command(args, handler)


async def _cmd_app_info(args: argparse.Namespace) -> None:
    """Handle ``app info`` command."""

    async def handler(client: TrueNASClient) -> None:
        app = await client.get_app(args.app_name)

        if args.json:
            print(json.dumps(app, indent=2))
            return

        name = app.get("name", "N/A")
        state = app.get("state", "UNKNOWN")
        version = app.get("version", "N/A")

        print(f"\n=== Application: {name} ===")
        print(f"State: {state}")
        print(f"Version: {version}")

        if app.get("human_version"):
            print(f"App Version: {app['human_version']}")

        if app.get("metadata"):
            metadata = app["metadata"]
            if metadata.get("train"):
                print(f"Train: {metadata['train']}")
            if metadata.get("app_version"):
                print(f"Catalog Version: {metadata['app_version']}")

        # Show workloads
        if app.get("active_workloads"):
            workloads = app["active_workloads"]
            containers = workloads.get("container_details", [])

            if containers:
                print(f"\nContainers ({len(containers)}):")
                for container in containers:
                    c_name = container.get("service_name", "unknown")
                    c_state = container.get("state", "unknown")
                    print(f"  - {c_name}: {c_state}")

        # Show resources
        if app.get("resources"):
            resources = app["resources"]
            if resources.get("host_path_volumes"):
                print("\nHost Path Volumes:")
                for vol in resources["host_path_volumes"]:
                    print(f"  - {vol.get('host_path', 'N/A')}")

            if resources.get("ix_volumes"):
                print("\nPersistent Volumes:")
                for vol in resources["ix_volumes"]:
                    print(f"  - {vol.get('name', 'N/A')}")

    await run_command(args, handler)


async def _cmd_app_available(args: argparse.Namespace) -> None:
    """Handle ``app available`` command."""

    async def handler(client: TrueNASClient) -> None:
        available = await client.get_available_apps()

        if args.json:
            print(json.dumps(available, indent=2))
            return

        print("\n=== Available Applications ===")

        # Count total apps
        total = 0
        for train_apps in available.values():
            if isinstance(train_apps, dict):
                total += len(train_apps)

        print(f"Total available: {total}")

        for train, apps_dict in sorted(available.items()):
            if not isinstance(apps_dict, dict):
                continue

            print(f"\n--- Train: {train} ({len(apps_dict)} apps) ---")

            for app_name, app_data in sorted(apps_dict.items()):
                if isinstance(app_data, dict):
                    latest = app_data.get("latest_version", "N/A")
                    description = app_data.get("description", "")
                    if description and len(description) > 60:
                        description = description[:57] + "..."
                    print(f"  {app_name} (v{latest})")
                    if description:
                        print(f"    {description}")

    await run_command(args, handler)


async def _cmd_app_categories(args: argparse.Namespace) -> None:
    """Handle ``app categories`` command."""

    async def handler(client: TrueNASClient) -> None:
        categories = await client.get_app_categories()

        if args.json:
            print(json.dumps(categories, indent=2))
            return

        print("\n=== Application Categories ===")
        for category in sorted(categories):
            print(f"  - {category}")

    await run_command(args, handler)


async def _cmd_app_start(args: argparse.Namespace) -> None:
    """Handle ``app start`` command."""

    async def handler(client: TrueNASClient) -> None:
        print(f"Starting application: {args.app_name}...")

        result = await client.start_app(args.app_name)

        if args.json:
            print(json.dumps({"success": result}, indent=2))
            return

        print(f"✓ Application '{args.app_name}' started successfully")

    await run_command(args, handler)


async def _cmd_app_stop(args: argparse.Namespace) -> None:
    """Handle ``app stop`` command."""

    async def handler(client: TrueNASClient) -> None:
        print(f"Stopping application: {args.app_name}...")

        result = await client.stop_app(args.app_name)

        if args.json:
            print(json.dumps({"success": result}, indent=2))
            return

        print(f"✓ Application '{args.app_name}' stopped successfully")

    await run_command(args, handler)


async def _cmd_app_delete(args: argparse.Namespace) -> None:
    """Handle ``app delete`` command."""

    async def handler(client: TrueNASClient) -> None:
        print(f"Deleting application: {args.app_name}...")

        result = await client.delete_app(args.app_name)

        if args.json:
            print(json.dumps({"success": result}, indent=2))
            return

        print(f"✓ Application '{args.app_name}' deleted successfully")

    await run_command(args, handler)


async def _cmd_app_redeploy(args: argparse.Namespace) -> None:
    """Handle ``app redeploy`` command."""

    async def handler(client: TrueNASClient) -> None:
        print(f"Redeploying application: {args.app_name}...")

        result = await client.redeploy_app(args.app_name)

        if args.json:
            print(json.dumps(result, indent=2))
            return

        print(f"✓ Application '{args.app_name}' redeployed successfully")

    await run_command(args, handler)


async def _cmd_app_upgrade(args: argparse.Namespace) -> None:
    """Handle ``app upgrade`` command."""

    async def handler(client: TrueNASClient) -> None:
        version_str = f" to {args.version}" if args.version else " to latest"
        print(f"Upgrading application: {args.app_name}{version_str}...")

        result = await client.upgrade_app(args.app_name, args.version)

        if args.json:
            print(json.dumps(result, indent=2))
            return

        print(f"✓ Application '{args.app_name}' upgraded successfully")

    await run_command(args, handler)


async def _cmd_app_config(args: argparse.Namespace) -> None:
    """Handle ``app config`` command."""

    async def handler(client: TrueNASClient) -> None:
        config = await client.get_app_config()

        if args.json:
            print(json.dumps(config, indent=2))
            return

        print("\n=== Applications Configuration ===")
        if config.get("pool"):
            print(f"Pool: {config['pool']}")
        if config.get("dataset"):
            print(f"Dataset: {config['dataset']}")

    await run_command(args, handler)


async def _cmd_app_images(args: argparse.Namespace) -> None:
    """Handle ``app images`` command."""

    async def handler(client: TrueNASClient) -> None:
        images = await client.get_app_images()

        if args.json:
            print(json.dumps(images, indent=2))
            return

        print("\n=== Docker Images ===")
        if not images:
            print("No Docker images found.")
            return

        for image in images:
            repo_tags = image.get("repo_tags", [])
            image_id = image.get("id", "N/A")
            # Safe string slicing with length check
            if isinstance(image_id, str) and len(image_id) > 12:
                image_id = image_id[:12]

            size = image.get("size", 0)

            # Format size with type validation
            if not isinstance(size, (int, float)):
                size = 0

            size_mb = size / (1024 * 1024) if size > 0 else 0
            size_str = (
                f"{size_mb:.1f} MB" if size_mb < 1024 else f"{size_mb / 1024:.1f} GB"
            )

            if repo_tags:
                for tag in repo_tags:
                    print(f"\n{tag}")
                    print(f"  ID: {image_id}")
                    print(f"  Size: {size_str}")
            else:
                print("\n<none>:<none>")
                print(f"  ID: {image_id}")
                print(f"  Size: {size_str}")

            if args.full and image.get("created"):
                print(f"  Created: {image['created']}")

    await run_command(args, handler)

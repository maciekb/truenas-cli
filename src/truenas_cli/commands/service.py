from __future__ import annotations

import argparse
import json
from argparse import Namespace

from truenas_client import TrueNASClient

from ..core import run_command, safe_get
from .base import CommandGroup


class ServiceCommands(CommandGroup):
    """Commands covering the ``service`` namespace."""

    name = "service"

    def register_commands(
        self,
        subparsers: argparse._SubParsersAction,
        parent_parser: argparse.ArgumentParser,
    ) -> None:
        """Register service subcommands."""
        # List services
        list_parser = self.add_command(
            subparsers,
            "list",
            "List system services (service.query)",
            _cmd_service_list,
            parent_parser=parent_parser,
        )
        self.add_optional_argument(
            list_parser,
            ["-F", "--full"],
            "full",
            "Show all available fields",
            action="store_true",
        )

        # Status
        status_parser = self.add_command(
            subparsers,
            "status",
            "Get service status (service.query)",
            _cmd_service_status,
            parent_parser=parent_parser,
        )
        status_parser.add_argument("service", help="Service name (e.g. cifs, nfs)")

        # Start
        start_parser = self.add_command(
            subparsers,
            "start",
            "Start a service (service.start)",
            _cmd_service_start,
            parent_parser=parent_parser,
        )
        start_parser.add_argument("service", help="Service name")

        # Stop
        stop_parser = self.add_command(
            subparsers,
            "stop",
            "Stop a service (service.stop)",
            _cmd_service_stop,
            parent_parser=parent_parser,
        )
        stop_parser.add_argument("service", help="Service name")

        # Enable
        enable_parser = self.add_command(
            subparsers,
            "enable",
            "Enable service on boot (service.update)",
            _cmd_service_enable,
            parent_parser=parent_parser,
        )
        enable_parser.add_argument("service", help="Service name")

        # Restart
        restart_parser = self.add_command(
            subparsers,
            "restart",
            "Restart a service (service.restart)",
            _cmd_service_restart,
            parent_parser=parent_parser,
        )
        restart_parser.add_argument("service", help="Service name")


async def _cmd_service_list(args: Namespace) -> None:
    async def handler(client: TrueNASClient):
        services = await client.get_services()

        if args.json:
            print(json.dumps(services, indent=2))
            return

        print("\n=== Services ===")
        if not services:
            print("No services found.")
            return

        for service in services:
            service_name = safe_get(service, "service", "N/A")
            state = safe_get(service, "state", "UNKNOWN")
            enable = safe_get(service, "enable", False)
            state_icon = "✓" if state == "RUNNING" else "✗"
            boot_str = "Yes" if enable else "No"

            print(f"\n{state_icon} Service: {service_name}")
            print(f"  State: {state}")
            print(f"  Boot: {boot_str}")

            if args.full:
                # Show all available fields
                excluded_keys = {"service", "state", "enable"}
                for key, value in sorted(service.items()):
                    if key not in excluded_keys:
                        if isinstance(value, bool):
                            value = "Yes" if value else "No"
                        elif isinstance(value, dict):
                            value = json.dumps(value)
                        elif isinstance(value, list):
                            value = ", ".join(map(str, value)) if value else "None"
                        print(f"  {key}: {value}")

    await run_command(args, handler)


async def _cmd_service_status(args: Namespace) -> None:
    async def handler(client: TrueNASClient):
        service = await client.get_service(args.service)

        if args.json:
            print(json.dumps(service, indent=2))
            return

        print(f"\n=== Service: {safe_get(service, 'service', args.service)} ===")
        print(f"State: {safe_get(service, 'state')}")
        print(f"Enabled on boot: {safe_get(service, 'enable')}")

    await run_command(args, handler)


async def _cmd_service_start(args: Namespace) -> None:
    async def handler(client: TrueNASClient):
        result = await client.start_service(args.service)

        if args.json:
            print(json.dumps({"started": result}, indent=2))
            return

        print(f"✓ Service started: {args.service}")

    await run_command(args, handler)


async def _cmd_service_stop(args: Namespace) -> None:
    async def handler(client: TrueNASClient):
        result = await client.stop_service(args.service)

        if args.json:
            print(json.dumps({"stopped": result}, indent=2))
            return

        print(f"✓ Service stopped: {args.service}")

    await run_command(args, handler)


async def _cmd_service_enable(args: Namespace) -> None:
    async def handler(client: TrueNASClient):
        result = await client.enable_service(args.service)

        if args.json:
            print(json.dumps({"enabled": result}, indent=2))
            return

        print(f"✓ Service enabled: {args.service}")

    await run_command(args, handler)


async def _cmd_service_restart(args: Namespace) -> None:
    """Handle ``service restart`` using ``service.restart``."""

    async def handler(client: TrueNASClient):
        print(f"Restarting service: {args.service}...")
        result = await client.call("service.restart", [args.service])

        if args.json:
            print(json.dumps(result, indent=2))
            return

        print(f"✓ Service restarted: {args.service}")

    await run_command(args, handler)

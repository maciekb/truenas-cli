"""System operations backed by the system.* API namespace."""

from __future__ import annotations

import argparse
import json

from truenas_client import TrueNASClient

from ..core import format_size, run_command
from .base import CommandGroup


class SystemCommands(CommandGroup):
    """Commands backed by the ``system`` API namespace."""

    name = "system"

    def register_commands(
        self,
        subparsers: argparse._SubParsersAction,
        parent_parser: argparse.ArgumentParser,
    ) -> None:
        """Register system subcommands."""
        self.add_command(
            subparsers,
            "info",
            "Get system information (system.info)",
            _cmd_system_info,
            parent_parser=parent_parser,
        )
        self.add_command(
            subparsers,
            "version",
            "Get system version information",
            _cmd_system_version,
            parent_parser=parent_parser,
        )

        # Power operations
        power_parser = subparsers.add_parser(
            "reboot",
            help="Reboot the system",
            parents=[parent_parser],
        )
        power_parser.add_argument(
            "--delay",
            type=int,
            default=10,
            help="Delay in seconds before reboot (default: 10)",
        )
        power_parser.set_defaults(func=_cmd_system_reboot)

        shutdown_parser = subparsers.add_parser(
            "shutdown",
            help="Shutdown the system",
            parents=[parent_parser],
        )
        shutdown_parser.add_argument(
            "--delay",
            type=int,
            default=10,
            help="Delay in seconds before shutdown (default: 10)",
        )
        shutdown_parser.set_defaults(func=_cmd_system_shutdown)

        halt_parser = subparsers.add_parser(
            "halt",
            help="Halt the system",
            parents=[parent_parser],
        )
        halt_parser.add_argument(
            "--force",
            action="store_true",
            help="Force halt without graceful shutdown",
        )
        halt_parser.set_defaults(func=_cmd_system_halt)


async def _cmd_system_info(args):
    """Handle ``system info`` using ``system.info``."""

    async def handler(client: TrueNASClient):
        info = await client.system_info()

        if args.json:
            print(json.dumps(info, indent=2))
            return

        print("\n=== TrueNAS System Information ===")
        print(f"Hostname: {info.get('hostname')}")
        print(f"Version: {info.get('version')}")
        print(f"Model: {info.get('model')}")
        print(f"Cores: {info.get('cores')} " f"({info.get('physical_cores')} physical)")
        physmem = info.get("physmem")
        if physmem is not None:
            print(f"Memory: {format_size(physmem)}")
        print(f"Uptime: {info.get('uptime')}")
        print(f"Timezone: {info.get('timezone')}")

    await run_command(args, handler)


async def _cmd_system_version(args):
    """Handle ``system version`` using ``system.version``."""

    async def handler(client: TrueNASClient):
        version_info = await client.call("system.version", [])

        if args.json:
            print(json.dumps(version_info, indent=2))
            return

        print("\n=== System Version Information ===")
        if isinstance(version_info, dict):
            for key, value in version_info.items():
                print(f"{key}: {value}")
        else:
            print(f"Version: {version_info}")

    await run_command(args, handler)


async def _cmd_system_reboot(args):
    """Handle ``system reboot`` using ``system.reboot``."""

    async def handler(client: TrueNASClient):
        delay = args.delay
        print(f"Sending reboot command with {delay}s delay...")
        result = await client.call("system.reboot", [{"delay": delay}])

        if args.json:
            print(json.dumps(result, indent=2))
            return

        print(f"System will reboot in {delay} seconds")

    await run_command(args, handler)


async def _cmd_system_shutdown(args):
    """Handle ``system shutdown`` using ``system.shutdown``."""

    async def handler(client: TrueNASClient):
        delay = args.delay
        print(f"Sending shutdown command with {delay}s delay...")
        result = await client.call("system.shutdown", [{"delay": delay}])

        if args.json:
            print(json.dumps(result, indent=2))
            return

        print(f"System will shutdown in {delay} seconds")

    await run_command(args, handler)


async def _cmd_system_halt(args):
    """Handle ``system halt`` using ``system.halt``."""

    async def handler(client: TrueNASClient):
        force = args.force
        print(f"Sending halt command (force={force})...")
        result = await client.call("system.halt", [{"force": force}])

        if args.json:
            print(json.dumps(result, indent=2))
            return

        print("System will halt")

    await run_command(args, handler)

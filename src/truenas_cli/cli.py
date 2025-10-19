"""
Parser/bootstrap utilities for the TrueNAS CLI.

The CLI is assembled from command group modules located in
``truenas_cli.commands``. Each group registers its subcommands while relying on
the shared helpers defined in :mod:`truenas_cli.core`.
"""

from __future__ import annotations

import argparse
import asyncio

from .commands import COMMAND_GROUPS  # Lazy imports avoided for clarity


def build_parser() -> argparse.ArgumentParser:
    """Create and configure the top-level CLI parser."""
    parent_parser = argparse.ArgumentParser(add_help=False)
    parent_parser.add_argument("-H", "--host", help="TrueNAS host [env: TRUENAS_HOST]")
    parent_parser.add_argument("--port", type=int, help="Port [env: TRUENAS_PORT]")
    parent_parser.add_argument(
        "--no-ssl",
        action="store_true",
        help="Disable SSL [env: TRUENAS_NO_SSL]",
    )
    parent_parser.add_argument(
        "--insecure",
        action="store_true",
        help="Allow self-signed certs [env: TRUENAS_INSECURE]",
    )
    parent_parser.add_argument("-k", "--api-key", help="API key [env: TRUENAS_API_KEY]")
    parent_parser.add_argument(
        "-u", "--username", help="Username [env: TRUENAS_USERNAME]"
    )
    parent_parser.add_argument(
        "-P", "--password", help="Password [env: TRUENAS_PASSWORD]"
    )
    parent_parser.add_argument(
        "-v",
        "--verbose",
        action="count",
        default=0,
        help="Verbose output (-v for INFO, -vv for DEBUG)",
    )
    parent_parser.add_argument(
        "-q",
        "--quiet",
        action="store_true",
        help="Quiet mode (only errors)",
    )
    parent_parser.add_argument("--json", action="store_true", help="JSON output")
    parent_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show planned actions without applying changes",
    )

    parser = argparse.ArgumentParser(
        prog="truenas-cli",
        description="TrueNAS CLI - Unified interface for TrueNAS API v25.10+",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
Examples:
  # Test connection
  %(prog)s test

  # Get system info
  %(prog)s system info

  # Create SMB share
  %(prog)s smb create --pool tank --dataset data --share Media

Environment Variables:
  TRUENAS_HOST, TRUENAS_PORT, TRUENAS_API_KEY, TRUENAS_USERNAME,
  TRUENAS_PASSWORD, TRUENAS_NO_SSL, TRUENAS_INSECURE
""",
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    for group in COMMAND_GROUPS:
        group.register(subparsers, parent_parser)

    return parser


def _ensure_subcommand(args, parser: argparse.ArgumentParser) -> None:
    """Validate that a subcommand was provided."""
    if not getattr(args, "command", None):
        parser.print_help()
        raise SystemExit(0)

    subparser_attr = getattr(args, "_subparser_attr", None)
    if subparser_attr:
        subparser, attr_name = subparser_attr
        if getattr(args, attr_name, None) is None:
            subparser.print_help()
            raise SystemExit(0)


def execute_from_args(parser: argparse.ArgumentParser, args) -> None:
    """Execute the CLI based on parsed arguments."""
    _ensure_subcommand(args, parser)

    if not hasattr(args, "func"):
        parser.print_help()
        raise SystemExit(1)

    asyncio.run(args.func(args))

"""
High-level CLI wiring for the TrueNAS command-line client.

This package exposes helpers to register argparse subcommands that are
implemented in dedicated modules grouped by API areas (system, datasets,
services, etc.). Each handler defers to :mod:`truenas_cli.core` for
connection management and documentation-driven validation.
"""

from .cli import build_parser, execute_from_args

__all__ = [
    "build_parser",
    "execute_from_args",
]

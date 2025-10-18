#!/usr/bin/env python3
"""
TrueNAS CLI entry-point.

The CLI wiring is handled by :mod:`truenas_cli`, which builds the argument
parser and registers subcommands backed by the TrueNAS API documentation.
"""

import os
import sys

# Ensure the local ``src`` directory is on the import path for editable usage.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from dotenv import load_dotenv

from truenas_cli import build_parser, execute_from_args


def main() -> None:
    load_dotenv()
    parser = build_parser()
    args = parser.parse_args()
    execute_from_args(parser, args)


if __name__ == "__main__":
    main()

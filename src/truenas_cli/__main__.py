"""Entry point for running truenas-cli as a module.

This allows the CLI to be run with:
    python -m truenas_cli
"""

from truenas_cli.cli import main

if __name__ == "__main__":
    main()

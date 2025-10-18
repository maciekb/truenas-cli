from __future__ import annotations

from truenas_client import TrueNASClient, TrueNASClientError

from ..core import authenticate_client, run_command


class GeneralCommands:
    """Top-level commands that are not grouped, e.g. ``test``."""

    name = "general"

    def register(self, subparsers, parent_parser):
        parser = subparsers.add_parser(
            "test",
            help="Test connection to TrueNAS",
            parents=[parent_parser],
        )
        parser.set_defaults(func=_cmd_test_connection)


async def _cmd_test_connection(args):
    """Handle ``truenas-cli test`` (documentation: system.info + auth endpoints)."""

    async def handler(client: TrueNASClient):
        print("\n=== Testing TrueNAS Connection ===")
        print(f"Host: {client.host}")
        print(f"Port: {client.port}")
        print(f"SSL: {'Enabled' if client.use_ssl else 'Disabled'}")
        print(f"SSL Verification: {'Enabled' if client.verify_ssl else 'Disabled'}")
        print()

        try:
            print("Step 1: Connecting...")
            await client.ensure_connected()
            print("  ✓ Connection established")

            print("\nStep 2: Authenticating...")
            await authenticate_client(client, args)
            print("  ✓ Authentication successful")

            print("\nStep 3: Testing API call (system.info)...")
            info = await client.system_info()
            print("  ✓ API working")
            print(f"  Hostname: {info.get('hostname')}")
            print(f"  Version: {info.get('version')}")

            print("\n=== Connection Test Passed! ===")
        except Exception as exc:
            raise TrueNASClientError(f"❌ Connection test failed: {exc}") from exc

    await run_command(args, handler, require_auth=False)

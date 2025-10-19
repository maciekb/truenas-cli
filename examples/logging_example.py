#!/usr/bin/env python3
"""
Logging configuration and usage examples for TrueNAS Client.

This example demonstrates:
- Configuring logging levels (DEBUG, INFO, WARNING, ERROR)
- Structured logging with context
- Sensitive data sanitization in logs
- File logging for persistent records
- Performance metrics in logs

The client automatically redacts:
- API keys and passwords
- Authentication tokens
- Any sensitive credentials

Prerequisites:
    - TrueNAS 25.10+ instance
    - Valid API key for authentication

Usage:
    python examples/logging_example.py
"""

import asyncio
import logging
import os
import tempfile

from dotenv import load_dotenv

from truenas_cli.logging_config import configure_logging
from truenas_client import TrueNASClient

load_dotenv()

TRUENAS_HOST = os.getenv("TRUENAS_HOST", "truenas.local")
TRUENAS_API_KEY = os.getenv("TRUENAS_API_KEY")
TRUENAS_INSECURE = os.getenv("TRUENAS_INSECURE", "false").lower() == "true"


async def demonstrate_logging_levels():
    """Show different logging levels."""
    print("\n=== Logging Levels Demo ===\n")

    if not TRUENAS_API_KEY:
        print("⚠ TRUENAS_API_KEY not set, skipping demo")
        return

    async with TrueNASClient(
        host=TRUENAS_HOST, verify_ssl=not TRUENAS_INSECURE
    ) as client:
        print("1. CRITICAL level (only errors):")
        configure_logging(verbose=0, quiet=True)
        try:
            await client.login_with_api_key(TRUENAS_API_KEY)
            await client.system_info()
            print("   ✓ Operation completed (no verbose output)")
        except Exception as e:
            print(f"   ✗ Error: {e}")

        print("\n2. WARNING level (default):")
        configure_logging(verbose=0, quiet=False)
        try:
            await client.system_info()
            print("   ✓ Operation completed")
        except Exception as e:
            print(f"   ✗ Error: {e}")

        print("\n3. INFO level (major operations):")
        configure_logging(verbose=1)
        try:
            await client.system_info()
            print("   ✓ Operation completed")
        except Exception as e:
            print(f"   ✗ Error: {e}")

        print("\n4. DEBUG level (detailed protocol info):")
        configure_logging(verbose=2)
        print("   (Watch for detailed WebSocket and JSON-RPC logs)")
        try:
            await client.system_info()
            print("   ✓ Operation completed with verbose logging")
        except Exception as e:
            print(f"   ✗ Error: {e}")


async def demonstrate_file_logging():
    """Show file logging with sanitization."""
    print("\n=== File Logging Demo ===\n")

    if not TRUENAS_API_KEY:
        print("⚠ TRUENAS_API_KEY not set, skipping demo")
        return

    # Create temporary log file
    with tempfile.NamedTemporaryFile(mode="w+", delete=False, suffix=".log") as f:
        log_file = f.name

    try:
        # Configure file logging with DEBUG level
        configure_logging(verbose=2, log_file=log_file)

        async with TrueNASClient(
            host=TRUENAS_HOST, verify_ssl=not TRUENAS_INSECURE
        ) as client:
            await client.login_with_api_key(TRUENAS_API_KEY)
            await client.system_info()
            print(f"✓ Operations logged to: {log_file}")

        # Read and display log contents
        print("\nLog file contents (last 20 lines):")
        print("-" * 60)
        with open(log_file) as f:
            lines = f.readlines()
            # Show last 20 lines
            for line in lines[-20:]:
                print(line.rstrip())
        print("-" * 60)

        # Verify sanitization
        print("\nVerifying sensitive data sanitization:")
        with open(log_file) as f:
            content = f.read()
            if TRUENAS_API_KEY in content:
                print("✗ WARNING: API key found in logs!")
            else:
                print("✓ API key properly redacted in logs")

            if "[REDACTED]" in content or "redacted" in content.lower():
                print("✓ Sanitization markers found in logs")

    finally:
        # Cleanup
        if os.path.exists(log_file):
            os.remove(log_file)
            print("✓ Cleaned up temporary log file")


async def demonstrate_performance_metrics():
    """Show performance metrics in logs."""
    print("\n=== Performance Metrics Demo ===\n")

    if not TRUENAS_API_KEY:
        print("⚠ TRUENAS_API_KEY not set, skipping demo")
        return

    # Use INFO level to see performance metrics
    configure_logging(verbose=1)

    print("Running operations with performance tracking...")
    print("(Watch logs for timing information)\n")

    async with TrueNASClient(
        host=TRUENAS_HOST, verify_ssl=not TRUENAS_INSECURE
    ) as client:
        print("Authenticating...")
        await client.login_with_api_key(TRUENAS_API_KEY)

        print("Fetching system info...")
        info = await client.system_info()

        print("Listing pools...")
        pools = await client.get_pools()

        print("✓ Operations completed")
        print(f"  - Hostname: {info.get('hostname')}")
        print(f"  - Pools: {len(pools)}")


async def demonstrate_context_propagation():
    """Show structured logging with context."""
    print("\n=== Structured Logging Demo ===\n")

    if not TRUENAS_API_KEY:
        print("⚠ TRUENAS_API_KEY not set, skipping demo")
        return

    configure_logging(verbose=2)

    logger = logging.getLogger(__name__)

    print("Making API calls with DEBUG logging...")
    print("(Each operation shows method, request ID, and timing)\n")

    async with TrueNASClient(
        host=TRUENAS_HOST, verify_ssl=not TRUENAS_INSECURE
    ) as client:
        await client.login_with_api_key(TRUENAS_API_KEY)

        logger.info("Custom: Starting pool query")
        pools = await client.get_pools()
        logger.info(f"Custom: Retrieved {len(pools)} pools")

        logger.info("Custom: Starting dataset query")
        datasets = await client.get_datasets()
        logger.info(f"Custom: Retrieved {len(datasets)} datasets")

        print("✓ Structured logging demonstrated")


async def main():
    """Run all logging demonstrations."""
    print("\n" + "=" * 60)
    print("TrueNAS Client - Logging Configuration Examples")
    print("=" * 60)

    print("\nNote: Logging output goes to stderr by default")
    print("Redirect stderr to see all output: python ... 2>&1\n")

    # Reset to warning level for clean output between demos
    configure_logging(verbose=0, quiet=False)

    try:
        await demonstrate_logging_levels()
        await demonstrate_performance_metrics()
        await demonstrate_file_logging()
        await demonstrate_context_propagation()
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Error in logging examples: {e}", exc_info=True)

    print("\n" + "=" * 60)
    print("Logging examples completed!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())

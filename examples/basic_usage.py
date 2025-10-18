#!/usr/bin/env python3
"""
Basic usage example for TrueNAS Client library.

This example demonstrates:
- Connecting to TrueNAS with API key authentication
- Querying basic system information
- Working with pools and datasets
- Proper resource cleanup using context managers

Prerequisites:
    - TrueNAS 25.10+ instance accessible
    - Valid API key for authentication
    - Environment variables or .env file configured

Usage:
    python examples/basic_usage.py
"""

import asyncio
import logging
import os
from typing import Optional

from dotenv import load_dotenv

from truenas_client import TrueNASClient

# Load environment variables from .env file
load_dotenv()

# Get configuration from environment
TRUENAS_HOST = os.getenv("TRUENAS_HOST", "truenas.local")
TRUENAS_API_KEY = os.getenv("TRUENAS_API_KEY")
TRUENAS_INSECURE = os.getenv("TRUENAS_INSECURE", "false").lower() == "true"

# Enable debug logging to see what's happening
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def main():
    """Main example function."""
    if not TRUENAS_API_KEY:
        logger.error("TRUENAS_API_KEY environment variable not set")
        return

    # Context manager handles connection cleanup automatically
    async with TrueNASClient(
        host=TRUENAS_HOST,
        verify_ssl=not TRUENAS_INSECURE
    ) as client:
        try:
            # Authenticate with API key
            logger.info("Authenticating with API key...")
            await client.login_with_api_key(TRUENAS_API_KEY)
            logger.info("Successfully authenticated")

            # Get system information
            logger.info("Fetching system information...")
            info = await client.system_info()
            print("\n=== System Information ===")
            print(f"Hostname: {info.get('hostname')}")
            print(f"Uptime: {info.get('uptime_seconds')} seconds")
            print(f"System: {info.get('system')}")

            # Get system version
            logger.info("Fetching system version...")
            version = await client.system_version()
            print(f"Version: {version}")

            # List all pools
            logger.info("Fetching pool list...")
            pools = await client.get_pools()
            print(f"\n=== Pools ({len(pools)}) ===")
            for pool in pools:
                print(f"  - {pool['name']}: {pool.get('status', 'UNKNOWN')}")

            # List all datasets
            logger.info("Fetching dataset list...")
            datasets = await client.get_datasets()
            print(f"\n=== Datasets ({len(datasets)}) ===")
            for dataset in datasets[:5]:  # Show first 5
                print(f"  - {dataset['name']}")
            if len(datasets) > 5:
                print(f"  ... and {len(datasets) - 5} more")

            logger.info("Example completed successfully")

        except Exception as e:
            logger.error(f"Error during example: {e}", exc_info=True)


if __name__ == "__main__":
    asyncio.run(main())

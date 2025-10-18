#!/usr/bin/env python3
"""
Error handling and retry examples for TrueNAS Client.

This example demonstrates:
- Handling specific exception types
- Using the @with_retry decorator for resilient operations
- Graceful error recovery
- Input validation with helpful error messages

Prerequisites:
    - TrueNAS 25.10+ instance
    - Valid API key for authentication

Usage:
    python examples/error_handling.py
"""

import asyncio
import logging
import os
from typing import Optional

from dotenv import load_dotenv

from truenas_client import (
    TrueNASClient,
    TrueNASConnectionError,
    TrueNASNotFoundError,
    TrueNASValidationError,
    TrueNASAPIError,
)
from truenas_client.retry import with_retry

load_dotenv()

TRUENAS_HOST = os.getenv("TRUENAS_HOST", "truenas.local")
TRUENAS_API_KEY = os.getenv("TRUENAS_API_KEY")
TRUENAS_INSECURE = os.getenv("TRUENAS_INSECURE", "false").lower() == "true"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Global client instance for retry examples
client: Optional[TrueNASClient] = None


@with_retry(max_attempts=3, delay=1.0)
async def get_system_info_with_retry():
    """Get system info with automatic retry on transient failures."""
    if client is None:
        raise RuntimeError("Client not connected")
    return await client.system_info()


@with_retry(max_attempts=3, delay=0.5)
async def list_pools_with_retry():
    """List pools with automatic retry on connection failures."""
    if client is None:
        raise RuntimeError("Client not connected")
    return await client.get_pools()


async def demonstrate_connection_errors():
    """Show how to handle connection errors."""
    print("\n=== Demonstrating Connection Error Handling ===")

    # Try to connect to invalid host
    try:
        async with TrueNASClient(host="invalid.host.local") as bad_client:
            await bad_client.login_with_api_key("dummy-key")
    except TrueNASConnectionError as e:
        logger.info(f"Caught connection error (expected): {e}")
        print(f"✓ Connection error properly caught: {e}")


async def demonstrate_validation_errors():
    """Show validation of pool names and paths."""
    print("\n=== Demonstrating Validation ===")

    from truenas_cli.validation import (
        validate_pool_name,
        validate_dataset_name,
    )

    # Test pool name validation
    test_cases = [
        ("valid_pool", True),
        ("tank-1", True),
        ("", False),
        ("invalid@pool", False),
    ]

    for name, should_pass in test_cases:
        try:
            validate_pool_name(name)
            result = "✓ Valid"
        except TrueNASValidationError as e:
            result = f"✗ {e}"

        expected = "✓" if should_pass else "✗"
        status = "OK" if (should_pass and "✓" in result) or (not should_pass and "✗" in result) else "FAIL"
        print(f"  [{status}] '{name}': {result}")


async def demonstrate_not_found_errors():
    """Show how to handle not found errors gracefully."""
    print("\n=== Demonstrating Not Found Error Handling ===")

    global client
    try:
        async with TrueNASClient(
            host=TRUENAS_HOST,
            verify_ssl=not TRUENAS_INSECURE
        ) as client:
            await client.login_with_api_key(TRUENAS_API_KEY)

            # Try to get a non-existent pool
            try:
                pool = await client.get_pool("nonexistent-pool-xyz")
                print("✗ Should have raised NotFoundError")
            except TrueNASNotFoundError as e:
                logger.info(f"Caught not found error (expected): {e}")
                print(f"✓ Not found error properly caught")

    except TrueNASConnectionError as e:
        logger.warning(f"Could not connect for not-found test: {e}")
        print(f"⚠ Skipping not-found test (connection unavailable)")


async def demonstrate_api_errors():
    """Show handling of API errors from TrueNAS."""
    print("\n=== Demonstrating API Error Handling ===")

    global client
    try:
        async with TrueNASClient(
            host=TRUENAS_HOST,
            verify_ssl=not TRUENAS_INSECURE
        ) as client:
            await client.login_with_api_key(TRUENAS_API_KEY)

            # Try an invalid API call
            try:
                result = await client.call("invalid.method.that.does.not.exist", [])
                print("✗ Should have raised APIError")
            except TrueNASAPIError as e:
                logger.info(f"Caught API error (expected): {e}")
                print(f"✓ API error properly caught")

    except TrueNASConnectionError as e:
        logger.warning(f"Could not connect for API error test: {e}")
        print(f"⚠ Skipping API error test (connection unavailable)")


async def demonstrate_retry_logic():
    """Show retry logic in action."""
    print("\n=== Demonstrating Retry Logic ===")

    global client
    try:
        async with TrueNASClient(
            host=TRUENAS_HOST,
            verify_ssl=not TRUENAS_INSECURE
        ) as client:
            await client.login_with_api_key(TRUENAS_API_KEY)

            logger.info("Calling system_info with retry logic...")
            info = await get_system_info_with_retry()
            print(f"✓ System info retrieved with retry: {info.get('hostname')}")

            logger.info("Calling list_pools with retry logic...")
            pools = await list_pools_with_retry()
            print(f"✓ Pools listed with retry: {len(pools)} pool(s)")

    except TrueNASConnectionError as e:
        logger.warning(f"Could not connect for retry test: {e}")
        print(f"⚠ Skipping retry test (connection unavailable)")


async def demonstrate_defensive_checks():
    """Show response validation and defensive checks."""
    print("\n=== Demonstrating Defensive Checks ===")

    global client
    try:
        async with TrueNASClient(
            host=TRUENAS_HOST,
            verify_ssl=not TRUENAS_INSECURE
        ) as client:
            await client.login_with_api_key(TRUENAS_API_KEY)

            # Query is defensive - validates response type
            pools = await client.query("pool")
            print(f"✓ Response validation passed: got list of {len(pools)} items")

            # get_pools includes response validation
            pools = await client.get_pools()
            print(f"✓ get_pools returned validated list: {len(pools)} pool(s)")

    except Exception as e:
        logger.error(f"Error during defensive check test: {e}", exc_info=True)


async def main():
    """Run all error handling demonstrations."""
    print("\n" + "=" * 60)
    print("TrueNAS Client - Error Handling Examples")
    print("=" * 60)

    # Demonstrations that don't require connection
    await demonstrate_validation_errors()
    await demonstrate_connection_errors()

    # Demonstrations that require valid connection
    if not TRUENAS_API_KEY:
        logger.warning("TRUENAS_API_KEY not set, skipping connection tests")
        print("\n⚠ Set TRUENAS_API_KEY to run connection tests")
        return

    try:
        await demonstrate_api_errors()
        await demonstrate_not_found_errors()
        await demonstrate_retry_logic()
        await demonstrate_defensive_checks()
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)

    print("\n" + "=" * 60)
    print("Examples completed!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())

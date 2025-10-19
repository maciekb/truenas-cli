"""Pytest configuration and fixtures for TrueNAS CLI tests."""

import os
from collections.abc import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock

import pytest
from dotenv import load_dotenv

from truenas_client import (
    TrueNASAuthenticationError,
    TrueNASClient,
    TrueNASConnectionError,
)

# Load environment variables from .env for integration tests.
load_dotenv()


@pytest.fixture
def mock_client() -> MagicMock:
    """Create a mock TrueNAS client for testing."""
    client = MagicMock(spec=TrueNASClient)
    client.is_connected = True
    client.is_authenticated = True
    client.host = "test.local"
    client.port = 443
    return client


@pytest.fixture
async def async_mock_client() -> AsyncGenerator[AsyncMock, None]:
    """Create an async mock TrueNAS client for testing."""
    client = AsyncMock(spec=TrueNASClient)
    client.is_connected = True
    client.is_authenticated = True
    client.host = "test.local"
    client.port = 443

    # Mock common async methods
    client.connect = AsyncMock()
    client.disconnect = AsyncMock()
    client.login_with_api_key = AsyncMock()
    client.call = AsyncMock()
    client.system_info = AsyncMock(
        return_value={
            "hostname": "test-nas",
            "version": "TrueNAS-SCALE-25.10.0",
            "uptime": "3 days",
        }
    )

    yield client


@pytest.fixture
def truenas_host() -> str:
    """Get TrueNAS host from environment for integration tests."""
    return os.getenv("TRUENAS_HOST", "truenas.local")


@pytest.fixture
def truenas_api_key() -> str | None:
    """Get TrueNAS API key from environment for integration tests."""
    return os.getenv("TRUENAS_API_KEY")


@pytest.fixture
def skip_if_no_credentials(truenas_api_key: str | None) -> None:
    """Skip test if no TrueNAS credentials are available."""
    if not truenas_api_key:
        pytest.skip("No TrueNAS credentials available")


@pytest.fixture
async def real_client(
    truenas_host: str, truenas_api_key: str
) -> AsyncGenerator[TrueNASClient, None]:
    """
    Create a real TrueNAS client for integration testing.

    Requires TRUENAS_HOST and TRUENAS_API_KEY environment variables.
    """
    if not truenas_api_key:
        pytest.skip("TRUENAS_API_KEY not set")

    client = TrueNASClient(truenas_host, verify_ssl=False)

    try:
        await client.connect()
        await client.login_with_api_key(truenas_api_key)
    except (TrueNASConnectionError, ConnectionError) as exc:
        pytest.skip(f"Unable to connect to TrueNAS host '{truenas_host}': {exc}")
    except TrueNASAuthenticationError as exc:
        pytest.skip(f"TrueNAS authentication failed: {exc}")
    except Exception as exc:  # pragma: no cover - defensive
        pytest.skip(f"Unexpected error during TrueNAS setup: {exc}")

    try:
        yield client
    finally:
        await client.disconnect()

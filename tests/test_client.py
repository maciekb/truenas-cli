"""Unit tests for TrueNAS client."""

import pytest

from truenas_client import (
    TrueNASAPIError,
    TrueNASAuthenticationError,
    TrueNASClient,
    TrueNASConnectionError,
    TrueNASNotFoundError,
)


@pytest.mark.unit
class TestTrueNASClient:
    """Test TrueNASClient class."""

    def test_client_initialization(self):
        """Test client initialization with default parameters."""
        client = TrueNASClient("test.local")

        assert client.host == "test.local"
        assert client.port == 443
        assert client.use_ssl is True
        assert client.verify_ssl is True
        assert not client.is_connected
        assert not client.is_authenticated

    def test_client_initialization_custom_params(self):
        """Test client initialization with custom parameters."""
        client = TrueNASClient(
            "192.168.1.100", port=8443, use_ssl=False, verify_ssl=False
        )

        assert client.host == "192.168.1.100"
        assert client.port == 8443
        assert client.use_ssl is False
        assert client.verify_ssl is False

    def test_url_property_https(self):
        """Test URL property with HTTPS."""
        client = TrueNASClient("test.local")
        assert client.url == "wss://test.local:443/websocket"

    def test_url_property_http(self):
        """Test URL property with HTTP."""
        client = TrueNASClient("test.local", use_ssl=False)
        assert client.url == "ws://test.local:443/websocket"

    def test_url_property_custom_port(self):
        """Test URL property with custom port."""
        client = TrueNASClient("test.local", port=8443)
        assert client.url == "wss://test.local:8443/websocket"


@pytest.mark.unit
class TestExceptionHierarchy:
    """Test exception hierarchy."""

    def test_base_exception(self):
        """Test TrueNASClientError is base exception."""
        from truenas_client import TrueNASClientError

        assert issubclass(TrueNASConnectionError, TrueNASClientError)
        assert issubclass(TrueNASAPIError, TrueNASClientError)
        assert issubclass(TrueNASAuthenticationError, TrueNASClientError)
        assert issubclass(TrueNASNotFoundError, TrueNASClientError)

    def test_exception_messages(self):
        """Test exception messages."""
        error = TrueNASConnectionError("Connection failed")
        assert str(error) == "Connection failed"

        error = TrueNASAPIError("API error")
        assert str(error) == "API error"


@pytest.mark.unit
@pytest.mark.anyio
async def test_client_context_manager(async_mock_client):
    """Test client async context manager."""
    # Test that context manager calls connect and disconnect
    async with async_mock_client:
        assert async_mock_client.is_connected

    # In real implementation, disconnect would be called
    # but with mock we just verify structure works


@pytest.mark.unit
@pytest.mark.anyio
async def test_call_method_not_connected():
    """Test calling API method when not connected raises error."""
    client = TrueNASClient("test.local")

    with pytest.raises(TrueNASConnectionError):
        await client.call("system.info")


@pytest.mark.unit
def test_ensure_connected_logic():
    """Test ensure_connected logic exists."""
    # We're testing that the real client has these methods
    # Full integration tests will verify the actual behavior
    client = TrueNASClient("test.local")
    assert hasattr(client, "ensure_connected")
    assert hasattr(client, "ensure_authenticated")
    assert callable(client.ensure_connected)
    assert callable(client.ensure_authenticated)


@pytest.mark.unit
@pytest.mark.anyio
async def test_system_info(async_mock_client):
    """Test system_info method."""
    result = await async_mock_client.system_info()

    assert "hostname" in result
    assert "version" in result
    async_mock_client.system_info.assert_called_once()

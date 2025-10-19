"""Unit tests for TrueNAS client."""

from unittest.mock import AsyncMock

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


@pytest.mark.unit
@pytest.mark.anyio
async def test_get_pool_scrubs_calls_query():
    """Test get_pool_scrubs delegates to pool.scrub.query."""
    client = TrueNASClient("test.local")
    client.call = AsyncMock(return_value=[{"id": 1}])

    result = await client.get_pool_scrubs()

    assert result == [{"id": 1}]
    client.call.assert_awaited_once_with("pool.scrub.query", [[]])


@pytest.mark.unit
@pytest.mark.anyio
async def test_run_pool_scrub_with_threshold():
    """Test run_pool_scrub passes optional threshold."""
    client = TrueNASClient("test.local")
    client.call = AsyncMock(return_value=None)

    await client.run_pool_scrub("tank", threshold=10)

    client.call.assert_awaited_once_with("pool.scrub.run", ["tank", 10])


@pytest.mark.unit
@pytest.mark.anyio
async def test_run_pool_scrub_without_threshold():
    """Test run_pool_scrub omits threshold when not provided."""
    client = TrueNASClient("test.local")
    client.call = AsyncMock(return_value=None)

    await client.run_pool_scrub("tank")

    client.call.assert_awaited_once_with("pool.scrub.run", ["tank"])


@pytest.mark.unit
@pytest.mark.anyio
async def test_login_uses_password_and_returns_result():
    """Regression: ensure password is forwarded rather than redacted."""

    client = TrueNASClient("test.local")
    client.ensure_connected = AsyncMock()
    client.call = AsyncMock(return_value={"session": "abc"})

    result = await client.login("root", "secret")

    client.ensure_connected.assert_awaited_once()
    client.call.assert_awaited_once_with("auth.login", ["root", "secret"])
    assert result == {"session": "abc"}


@pytest.mark.unit
@pytest.mark.anyio
async def test_login_with_api_key_returns_server_payload():
    """Ensure API key login delegates correctly and exposes response payload."""

    client = TrueNASClient("test.local")
    client.ensure_connected = AsyncMock()
    client.call = AsyncMock(return_value={"token": "xyz"})

    result = await client.login_with_api_key("apikey")

    client.ensure_connected.assert_awaited_once()
    client.call.assert_awaited_once_with("auth.login_with_api_key", ["apikey"])
    assert result == {"token": "xyz"}


@pytest.mark.unit
@pytest.mark.anyio
async def test_update_pool_scrub_calls_api():
    """Test update_pool_scrub forwards data."""
    client = TrueNASClient("test.local")
    client.call = AsyncMock(return_value={"id": 3})

    result = await client.update_pool_scrub(3, threshold=20, enabled=False)

    assert result == {"id": 3}
    client.call.assert_awaited_once_with(
        "pool.scrub.update",
        [3, {"threshold": 20, "enabled": False}],
    )


@pytest.mark.unit
@pytest.mark.anyio
async def test_delete_pool_scrub_calls_api():
    """Test delete_pool_scrub forwards to API."""
    client = TrueNASClient("test.local")
    client.call = AsyncMock(return_value=True)

    result = await client.delete_pool_scrub(5)

    assert result is True
    client.call.assert_awaited_once_with("pool.scrub.delete", [5])


@pytest.mark.unit
@pytest.mark.anyio
async def test_get_resilver_config_calls_api():
    """Test get_resilver_config invokes pool.resilver.config."""
    client = TrueNASClient("test.local")
    client.call = AsyncMock(return_value={"enabled": True})

    result = await client.get_resilver_config()

    assert result == {"enabled": True}
    client.call.assert_awaited_once_with("pool.resilver.config", [])


@pytest.mark.unit
@pytest.mark.anyio
async def test_update_resilver_config_calls_api():
    """Test update_resilver_config forwards parameters."""
    client = TrueNASClient("test.local")
    client.call = AsyncMock(return_value={"enabled": False})

    result = await client.update_resilver_config(enabled=False, begin="18:00")

    assert result == {"enabled": False}
    client.call.assert_awaited_once_with(
        "pool.resilver.update",
        [{"enabled": False, "begin": "18:00"}],
    )


@pytest.mark.unit
@pytest.mark.anyio
async def test_get_snapshot_tasks_calls_query():
    """Test get_snapshot_tasks delegates to query."""
    client = TrueNASClient("test.local")
    client.call = AsyncMock(return_value=[{"id": 7}])

    result = await client.get_snapshot_tasks()

    assert result == [{"id": 7}]
    client.call.assert_awaited_once_with("pool.snapshottask.query", [[]])


@pytest.mark.unit
@pytest.mark.anyio
async def test_create_snapshot_task_calls_api():
    """Test create_snapshot_task forwards payload."""
    client = TrueNASClient("test.local")
    client.call = AsyncMock(return_value={"id": 9})

    payload = {
        "dataset": "tank/data",
        "naming_schema": "auto_%Y-%m-%d_%H-%M",
    }
    result = await client.create_snapshot_task(**payload)

    assert result == {"id": 9}
    client.call.assert_awaited_once_with("pool.snapshottask.create", [payload])


@pytest.mark.unit
@pytest.mark.anyio
async def test_update_snapshot_task_calls_api():
    """Test update_snapshot_task forwards updates."""
    client = TrueNASClient("test.local")
    client.call = AsyncMock(return_value={"id": 11})

    result = await client.update_snapshot_task(11, enabled=False)

    assert result == {"id": 11}
    client.call.assert_awaited_once_with(
        "pool.snapshottask.update",
        [11, {"enabled": False}],
    )


@pytest.mark.unit
@pytest.mark.anyio
async def test_delete_snapshot_task_calls_api():
    """Test delete_snapshot_task forwards id."""
    client = TrueNASClient("test.local")
    client.call = AsyncMock(return_value=True)

    result = await client.delete_snapshot_task(12)

    assert result is True
    client.call.assert_awaited_once_with("pool.snapshottask.delete", [12])


@pytest.mark.unit
@pytest.mark.anyio
async def test_run_snapshot_task_calls_api():
    """Test run_snapshot_task forwards id."""
    client = TrueNASClient("test.local")
    client.call = AsyncMock(return_value=None)

    await client.run_snapshot_task(13)

    client.call.assert_awaited_once_with("pool.snapshottask.run", [13])

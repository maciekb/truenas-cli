"""Basic integration tests for TrueNAS CLI.

These tests connect to a real TrueNAS instance.
Requires TRUENAS_HOST and TRUENAS_API_KEY environment variables.

Run with:
    export TRUENAS_HOST=your-truenas-host
    export TRUENAS_API_KEY=your-api-key
    pytest tests/integration/ -m integration
"""

import pytest

from truenas_client import TrueNASClient


@pytest.mark.integration
@pytest.mark.anyio
async def test_connection(real_client: TrueNASClient) -> None:
    """Test basic connection to TrueNAS."""
    assert real_client.is_connected
    assert real_client.is_authenticated


@pytest.mark.integration
@pytest.mark.anyio
async def test_system_info(real_client: TrueNASClient) -> None:
    """Test fetching system information."""
    info = await real_client.system_info()

    assert isinstance(info, dict)
    assert "hostname" in info
    assert "version" in info
    assert len(info["hostname"]) > 0


@pytest.mark.integration
@pytest.mark.anyio
async def test_system_version(real_client: TrueNASClient) -> None:
    """Test fetching system version."""
    version = await real_client.system_version()

    assert isinstance(version, str)
    assert len(version) > 0


@pytest.mark.integration
@pytest.mark.anyio
async def test_get_pools(real_client: TrueNASClient) -> None:
    """Test fetching pool list."""
    pools = await real_client.get_pools()

    assert isinstance(pools, list)
    # May be empty on fresh install
    if pools:
        pool = pools[0]
        assert "name" in pool
        assert "status" in pool


@pytest.mark.integration
@pytest.mark.anyio
async def test_get_datasets(real_client: TrueNASClient) -> None:
    """Test fetching dataset list."""
    datasets = await real_client.get_datasets()

    assert isinstance(datasets, list)
    # May be empty on fresh install


@pytest.mark.integration
@pytest.mark.anyio
async def test_get_services(real_client: TrueNASClient) -> None:
    """Test fetching service list."""
    services = await real_client.get_services()

    assert isinstance(services, list)
    assert len(services) > 0

    # Check that at least some common services exist
    service_names = [s.get("service") for s in services]
    assert "cifs" in service_names or "smb" in service_names
    assert "ssh" in service_names


@pytest.mark.integration
@pytest.mark.anyio
async def test_get_disks(real_client: TrueNASClient) -> None:
    """Test fetching disk list."""
    disks = await real_client.get_disks()

    assert isinstance(disks, list)
    # Should have at least one disk
    assert len(disks) > 0

    disk = disks[0]
    assert "name" in disk


@pytest.mark.integration
@pytest.mark.anyio
async def test_get_alerts(real_client: TrueNASClient) -> None:
    """Test fetching alerts."""
    alerts = await real_client.get_alerts()

    assert isinstance(alerts, list)
    # May be empty if no alerts


@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.anyio
async def test_query_with_filters(real_client: TrueNASClient) -> None:
    """Test query method with filters."""
    # Query for services with specific name
    results = await real_client.query("service", [["service", "=", "ssh"]])

    assert isinstance(results, list)
    if results:
        assert results[0]["service"] == "ssh"


@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.anyio
async def test_get_snapshots(real_client: TrueNASClient) -> None:
    """Test fetching snapshots."""
    snapshots = await real_client.get_snapshots()

    assert isinstance(snapshots, list)
    # May be empty if no snapshots exist

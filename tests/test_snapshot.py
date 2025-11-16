"""Tests for snapshot management functionality."""

import pytest
from unittest.mock import MagicMock, patch

from truenas_cli.client.base import TrueNASClient
from truenas_cli.client.exceptions import APIError, TrueNASError
from truenas_cli.config import ProfileConfig


@pytest.fixture
def mock_profile():
    """Create a mock profile for testing."""
    return ProfileConfig(
        url="https://truenas.local",
        api_key="test-api-key",
        verify_ssl=True,
        timeout=30.0,
    )


@pytest.fixture
def client(mock_profile):
    """Create a TrueNAS client for testing."""
    return TrueNASClient(profile=mock_profile, verbose=False)


@pytest.fixture
def mock_snapshot_response():
    """Sample snapshot API response."""
    return {
        "name": "tank/data@backup-2025-01-15",
        "dataset": "tank/data",
        "snapshot_name": "backup-2025-01-15",
        "type": "SNAPSHOT",
        "createtxg": 12345,
        "creation": {"$date": 1705315200000},  # 2025-01-15 10:00:00
        "used": {"parsed": 1073741824},  # 1GB
        "referenced": {"parsed": 10737418240},  # 10GB
        "properties": {},
    }


@pytest.fixture
def mock_snapshot_list_response():
    """Sample snapshot list API response."""
    return [
        {
            "name": "tank/data@snap1",
            "dataset": "tank/data",
            "snapshot_name": "snap1",
            "createtxg": 12340,
            "creation": {"$date": 1705315200000},
            "used": {"parsed": 524288000},
            "referenced": {"parsed": 5368709120},
        },
        {
            "name": "tank/data@snap2",
            "dataset": "tank/data",
            "snapshot_name": "snap2",
            "createtxg": 12350,
            "creation": {"$date": 1705401600000},
            "used": {"parsed": 1048576000},
            "referenced": {"parsed": 10737418240},
        },
    ]


class TestSnapshotAPIMethods:
    """Test snapshot API client methods."""

    def test_list_snapshots_all(self, client, mock_snapshot_list_response, httpx_mock):
        """Test listing all snapshots."""
        httpx_mock.add_response(
            url="https://truenas.local/api/v2.0/zfs/snapshot",
            json=mock_snapshot_list_response,
        )

        snapshots = client.list_snapshots()

        assert len(snapshots) == 2
        assert snapshots[0]["name"] == "tank/data@snap1"
        assert snapshots[1]["name"] == "tank/data@snap2"

    def test_list_snapshots_filtered(self, client, mock_snapshot_list_response, httpx_mock):
        """Test listing snapshots filtered by dataset."""
        # Note: httpx_mock doesn't easily support query params validation,
        # so we just test the call is made
        httpx_mock.add_response(
            url="https://truenas.local/api/v2.0/zfs/snapshot",
            json=mock_snapshot_list_response,
        )

        snapshots = client.list_snapshots(dataset="tank/data")

        assert len(snapshots) == 2

    def test_get_snapshot(self, client, mock_snapshot_response, httpx_mock):
        """Test getting a specific snapshot."""
        snapshot_id = "tank/data@backup-2025-01-15"
        # URL encoded: tank%2Fdata%40backup-2025-01-15
        httpx_mock.add_response(
            url="https://truenas.local/api/v2.0/zfs/snapshot/id/tank%2Fdata%40backup-2025-01-15",
            json=mock_snapshot_response,
        )

        snapshot = client.get_snapshot(snapshot_id)

        assert snapshot["name"] == snapshot_id
        assert snapshot["dataset"] == "tank/data"

    def test_create_snapshot(self, client, mock_snapshot_response, httpx_mock):
        """Test creating a snapshot."""
        httpx_mock.add_response(
            url="https://truenas.local/api/v2.0/zfs/snapshot",
            method="POST",
            json=mock_snapshot_response,
        )

        result = client.create_snapshot(
            dataset="tank/data",
            snapshot_name="backup-2025-01-15",
            recursive=False,
        )

        assert result["name"] == "tank/data@backup-2025-01-15"
        assert result["dataset"] == "tank/data"

        # Verify the request payload
        request = httpx_mock.get_request()
        assert request.method == "POST"
        import json
        payload = json.loads(request.content)
        assert payload["dataset"] == "tank/data"
        assert payload["name"] == "backup-2025-01-15"
        assert payload["recursive"] is False

    def test_create_snapshot_recursive(self, client, mock_snapshot_response, httpx_mock):
        """Test creating a recursive snapshot."""
        httpx_mock.add_response(
            url="https://truenas.local/api/v2.0/zfs/snapshot",
            method="POST",
            json=mock_snapshot_response,
        )

        result = client.create_snapshot(
            dataset="tank/data",
            snapshot_name="backup-recursive",
            recursive=True,
        )

        # Verify the recursive flag was sent
        request = httpx_mock.get_request()
        import json
        payload = json.loads(request.content)
        assert payload["recursive"] is True

    def test_delete_snapshot(self, client, httpx_mock):
        """Test deleting a snapshot."""
        snapshot_id = "tank/data@backup-2025-01-15"
        httpx_mock.add_response(
            url="https://truenas.local/api/v2.0/zfs/snapshot/id/tank%2Fdata%40backup-2025-01-15",
            method="DELETE",
            json={"status": "deleted"},
        )

        result = client.delete_snapshot(snapshot_id)

        assert result["status"] == "deleted"

    def test_delete_snapshot_recursive(self, client, httpx_mock):
        """Test deleting a snapshot with recursive option."""
        snapshot_id = "tank/data@backup-2025-01-15"
        httpx_mock.add_response(
            method="DELETE",
            json={"status": "deleted"},
        )

        result = client.delete_snapshot(snapshot_id, recursive=True)

        assert result["status"] == "deleted"

    def test_rollback_snapshot(self, client, httpx_mock):
        """Test rolling back to a snapshot."""
        snapshot_id = "tank/data@backup-2025-01-15"
        httpx_mock.add_response(
            url="https://truenas.local/api/v2.0/zfs/snapshot/rollback",
            method="POST",
            json={"status": "success"},
        )

        result = client.rollback_snapshot(snapshot_id, force=True, recursive=False)

        assert result["status"] == "success"

        # Verify the request payload
        request = httpx_mock.get_request()
        import json
        payload = json.loads(request.content)
        assert payload["id"] == snapshot_id
        assert payload["options"]["force"] is True
        assert payload["options"]["recursive"] is False

    def test_clone_snapshot(self, client, httpx_mock):
        """Test cloning a snapshot."""
        snapshot_id = "tank/data@backup-2025-01-15"
        target_dataset = "tank/data-restore"

        httpx_mock.add_response(
            url="https://truenas.local/api/v2.0/zfs/snapshot/clone",
            method="POST",
            json={"name": target_dataset, "cloned_from": snapshot_id},
        )

        result = client.clone_snapshot(snapshot_id, target_dataset)

        assert result["name"] == target_dataset
        assert result["cloned_from"] == snapshot_id

        # Verify the request payload
        request = httpx_mock.get_request()
        import json
        payload = json.loads(request.content)
        assert payload["snapshot"] == snapshot_id
        assert payload["dataset_dst"] == target_dataset

    def test_api_error_handling(self, client, httpx_mock):
        """Test handling of API errors."""
        httpx_mock.add_response(
            url="https://truenas.local/api/v2.0/zfs/snapshot",
            status_code=404,
            json={"message": "Snapshot not found"},
        )

        with pytest.raises(APIError) as exc_info:
            client.list_snapshots()

        assert "404" in str(exc_info.value)


class TestSnapshotNameParsing:
    """Test snapshot name parsing utilities."""

    def test_parse_valid_snapshot_name(self):
        """Test parsing valid snapshot names."""
        from truenas_cli.commands.snapshot import parse_snapshot_name

        dataset, snapshot = parse_snapshot_name("tank/data@backup-2025-01-15")
        assert dataset == "tank/data"
        assert snapshot == "backup-2025-01-15"

    def test_parse_nested_dataset_snapshot(self):
        """Test parsing snapshot with nested dataset path."""
        from truenas_cli.commands.snapshot import parse_snapshot_name

        dataset, snapshot = parse_snapshot_name("tank/parent/child@snap1")
        assert dataset == "tank/parent/child"
        assert snapshot == "snap1"

    def test_parse_invalid_snapshot_missing_at(self):
        """Test parsing invalid snapshot name without @."""
        from truenas_cli.commands.snapshot import parse_snapshot_name

        with pytest.raises(ValueError) as exc_info:
            parse_snapshot_name("tank/data")

        assert "Invalid snapshot format" in str(exc_info.value)
        assert "dataset@snapshot_name" in str(exc_info.value)

    def test_parse_snapshot_with_multiple_at(self):
        """Test parsing snapshot name with multiple @ symbols."""
        from truenas_cli.commands.snapshot import parse_snapshot_name

        # Should split on first @
        dataset, snapshot = parse_snapshot_name("tank/data@snap@with@at")
        assert dataset == "tank/data"
        assert snapshot == "snap@with@at"


class TestSnapshotValidation:
    """Test snapshot validation and error handling."""

    def test_create_snapshot_invalid_format(self, client):
        """Test creating snapshot with invalid name format."""
        # This would be caught at CLI level, but test API level too
        with pytest.raises((ValueError, TrueNASError, APIError)):
            # Missing snapshot name part
            client.create_snapshot(dataset="tank/data", snapshot_name="")

    def test_snapshot_not_found(self, client, httpx_mock):
        """Test handling of non-existent snapshot."""
        httpx_mock.add_response(
            status_code=404,
            json={"message": "Snapshot not found"},
        )

        with pytest.raises(APIError) as exc_info:
            client.get_snapshot("tank/data@nonexistent")

        assert "404" in str(exc_info.value)


class TestSnapshotEdgeCases:
    """Test edge cases and special scenarios."""

    def test_snapshot_with_special_characters(self, client, httpx_mock):
        """Test snapshot names with special characters."""
        # Snapshot names can contain hyphens, underscores, periods
        snapshot_id = "tank/data@backup-2025.01.15_daily"

        httpx_mock.add_response(
            url="https://truenas.local/api/v2.0/zfs/snapshot",
            method="POST",
            json={"name": snapshot_id},
        )

        result = client.create_snapshot(
            dataset="tank/data",
            snapshot_name="backup-2025.01.15_daily",
        )

        assert result["name"] == snapshot_id

    def test_empty_snapshot_list(self, client, httpx_mock):
        """Test handling of empty snapshot list."""
        httpx_mock.add_response(
            url="https://truenas.local/api/v2.0/zfs/snapshot",
            json=[],
        )

        snapshots = client.list_snapshots()

        assert snapshots == []
        assert len(snapshots) == 0

    def test_clone_with_properties(self, client, httpx_mock):
        """Test cloning snapshot with additional properties."""
        snapshot_id = "tank/data@backup"
        target = "tank/data-clone"
        properties = {"compression": "lz4", "quota": "100G"}

        httpx_mock.add_response(
            url="https://truenas.local/api/v2.0/zfs/snapshot/clone",
            method="POST",
            json={"name": target},
        )

        result = client.clone_snapshot(
            snapshot_id, target, properties=properties
        )

        # Verify properties were sent
        request = httpx_mock.get_request()
        import json
        payload = json.loads(request.content)
        assert payload["dataset_properties"] == properties


class TestSnapshotIntegration:
    """Integration-style tests simulating real workflows."""

    def test_snapshot_lifecycle(self, client, httpx_mock):
        """Test complete snapshot lifecycle: create, list, delete."""
        snapshot_id = "tank/data@test-snapshot"

        # Create snapshot
        httpx_mock.add_response(
            url="https://truenas.local/api/v2.0/zfs/snapshot",
            method="POST",
            json={"name": snapshot_id, "dataset": "tank/data"},
        )

        create_result = client.create_snapshot("tank/data", "test-snapshot")
        assert create_result["name"] == snapshot_id

        # List snapshots
        httpx_mock.add_response(
            url="https://truenas.local/api/v2.0/zfs/snapshot",
            json=[{"name": snapshot_id, "dataset": "tank/data"}],
        )

        snapshots = client.list_snapshots()
        assert len(snapshots) == 1
        assert snapshots[0]["name"] == snapshot_id

        # Delete snapshot
        httpx_mock.add_response(
            method="DELETE",
            json={"status": "deleted"},
        )

        delete_result = client.delete_snapshot(snapshot_id)
        assert delete_result["status"] == "deleted"

    def test_snapshot_clone_workflow(self, client, httpx_mock):
        """Test snapshot and clone workflow."""
        snapshot_id = "tank/data@pre-update"
        clone_name = "tank/data-backup"

        # Create snapshot
        httpx_mock.add_response(
            url="https://truenas.local/api/v2.0/zfs/snapshot",
            method="POST",
            json={"name": snapshot_id},
        )

        client.create_snapshot("tank/data", "pre-update")

        # Clone snapshot
        httpx_mock.add_response(
            url="https://truenas.local/api/v2.0/zfs/snapshot/clone",
            method="POST",
            json={"name": clone_name, "cloned_from": snapshot_id},
        )

        clone_result = client.clone_snapshot(snapshot_id, clone_name)
        assert clone_result["name"] == clone_name

"""Unit tests for CLI commands."""

from unittest.mock import AsyncMock

import pytest

from truenas_cli.commands import COMMAND_GROUPS


@pytest.mark.unit
class TestCommandRegistration:
    """Test command group registration."""

    def test_all_command_groups_registered(self) -> None:
        """Test that all command groups are registered."""
        assert len(COMMAND_GROUPS) > 0

        expected_commands = [
            "general",  # "test" command is in general group
            "system",
            "pool",
            "dataset",
            "smb",
            "nfs",
            "snapshot",
            "service",
            "disk",
            "alerts",
            "app",
            "user",
            "group",
            "replication",
            "cloudsync",
        ]

        registered_names = [group.name for group in COMMAND_GROUPS]

        for expected in expected_commands:
            assert expected in registered_names, f"Command '{expected}' not registered"

    def test_command_groups_have_register_method(self) -> None:
        """Test that all command groups have register method."""
        for group in COMMAND_GROUPS:
            assert hasattr(group, "register"), f"Group {group} missing register method"
            assert hasattr(group, "name"), f"Group {group} missing name attribute"


@pytest.mark.unit
class TestSystemCommands:
    """Test system command group."""

    def test_system_commands_exist(self) -> None:
        """Test that system commands are registered."""
        from truenas_cli.commands.system import SystemCommands

        system = SystemCommands()
        assert system.name == "system"

    @pytest.mark.anyio
    async def test_system_info_output(
        self,
        async_mock_client: AsyncMock,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """Test system info command output."""
        # This is a basic test structure - would need actual implementation
        # to test command execution
        result = await async_mock_client.system_info()
        assert "hostname" in result


@pytest.mark.unit
class TestPoolCommands:
    """Test pool command group."""

    def test_pool_commands_exist(self) -> None:
        """Test that pool commands are registered."""
        from truenas_cli.commands.pool import PoolCommands

        pool = PoolCommands()
        assert pool.name == "pool"


@pytest.mark.unit
class TestDatasetCommands:
    """Test dataset command group."""

    def test_dataset_commands_exist(self) -> None:
        """Test that dataset commands are registered."""
        from truenas_cli.commands.dataset import DatasetCommands

        dataset = DatasetCommands()
        assert dataset.name == "dataset"


@pytest.mark.unit
class TestServiceCommands:
    """Test service command group."""

    def test_service_commands_exist(self) -> None:
        """Test that service commands are registered."""
        from truenas_cli.commands.service import ServiceCommands

        service = ServiceCommands()
        assert service.name == "service"


@pytest.mark.unit
class TestSMBCommands:
    """Test SMB command group."""

    def test_smb_commands_exist(self) -> None:
        """Test that SMB commands are registered."""
        from truenas_cli.commands.smb import SMBCommands

        smb = SMBCommands()
        assert smb.name == "smb"


@pytest.mark.unit
class TestNFSCommands:
    """Test NFS command group."""

    def test_nfs_commands_exist(self) -> None:
        """Test that NFS commands are registered."""
        from truenas_cli.commands.nfs import NFSCommands

        nfs = NFSCommands()
        assert nfs.name == "nfs"


@pytest.mark.unit
class TestSnapshotCommands:
    """Test snapshot command group."""

    def test_snapshot_commands_exist(self) -> None:
        """Test that snapshot commands are registered."""
        from truenas_cli.commands.snapshot import SnapshotCommands

        snapshot = SnapshotCommands()
        assert snapshot.name == "snapshot"


@pytest.mark.unit
class TestDiskCommands:
    """Test disk command group."""

    def test_disk_commands_exist(self) -> None:
        """Test that disk commands are registered."""
        from truenas_cli.commands.disk import DiskCommands

        disk = DiskCommands()
        assert disk.name == "disk"


@pytest.mark.unit
class TestAlertsCommands:
    """Test alerts command group."""

    def test_alerts_commands_exist(self) -> None:
        """Test that alerts commands are registered."""
        from truenas_cli.commands.alerts import AlertsCommands

        alerts = AlertsCommands()
        assert alerts.name == "alerts"


@pytest.mark.unit
class TestAppCommands:
    """Test app command group."""

    def test_app_commands_exist(self) -> None:
        """Test that app commands are registered."""
        from truenas_cli.commands.app import AppCommands

        app = AppCommands()
        assert app.name == "app"


@pytest.mark.unit
class TestUserCommands:
    """Test user command group."""

    def test_user_commands_exist(self) -> None:
        """Test that user commands are registered."""
        from truenas_cli.commands.user import UserCommands

        user = UserCommands()
        assert user.name == "user"


@pytest.mark.unit
class TestGroupCommands:
    """Test group command group."""

    def test_group_commands_exist(self) -> None:
        """Test that group commands are registered."""
        from truenas_cli.commands.group import GroupCommands

        group = GroupCommands()
        assert group.name == "group"


@pytest.mark.unit
class TestReplicationCommands:
    """Test replication command group."""

    def test_replication_commands_exist(self) -> None:
        """Test that replication commands are registered."""
        from truenas_cli.commands.replication import ReplicationCommands

        replication = ReplicationCommands()
        assert replication.name == "replication"


@pytest.mark.unit
class TestPoolHelperUtilities:
    """Test helper utilities used by pool commands."""

    def test_parse_cron_schedule_valid(self) -> None:
        """Ensure cron schedule parsing works."""
        from truenas_cli.commands.pool import _parse_cron_schedule

        result = _parse_cron_schedule("0 * * * *")
        assert result == {
            "minute": "0",
            "hour": "*",
            "dom": "*",
            "month": "*",
            "dow": "*",
        }

    def test_parse_cron_schedule_invalid(self) -> None:
        """Ensure invalid cron schedule raises error."""
        from truenas_cli.commands.pool import _parse_cron_schedule

        with pytest.raises(ValueError):
            _parse_cron_schedule("0 * * *")

    def test_parse_weekday_list_valid(self) -> None:
        """Ensure weekday parsing returns integers."""
        from truenas_cli.commands.pool import _parse_weekday_list

        assert _parse_weekday_list("1,2,7") == [1, 2, 7]

    def test_parse_weekday_list_invalid(self) -> None:
        """Ensure invalid weekdays raise."""
        from truenas_cli.commands.pool import _parse_weekday_list

        with pytest.raises(ValueError):
            _parse_weekday_list("0,8")

    def test_build_schedule_helper(self) -> None:
        """Ensure schedule builder attaches window."""
        from truenas_cli.commands.pool import _build_schedule

        result = _build_schedule("0 2 * * 1", "01:00", "03:00")
        assert result == {
            "minute": "0",
            "hour": "2",
            "dom": "*",
            "month": "*",
            "dow": "1",
            "begin": "01:00",
            "end": "03:00",
        }

    def test_build_schedule_invalid_time(self) -> None:
        """Ensure invalid window times raise errors."""
        from truenas_cli.commands.pool import _build_schedule

        with pytest.raises(ValueError):
            _build_schedule("0 * * * *", "25:00", None)

    def test_build_schedule_equal_window(self) -> None:
        """Ensure identical begin/end times are rejected."""
        from truenas_cli.commands.pool import _build_schedule

        with pytest.raises(ValueError):
            _build_schedule("0 * * * *", "12:00", "12:00")


@pytest.mark.unit
class TestCloudSyncCommands:
    """Test cloudsync command group."""

    def test_cloudsync_commands_exist(self) -> None:
        """Test that cloudsync commands are registered."""
        from truenas_cli.commands.cloudsync import CloudSyncCommands

        cloudsync = CloudSyncCommands()
        assert cloudsync.name == "cloudsync"

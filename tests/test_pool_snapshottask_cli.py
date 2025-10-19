"""Integration-style tests for pool snapshot task CLI commands."""

import argparse
from collections.abc import Awaitable, Callable
from unittest.mock import AsyncMock

import pytest

from truenas_client import TrueNASClient


@pytest.mark.anyio
async def test_snapshottask_create_invokes_client(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Ensure create command calls client with expected payload."""
    from truenas_cli.commands import pool as pool_module

    client = AsyncMock()
    client.create_snapshot_task.return_value = {"id": 42}

    async def fake_run_command(
        args: argparse.Namespace,
        handler: Callable[[TrueNASClient], Awaitable[None]],
        require_auth: bool = True,
    ) -> None:
        await handler(client)

    monkeypatch.setattr(pool_module, "run_command", fake_run_command)

    args = argparse.Namespace(
        dataset="tank/data",
        naming_schema="auto_%Y-%m-%d_%H-%M",
        lifetime_value=2,
        lifetime_unit="WEEK",
        schedule="0 * * * *",
        begin=None,
        end=None,
        disable=False,
        recursive=True,
        exclude=["tank/data/tmp"],
        json=False,
    )

    await pool_module._cmd_pool_snapshottask_create(args)

    client.create_snapshot_task.assert_awaited_once_with(
        dataset="tank/data",
        naming_schema="auto_%Y-%m-%d_%H-%M",
        lifetime_value=2,
        lifetime_unit="WEEK",
        schedule={
            "minute": "0",
            "hour": "*",
            "dom": "*",
            "month": "*",
            "dow": "*",
        },
        enabled=True,
        recursive=True,
        exclude=["tank/data/tmp"],
    )


@pytest.mark.anyio
async def test_snapshottask_update_builds_payload(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Ensure update command constructs payload correctly."""
    from truenas_cli.commands import pool as pool_module

    client = AsyncMock()
    client.update_snapshot_task.return_value = {"id": 5}

    async def fake_run_command(
        args: argparse.Namespace,
        handler: Callable[[TrueNASClient], Awaitable[None]],
        require_auth: bool = True,
    ) -> None:
        await handler(client)

    monkeypatch.setattr(pool_module, "run_command", fake_run_command)

    args = argparse.Namespace(
        task_id=5,
        dataset="tank/backups",
        naming_schema=None,
        lifetime_value=4,
        lifetime_unit="DAY",
        schedule="15 2 * * 1",
        begin="01:00",
        end="04:00",
        exclude=None,
        clear_exclude=True,
        enable=True,
        disable=False,
        recursive=None,
        json=False,
    )

    await pool_module._cmd_pool_snapshottask_update(args)

    client.update_snapshot_task.assert_awaited_once_with(
        5,
        dataset="tank/backups",
        lifetime_value=4,
        lifetime_unit="DAY",
        schedule={
            "minute": "15",
            "hour": "2",
            "dom": "*",
            "month": "*",
            "dow": "1",
            "begin": "01:00",
            "end": "04:00",
        },
        exclude=[],
        enabled=True,
    )


@pytest.mark.anyio
async def test_snapshottask_delete_with_force(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Ensure delete command calls client without prompting when forced."""
    from truenas_cli.commands import pool as pool_module

    client = AsyncMock()

    async def fake_run_command(
        args: argparse.Namespace,
        handler: Callable[[TrueNASClient], Awaitable[None]],
        require_auth: bool = True,
    ) -> None:
        await handler(client)

    monkeypatch.setattr(pool_module, "run_command", fake_run_command)

    args = argparse.Namespace(
        task_id=7,
        force=True,
        json=False,
    )

    await pool_module._cmd_pool_snapshottask_delete(args)

    client.delete_snapshot_task.assert_awaited_once_with(7)


@pytest.mark.anyio
async def test_snapshottask_run_invokes_client(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Ensure run command triggers client execution."""
    from truenas_cli.commands import pool as pool_module

    client = AsyncMock()

    async def fake_run_command(
        args: argparse.Namespace,
        handler: Callable[[TrueNASClient], Awaitable[None]],
        require_auth: bool = True,
    ) -> None:
        await handler(client)

    monkeypatch.setattr(pool_module, "run_command", fake_run_command)

    args = argparse.Namespace(task_id=9, json=False)

    await pool_module._cmd_pool_snapshottask_run(args)

    client.run_snapshot_task.assert_awaited_once_with(9)

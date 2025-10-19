"""Tests for snapshot CLI commands."""

import argparse
from unittest.mock import AsyncMock

import pytest


@pytest.mark.anyio
async def test_snapshot_rollback_without_force(monkeypatch):
    """Ensure rollback sends empty options when no flags provided."""
    from truenas_cli.commands import snapshot as snapshot_module

    client = AsyncMock()
    client.call = AsyncMock(return_value=True)

    async def fake_run_command(args, handler, require_auth=True):
        await handler(client)

    monkeypatch.setattr(snapshot_module, "run_command", fake_run_command)
    monkeypatch.setattr("builtins.input", lambda _: "yes")

    args = argparse.Namespace(
        snapshot="tank/data@daily",
        force=False,
        recursive=False,
        json=False,
    )

    await snapshot_module._cmd_snapshot_rollback(args)

    client.call.assert_awaited_once_with(
        "pool.snapshot.rollback",
        ["tank/data@daily", {}],
    )


@pytest.mark.anyio
async def test_snapshot_rollback_with_flags(monkeypatch):
    """Ensure rollback forwards recursive and force flags."""
    from truenas_cli.commands import snapshot as snapshot_module

    client = AsyncMock()
    client.call = AsyncMock(return_value=True)

    async def fake_run_command(args, handler, require_auth=True):
        await handler(client)

    monkeypatch.setattr(snapshot_module, "run_command", fake_run_command)

    args = argparse.Namespace(
        snapshot="tank/data@daily",
        force=True,
        recursive=True,
        json=False,
    )

    await snapshot_module._cmd_snapshot_rollback(args)

    client.call.assert_awaited_once_with(
        "pool.snapshot.rollback",
        [
            "tank/data@daily",
            {"recursive": True, "force": True},
        ],
    )

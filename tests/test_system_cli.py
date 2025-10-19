"""Tests for system command CLI behavior."""

import argparse
from unittest.mock import AsyncMock

import pytest


@pytest.mark.anyio
async def test_system_shutdown_uses_reason_and_delay(monkeypatch):
    """Ensure shutdown command forwards reason and delay."""
    from truenas_cli.commands import system as system_module

    client = AsyncMock()

    async def fake_run_command(args, handler, require_auth=True):
        await handler(client)

    monkeypatch.setattr(system_module, "run_command", fake_run_command)

    args = argparse.Namespace(
        delay=15,
        reason="Maintenance window",
        json=False,
    )

    await system_module._cmd_system_shutdown(args)

    client.call.assert_awaited_once_with(
        "system.shutdown",
        ["Maintenance window", {"delay": 15}],
    )


@pytest.mark.anyio
async def test_system_shutdown_rejects_empty_reason(monkeypatch):
    """Ensure shutdown validation rejects empty reasons."""
    from truenas_cli.commands import system as system_module

    client = AsyncMock()

    async def fake_run_command(args, handler, require_auth=True):
        await handler(client)

    monkeypatch.setattr(system_module, "run_command", fake_run_command)

    args = argparse.Namespace(
        delay=5,
        reason="   ",
        json=False,
    )

    with pytest.raises(ValueError):
        await system_module._cmd_system_shutdown(args)

    client.call.assert_not_called()

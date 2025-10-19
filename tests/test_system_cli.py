"""Tests for system command CLI behavior."""

import argparse
from collections.abc import Awaitable, Callable
from unittest.mock import AsyncMock

import pytest

from truenas_client import TrueNASClient


@pytest.mark.anyio
async def test_system_shutdown_uses_reason_and_delay(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Ensure shutdown command forwards reason and delay."""
    from truenas_cli.commands import system as system_module

    client = AsyncMock()

    async def fake_run_command(
        args: argparse.Namespace,
        handler: Callable[[TrueNASClient], Awaitable[None]],
        require_auth: bool = True,
    ) -> None:
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
async def test_system_shutdown_rejects_empty_reason(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Ensure shutdown validation rejects empty reasons."""
    from truenas_cli.commands import system as system_module

    client = AsyncMock()

    async def fake_run_command(
        args: argparse.Namespace,
        handler: Callable[[TrueNASClient], Awaitable[None]],
        require_auth: bool = True,
    ) -> None:
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


@pytest.mark.anyio
async def test_system_halt_uses_shutdown(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Ensure halt leverages system.shutdown with zero delay."""
    from truenas_cli.commands import system as system_module

    client = AsyncMock()

    async def fake_run_command(
        args: argparse.Namespace,
        handler: Callable[[TrueNASClient], Awaitable[None]],
        require_auth: bool = True,
    ) -> None:
        await handler(client)

    monkeypatch.setattr(system_module, "run_command", fake_run_command)

    args = argparse.Namespace(
        force=False,
        json=False,
    )

    await system_module._cmd_system_halt(args)

    client.call.assert_awaited_once_with(
        "system.shutdown",
        [system_module.DEFAULT_HALT_REASON, {"delay": None}],
    )

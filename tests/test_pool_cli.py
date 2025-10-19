"""Tests for pool CLI commands that wrap API calls."""

import argparse
from collections.abc import Awaitable, Callable
from unittest.mock import AsyncMock, call

import pytest

from truenas_client import TrueNASClient


@pytest.mark.anyio
async def test_pool_create_builds_topology(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Ensure pool create command builds documented topology payload."""
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
        name="tank",
        disks="da0, da1,da2",
        vdev_type="raidz2",
        encryption="no",
        encryption_key=None,
        json=False,
    )

    await pool_module._cmd_pool_create(args)

    client.call.assert_awaited_once_with(
        "pool.create",
        [
            {
                "name": "tank",
                "topology": {
                    "data": [
                        {
                            "type": "RAIDZ2",
                            "disks": ["da0", "da1", "da2"],
                        }
                    ]
                },
            }
        ],
    )


@pytest.mark.anyio
async def test_pool_create_encryption_requires_passphrase(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Ensure encryption requires passphrase and populates encryption options."""
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
        name="secure",
        disks="da0,da1",
        vdev_type="mirror",
        encryption="yes",
        encryption_key="supersecret",
        json=False,
    )

    await pool_module._cmd_pool_create(args)

    client.call.assert_awaited_once_with(
        "pool.create",
        [
            {
                "name": "secure",
                "topology": {
                    "data": [
                        {
                            "type": "MIRROR",
                            "disks": ["da0", "da1"],
                        }
                    ]
                },
                "encryption": True,
                "encryption_options": {
                    "passphrase": "supersecret",
                },
            }
        ],
    )


@pytest.mark.anyio
async def test_pool_create_encryption_missing_passphrase(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Ensure missing encryption key raises validation error."""
    from truenas_cli.commands import pool as pool_module

    async def fake_run_command(
        args: argparse.Namespace,
        handler: Callable[[TrueNASClient], Awaitable[None]],
        require_auth: bool = True,
    ) -> None:
        await handler(AsyncMock(spec=TrueNASClient))

    monkeypatch.setattr(pool_module, "run_command", fake_run_command)

    args = argparse.Namespace(
        name="secure",
        disks="disk0,disk1",
        vdev_type="mirror",
        encryption="yes",
        encryption_key="",
        json=False,
    )

    with pytest.raises(ValueError):
        await pool_module._cmd_pool_create(args)


@pytest.mark.anyio
async def test_pool_import_uses_guid(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Ensure pool import passes GUID as required by API."""
    from truenas_cli.commands import pool as pool_module

    client = AsyncMock()
    client.call = AsyncMock(
        side_effect=[
            [{"name": "tank", "guid": "abc123"}],
            True,
        ]
    )

    async def fake_run_command(
        args: argparse.Namespace,
        handler: Callable[[TrueNASClient], Awaitable[None]],
        require_auth: bool = True,
    ) -> None:
        await handler(client)

    monkeypatch.setattr(pool_module, "run_command", fake_run_command)

    args = argparse.Namespace(
        name="tank",
        guid=None,
        new_name=None,
        json=False,
    )

    await pool_module._cmd_pool_import(args)

    assert client.call.await_args_list == [
        call("pool.import_find", []),
        call("pool.import_pool", [{"guid": "abc123"}]),
    ]


@pytest.mark.anyio
async def test_pool_import_with_new_name(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Ensure pool import sends optional name override when provided."""
    from truenas_cli.commands import pool as pool_module

    client = AsyncMock()
    client.call = AsyncMock(
        side_effect=[
            [{"name": "tank", "guid": "abc123"}],
            True,
        ]
    )

    async def fake_run_command(
        args: argparse.Namespace,
        handler: Callable[[TrueNASClient], Awaitable[None]],
        require_auth: bool = True,
    ) -> None:
        await handler(client)

    monkeypatch.setattr(pool_module, "run_command", fake_run_command)

    args = argparse.Namespace(
        name="tank",
        guid=None,
        new_name="tank_new",
        json=False,
    )

    await pool_module._cmd_pool_import(args)

    assert client.call.await_args_list == [
        call("pool.import_find", []),
        call("pool.import_pool", [{"guid": "abc123", "name": "tank_new"}]),
    ]


@pytest.mark.anyio
async def test_pool_export_builds_options(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Ensure export command passes pool ID and options object."""
    from truenas_cli.commands import pool as pool_module

    client = AsyncMock()
    client.get_pool = AsyncMock(return_value={"id": 7, "name": "tank"})
    client.call = AsyncMock(return_value=True)

    async def fake_run_command(
        args: argparse.Namespace,
        handler: Callable[[TrueNASClient], Awaitable[None]],
        require_auth: bool = True,
    ) -> None:
        await handler(client)

    monkeypatch.setattr(pool_module, "run_command", fake_run_command)

    args = argparse.Namespace(
        pool="tank",
        force=False,
        cascade=False,
        restart_services=False,
        json=False,
    )

    await pool_module._cmd_pool_export(args)

    client.get_pool.assert_awaited_once_with("tank")
    client.call.assert_awaited_once_with("pool.export", [7, {}])


@pytest.mark.anyio
async def test_pool_export_force_sets_cascade_and_restart(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Ensure force flag cascades attachments and restarts services."""
    from truenas_cli.commands import pool as pool_module

    client = AsyncMock()
    client.get_pool = AsyncMock(return_value={"id": 9, "name": "tank"})
    client.call = AsyncMock(return_value=True)

    async def fake_run_command(
        args: argparse.Namespace,
        handler: Callable[[TrueNASClient], Awaitable[None]],
        require_auth: bool = True,
    ) -> None:
        await handler(client)

    monkeypatch.setattr(pool_module, "run_command", fake_run_command)

    args = argparse.Namespace(
        pool="tank",
        force=True,
        cascade=False,
        restart_services=False,
        json=False,
    )

    await pool_module._cmd_pool_export(args)

    client.call.assert_awaited_once_with(
        "pool.export",
        [9, {"cascade": True, "restart_services": True}],
    )


@pytest.mark.anyio
async def test_pool_delete_uses_destroy(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Ensure delete command maps to pool.export destroy option."""
    from truenas_cli.commands import pool as pool_module

    client = AsyncMock()
    client.get_pool = AsyncMock(return_value={"id": 11, "name": "tank"})
    client.call = AsyncMock(return_value=True)

    async def fake_run_command(
        args: argparse.Namespace,
        handler: Callable[[TrueNASClient], Awaitable[None]],
        require_auth: bool = True,
    ) -> None:
        await handler(client)

    monkeypatch.setattr(pool_module, "run_command", fake_run_command)

    args = argparse.Namespace(
        pool="tank",
        force=True,
        remove_data=True,
        restart_services=True,
        json=False,
    )

    await pool_module._cmd_pool_delete(args)

    client.call.assert_awaited_once_with(
        "pool.export",
        [
            11,
            {
                "destroy": True,
                "cascade": True,
                "restart_services": True,
            },
        ],
    )

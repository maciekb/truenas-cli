"""Tests for dataset CLI commands."""

import argparse
from unittest.mock import AsyncMock

import pytest


@pytest.mark.anyio
async def test_dataset_rename_calls_pool_rename(monkeypatch):
    """Ensure dataset rename uses pool.dataset.rename."""
    from truenas_cli.commands import dataset as dataset_module

    client = AsyncMock()
    client.get_datasets = AsyncMock(
        return_value=[
            {"name": "tank/data"},
            {"name": "tank/other"},
        ]
    )
    client.call = AsyncMock(return_value=True)

    async def fake_run_command(args, handler, require_auth=True):
        await handler(client)

    monkeypatch.setattr(dataset_module, "run_command", fake_run_command)

    args = argparse.Namespace(
        dataset="tank/data",
        new_name="tank/data_backup",
        recursive=True,
        json=False,
    )

    await dataset_module._cmd_dataset_rename(args)

    client.call.assert_awaited_once_with(
        "pool.dataset.rename",
        [
            "tank/data",
            {"new_name": "tank/data_backup", "recursive": True},
        ],
    )

"""
Command group registration for the TrueNAS CLI.

Each group encapsulates a related set of API calls defined in the official
TrueNAS documentation. Modules expose a ``name`` attribute (used for ordering)
and a ``register`` method that adds argparse subparsers.
"""

from __future__ import annotations

from .alerts import AlertsCommands
from .app import AppCommands
from .dataset import DatasetCommands
from .disk import DiskCommands
from .general import GeneralCommands
from .group import GroupCommands
from .nfs import NFSCommands
from .pool import PoolCommands
from .service import ServiceCommands
from .smb import SMBCommands
from .snapshot import SnapshotCommands
from .system import SystemCommands
from .user import UserCommands

COMMAND_GROUPS = [
    GeneralCommands(),
    SystemCommands(),
    PoolCommands(),
    DatasetCommands(),
    SMBCommands(),
    ServiceCommands(),
    NFSCommands(),
    SnapshotCommands(),
    DiskCommands(),
    AlertsCommands(),
    AppCommands(),
    UserCommands(),
    GroupCommands(),
]

__all__ = ["COMMAND_GROUPS"]

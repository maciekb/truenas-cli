"""Pytest configuration and fixtures for truenas-cli tests.

This module provides common fixtures for testing the CLI application,
including mock API clients, configuration, and test data.
"""

import json
from pathlib import Path
from typing import Dict, Any
from unittest.mock import Mock

import httpx
import pytest
from pytest_httpx import HTTPXMock

from truenas_cli.config import Config, ConfigManager, ProfileConfig


@pytest.fixture
def mock_config_dir(tmp_path: Path) -> Path:
    """Create a temporary configuration directory.

    Args:
        tmp_path: Pytest temporary directory fixture

    Returns:
        Path to temporary config directory
    """
    config_dir = tmp_path / ".truenas-cli"
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir


@pytest.fixture
def mock_profile_config() -> ProfileConfig:
    """Create a mock profile configuration.

    Returns:
        ProfileConfig instance with test values
    """
    return ProfileConfig(
        url="https://truenas.local",
        api_key="test-api-key-12345",
        verify_ssl=True,
        timeout=30,
    )


@pytest.fixture
def mock_config(mock_profile_config: ProfileConfig) -> Config:
    """Create a mock configuration with default profile.

    Args:
        mock_profile_config: Mock profile configuration fixture

    Returns:
        Config instance with test profile
    """
    return Config(
        active_profile="default",
        profiles={"default": mock_profile_config},
    )


@pytest.fixture
def mock_config_file(mock_config_dir: Path, mock_config: Config) -> Path:
    """Create a mock configuration file.

    Args:
        mock_config_dir: Mock config directory fixture
        mock_config: Mock config fixture

    Returns:
        Path to configuration file
    """
    config_file = mock_config_dir / "config.json"
    config_file.write_text(mock_config.model_dump_json(indent=2))
    config_file.chmod(0o600)
    return config_file


@pytest.fixture
def mock_config_manager(monkeypatch, mock_config_dir: Path) -> ConfigManager:
    """Create a ConfigManager with mocked paths.

    Args:
        monkeypatch: Pytest monkeypatch fixture
        mock_config_dir: Mock config directory fixture

    Returns:
        ConfigManager instance using temporary directory
    """
    config_mgr = ConfigManager()
    monkeypatch.setattr(config_mgr, "config_dir", mock_config_dir)
    monkeypatch.setattr(config_mgr, "config_file", mock_config_dir / "config.json")
    return config_mgr


# Sample API responses for testing
MOCK_SYSTEM_INFO = {
    "version": "TrueNAS-SCALE-24.04",
    "hostname": "truenas",
    "uptime": "12:34:56",
    "system_product": "Virtual Machine",
}

MOCK_SYSTEM_VERSION = "TrueNAS-SCALE-24.04.0"

MOCK_POOL_LIST = [
    {
        "id": 1,
        "name": "tank",
        "guid": "1234567890",
        "status": "ONLINE",
        "healthy": True,
        "topology": {
            "data": [
                {"type": "RAIDZ1", "children": [], "stats": {}},
            ],
        },
    },
    {
        "id": 2,
        "name": "backup",
        "guid": "0987654321",
        "status": "ONLINE",
        "healthy": True,
        "topology": {"data": []},
    },
]

MOCK_DATASET_LIST = [
    {
        "id": "tank",
        "name": "tank",
        "pool": "tank",
        "type": "FILESYSTEM",
        "used": {"parsed": 1073741824},
        "available": {"parsed": 10737418240},
        "compression": "lz4",
        "quota": None,
    },
    {
        "id": "tank/data",
        "name": "tank/data",
        "pool": "tank",
        "type": "FILESYSTEM",
        "used": {"parsed": 536870912},
        "available": {"parsed": 10737418240},
        "compression": "lz4",
        "quota": None,
    },
]

MOCK_NFS_SHARE_LIST = [
    {
        "id": 1,
        "path": "/mnt/tank/data",
        "comment": "Test share",
        "enabled": True,
        "networks": [],
        "hosts": [],
    },
]

MOCK_SMB_SHARE_LIST = [
    {
        "id": 1,
        "name": "data",
        "path": "/mnt/tank/data",
        "comment": "Test SMB share",
        "enabled": True,
        "guestok": False,
    },
]


@pytest.fixture
def httpx_mock_with_data(httpx_mock: HTTPXMock) -> HTTPXMock:
    """Configure HTTPXMock with common API responses.

    Args:
        httpx_mock: pytest-httpx mock fixture

    Returns:
        Configured HTTPXMock instance
    """
    # System endpoints
    httpx_mock.add_response(
        url="https://truenas.local/api/v2.0/system/info",
        json=MOCK_SYSTEM_INFO,
    )
    httpx_mock.add_response(
        url="https://truenas.local/api/v2.0/system/version",
        json=MOCK_SYSTEM_VERSION,
    )

    # Pool endpoints
    httpx_mock.add_response(
        url="https://truenas.local/api/v2.0/pool",
        json=MOCK_POOL_LIST,
    )

    # Dataset endpoints
    httpx_mock.add_response(
        url="https://truenas.local/api/v2.0/pool/dataset",
        json=MOCK_DATASET_LIST,
    )

    # Share endpoints
    httpx_mock.add_response(
        url="https://truenas.local/api/v2.0/sharing/nfs",
        json=MOCK_NFS_SHARE_LIST,
    )
    httpx_mock.add_response(
        url="https://truenas.local/api/v2.0/sharing/smb",
        json=MOCK_SMB_SHARE_LIST,
    )

    return httpx_mock


@pytest.fixture
def mock_client(httpx_mock_with_data: HTTPXMock, mock_profile_config: ProfileConfig):
    """Create a mock TrueNAS client with pre-configured responses.

    Args:
        httpx_mock_with_data: Configured HTTPXMock fixture
        mock_profile_config: Mock profile configuration

    Returns:
        TrueNASClient instance with mocked HTTP responses
    """
    from truenas_cli.client.base import TrueNASClient

    return TrueNASClient(mock_profile_config, verbose=False)


@pytest.fixture(autouse=True)
def reset_logging():
    """Reset logging configuration between tests."""
    import logging

    # Remove all handlers from root logger
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Reset level
    root_logger.setLevel(logging.WARNING)

    yield

    # Cleanup after test
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

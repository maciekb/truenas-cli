"""Shell completion utilities for dynamic value completion.

This module provides completion functions for dynamic values like pool names
and dataset paths from the TrueNAS API.
"""

from typing import List, Optional

from truenas_cli.client.base import TrueNASClient
from truenas_cli.client.exceptions import TrueNASError
from truenas_cli.config import ConfigManager


def complete_pool_names(incomplete: str) -> List[str]:
    """Complete pool names from TrueNAS API.

    Args:
        incomplete: Partial pool name being typed

    Returns:
        List of matching pool names
    """
    try:
        config_mgr = ConfigManager()
        config, profile_config, _ = config_mgr.get_profile_or_active(None)
        client = TrueNASClient(profile_config, verbose=False)

        # Get pool list
        pools = client.get("pool")

        # Extract pool names
        pool_names = [pool.get("name", "") for pool in pools if isinstance(pool, dict)]

        # Filter by incomplete prefix
        if incomplete:
            return [name for name in pool_names if name.startswith(incomplete)]
        return pool_names

    except (TrueNASError, Exception):
        # Return empty list if API call fails
        # Completion should never break the CLI
        return []


def complete_dataset_paths(incomplete: str) -> List[str]:
    """Complete dataset paths from TrueNAS API.

    Args:
        incomplete: Partial dataset path being typed

    Returns:
        List of matching dataset paths
    """
    try:
        config_mgr = ConfigManager()
        config, profile_config, _ = config_mgr.get_profile_or_active(None)
        client = TrueNASClient(profile_config, verbose=False)

        # Get dataset list
        datasets = client.get("pool/dataset")

        # Extract dataset names
        dataset_names = [
            dataset.get("name", "") for dataset in datasets if isinstance(dataset, dict)
        ]

        # Filter by incomplete prefix
        if incomplete:
            return [name for name in dataset_names if name.startswith(incomplete)]
        return dataset_names

    except (TrueNASError, Exception):
        # Return empty list if API call fails
        return []


def complete_profile_names(incomplete: str) -> List[str]:
    """Complete profile names from configuration.

    Args:
        incomplete: Partial profile name being typed

    Returns:
        List of matching profile names
    """
    try:
        config_mgr = ConfigManager()
        config = config_mgr.load()

        profile_names = list(config.profiles.keys())

        # Filter by incomplete prefix
        if incomplete:
            return [name for name in profile_names if name.startswith(incomplete)]
        return profile_names

    except Exception:
        return []


def complete_share_types(incomplete: str) -> List[str]:
    """Complete share type names.

    Args:
        incomplete: Partial share type being typed

    Returns:
        List of matching share types
    """
    share_types = ["nfs", "smb", "iscsi"]

    if incomplete:
        return [st for st in share_types if st.startswith(incomplete)]
    return share_types


def complete_output_formats(incomplete: str) -> List[str]:
    """Complete output format names.

    Args:
        incomplete: Partial format name being typed

    Returns:
        List of matching output formats
    """
    formats = ["table", "json", "yaml", "plain"]

    if incomplete:
        return [fmt for fmt in formats if fmt.startswith(incomplete)]
    return formats

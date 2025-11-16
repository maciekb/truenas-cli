"""TrueNAS API client package.

This package provides the HTTP client for interacting with the TrueNAS SCALE API,
including models, exceptions, and the base client implementation.
"""

# Import only exceptions and models to avoid circular imports
# TrueNASClient should be imported directly from truenas_cli.client.base
from truenas_cli.client.exceptions import (
    APIError,
    AuthenticationError,
    ConfigurationError,
    NetworkError,
    RateLimitError,
    TrueNASError,
)
from truenas_cli.client.models import SystemInfo, SystemVersion

__all__ = [
    "TrueNASError",
    "AuthenticationError",
    "ConfigurationError",
    "APIError",
    "NetworkError",
    "RateLimitError",
    "SystemInfo",
    "SystemVersion",
]

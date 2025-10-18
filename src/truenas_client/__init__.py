"""TrueNAS API Client Package"""

from .client import (
    TrueNASAPIError,
    TrueNASAuthenticationError,
    TrueNASClient,
    TrueNASClientError,
    TrueNASConnectionError,
    TrueNASNotFoundError,
    TrueNASResponseError,
    TrueNASTimeoutError,
    TrueNASValidationError,
)

__version__ = "0.1.0"
__all__ = [
    "TrueNASClient",
    "TrueNASClientError",
    "TrueNASConnectionError",
    "TrueNASAPIError",
    "TrueNASAuthenticationError",
    "TrueNASValidationError",
    "TrueNASNotFoundError",
    "TrueNASTimeoutError",
    "TrueNASResponseError",
]

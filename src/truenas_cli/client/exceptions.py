"""Custom exceptions for TrueNAS CLI.

This module defines a hierarchy of exceptions for different error conditions,
making it easier to handle specific error types and provide helpful messages.
"""


class TrueNASError(Exception):
    """Base exception for all TrueNAS CLI errors.

    All custom exceptions in the CLI inherit from this base class,
    making it easy to catch all CLI-related errors if needed.
    """

    pass


class ConfigurationError(TrueNASError):
    """Exception raised for configuration-related errors.

    This includes:
    - Missing or invalid configuration files
    - Missing required configuration values
    - Invalid profile names
    - Configuration validation errors

    Exit code: 3
    """

    pass


class AuthenticationError(TrueNASError):
    """Exception raised for authentication failures.

    This includes:
    - Invalid API keys
    - Expired credentials
    - Insufficient permissions
    - 401 Unauthorized responses

    Exit code: 2
    """

    pass


class APIError(TrueNASError):
    """Exception raised for API-related errors.

    This includes:
    - 4xx client errors (except 401)
    - 5xx server errors
    - Invalid API responses
    - Resource not found (404)
    - Validation errors (422)

    Attributes:
        status_code: HTTP status code if available
        response_body: Response body if available
    """

    def __init__(
        self,
        message: str,
        status_code: int | None = None,
        response_body: str | None = None,
    ):
        """Initialize API error.

        Args:
            message: Error message
            status_code: HTTP status code
            response_body: Response body content
        """
        super().__init__(message)
        self.status_code = status_code
        self.response_body = response_body


class NetworkError(TrueNASError):
    """Exception raised for network-related errors.

    This includes:
    - Connection timeouts
    - DNS resolution failures
    - Connection refused
    - SSL/TLS errors
    - Network unreachable
    """

    pass


class RateLimitError(TrueNASError):
    """Exception raised when API rate limit is exceeded.

    This is a special case of APIError for 429 Too Many Requests responses.

    Attributes:
        retry_after: Number of seconds to wait before retrying
    """

    def __init__(self, message: str, retry_after: int | None = None):
        """Initialize rate limit error.

        Args:
            message: Error message
            retry_after: Seconds to wait before retry (from Retry-After header)
        """
        super().__init__(message)
        self.retry_after = retry_after


class ValidationError(TrueNASError):
    """Exception raised for data validation errors.

    This includes:
    - Invalid request parameters
    - Schema validation failures
    - Type conversion errors
    """

    pass

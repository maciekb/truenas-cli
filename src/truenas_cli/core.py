"""Core utilities for the TrueNAS CLI implementation.

This module provides shared infrastructure for CLI commands:
    - Credential management and resolution
    - Client initialization from CLI arguments
    - Authentication handling
    - Error handling with context-specific messages
    - Logging configuration
    - Output formatting utilities

All command modules should use the :func:`run_command` function to ensure
consistent error handling, logging, and cleanup behavior.

Architecture:
    CLI Command Flow:
        CLI Parser (cli.py)
            ↓
        Command Module (commands/*.py)
            ↓
        run_command() [this module]
            ↓
        TrueNASClient
            ↓
        TrueNAS API (WebSocket/DDP)

Command Implementation Pattern:
    1. Define handler function taking TrueNASClient
    2. Call run_command(args, handler)
    3. run_command handles: connection, auth, logging, errors, cleanup

Error Handling:
    TrueNASConnectionError: Connection/network issues
    TrueNASAuthenticationError: Authentication failures
    TrueNASAPIError: API returned errors
    TrueNASValidationError: Input/output validation failures
    TrueNASNotFoundError: Resource not found
    ValueError: User input validation

Environment Variables:
    TRUENAS_HOST: TrueNAS hostname/IP
    TRUENAS_PORT: WebSocket port (default: 443)
    TRUENAS_API_KEY: API key for authentication
    TRUENAS_USERNAME: Username (if not using API key)
    TRUENAS_PASSWORD: Password (if not using API key)
    TRUENAS_NO_SSL: Disable SSL (default: enabled)
    TRUENAS_INSECURE: Skip SSL verification for self-signed certs

Examples:
    >>> # Direct usage in command handler
    >>> async def my_handler(client):
    ...     info = await client.system_info()
    ...     print(f"Hostname: {info['hostname']}")
    >>> await run_command(args, my_handler)
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import sys
from collections.abc import Awaitable
from typing import Any, Callable

from pydantic import BaseModel, Field, ValidationError, field_validator

from truenas_client import (
    TrueNASAPIError,
    TrueNASAuthenticationError,
    TrueNASClient,
    TrueNASClientError,
    TrueNASConnectionError,
    TrueNASNotFoundError,
    TrueNASValidationError,
)

from .logging_config import configure_logging

CommandHandler = Callable[[TrueNASClient], Awaitable[None]]


class Credentials(BaseModel):
    """Container for resolved credential sources."""

    api_key: str | None = Field(default=None)
    username: str | None = Field(default=None)
    password: str | None = Field(default=None)

    @field_validator("api_key", "username", "password")
    @classmethod
    def strip_empty_strings(cls, value: str | None) -> str | None:
        """Normalise empty string values to ``None``."""

        if value is not None:
            stripped = value.strip()
            if not stripped:
                return None
            return stripped
        return value


def resolve_credentials(args: argparse.Namespace) -> Credentials:
    """Gather credentials from CLI arguments or environment variables.

    Resolves authentication credentials with precedence:
    CLI arguments > Environment variables > None

    Args:
        args: Parsed command-line arguments containing:
            - api_key: Optional API key from --api-key flag
            - username: Optional username from --username flag
            - password: Optional password from --password flag

    Returns:
        Credentials object with resolved api_key, username, and password.
        Any field can be None if not provided.

    Environment Variables (checked if not in args):
        - TRUENAS_API_KEY: API key
        - TRUENAS_USERNAME: Username
        - TRUENAS_PASSWORD: Password

    Example:
        >>> credentials = resolve_credentials(args)
        >>> if credentials.api_key:
        ...     print("Using API key auth")
    """
    try:
        return Credentials(
            api_key=(getattr(args, "api_key", None) or os.getenv("TRUENAS_API_KEY")),
            username=(getattr(args, "username", None) or os.getenv("TRUENAS_USERNAME")),
            password=(getattr(args, "password", None) or os.getenv("TRUENAS_PASSWORD")),
        )
    except ValidationError as exc:  # pragma: no cover - defensive path
        raise TrueNASClientError(f"Invalid credential configuration: {exc}") from exc


async def authenticate_client(client: TrueNASClient, args: argparse.Namespace) -> None:
    """Authenticate client with API key or username/password.

    Resolves credentials from CLI args or environment variables and
    authenticates the client. Prefers API key over username/password.

    Args:
        client: TrueNASClient instance to authenticate
        args: Parsed command-line arguments with auth options

    Raises:
        TrueNASClientError: If no credentials provided or auth fails
        TrueNASAuthenticationError: If credentials are invalid

    Example:
        >>> await authenticate_client(client, args)
    """
    credentials = resolve_credentials(args)

    if not credentials.api_key and not (credentials.username and credentials.password):
        raise TrueNASClientError(
            "Either --api-key or --username/--password required "
            "(or set corresponding TRUENAS_* env vars)."
        )

    await client.ensure_authenticated(
        api_key=credentials.api_key,
        username=credentials.username,
        password=credentials.password,
    )


def get_client_from_args(args: argparse.Namespace) -> TrueNASClient:
    """Create TrueNAS client from command line arguments.

    Resolves connection parameters from CLI args or environment variables.
    Precedence: CLI args > environment variables > defaults

    Args:
        args: Parsed command-line arguments containing connection options:
            - host: TrueNAS host (TRUENAS_HOST env var)
            - port: WebSocket port (TRUENAS_PORT env var, default 443)
            - no_ssl: Disable SSL (TRUENAS_NO_SSL env var)
            - insecure: Skip SSL verification (TRUENAS_INSECURE env var)

    Returns:
        Configured TrueNASClient instance

    Raises:
        SystemExit: If host is not provided via args or environment

    Example:
        >>> parser = argparse.ArgumentParser()
        >>> parser.add_argument("--host")
        >>> parser.add_argument("--port", type=int)
        >>> args = parser.parse_args(["--host", "truenas.local"])
        >>> client = get_client_from_args(args)
    """
    host = getattr(args, "host", None) or os.getenv("TRUENAS_HOST")
    port = getattr(args, "port", None) or int(os.getenv("TRUENAS_PORT", "443"))
    no_ssl = (
        getattr(args, "no_ssl", False)
        or os.getenv("TRUENAS_NO_SSL", "false").lower() == "true"
    )
    insecure = (
        getattr(args, "insecure", False)
        or os.getenv("TRUENAS_INSECURE", "false").lower() == "true"
    )

    if not host:
        raise SystemExit(
            "Error: --host is required (or set TRUENAS_HOST in environment)"
        )

    return TrueNASClient(
        host=host,
        port=port,
        use_ssl=not no_ssl,
        verify_ssl=not insecure,
    )


async def run_command(
    args: argparse.Namespace,
    handler: CommandHandler,
    *,
    require_auth: bool = True,
) -> None:
    """Execute a command ensuring connection, authentication, and error handling.

    Handles all phases of command execution:
    1. Client creation from CLI arguments
    2. Logging configuration
    3. Connection and authentication (optional)
    4. Command execution with error handling
    5. Resource cleanup

    Args:
        args: Parsed command-line arguments
        handler: Async function to execute the command
        require_auth: If True, authenticate before running handler

    Raises:
        SystemExit: On any error (exit code 1)
    """
    client = get_client_from_args(args)
    configure_logging(getattr(args, "verbose", 0), getattr(args, "quiet", False))
    logger = logging.getLogger(__name__)

    try:
        if require_auth:
            await authenticate_client(client, args)
        else:
            await client.ensure_connected()

        await handler(client)
    except TrueNASConnectionError as exc:
        logger.error("Connection error: %s", exc)
        print(
            (
                "Connection Error: Could not connect to TrueNAS at "
                f"{client.host}:{client.port}\n"
            )
            + f"Details: {exc}\n\n"
            + "Troubleshooting:\n"
            + "  - Verify TRUENAS_HOST is correct\n"
            + "  - Check if TrueNAS is running and accessible\n"
            + "  - Try using --insecure flag if using self-signed certificates",
            file=sys.stderr,
        )
        raise SystemExit(1) from exc
    except TrueNASAuthenticationError as exc:
        logger.error("Authentication error: %s", exc)
        print(
            f"Authentication Error: {exc}\n\n"
            f"Troubleshooting:\n"
            f"  - Verify your API key or username/password\n"
            f"  - Check that credentials are set correctly",
            file=sys.stderr,
        )
        raise SystemExit(1) from exc
    except TrueNASNotFoundError as exc:
        logger.error("Resource not found: %s", exc)
        print(f"Not Found: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
    except TrueNASValidationError as exc:
        logger.error("Validation error: %s", exc)
        print(f"Validation Error: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
    except TrueNASAPIError as exc:
        logger.error("API error: %s", exc)
        try:
            message = json.dumps(exc.args[0], indent=2, default=str)
            print(f"API Error:\n{message}", file=sys.stderr)
        except (ValueError, TypeError):
            print(f"API Error: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
    except TrueNASClientError as exc:
        logger.error("Client error: %s", exc)
        print(f"Error: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
    except ValueError as exc:
        logger.error("Validation error: %s", exc)
        print(f"Error: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
    except Exception as exc:  # pragma: no cover - unexpected branch
        logger.exception("Unexpected error while executing command")
        print(
            f"Unexpected Error: {exc}\n\n"
            f"This is a bug. Please report it at: "
            f"https://github.com/truenas/api-client/issues",
            file=sys.stderr,
        )
        raise SystemExit(1) from exc
    finally:
        try:
            await client.disconnect()
        except asyncio.CancelledError:
            pass
        except Exception:
            logger.debug("Error during disconnect", exc_info=True)


def format_size(value: Any) -> str:
    """Format size value from API response.

    Converts byte values to human-readable format (B, KiB, MiB, GiB, TiB, PiB).

    Args:
        value: Value to format. Can be:
            - int/float: Bytes
            - str: Numeric string or "parsed" size string
            - dict: With 'value', 'parsed', or 'rawvalue' key
            - None: Returns "N/A"

    Returns:
        Formatted size string (e.g., "1.50 GiB") or "N/A"

    Example:
        >>> format_size(1024*1024*1024)
        '1.00 GiB'
        >>> format_size({"parsed": "512 MiB"})
        '512 MiB'
    """
    if value is None:
        return "N/A"

    if isinstance(value, dict):
        if "value" in value:
            return value.get("value", "N/A")
        if "parsed" in value:
            return value.get("parsed", "N/A")

    if isinstance(value, str):
        try:
            val = float(value)
        except (ValueError, TypeError):
            return value
    elif isinstance(value, (int, float)):
        val = float(value)
    else:
        return str(value)

    units = ["B", "KiB", "MiB", "GiB", "TiB", "PiB"]
    for unit in units:
        if val < 1024:
            if val == int(val):
                return f"{int(val)} {unit}"
            return f"{val:.2f} {unit}"
        val /= 1024
    return f"{val:.2f} PiB"


def safe_get(
    obj: Any,
    key: Any,
    default: Any = None,
) -> Any:
    """Safely get value from dict-like object.

    Safely retrieves a value from an object with default fallback if the key
    doesn't exist or the object is None/not a dict.

    Args:
        obj: Object to get value from (typically a dict)
        key: Key to look up
        default: Default value to return if key not found or obj is None

    Returns:
        Value at obj[key] if it exists and obj is a dict, else default

    Example:
        >>> safe_get({"name": "tank"}, "name")
        'tank'
        >>> safe_get(None, "name", "unknown")
        'unknown'
        >>> safe_get({"name": "tank"}, "missing", "N/A")
        'N/A'
    """
    if obj is None:
        return default
    if isinstance(obj, dict):
        return obj.get(key, default)
    return default

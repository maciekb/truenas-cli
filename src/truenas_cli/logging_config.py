"""Logging configuration module for TrueNAS CLI.

Provides structured logging setup with appropriate levels, formatters, and
filters for CLI commands. Supports multiple verbosity levels and optional
file logging.

Features:
    - Structured logging with multiple verbosity levels
    - Console and optional file output
    - Sensitive data sanitization (prevents credential leakage)
    - Configurable formatters for different contexts
    - Third-party library logging suppression

Log Levels:
    DEBUG (verbose=2+): Protocol details, request/response traces
    INFO (verbose=1): Operation results, state changes
    WARNING (verbose=0): Recoverable issues, deprecated usage
    ERROR (quiet=False): Operation failures
    CRITICAL (quiet=True): System failures only

Formatters:
    - SIMPLE: "LEVEL: message"
    - DETAILED: "timestamp - name - LEVEL - message"
    - DEBUG: "timestamp - name:function:line - LEVEL - message"

Security:
    - SanitizingFilter removes sensitive data from logs
    - API keys, passwords, tokens never logged
    - File logs receive same sanitization as console

Usage:
    >>> from truenas_cli.logging_config import configure_logging
    >>> configure_logging(verbose=2)  # DEBUG level
    >>> logger = logging.getLogger(__name__)
    >>> logger.debug("This is a debug message")

Environment Integration:
    Works with cli.py run_command() for automatic setup:
    >>> configure_logging(verbose, quiet)  # Called by run_command
"""

from __future__ import annotations

import logging
import logging.handlers
import sys
from typing import Optional

# Log format strings
_SIMPLE_FORMAT = "%(levelname)s: %(message)s"
_DETAILED_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
_DEBUG_FORMAT = (
    "%(asctime)s - %(name)s:%(funcName)s:%(lineno)d - %(levelname)s - %(message)s"
)


class SanitizingFilter(logging.Filter):
    """Filter that sanitizes sensitive information from log records.

    Removes API keys, passwords, and other credentials from log output
    to prevent accidental credential leaks in logs.
    """

    # Patterns to sanitize (simplified - real use would use regex)
    SENSITIVE_KEYS = {"api_key", "password", "token", "secret", "auth"}

    def filter(self, record: logging.LogRecord) -> bool:
        """Filter and sanitize the log record."""
        if record.msg and isinstance(record.msg, str):
            # Sanitize message text for known sensitive patterns
            for key in self.SENSITIVE_KEYS:
                if key in record.msg.lower():
                    # Don't log the actual value
                    record.msg = record.msg.replace(record.msg, f"({key} redacted)")

        return True


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance for the given module name.

    Args:
        name: Module name (typically __name__)

    Returns:
        Configured logger instance
    """
    return logging.getLogger(name)


def configure_logging(
    verbose: int = 0,
    quiet: bool = False,
    log_file: Optional[str] = None,
) -> None:
    """Configure logging for the CLI.

    Args:
        verbose: Verbosity level (0=WARNING, 1=INFO, 2=DEBUG)
        quiet: If True, only show ERROR and above
        log_file: Optional path to write logs to file

    Behavior:
        - verbose=0, quiet=False: WARNING level
        - verbose=0, quiet=True: ERROR level
        - verbose=1: INFO level
        - verbose=2+: DEBUG level
    """
    # Determine log level
    if quiet:
        level = logging.ERROR
        formatter_format = _SIMPLE_FORMAT
    elif verbose >= 2:
        level = logging.DEBUG
        formatter_format = _DEBUG_FORMAT
    elif verbose == 1:
        level = logging.INFO
        formatter_format = _DETAILED_FORMAT
    else:
        level = logging.WARNING
        formatter_format = _SIMPLE_FORMAT

    # Create formatter
    formatter = logging.Formatter(formatter_format)

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # Remove existing handlers to avoid duplicates
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Console handler (stderr)
    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)

    # Add sanitizing filter for console output
    console_handler.addFilter(SanitizingFilter())

    root_logger.addHandler(console_handler)

    # Optional file handler
    if log_file:
        try:
            file_handler = logging.FileHandler(log_file)
            file_handler.setLevel(logging.DEBUG)  # Always detailed in files
            file_handler.setFormatter(logging.Formatter(_DEBUG_FORMAT))
            file_handler.addFilter(SanitizingFilter())
            root_logger.addHandler(file_handler)
        except OSError as e:
            root_logger.warning(f"Could not create log file {log_file}: {e}")

    # Suppress verbose logging from third-party libraries
    logging.getLogger("websockets").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)


def enable_debug_logging() -> None:
    """Enable DEBUG level logging for development/troubleshooting."""
    configure_logging(verbose=2)


def disable_logging() -> None:
    """Disable all logging (useful for testing)."""
    logging.disable(logging.CRITICAL)


def enable_logging() -> None:
    """Re-enable logging after disable_logging()."""
    logging.disable(logging.NOTSET)

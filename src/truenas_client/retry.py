"""Retry logic for resilient API operations.

Provides retry decorators and utilities for handling transient failures
and automatic recovery.

Usage:
    >>> from truenas_client.retry import with_retry
    >>> @with_retry(max_attempts=3, delay=1.0)
    ... async def fetch_data():
    ...     return await client.system_info()
"""

from __future__ import annotations

import asyncio
import functools
import logging
from typing import Any, Awaitable, Callable, TypeVar

from .client import TrueNASConnectionError, TrueNASTimeoutError

logger = logging.getLogger(__name__)

T = TypeVar("T")


def with_retry(
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    retryable_exceptions: tuple = (TrueNASConnectionError, TrueNASTimeoutError),
) -> Callable[[Callable[..., Awaitable[T]]], Callable[..., Awaitable[T]]]:
    """Decorator for retrying async functions with exponential backoff.

    Args:
        max_attempts: Maximum number of retry attempts (default: 3)
        delay: Initial delay between retries in seconds (default: 1.0)
        backoff: Multiplier for exponential backoff (default: 2.0)
        retryable_exceptions: Tuple of exceptions that trigger retry
            (default: (TrueNASConnectionError, TrueNASTimeoutError))

    Returns:
        Decorated async function

    Behavior:
        - Tries the function up to max_attempts times
        - On failure, waits delay seconds before retry
        - Each retry multiplies delay by backoff factor
        - Non-retryable exceptions are raised immediately
        - Last attempt exception is raised if all attempts fail

    Example:
        >>> @with_retry(max_attempts=3, delay=0.5)
        ... async def get_info():
        ...     return await client.system_info()
        >>>
        >>> info = await get_info()  # Retries up to 3 times
    """

    def decorator(func: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            current_delay = delay
            last_exception: Exception | None = None

            for attempt in range(1, max_attempts + 1):
                try:
                    logger.debug(f"Attempt {attempt}/{max_attempts} for {func.__name__}")
                    return await func(*args, **kwargs)
                except retryable_exceptions as e:
                    last_exception = e
                    if attempt == max_attempts:
                        logger.error(f"All {max_attempts} attempts failed for {func.__name__}: {e}")
                        raise
                    logger.warning(
                        f"Attempt {attempt} failed for {func.__name__}: {e}. "
                        f"Retrying in {current_delay:.1f}s..."
                    )
                    await asyncio.sleep(current_delay)
                    current_delay *= backoff

            # Should not reach here, but include for type safety
            if last_exception:
                raise last_exception
            raise RuntimeError(f"Unexpected error in {func.__name__}")

        return wrapper

    return decorator


async def retry_operation(
    operation: Callable[[], Awaitable[T]],
    max_attempts: int = 3,
    delay: float = 1.0,
    operation_name: str = "operation",
) -> T:
    """Execute an operation with automatic retry on transient failures.

    Args:
        operation: Async function to execute
        max_attempts: Maximum retry attempts (default: 3)
        delay: Initial delay between retries in seconds (default: 1.0)
        operation_name: Name for logging (default: "operation")

    Returns:
        Result from the operation

    Raises:
        TrueNASConnectionError: If connection fails on all attempts
        TrueNASTimeoutError: If operation times out on all attempts
        Other exceptions are raised immediately without retry

    Example:
        >>> async def fetch():
        ...     return await client.system_info()
        >>>
        >>> info = await retry_operation(fetch, max_attempts=3)
    """
    current_delay = delay

    for attempt in range(1, max_attempts + 1):
        try:
            logger.debug(f"Attempt {attempt}/{max_attempts} for {operation_name}")
            return await operation()
        except (TrueNASConnectionError, TrueNASTimeoutError) as e:
            if attempt == max_attempts:
                logger.error(f"All {max_attempts} attempts failed for {operation_name}: {e}")
                raise
            logger.warning(
                f"Attempt {attempt} failed for {operation_name}: {e}. "
                f"Retrying in {current_delay:.1f}s..."
            )
            await asyncio.sleep(current_delay)
            current_delay *= 2.0  # Exponential backoff

    # Should never reach here, but mypy requires explicit return/raise
    raise RuntimeError(f"Unexpected exit from retry loop for {operation_name}")

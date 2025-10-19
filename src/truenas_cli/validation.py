"""Input validation utilities for TrueNAS CLI.

Provides validation functions for CLI arguments, API responses, and user inputs.
All validation functions raise appropriate exceptions with helpful messages.

Usage:
    >>> from truenas_cli.validation import validate_pool_name, validate_dataset_name
    >>> try:
    ...     validate_pool_name("tank")
    ...     validate_dataset_name("tank/data")
    ... except TrueNASValidationError as e:
    ...     print(f"Validation error: {e}")

Validation Categories:
    - Names: pool names, dataset names, share names
    - Paths: filesystem paths for shares
    - Arguments: CLI argument validation
    - Responses: API response validation
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from truenas_client import TrueNASValidationError


def validate_pool_name(name: str) -> None:
    """Validate TrueNAS pool name.

    Pool names must:
    - Not be empty
    - Contain only alphanumeric characters, underscores, and hyphens
    - Not start or end with special characters
    - Be less than 256 characters

    Args:
        name: Pool name to validate

    Raises:
        TrueNASValidationError: If pool name is invalid

    Example:
        >>> validate_pool_name("tank")  # Valid
        >>> validate_pool_name("")  # Raises
        >>> validate_pool_name("tank-1")  # Valid
    """
    if not name:
        raise TrueNASValidationError("Pool name cannot be empty")

    if len(name) > 255:
        raise TrueNASValidationError(f"Pool name too long (max 255 chars): {name}")

    # ZFS pool names: alphanumeric, underscores, hyphens, dots
    if not re.match(r"^[a-zA-Z0-9._-]+$", name):
        raise TrueNASValidationError(
            f"Invalid pool name '{name}'. "
            "Use only alphanumeric characters, underscores, hyphens, and dots."
        )

    if name[0] in "-._" or name[-1] in "-._":
        raise TrueNASValidationError(
            f"Pool name '{name}' cannot start or end with special characters."
        )


def validate_dataset_name(name: str) -> None:
    """Validate TrueNAS dataset name.

    Dataset names must:
    - Contain a pool name and dataset path separated by /
    - Each component must be a valid name (no special chars except /)
    - Not be empty or exceed limits

    Args:
        name: Full dataset name (e.g., 'tank/mydata')

    Raises:
        TrueNASValidationError: If dataset name is invalid

    Example:
        >>> validate_dataset_name("tank/data")  # Valid
        >>> validate_dataset_name("tank/data/sub")  # Valid
        >>> validate_dataset_name("tank")  # Valid (just pool)
        >>> validate_dataset_name("")  # Raises
    """
    if not name:
        raise TrueNASValidationError("Dataset name cannot be empty")

    if len(name) > 255:
        raise TrueNASValidationError(f"Dataset name too long (max 255 chars): {name}")

    # Split into components
    components = name.split("/")

    if not components[0]:
        raise TrueNASValidationError(
            f"Dataset name '{name}' must start with a pool name"
        )

    # Validate each component
    for i, component in enumerate(components):
        if not component:
            if i == 0:
                raise TrueNASValidationError(
                    f"Dataset name '{name}' cannot start with /"
                )
            raise TrueNASValidationError(
                f"Dataset name '{name}' has empty component (consecutive slashes)"
            )

        # Component validation: alphanumeric, underscores, hyphens, dots
        if not re.match(r"^[a-zA-Z0-9._-]+$", component):
            raise TrueNASValidationError(
                f"Invalid dataset component '{component}' in '{name}'. "
                "Use only alphanumeric characters, underscores, hyphens, and dots."
            )


def validate_share_name(name: str) -> None:
    """Validate share name.

    Share names must:
    - Not be empty
    - Not exceed 80 characters
    - Not contain certain special characters

    Args:
        name: Share name to validate

    Raises:
        TrueNASValidationError: If share name is invalid
    """
    if not name:
        raise TrueNASValidationError("Share name cannot be empty")

    if len(name) > 80:
        raise TrueNASValidationError(f"Share name too long (max 80 chars): {name}")

    # Windows share name restrictions
    invalid_chars = r'["/\\:*?<>|]'
    if re.search(invalid_chars, name):
        raise TrueNASValidationError(
            f"Share name '{name}' contains invalid characters. "
            'Avoid: " / \\ : * ? < > |'
        )


def validate_path(path: str) -> None:
    """Validate filesystem path.

    Args:
        path: Filesystem path to validate (e.g., '/mnt/tank/data')

    Raises:
        TrueNASValidationError: If path is invalid
    """
    if not path:
        raise TrueNASValidationError("Path cannot be empty")

    if not path.startswith("/"):
        raise TrueNASValidationError(f"Path '{path}' must be absolute (start with /)")

    if len(path) > 4096:
        raise TrueNASValidationError(f"Path too long (max 4096 chars): {path}")


def validate_response_dict(
    response: Any,
    expected_keys: list[str] | None = None,
    context: str = "API response",
) -> dict[str, Any]:
    """Validate that response is a dictionary with expected keys.

    Args:
        response: Response to validate
        expected_keys: List of keys that should exist in response (optional)
        context: Context string for error messages (e.g., "system.info response")

    Returns:
        The validated dictionary

    Raises:
        TrueNASValidationError: If response is not a dict or missing keys

    Example:
        >>> response = await client.system_info()
        >>> validated = validate_response_dict(
        ...     response,
        ...     expected_keys=["hostname", "version"],
        ...     context="system.info response"
        ... )
    """
    if not isinstance(response, dict):
        raise TrueNASValidationError(
            f"{context}: Expected dictionary, got {type(response).__name__}"
        )

    if expected_keys:
        missing = [key for key in expected_keys if key not in response]
        if missing:
            raise TrueNASValidationError(
                f"{context}: Missing expected keys: {', '.join(missing)}"
            )

    return response


def validate_response_list(
    response: Any,
    context: str = "API response",
) -> list[Any]:
    """Validate that response is a list.

    Args:
        response: Response to validate
        context: Context string for error messages

    Returns:
        The validated list

    Raises:
        TrueNASValidationError: If response is not a list
    """
    if not isinstance(response, list):
        raise TrueNASValidationError(
            f"{context}: Expected list, got {type(response).__name__}"
        )

    return response


def validate_required_arg(
    value: str | None,
    arg_name: str,
) -> str:
    """Validate that a required argument was provided.

    Args:
        value: Argument value (can be None)
        arg_name: Argument name for error message

    Returns:
        The validated value

    Raises:
        TrueNASValidationError: If value is None or empty
    """
    if not value:
        raise TrueNASValidationError(f"Required argument '{arg_name}' not provided")

    return value


def validate_choice(
    value: str,
    choices: list[str],
    arg_name: str,
) -> str:
    """Validate that value is one of allowed choices.

    Args:
        value: Value to validate
        choices: List of allowed values
        arg_name: Argument name for error message

    Returns:
        The validated value

    Raises:
        TrueNASValidationError: If value not in choices
    """
    if value not in choices:
        raise TrueNASValidationError(
            f"Invalid value for {arg_name}: '{value}'. "
            f"Must be one of: {', '.join(choices)}"
        )

    return value


def validate_positive_int(
    value: int | None,
    arg_name: str,
    allow_none: bool = False,
) -> int | None:
    """Validate that value is a positive integer.

    Args:
        value: Value to validate
        arg_name: Argument name for error message
        allow_none: If True, None is acceptable

    Returns:
        The validated value

    Raises:
        TrueNASValidationError: If value is invalid
    """
    if value is None:
        if allow_none:
            return None
        raise TrueNASValidationError(f"Required argument '{arg_name}' not provided")

    if not isinstance(value, int):
        raise TrueNASValidationError(
            f"Argument '{arg_name}' must be an integer, got {type(value).__name__}"
        )

    if value <= 0:
        raise TrueNASValidationError(
            f"Argument '{arg_name}' must be positive, got {value}"
        )

    return value


def parse_json_argument(value: str, *, name: str, allow_file: bool = True) -> Any:
    """Parse JSON argument and support @file syntax for convenience.

    Args:
        value: Raw CLI argument supplied by the user.
        name: Logical argument name used in error messages (e.g., ``\"attributes\"``).
        allow_file: When True, ``@<path>`` loads JSON from the specified file.

    Returns:
        The parsed JSON object (dict/list/primitive).

    Raises:
        TrueNASValidationError: If the argument is empty, the file cannot be read,
            or the content is not valid JSON.
    """
    if value is None or not str(value).strip():
        raise TrueNASValidationError(f"{name} cannot be empty")

    raw = value.strip()
    source_desc = "provided string"

    if allow_file and raw.startswith("@"):
        file_path = Path(raw[1:])
        if not file_path.exists():
            raise TrueNASValidationError(
                f"{name}: File '{file_path}' not found. "
                "Provide JSON directly or use @<path>."
            )
        try:
            raw = file_path.read_text(encoding="utf-8")
        except OSError as exc:
            raise TrueNASValidationError(
                f"{name}: Unable to read file '{file_path}': {exc}"
            ) from exc
        source_desc = f"file '{file_path}'"

    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise TrueNASValidationError(
            f"{name}: Invalid JSON in {source_desc}: {exc.msg} "
            f"(line {exc.lineno}, column {exc.colno})"
        ) from exc

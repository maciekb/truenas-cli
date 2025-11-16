"""Date and time formatting utilities for TrueNAS CLI.

This module provides consistent formatting for datetime values across all commands,
handling various input formats from the TrueNAS API including MongoDB Extended JSON
format and ISO 8601 timestamps.
"""

from datetime import datetime, timezone
from typing import Any, Optional, Union


def parse_truenas_datetime(value: Any) -> Optional[datetime]:
    """Parse datetime from various TrueNAS API formats.

    The TrueNAS API returns dates in MongoDB Extended JSON format:
    {'$date': 1763283706000} - milliseconds since Unix epoch

    This function also handles:
    - ISO 8601 strings
    - Unix timestamps (seconds)
    - datetime objects (passthrough)
    - None/null values

    Args:
        value: Datetime value in various formats

    Returns:
        Parsed datetime object in UTC, or None if value is None/invalid

    Examples:
        >>> parse_truenas_datetime({'$date': 1763283706000})
        datetime.datetime(2025, 11, 16, 9, 15, 6, tzinfo=datetime.timezone.utc)

        >>> parse_truenas_datetime('2025-11-16T09:15:06Z')
        datetime.datetime(2025, 11, 16, 9, 15, 6, tzinfo=datetime.timezone.utc)

        >>> parse_truenas_datetime(1763283706)
        datetime.datetime(2025, 11, 16, 9, 15, 6, tzinfo=datetime.timezone.utc)

        >>> parse_truenas_datetime(None)
        None
    """
    if value is None:
        return None

    # Already a datetime object
    if isinstance(value, datetime):
        # Ensure UTC timezone
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

    # MongoDB Extended JSON format: {'$date': milliseconds}
    if isinstance(value, dict) and '$date' in value:
        try:
            timestamp_ms = value['$date']
            # Convert milliseconds to seconds
            timestamp_sec = timestamp_ms / 1000.0
            return datetime.fromtimestamp(timestamp_sec, tz=timezone.utc)
        except (ValueError, TypeError, KeyError):
            return None

    # ISO 8601 string format
    if isinstance(value, str):
        try:
            # Try parsing with timezone info
            if value.endswith('Z'):
                # UTC timezone
                dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
            elif '+' in value or value.count('-') > 2:
                # Has timezone offset
                dt = datetime.fromisoformat(value)
            else:
                # No timezone, assume UTC
                dt = datetime.fromisoformat(value).replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc)
        except (ValueError, AttributeError):
            return None

    # Unix timestamp (seconds)
    if isinstance(value, (int, float)):
        try:
            # Distinguish between seconds and milliseconds
            # Timestamps after year 2286 would be > 10^10 in seconds
            if value > 10_000_000_000:
                # Likely milliseconds
                timestamp_sec = value / 1000.0
            else:
                # Likely seconds
                timestamp_sec = float(value)
            return datetime.fromtimestamp(timestamp_sec, tz=timezone.utc)
        except (ValueError, OSError):
            # Invalid timestamp
            return None

    # Unrecognized format
    return None


def format_datetime(
    value: Any,
    format_type: str = "human",
    timezone_name: Optional[str] = None,
) -> str:
    """Format datetime value for display.

    Args:
        value: Datetime value to format (various formats supported)
        format_type: Output format type:
            - "human": Human-readable format (default)
                       "2025-11-16 09:15:06 UTC"
            - "iso": ISO 8601 format with timezone
                     "2025-11-16T09:15:06+00:00"
            - "compact": Compact format without timezone
                         "2025-11-16 09:15"
            - "date": Date only
                      "2025-11-16"
            - "time": Time only with timezone
                      "09:15:06 UTC"
            - "relative": Relative time (not implemented yet)
                          "2 hours ago"
        timezone_name: Optional timezone name for display (e.g., "Europe/Warsaw")
                      If provided, converts to that timezone for display

    Returns:
        Formatted datetime string, or "N/A" if value is None/invalid

    Examples:
        >>> value = {'$date': 1763283706000}
        >>> format_datetime(value)
        '2025-11-16 09:15:06 UTC'

        >>> format_datetime(value, format_type="iso")
        '2025-11-16T09:15:06+00:00'

        >>> format_datetime(value, format_type="compact")
        '2025-11-16 09:15'

        >>> format_datetime(value, format_type="date")
        '2025-11-16'

        >>> format_datetime(None)
        'N/A'
    """
    # Parse the datetime
    dt = parse_truenas_datetime(value)

    if dt is None:
        return "N/A"

    # Convert to specified timezone if provided
    if timezone_name:
        try:
            import zoneinfo
            tz = zoneinfo.ZoneInfo(timezone_name)
            dt = dt.astimezone(tz)
            tz_display = timezone_name
        except Exception:
            # Fallback to UTC if timezone conversion fails
            tz_display = "UTC"
    else:
        tz_display = "UTC"

    # Format based on type
    if format_type == "iso":
        return dt.isoformat()

    elif format_type == "compact":
        # Compact format without seconds and timezone
        return dt.strftime("%Y-%m-%d %H:%M")

    elif format_type == "date":
        # Date only
        return dt.strftime("%Y-%m-%d")

    elif format_type == "time":
        # Time only with timezone
        return dt.strftime(f"%H:%M:%S {tz_display}")

    elif format_type == "relative":
        # Relative time (future enhancement)
        # For now, fallback to human format
        # TODO: Implement relative time formatting (e.g., "2 hours ago")
        return format_datetime(value, format_type="human", timezone_name=timezone_name)

    else:  # "human" (default)
        # Human-readable format with timezone
        return dt.strftime(f"%Y-%m-%d %H:%M:%S {tz_display}")


def format_uptime(seconds: Optional[float]) -> str:
    """Format uptime in seconds to human-readable format.

    Args:
        seconds: Uptime in seconds

    Returns:
        Human-readable uptime string

    Examples:
        >>> format_uptime(918.231651558)
        '15m 18s'

        >>> format_uptime(3665.5)
        '1h 1m 5s'

        >>> format_uptime(90061.2)
        '1d 1h 1m'

        >>> format_uptime(None)
        'N/A'
    """
    if seconds is None:
        return "N/A"

    try:
        seconds = int(seconds)
    except (ValueError, TypeError):
        return "N/A"

    if seconds < 0:
        return "N/A"

    # Calculate time components
    days = seconds // 86400
    hours = (seconds % 86400) // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60

    # Build formatted string based on magnitude
    parts = []

    if days > 0:
        parts.append(f"{days}d")
    if hours > 0 or days > 0:
        parts.append(f"{hours}h")
    if minutes > 0 or hours > 0 or days > 0:
        parts.append(f"{minutes}m")

    # Only show seconds if less than 1 hour
    if days == 0 and hours == 0:
        parts.append(f"{secs}s")

    return " ".join(parts) if parts else "0s"


def is_datetime_field(field_name: str, value: Any) -> bool:
    """Check if a field name and value suggest it's a datetime.

    This is a heuristic to automatically detect datetime fields based on
    common naming patterns and value formats.

    Args:
        field_name: Name of the field (e.g., "datetime", "boottime", "created_at")
        value: Value to check

    Returns:
        True if this appears to be a datetime field

    Examples:
        >>> is_datetime_field("datetime", {'$date': 1763283706000})
        True

        >>> is_datetime_field("buildtime", {'$date': 1761589266000})
        True

        >>> is_datetime_field("version", "25.10.0")
        False
    """
    # Common datetime field name patterns (case-insensitive)
    datetime_patterns = [
        'datetime', 'date', 'time',
        'created', 'updated', 'modified',
        'started', 'finished', 'completed',
        'boot', 'build',
        'timestamp', 'ts',
    ]

    # Check field name
    field_lower = field_name.lower()
    has_datetime_name = any(pattern in field_lower for pattern in datetime_patterns)

    # Check value format
    has_datetime_value = False

    if isinstance(value, dict) and '$date' in value:
        has_datetime_value = True
    elif isinstance(value, datetime):
        has_datetime_value = True
    elif isinstance(value, str):
        # Check if it looks like ISO 8601
        if 'T' in value or (value.count('-') >= 2 and ':' in value):
            has_datetime_value = True

    return has_datetime_name and has_datetime_value

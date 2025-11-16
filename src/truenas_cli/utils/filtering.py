"""Output filtering utilities for CLI commands.

This module provides simple expression-based filtering for list outputs.
Supports filtering by field values using simple operators.
"""

import operator
import re
from typing import Any, Dict, List, Callable


class FilterExpression:
    """Parse and evaluate filter expressions.

    Supports:
    - field=value: Exact match
    - field!=value: Not equal
    - field>value: Greater than (numeric)
    - field<value: Less than (numeric)
    - field>=value: Greater than or equal (numeric)
    - field<=value: Less than or equal (numeric)
    - field~value: Contains (substring match, case-insensitive)
    """

    OPERATORS: Dict[str, Callable[[Any, Any], bool]] = {
        "=": operator.eq,
        "!=": operator.ne,
        ">": operator.gt,
        "<": operator.lt,
        ">=": operator.ge,
        "<=": operator.le,
    }

    def __init__(self, expression: str):
        """Initialize filter expression.

        Args:
            expression: Filter expression string (e.g., "status=ONLINE")
        """
        self.expression = expression
        self.field, self.op, self.value = self._parse()

    def _parse(self) -> tuple[str, str, str]:
        """Parse filter expression into field, operator, and value.

        Returns:
            Tuple of (field, operator, value)

        Raises:
            ValueError: If expression format is invalid
        """
        # Check for contains operator first
        if "~" in self.expression:
            parts = self.expression.split("~", 1)
            if len(parts) == 2:
                return parts[0].strip(), "~", parts[1].strip()

        # Check for two-character operators
        for op in [">=", "<=", "!="]:
            if op in self.expression:
                parts = self.expression.split(op, 1)
                if len(parts) == 2:
                    return parts[0].strip(), op, parts[1].strip()

        # Check for single-character operators
        for op in ["=", ">", "<"]:
            if op in self.expression:
                parts = self.expression.split(op, 1)
                if len(parts) == 2:
                    return parts[0].strip(), op, parts[1].strip()

        raise ValueError(
            f"Invalid filter expression: {self.expression}. "
            "Expected format: field=value, field!=value, field>value, field<value, "
            "field>=value, field<=value, or field~value"
        )

    def _get_nested_value(self, data: Dict[str, Any], field: str) -> Any:
        """Get value from nested dictionary using dot notation.

        Args:
            data: Dictionary to extract value from
            field: Field path (e.g., "status" or "config.enabled")

        Returns:
            Value at field path, or None if not found
        """
        parts = field.split(".")
        value = data

        for part in parts:
            if isinstance(value, dict):
                value = value.get(part)
            else:
                return None

        return value

    def matches(self, item: Dict[str, Any]) -> bool:
        """Check if item matches filter expression.

        Args:
            item: Dictionary to check

        Returns:
            True if item matches filter, False otherwise
        """
        value = self._get_nested_value(item, self.field)

        # Handle None values
        if value is None:
            return False

        # Convert value to string for comparison
        item_value = str(value)
        filter_value = self.value

        # Handle contains operator
        if self.op == "~":
            return filter_value.lower() in item_value.lower()

        # Try numeric comparison for numeric operators
        if self.op in [">", "<", ">=", "<="]:
            try:
                item_num = float(item_value)
                filter_num = float(filter_value)
                return self.OPERATORS[self.op](item_num, filter_num)
            except (ValueError, TypeError):
                # Fall back to string comparison
                return self.OPERATORS[self.op](item_value, filter_value)

        # String comparison for = and !=
        op_func = self.OPERATORS[self.op]
        return op_func(item_value, filter_value)


class Filter:
    """Filter list of items based on multiple expressions."""

    def __init__(self, expressions: List[str]):
        """Initialize filter with multiple expressions.

        Args:
            expressions: List of filter expression strings
        """
        self.expressions = [FilterExpression(expr) for expr in expressions]

    def apply(self, items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Apply filter to list of items.

        All expressions must match (AND logic).

        Args:
            items: List of dictionaries to filter

        Returns:
            Filtered list of items
        """
        if not self.expressions:
            return items

        filtered = items
        for expr in self.expressions:
            filtered = [item for item in filtered if expr.matches(item)]

        return filtered


def parse_filters(filter_args: List[str]) -> Filter:
    """Parse filter arguments into Filter object.

    Args:
        filter_args: List of filter expression strings

    Returns:
        Filter object ready to apply to items
    """
    return Filter(filter_args)


def filter_items(
    items: List[Dict[str, Any]], filter_expressions: List[str]
) -> List[Dict[str, Any]]:
    """Convenience function to filter items.

    Args:
        items: List of dictionaries to filter
        filter_expressions: List of filter expression strings

    Returns:
        Filtered list of items
    """
    if not filter_expressions:
        return items

    filter_obj = parse_filters(filter_expressions)
    return filter_obj.apply(items)


def sort_items(
    items: List[Dict[str, Any]], sort_key: str, reverse: bool = False
) -> List[Dict[str, Any]]:
    """Sort items by a field.

    Args:
        items: List of dictionaries to sort
        sort_key: Field to sort by (supports dot notation)
        reverse: Sort in descending order if True

    Returns:
        Sorted list of items
    """

    def get_sort_value(item: Dict[str, Any]) -> Any:
        """Extract sort value from item."""
        parts = sort_key.split(".")
        value = item

        for part in parts:
            if isinstance(value, dict):
                value = value.get(part)
            else:
                return ""

        # Convert None to empty string for sorting
        if value is None:
            return ""

        return value

    try:
        return sorted(items, key=get_sort_value, reverse=reverse)
    except TypeError:
        # If comparison fails, convert all to strings
        return sorted(items, key=lambda x: str(get_sort_value(x)), reverse=reverse)


def select_columns(
    items: List[Dict[str, Any]], columns: List[str]
) -> List[Dict[str, Any]]:
    """Select specific columns from items.

    Args:
        items: List of dictionaries
        columns: List of column names to keep

    Returns:
        List of dictionaries with only selected columns
    """
    if not columns:
        return items

    return [{col: item.get(col) for col in columns} for item in items]

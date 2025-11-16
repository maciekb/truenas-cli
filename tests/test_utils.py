"""Tests for utility modules."""

import pytest

from truenas_cli.utils.filtering import (
    FilterExpression,
    Filter,
    filter_items,
    sort_items,
    select_columns,
)


class TestFilterExpression:
    """Tests for FilterExpression class."""

    def test_parse_equal(self):
        """Test parsing = operator."""
        expr = FilterExpression("status=ONLINE")
        assert expr.field == "status"
        assert expr.op == "="
        assert expr.value == "ONLINE"

    def test_parse_not_equal(self):
        """Test parsing != operator."""
        expr = FilterExpression("status!=OFFLINE")
        assert expr.field == "status"
        assert expr.op == "!="
        assert expr.value == "OFFLINE"

    def test_parse_greater_than(self):
        """Test parsing > operator."""
        expr = FilterExpression("size>100")
        assert expr.field == "size"
        assert expr.op == ">"
        assert expr.value == "100"

    def test_parse_greater_equal(self):
        """Test parsing >= operator."""
        expr = FilterExpression("size>=100")
        assert expr.field == "size"
        assert expr.op == ">="
        assert expr.value == "100"

    def test_parse_contains(self):
        """Test parsing ~ (contains) operator."""
        expr = FilterExpression("name~test")
        assert expr.field == "name"
        assert expr.op == "~"
        assert expr.value == "test"

    def test_matches_equal(self):
        """Test matching with = operator."""
        expr = FilterExpression("status=ONLINE")
        assert expr.matches({"status": "ONLINE"}) is True
        assert expr.matches({"status": "OFFLINE"}) is False

    def test_matches_contains(self):
        """Test matching with ~ operator."""
        expr = FilterExpression("name~test")
        assert expr.matches({"name": "test-pool"}) is True
        assert expr.matches({"name": "TESTING"}) is True  # case-insensitive
        assert expr.matches({"name": "pool"}) is False

    def test_matches_numeric(self):
        """Test numeric comparisons."""
        expr = FilterExpression("size>100")
        assert expr.matches({"size": 200}) is True
        assert expr.matches({"size": "200"}) is True  # string numbers work
        assert expr.matches({"size": 50}) is False

    def test_matches_nested_field(self):
        """Test matching with nested field using dot notation."""
        expr = FilterExpression("config.enabled=true")
        assert expr.matches({"config": {"enabled": "true"}}) is True
        assert expr.matches({"config": {"enabled": "false"}}) is False

    def test_invalid_expression(self):
        """Test invalid expression raises ValueError."""
        with pytest.raises(ValueError):
            FilterExpression("invalid expression")


class TestFilter:
    """Tests for Filter class."""

    def test_filter_single_expression(self):
        """Test filtering with single expression."""
        items = [
            {"name": "tank", "status": "ONLINE"},
            {"name": "backup", "status": "OFFLINE"},
            {"name": "data", "status": "ONLINE"},
        ]

        filter_obj = Filter(["status=ONLINE"])
        result = filter_obj.apply(items)

        assert len(result) == 2
        assert result[0]["name"] == "tank"
        assert result[1]["name"] == "data"

    def test_filter_multiple_expressions(self):
        """Test filtering with multiple expressions (AND logic)."""
        items = [
            {"name": "tank", "status": "ONLINE", "size": 100},
            {"name": "backup", "status": "ONLINE", "size": 200},
            {"name": "data", "status": "OFFLINE", "size": 150},
        ]

        filter_obj = Filter(["status=ONLINE", "size>150"])
        result = filter_obj.apply(items)

        assert len(result) == 1
        assert result[0]["name"] == "backup"

    def test_filter_empty_expressions(self):
        """Test filtering with no expressions returns all items."""
        items = [{"name": "tank"}, {"name": "backup"}]

        filter_obj = Filter([])
        result = filter_obj.apply(items)

        assert len(result) == 2


class TestSortItems:
    """Tests for sort_items function."""

    def test_sort_ascending(self):
        """Test sorting in ascending order."""
        items = [
            {"name": "zebra", "size": 100},
            {"name": "apple", "size": 200},
            {"name": "mango", "size": 150},
        ]

        result = sort_items(items, "name", reverse=False)

        assert result[0]["name"] == "apple"
        assert result[1]["name"] == "mango"
        assert result[2]["name"] == "zebra"

    def test_sort_descending(self):
        """Test sorting in descending order."""
        items = [
            {"name": "a", "size": 100},
            {"name": "b", "size": 200},
            {"name": "c", "size": 150},
        ]

        result = sort_items(items, "size", reverse=True)

        assert result[0]["size"] == 200
        assert result[1]["size"] == 150
        assert result[2]["size"] == 100

    def test_sort_nested_field(self):
        """Test sorting by nested field."""
        items = [
            {"name": "a", "config": {"priority": 3}},
            {"name": "b", "config": {"priority": 1}},
            {"name": "c", "config": {"priority": 2}},
        ]

        result = sort_items(items, "config.priority", reverse=False)

        assert result[0]["name"] == "b"
        assert result[1]["name"] == "c"
        assert result[2]["name"] == "a"


class TestSelectColumns:
    """Tests for select_columns function."""

    def test_select_columns(self):
        """Test selecting specific columns."""
        items = [
            {"name": "tank", "status": "ONLINE", "size": 100},
            {"name": "backup", "status": "OFFLINE", "size": 200},
        ]

        result = select_columns(items, ["name", "status"])

        assert len(result) == 2
        assert "name" in result[0]
        assert "status" in result[0]
        assert "size" not in result[0]

    def test_select_empty_columns(self):
        """Test selecting no columns returns all items unchanged."""
        items = [{"name": "tank", "status": "ONLINE"}]

        result = select_columns(items, [])

        assert result == items

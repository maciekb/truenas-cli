"""Tests for validation helpers."""

from __future__ import annotations

import pytest

from truenas_cli.validation import parse_json_argument
from truenas_client import TrueNASValidationError


@pytest.mark.unit
def test_parse_json_argument_from_string():
    result = parse_json_argument('{"name": "demo", "enabled": true}', name="attributes")
    assert result["name"] == "demo"
    assert result["enabled"] is True


@pytest.mark.unit
def test_parse_json_argument_from_file(tmp_path):
    json_file = tmp_path / "config.json"
    json_file.write_text('{"token": "abc", "count": 2}', encoding="utf-8")

    result = parse_json_argument(f"@{json_file}", name="config")
    assert result == {"token": "abc", "count": 2}


@pytest.mark.unit
def test_parse_json_argument_invalid_json():
    with pytest.raises(TrueNASValidationError) as excinfo:
        parse_json_argument("{invalid json}", name="attributes")
    assert "Invalid JSON" in str(excinfo.value)


@pytest.mark.unit
def test_parse_json_argument_missing_file(tmp_path):
    missing = tmp_path / "missing.json"
    with pytest.raises(TrueNASValidationError) as excinfo:
        parse_json_argument(f"@{missing}", name="config")
    assert "not found" in str(excinfo.value)

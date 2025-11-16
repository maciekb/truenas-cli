"""Tests for TrueNAS API client."""

import pytest
from pytest_httpx import HTTPXMock

from truenas_cli.client.base import TrueNASClient
from truenas_cli.client.exceptions import APIError, AuthenticationError, NetworkError
from truenas_cli.config import ProfileConfig


def test_client_initialization(mock_profile_config):
    """Test client initialization with profile config."""
    client = TrueNASClient(mock_profile_config, verbose=False)

    assert client.base_url == "https://truenas.local"
    assert client.api_key == "test-api-key-12345"
    assert client.timeout == 30
    assert client.verify_ssl is True


def test_client_get_request(httpx_mock, mock_profile_config):
    """Test successful GET request."""
    httpx_mock.add_response(
        url="https://truenas.local/api/v2.0/system/info",
        json={"version": "TrueNAS-SCALE-24.04"},
    )

    client = TrueNASClient(mock_profile_config, verbose=False)
    response = client.get("system/info")

    assert response == {"version": "TrueNAS-SCALE-24.04"}


def test_client_authentication_error(httpx_mock, mock_profile_config):
    """Test client handles 401 authentication errors."""
    httpx_mock.add_response(
        url="https://truenas.local/api/v2.0/system/info",
        status_code=401,
        json={"error": "Unauthorized"},
    )

    client = TrueNASClient(mock_profile_config, verbose=False)

    with pytest.raises(AuthenticationError):
        client.get("system/info")


def test_client_api_error(httpx_mock, mock_profile_config):
    """Test client handles general API errors."""
    httpx_mock.add_response(
        url="https://truenas.local/api/v2.0/system/info",
        status_code=500,
        json={"error": "Internal Server Error"},
    )

    client = TrueNASClient(mock_profile_config, verbose=False)

    with pytest.raises(APIError):
        client.get("system/info")


def test_client_url_building(mock_profile_config):
    """Test URL building with different endpoint formats."""
    client = TrueNASClient(mock_profile_config, verbose=False)

    # Test with leading slash
    url1 = client._build_url("/api/v2.0/system/info")
    assert url1 == "https://truenas.local/api/v2.0/system/info"

    # Test without leading slash or api prefix
    url2 = client._build_url("system/info")
    assert url2 == "https://truenas.local/api/v2.0/system/info"

"""Base TrueNAS API client.

This module provides the core HTTP client for interacting with the TrueNAS SCALE API.
It handles authentication, retries, error handling, and request/response processing.
"""

import asyncio
import logging
from typing import Any, Dict, Optional
from urllib.parse import quote, urljoin

import httpx
from pydantic import BaseModel

from truenas_cli.client.exceptions import (
    APIError,
    AuthenticationError,
    NetworkError,
    RateLimitError,
)
from truenas_cli.config import ProfileConfig

logger = logging.getLogger(__name__)


class TrueNASClient:
    """HTTP client for TrueNAS SCALE API.

    This client provides both synchronous and asynchronous methods for
    interacting with the TrueNAS API. It handles:
    - API key authentication
    - Automatic retries with exponential backoff
    - Rate limiting
    - Error handling and mapping to custom exceptions
    - Request/response logging in verbose mode

    Attributes:
        base_url: Base URL for API requests
        api_key: API key for authentication
        timeout: Request timeout in seconds
        verify_ssl: Whether to verify SSL certificates
    """

    def __init__(
        self,
        profile: ProfileConfig,
        verbose: bool = False,
    ):
        """Initialize TrueNAS client.

        Args:
            profile: Profile configuration with connection details
            verbose: Enable verbose logging
        """
        self.base_url = profile.url.rstrip("/")
        self.api_key = profile.api_key
        self.timeout = profile.timeout
        self.verify_ssl = profile.verify_ssl
        self.verbose = verbose

        # Configure logging
        if verbose:
            logging.basicConfig(level=logging.DEBUG)
        else:
            logging.basicConfig(level=logging.WARNING)

        # Build headers
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def _build_url(self, endpoint: str) -> str:
        """Build full API URL from endpoint.

        Args:
            endpoint: API endpoint path (e.g., '/api/v2.0/system/info')

        Returns:
            Full URL
        """
        # Ensure endpoint starts with /api/v2.0
        if not endpoint.startswith("/api/"):
            endpoint = f"/api/v2.0/{endpoint.lstrip('/')}"

        return urljoin(self.base_url, endpoint)

    def _handle_response(self, response: httpx.Response) -> Any:
        """Handle HTTP response and map errors to exceptions.

        Args:
            response: HTTP response object

        Returns:
            Response JSON data

        Raises:
            AuthenticationError: For 401 responses
            RateLimitError: For 429 responses
            APIError: For other 4xx/5xx responses
        """
        if self.verbose:
            logger.debug(f"Response status: {response.status_code}")
            logger.debug(f"Response headers: {response.headers}")
            logger.debug(f"Response body: {response.text[:1000]}")  # First 1000 chars

        # Handle successful responses
        if response.status_code < 400:
            try:
                return response.json()
            except Exception:
                # Some endpoints return empty responses
                return None

        # Handle error responses
        try:
            error_data = response.json()
            error_message = error_data.get("message", response.text)
        except Exception:
            error_message = response.text or response.reason_phrase

        # Authentication errors
        if response.status_code == 401:
            raise AuthenticationError(
                f"Authentication failed: {error_message}\n"
                "Please check your API key is valid and not expired."
            )

        # Rate limiting
        if response.status_code == 429:
            retry_after = response.headers.get("Retry-After")
            retry_seconds = int(retry_after) if retry_after else None
            raise RateLimitError(
                f"Rate limit exceeded: {error_message}",
                retry_after=retry_seconds,
            )

        # Client errors (4xx)
        if 400 <= response.status_code < 500:
            raise APIError(
                f"API client error ({response.status_code}): {error_message}",
                status_code=response.status_code,
                response_body=response.text,
            )

        # Server errors (5xx)
        if response.status_code >= 500:
            raise APIError(
                f"API server error ({response.status_code}): {error_message}",
                status_code=response.status_code,
                response_body=response.text,
            )

        # Shouldn't reach here, but just in case
        raise APIError(
            f"Unexpected response ({response.status_code}): {error_message}",
            status_code=response.status_code,
            response_body=response.text,
        )

    def request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        json: Optional[Dict[str, Any]] = None,
        max_retries: int = 3,
    ) -> Any:
        """Make a synchronous HTTP request to the API.

        Implements retry logic with exponential backoff for transient failures.

        Args:
            method: HTTP method (GET, POST, PUT, DELETE, etc.)
            endpoint: API endpoint path
            params: Query parameters
            json: JSON request body
            max_retries: Maximum number of retries for transient failures

        Returns:
            Response data

        Raises:
            NetworkError: For connection/network errors
            AuthenticationError: For authentication failures
            APIError: For API errors
            RateLimitError: For rate limiting
        """
        url = self._build_url(endpoint)

        if self.verbose:
            logger.debug(f"{method} {url}")
            if params:
                logger.debug(f"Query params: {params}")
            if json:
                logger.debug(f"Request body: {json}")

        retry_count = 0
        last_exception = None

        while retry_count <= max_retries:
            try:
                with httpx.Client(
                    timeout=self.timeout,
                    verify=self.verify_ssl,
                ) as client:
                    response = client.request(
                        method=method,
                        url=url,
                        headers=self.headers,
                        params=params,
                        json=json,
                    )
                    return self._handle_response(response)

            except (httpx.ConnectError, httpx.TimeoutException) as e:
                last_exception = e
                retry_count += 1

                if retry_count > max_retries:
                    raise NetworkError(
                        f"Network error after {max_retries} retries: {e}\n"
                        f"Failed to connect to {self.base_url}"
                    ) from e

                # Exponential backoff: 1s, 2s, 4s, 8s, ...
                wait_time = 2 ** (retry_count - 1)
                if self.verbose:
                    logger.debug(f"Retry {retry_count}/{max_retries} after {wait_time}s...")

                import time
                time.sleep(wait_time)

            except httpx.HTTPStatusError as e:
                # HTTP errors are handled by _handle_response
                return self._handle_response(e.response)

        # Should not reach here, but just in case
        raise NetworkError(f"Request failed after {max_retries} retries") from last_exception

    async def async_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        json: Optional[Dict[str, Any]] = None,
        max_retries: int = 3,
    ) -> Any:
        """Make an asynchronous HTTP request to the API.

        Async version of request() with the same retry logic.

        Args:
            method: HTTP method
            endpoint: API endpoint path
            params: Query parameters
            json: JSON request body
            max_retries: Maximum number of retries

        Returns:
            Response data

        Raises:
            NetworkError: For connection/network errors
            AuthenticationError: For authentication failures
            APIError: For API errors
            RateLimitError: For rate limiting
        """
        url = self._build_url(endpoint)

        if self.verbose:
            logger.debug(f"[Async] {method} {url}")
            if params:
                logger.debug(f"Query params: {params}")
            if json:
                logger.debug(f"Request body: {json}")

        retry_count = 0
        last_exception = None

        while retry_count <= max_retries:
            try:
                async with httpx.AsyncClient(
                    timeout=self.timeout,
                    verify=self.verify_ssl,
                ) as client:
                    response = await client.request(
                        method=method,
                        url=url,
                        headers=self.headers,
                        params=params,
                        json=json,
                    )
                    return self._handle_response(response)

            except (httpx.ConnectError, httpx.TimeoutException) as e:
                last_exception = e
                retry_count += 1

                if retry_count > max_retries:
                    raise NetworkError(
                        f"Network error after {max_retries} retries: {e}\n"
                        f"Failed to connect to {self.base_url}"
                    ) from e

                # Exponential backoff
                wait_time = 2 ** (retry_count - 1)
                if self.verbose:
                    logger.debug(f"Retry {retry_count}/{max_retries} after {wait_time}s...")

                await asyncio.sleep(wait_time)

            except httpx.HTTPStatusError as e:
                return self._handle_response(e.response)

        raise NetworkError(f"Request failed after {max_retries} retries") from last_exception

    # Convenience methods for common HTTP verbs
    def get(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Any:
        """Make a GET request.

        Args:
            endpoint: API endpoint
            params: Query parameters

        Returns:
            Response data
        """
        return self.request("GET", endpoint, params=params)

    def post(
        self, endpoint: str, json: Optional[Dict[str, Any]] = None
    ) -> Any:
        """Make a POST request.

        Args:
            endpoint: API endpoint
            json: Request body

        Returns:
            Response data
        """
        return self.request("POST", endpoint, json=json)

    def put(
        self, endpoint: str, json: Optional[Dict[str, Any]] = None
    ) -> Any:
        """Make a PUT request.

        Args:
            endpoint: API endpoint
            json: Request body

        Returns:
            Response data
        """
        return self.request("PUT", endpoint, json=json)

    def delete(self, endpoint: str) -> Any:
        """Make a DELETE request.

        Args:
            endpoint: API endpoint

        Returns:
            Response data
        """
        return self.request("DELETE", endpoint)

    async def async_get(
        self, endpoint: str, params: Optional[Dict[str, Any]] = None
    ) -> Any:
        """Make an async GET request.

        Args:
            endpoint: API endpoint
            params: Query parameters

        Returns:
            Response data
        """
        return await self.async_request("GET", endpoint, params=params)

    async def async_post(
        self, endpoint: str, json: Optional[Dict[str, Any]] = None
    ) -> Any:
        """Make an async POST request.

        Args:
            endpoint: API endpoint
            json: Request body

        Returns:
            Response data
        """
        return await self.async_request("POST", endpoint, json=json)

    # System monitoring methods
    def get_system_info(self) -> Any:
        """Get system information.

        Returns:
            System information dictionary
        """
        return self.get("/system/info")

    def get_system_version(self) -> Any:
        """Get system version.

        Returns:
            Version information
        """
        return self.get("/system/version")

    def get_system_state(self) -> Any:
        """Get system state.

        Returns:
            System state information
        """
        return self.get("/system/state")

    def get_system_health(self) -> Any:
        """Get system health status.

        Returns:
            Health status information
        """
        return self.get("/system/health")

    def get_system_stats(self) -> Any:
        """Get system resource statistics.

        Returns:
            System stats including CPU, memory, network
        """
        return self.get("/reporting/get_data")

    def get_alerts(self) -> Any:
        """Get system alerts.

        Returns:
            List of active alerts
        """
        return self.get("/alert/list")

    # Pool management methods
    def get_pools(self) -> Any:
        """Get all storage pools.

        Returns:
            List of pool information
        """
        return self.get("/pool")

    def get_pool(self, pool_id: int) -> Any:
        """Get specific pool information.

        Args:
            pool_id: Pool ID

        Returns:
            Detailed pool information
        """
        return self.get(f"/pool/id/{pool_id}")

    def get_pool_processes(self, pool_name: str) -> Any:
        """Get processes using a pool.

        Args:
            pool_name: Pool name

        Returns:
            List of processes
        """
        return self.post("/pool/processes", json={"name": pool_name})

    def scrub_pool(self, pool_id: int, action: str = "START") -> Any:
        """Start, stop, or pause a pool scrub.

        Args:
            pool_id: Pool ID
            action: Scrub action (START, STOP, PAUSE)

        Returns:
            Job information
        """
        return self.post(f"/pool/id/{pool_id}/scrub", json={"action": action})

    def get_pool_attachments(self, pool_id: int) -> Any:
        """Get pool attachments (services using the pool).

        Args:
            pool_id: Pool ID

        Returns:
            List of attachments
        """
        return self.post(f"/pool/id/{pool_id}/attachments")

    # Dataset management methods
    def get_datasets(self, filters: Optional[Dict[str, Any]] = None) -> Any:
        """Get all datasets.

        Args:
            filters: Optional filters for datasets

        Returns:
            List of datasets
        """
        endpoint = "/pool/dataset"
        if filters:
            return self.get(endpoint, params=filters)
        return self.get(endpoint)

    def get_dataset(self, dataset_id: str) -> Any:
        """Get specific dataset information.

        Args:
            dataset_id: Dataset ID (path, e.g., 'tank/mydata')

        Returns:
            Dataset information

        Note:
            The dataset_id is URL-encoded to handle slashes in dataset paths.
        """
        # URL-encode the dataset path to handle slashes correctly
        encoded_id = quote(dataset_id, safe='')
        return self.get(f"/pool/dataset/id/{encoded_id}")

    def create_dataset(self, dataset_data: Dict[str, Any]) -> Any:
        """Create a new dataset.

        Args:
            dataset_data: Dataset configuration

        Returns:
            Created dataset information
        """
        return self.post("/pool/dataset", json=dataset_data)

    def update_dataset(self, dataset_id: str, dataset_data: Dict[str, Any]) -> Any:
        """Update dataset properties.

        Args:
            dataset_id: Dataset ID (path, e.g., 'tank/mydata')
            dataset_data: Properties to update

        Returns:
            Updated dataset information

        Note:
            The dataset_id is URL-encoded to handle slashes in dataset paths.
        """
        # URL-encode the dataset path to handle slashes correctly
        encoded_id = quote(dataset_id, safe='')
        return self.put(f"/pool/dataset/id/{encoded_id}", json=dataset_data)

    def delete_dataset(self, dataset_id: str, recursive: bool = False) -> Any:
        """Delete a dataset.

        Args:
            dataset_id: Dataset ID (path, e.g., 'tank/mydata')
            recursive: Delete recursively

        Returns:
            Deletion result

        Note:
            The dataset_id is URL-encoded to handle slashes in dataset paths.
        """
        # URL-encode the dataset path to handle slashes correctly
        encoded_id = quote(dataset_id, safe='')
        params = {"recursive": recursive}
        return self.delete(f"/pool/dataset/id/{encoded_id}")

    # Share management methods
    def get_nfs_shares(self) -> Any:
        """Get all NFS shares.

        Returns:
            List of NFS shares
        """
        return self.get("/sharing/nfs")

    def get_nfs_share(self, share_id: int) -> Any:
        """Get specific NFS share.

        Args:
            share_id: Share ID

        Returns:
            NFS share information
        """
        return self.get(f"/sharing/nfs/id/{share_id}")

    def create_nfs_share(self, share_data: Dict[str, Any]) -> Any:
        """Create NFS share.

        Args:
            share_data: Share configuration

        Returns:
            Created share information
        """
        return self.post("/sharing/nfs", json=share_data)

    def update_nfs_share(self, share_id: int, share_data: Dict[str, Any]) -> Any:
        """Update NFS share.

        Args:
            share_id: Share ID
            share_data: Share configuration

        Returns:
            Updated share information
        """
        return self.put(f"/sharing/nfs/id/{share_id}", json=share_data)

    def delete_nfs_share(self, share_id: int) -> Any:
        """Delete NFS share.

        Args:
            share_id: Share ID

        Returns:
            Deletion result
        """
        return self.delete(f"/sharing/nfs/id/{share_id}")

    def get_smb_shares(self) -> Any:
        """Get all SMB shares.

        Returns:
            List of SMB shares
        """
        return self.get("/sharing/smb")

    def get_smb_share(self, share_id: int) -> Any:
        """Get specific SMB share.

        Args:
            share_id: Share ID

        Returns:
            SMB share information
        """
        return self.get(f"/sharing/smb/id/{share_id}")

    def create_smb_share(self, share_data: Dict[str, Any]) -> Any:
        """Create SMB share.

        Args:
            share_data: Share configuration

        Returns:
            Created share information
        """
        return self.post("/sharing/smb", json=share_data)

    def update_smb_share(self, share_id: int, share_data: Dict[str, Any]) -> Any:
        """Update SMB share.

        Args:
            share_id: Share ID
            share_data: Share configuration

        Returns:
            Updated share information
        """
        return self.put(f"/sharing/smb/id/{share_id}", json=share_data)

    def delete_smb_share(self, share_id: int) -> Any:
        """Delete SMB share.

        Args:
            share_id: Share ID

        Returns:
            Deletion result
        """
        return self.delete(f"/sharing/smb/id/{share_id}")

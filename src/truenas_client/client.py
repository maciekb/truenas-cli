"""TrueNAS API Client module.

This module provides a WebSocket-based client for communicating with TrueNAS
systems via the Distributed Data Protocol (DDP). The client supports both
low-level API calls and high-level convenience methods for common operations.

Compatible with: TrueNAS 25.10+ (Community Edition / SCALE)

Key Components:
    - TrueNASClient: Main client class for API communication
    - Exception hierarchy: Specific exception types for different error scenarios
    - DDP Protocol: Implements Distributed Data Protocol for async communication

Authentication Methods:
    - API Key (recommended): login_with_api_key()
    - Username/Password: login()

Common Usage:
    >>> async with TrueNASClient("truenas.local") as client:
    ...     await client.login_with_api_key("my-api-key")
    ...     pools = await client.get_pools()
    ...     for pool in pools:
    ...         print(f"Pool: {pool['name']}")

API Reference:
    See https://api.truenas.com/v25.10/ for complete API documentation

Module Structure:
    - Exception Classes: TrueNASClientError and subclasses
    - TrueNASClient Class: Main API client
    - Helper Methods: Connection, authentication, queries, and convenience methods
"""

import json
import logging
import ssl
import time
from typing import Any, Dict, List, Optional

import websockets
from websockets.client import WebSocketClientProtocol  # type: ignore[attr-defined]

logger = logging.getLogger(__name__)


def _sanitize_for_logging(data: Any) -> Any:
    """Sanitize data for logging to remove sensitive information.

    Redacts API keys, passwords, and other credentials from log output.

    Args:
        data: Data to sanitize (dict, string, or other)

    Returns:
        Sanitized version of data safe for logging
    """
    if isinstance(data, dict):
        sanitized = {}
        sensitive_keys = {"password", "api_key", "token", "secret", "auth"}
        for key, value in data.items():
            if key.lower() in sensitive_keys:
                sanitized[key] = "[REDACTED]"
            else:
                sanitized[key] = _sanitize_for_logging(value)
        return sanitized
    elif isinstance(data, list):
        return [_sanitize_for_logging(item) for item in data]
    elif isinstance(data, str) and len(data) > 500:
        return f"{data[:500]}... [truncated]"
    return data


class TrueNASClientError(Exception):
    """Base exception for TrueNAS client issues."""


class TrueNASConnectionError(TrueNASClientError):
    """Raised when the client cannot connect to TrueNAS."""


class TrueNASAPIError(TrueNASClientError):
    """Raised when the API returns an error response."""


class TrueNASAuthenticationError(TrueNASClientError):
    """Raised when authentication fails."""


class TrueNASValidationError(TrueNASClientError):
    """Raised when input validation fails."""


class TrueNASNotFoundError(TrueNASClientError):
    """Raised when a requested resource is not found."""


class TrueNASTimeoutError(TrueNASClientError):
    """Raised when an operation times out."""


class TrueNASResponseError(TrueNASClientError):
    """Raised when API response is malformed or unexpected."""


class TrueNASClient:
    """WebSocket-based client for TrueNAS API.

    Implements the Distributed Data Protocol (DDP) for communicating with
    TrueNAS 25.10+ systems. Provides both low-level RPC methods via `call()`
    and high-level convenience methods for common operations.

    Attributes:
        host: TrueNAS server hostname or IP address
        port: WebSocket port (default 443)
        use_ssl: Whether to use secure WebSocket (WSS)
        verify_ssl: Whether to verify SSL certificates

    Example:
        >>> async with TrueNASClient("192.168.1.100") as client:
        ...     await client.login_with_api_key("my-api-key")
        ...     pools = await client.get_pools()
        ...     print(pools)
    """

    def __init__(
        self,
        host: str,
        port: int = 443,
        use_ssl: bool = True,
        verify_ssl: bool = True,
    ) -> None:
        """Initialize TrueNAS API client.

        Args:
            host: TrueNAS host address (hostname or IP)
            port: WebSocket port (default: 443)
            use_ssl: Use WSS (secure WebSocket) connection (default: True)
            verify_ssl: Verify SSL certificates (set to False for self-signed certs)
                (default: True)

        Example:
            >>> client = TrueNASClient("truenas.local")
            >>> client = TrueNASClient("192.168.1.100", verify_ssl=False)
        """
        self.host = host
        self.port = port
        self.use_ssl = use_ssl
        self.verify_ssl = verify_ssl
        self.ws: Optional[WebSocketClientProtocol] = None
        self._request_id = 0
        self._authenticated = False
        self._session_id: Optional[str] = None

    @property
    def is_connected(self) -> bool:
        return self.ws is not None

    @property
    def is_authenticated(self) -> bool:
        return self._authenticated

    @property
    def url(self) -> str:
        """Construct WebSocket URL"""
        protocol = "wss" if self.use_ssl else "ws"
        return f"{protocol}://{self.host}:{self.port}/websocket"

    async def connect(self) -> None:
        """Establish WebSocket connection and perform DDP handshake.

        The connection process has two phases:
        1. WebSocket connection: Establishes the initial TCP/WebSocket connection
        2. DDP handshake: Performs Distributed Data Protocol handshake to get session ID

        The DDP protocol requires:
        - Send: {"msg": "connect", "version": "1", "support": ["1"]}
        - Receive: {"msg": "connected", "session": <id>}

        Raises:
            TrueNASConnectionError: If connection or DDP handshake fails
        """
        if self.is_connected:
            logger.debug("Client already connected to TrueNAS")
            return

        start_time = time.time()
        logger.info(f"Starting connection to TrueNAS at {self.url}")

        try:
            # Phase 1: Configure SSL context for WebSocket connection
            ssl_context: Optional[ssl.SSLContext] = None
            if self.use_ssl:
                if not self.verify_ssl:
                    # Create unverified SSL context for self-signed certificates
                    ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
                    ssl_context.check_hostname = False
                    ssl_context.verify_mode = ssl.CERT_NONE
                    logger.warning("SSL certificate verification is disabled!")
                else:
                    # Use default SSL context with verification
                    # ssl_context = None will use default websockets SSL verification
                    logger.debug("Using default SSL context with certificate verification")
            else:
                logger.warning("SSL is disabled - connection will be unencrypted")

            # Phase 1: Establish WebSocket connection
            ws_start = time.time()
            logger.debug(f"Establishing WebSocket connection to {self.url}")
            self.ws = await websockets.connect(
                self.url,
                ssl=ssl_context,
                ping_interval=20,
                ping_timeout=20,
            )
            ws_time = time.time() - ws_start
            logger.info(f"WebSocket connected ({ws_time:.2f}s): {self.url}")
            self._authenticated = False

            # Phase 2: Perform DDP handshake
            # Send DDP connect message to establish protocol session
            connect_msg = {
                "msg": "connect",
                "version": "1",
                "support": ["1"],
            }
            logger.debug(f"Sending DDP handshake message: {_sanitize_for_logging(connect_msg)}")
            await self.ws.send(json.dumps(connect_msg))

            # Receive DDP connected response containing session ID
            handshake_start = time.time()
            response = await self.ws.recv()
            data = json.loads(response)
            handshake_time = time.time() - handshake_start
            logger.debug(
                f"Received DDP handshake response ({handshake_time:.2f}s): "
                f"{_sanitize_for_logging(data)}"
            )

            if data.get("msg") == "connected":
                self._session_id = data.get("session")
                total_time = time.time() - start_time
                logger.info(
                    f"DDP session established ({total_time:.2f}s total): "
                    f"session_id={self._session_id}"
                )
            else:
                raise ConnectionError(
                    f"Unexpected DDP response: {data}. "
                    "Expected 'connected' message with session ID"
                )

        except Exception as e:
            elapsed = time.time() - start_time
            logger.error(f"Connection failed after {elapsed:.2f}s: {type(e).__name__}: {e}")
            raise TrueNASConnectionError(str(e)) from e

    async def disconnect(self) -> None:
        """Close WebSocket connection"""
        if self.ws:
            await self.ws.close()
            self.ws = None
            self._authenticated = False
            self._session_id = None
            logger.info("Disconnected from TrueNAS")

    def _get_next_id(self) -> str:
        """Generate next request ID"""
        self._request_id += 1
        return f"req_{self._request_id}"

    async def call(self, method: str, params: Optional[List[Any]] = None) -> Any:
        """Make a JSON-RPC 2.0 method call over DDP protocol.

        Sends a method call request to the TrueNAS API and waits for the response.

        Protocol Details (DDP/JSON-RPC 2.0):
            Request format:
                {
                    "msg": "method",
                    "method": "system.info",
                    "id": "req_1",
                    "params": [arg1, arg2, ...]
                }

            Response formats:
                Success:
                    {
                        "msg": "result",
                        "id": "req_1",
                        "result": {...}  # Return value
                    }

                Error:
                    {
                        "msg": "error",
                        "id": "req_1",
                        "error": {
                            "error": "Error message",
                            "reason": "Optional reason"
                        }
                    }

        Args:
            method: API method name in namespace.method format
                (e.g., 'system.info', 'pool.query', 'service.start')
            params: List of parameters to pass to the method (default: empty list)

        Returns:
            The "result" value from the API response (can be dict, list, str, etc.)

        Raises:
            TrueNASConnectionError: If not connected to server
            TrueNASAPIError: If API returns an error response
            Exception: On network errors or malformed responses

        Example:
            >>> # Low-level API call
            >>> result = await client.call("system.info", [])
            >>> hostname = result["hostname"]
            >>>
            >>> # Typical usage via high-level method
            >>> info = await client.system_info()  # Calls system.info internally
        """
        if not self.ws:
            raise TrueNASConnectionError("Not connected. Call connect() first.")

        # Build JSON-RPC request with unique ID for request tracking
        request_id = self._get_next_id()
        payload = {
            "msg": "method",
            "method": method,
            "id": request_id,
            "params": params or [],
        }

        start_time = time.time()

        # Send request as JSON over WebSocket
        logger.debug(
            f"API request: method={method} id={request_id} "
            f"params={_sanitize_for_logging(params or [])}"
        )
        await self.ws.send(json.dumps(payload))
        logger.debug(f"Sent JSON-RPC request: {request_id}")

        try:
            # Receive response - blocks until response arrives
            # Note: DDP protocol sends one response per request with matching ID
            response = await self.ws.recv()
            data = json.loads(response)
            elapsed = time.time() - start_time

            # Parse response based on message type
            if data.get("msg") == "result":
                # Success: return the result value
                result = data.get("result")
                logger.debug(
                    f"API response: method={method} id={request_id} "
                    f"status=success time={elapsed:.3f}s "
                    f"result_type={type(result).__name__}"
                )
                return result
            elif data.get("msg") == "error":
                # Error: extract error details and raise exception
                error = data.get("error", {})
                logger.warning(
                    f"API error: method={method} id={request_id} "
                    f"error={_sanitize_for_logging(error)} time={elapsed:.3f}s"
                )
                raise TrueNASAPIError(error)
            else:
                # Unexpected response: protocol error
                logger.error(
                    f"Unexpected DDP response: method={method} id={request_id} "
                    f"msg={data.get('msg')} time={elapsed:.3f}s"
                )
                raise TrueNASAPIError(f"Unexpected response: {data}")

        except Exception as e:
            elapsed = time.time() - start_time
            logger.error(
                f"API call failed: method={method} id={request_id} "
                f"error={type(e).__name__} time={elapsed:.3f}s"
            )
            raise

    async def login(self, username: str, password: str) -> None:
        """Authenticate with username and password.

        Connects to the server if not already connected, then authenticates
        using the provided username and password credentials.

        Args:
            username: TrueNAS username (typically "root")
            password: TrueNAS password

        Raises:
            TrueNASConnectionError: If not connected to server
            TrueNASAuthenticationError: If credentials are invalid

        Example:
            >>> await client.connect()
            >>> await client.login("root", "password")
        """
        logger.info(f"Attempting authentication with username: {username}")
        start_time = time.time()
        try:
            await self.ensure_connected()
            result = await self.call("auth.login", [username, "[REDACTED]"])
            self._authenticated = True
            elapsed = time.time() - start_time
            logger.info(f"Successfully authenticated as {username} ({elapsed:.2f}s)")
            return result
        except Exception as e:
            elapsed = time.time() - start_time
            logger.error(
                f"Authentication failed for {username}: {type(e).__name__} ({elapsed:.2f}s)"
            )
            raise

    async def login_with_api_key(self, api_key: str) -> None:
        """Authenticate using an API key.

        Preferred authentication method over username/password.
        Connects to the server if not already connected.

        Args:
            api_key: TrueNAS API key (generate in WebUI Settings > API Keys)

        Raises:
            TrueNASConnectionError: If not connected to server
            TrueNASAuthenticationError: If API key is invalid

        Example:
            >>> await client.connect()
            >>> await client.login_with_api_key("your-api-key-here")
        """
        logger.info("Attempting authentication with API key")
        start_time = time.time()
        try:
            await self.ensure_connected()
            result = await self.call("auth.login_with_api_key", [api_key])
            self._authenticated = True
            elapsed = time.time() - start_time
            logger.info(f"Successfully authenticated with API key ({elapsed:.2f}s)")
            return result
        except Exception as e:
            elapsed = time.time() - start_time
            logger.error(f"API key authentication failed: {type(e).__name__} ({elapsed:.2f}s)")
            raise

    async def ensure_connected(self):
        """Ensure the client is connected before performing operations."""
        if not self.is_connected:
            await self.connect()

    async def ensure_authenticated(
        self,
        *,
        api_key: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
    ):
        """
        Ensure the client is authenticated. Follows API priority: API key first, then user credentials.
        """
        await self.ensure_connected()

        if self.is_authenticated:
            return

        if api_key:
            await self.login_with_api_key(api_key)
            return

        if username and password:
            await self.login(username, password)
            return

        raise TrueNASClientError("Authentication required but no credentials provided.")

    async def system_info(self) -> Dict[str, Any]:
        """Get system information.

        Returns comprehensive information about the TrueNAS system including
        hostname, version, hardware specs, and status.

        Returns:
            Dictionary containing system information with keys like:
            - hostname: System hostname
            - version: TrueNAS version
            - model: Hardware model
            - cores: Number of CPU cores
            - physical_cores: Number of physical cores
            - physmem: Total physical memory in bytes
            - uptime: System uptime in seconds
            - timezone: System timezone

        Raises:
            TrueNASConnectionError: If not connected
            TrueNASAPIError: If API call fails

        Example:
            >>> info = await client.system_info()
            >>> print(f"Hostname: {info['hostname']}")
            >>> print(f"Version: {info['version']}")
        """
        return await self.call("system.info")

    async def system_version(self) -> str:
        """Get TrueNAS version.

        Returns:
            Version string (e.g., "TrueNAS-13.0-RELEASE")

        Raises:
            TrueNASConnectionError: If not connected
            TrueNASAPIError: If API call fails

        Example:
            >>> version = await client.system_version()
            >>> print(version)
        """
        return await self.call("system.version")

    async def query(
        self,
        resource: str,
        filters: Optional[List] = None,
        options: Optional[Dict] = None,
    ) -> List[Dict]:
        """Query API resources.

        Generic method to query any TrueNAS API resource. This is the foundation
        for other convenience methods.

        Args:
            resource: Resource to query (e.g., 'pool', 'dataset', 'service')
            filters: Optional query filters in format [["field", "operator", "value"], ...]
                Common operators: "=", "!=", ">", "<", ">=", "<=", "in", "nin"
                Example: [["name", "=", "tank"], ["status", "!=", "OFFLINE"]]
            options: Optional query options dictionary:
                - limit: Max results to return (default: no limit)
                - offset: Starting offset (default: 0)
                - order_by: Field to sort by (default: natural)
                - get: Return single result as dict instead of list

        Returns:
            List of dictionaries representing matching resources.
            Empty list if no matches.

        Raises:
            TrueNASConnectionError: If not connected
            TrueNASAPIError: If API call fails

        Example:
            >>> # List all pools
            >>> pools = await client.query("pool")
            >>> # List specific pool
            >>> pool = await client.query("pool", [["name", "=", "tank"]], {"get": True})
            >>> # Get 10 datasets with offset
            >>> datasets = await client.query(
            ...     "pool.dataset",
            ...     options={"limit": 10, "offset": 0}
            ... )
        """
        method = f"{resource}.query"
        params: List[Any] = [filters or []]
        if options:
            params.append(options)
        return await self.call(method, params)

    # Dataset operations
    async def create_dataset(
        self,
        name: str,
        dataset_type: str = "FILESYSTEM",
        share_type: Optional[str] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """Create a new dataset.

        Creates a new ZFS dataset with specified properties. Datasets can be
        FILESYSTEM (mountable) or VOLUME (block device).

        Args:
            name: Full dataset name (e.g., 'tank/mydata'). Parent pool/dataset
                must exist.
            dataset_type: Type of dataset. Either 'FILESYSTEM' (mountable,
                default) or 'VOLUME' (block device).
            share_type: Optional share type preset ('SMB', 'NFS', or 'GENERIC').
                Pre-configures dataset for the specified sharing protocol.
            **kwargs: Additional dataset properties:
                - encryption: 'ON' or 'OFF' (default: inherited from parent)
                - comments: Dataset description (default: "")
                - sync: Sync mode - 'ALWAYS', 'NORMAL', or 'DISABLED'
                    (default: 'NORMAL')
                - compression: Compression algorithm (default: inherited)
                - dedup: 'ON' or 'OFF' (default: OFF - note: enables dedup)
                - atime: 'ON' or 'OFF' (default: ON)
                - readonly: 'ON' or 'OFF' (default: OFF)
                - recordsize: Block size in bytes (default: inherited)
                - copies: Number of copies (default: 1)
                - quota: Dataset quota in bytes
                - refquota: Reference quota in bytes

        Returns:
            Dictionary with created dataset information:
            - id: Dataset ID (same as name)
            - name: Dataset name
            - type: 'FILESYSTEM' or 'VOLUME'
            - mountpoint: Mount path (FILESYSTEM only)
            - And other ZFS properties

        Raises:
            TrueNASConnectionError: If not connected
            TrueNASValidationError: If dataset name is invalid
            TrueNASNotFoundError: If parent dataset doesn't exist
            TrueNASAPIError: If creation fails

        Example:
            >>> # Create simple filesystem
            >>> ds = await client.create_dataset("tank/data")
            >>> # Create with encryption
            >>> ds = await client.create_dataset(
            ...     "tank/secure",
            ...     encryption="ON",
            ...     compression="lz4"
            ... )
            >>> # Create SMB-optimized dataset
            >>> ds = await client.create_dataset(
            ...     "tank/shares",
            ...     share_type="SMB"
            ... )
        """
        # Check if dataset already exists
        if await self.dataset_exists(name):
            raise ValueError(f"Dataset '{name}' already exists")

        params = {
            "name": name,
            "type": dataset_type,
        }

        if share_type:
            params["share_type"] = share_type

        # Merge additional parameters
        params.update(kwargs)

        return await self.call("pool.dataset.create", [params])

    async def get_dataset(self, dataset_id: str) -> Dict[str, Any]:
        """Get dataset information by ID.

        Args:
            dataset_id: Dataset ID (full path like 'tank/mydata')

        Returns:
            Dataset information dictionary

        Raises:
            TrueNASConnectionError: If not connected
            TrueNASNotFoundError: If dataset doesn't exist
            TrueNASAPIError: If API call fails

        Example:
            >>> ds = await client.get_dataset("tank/data")
            >>> print(ds["mountpoint"])
        """
        try:
            result = await self.call("pool.dataset.get_instance", [dataset_id])
            # Validate response
            if result is None:
                raise TrueNASNotFoundError(
                    f"Dataset '{dataset_id}' not found. "
                    f"Use 'dataset list' to see available datasets."
                )
            if not isinstance(result, dict):
                raise TrueNASValidationError(
                    f"Unexpected response type for dataset '{dataset_id}': "
                    f"expected dict, got {type(result).__name__}"
                )
            return result
        except TrueNASNotFoundError:
            raise  # Re-raise our specific error
        except TrueNASAPIError as e:
            # Check if error indicates dataset not found
            error_msg = str(e).lower()
            if "not found" in error_msg or "does not exist" in error_msg:
                raise TrueNASNotFoundError(f"Dataset '{dataset_id}' not found") from e
            raise  # Re-raise other API errors

    async def dataset_exists(self, dataset_name: str) -> bool:
        """Check if a dataset exists.

        Args:
            dataset_name: Full dataset name (e.g., 'tank/mydata')

        Returns:
            True if dataset exists, False otherwise

        Example:
            >>> if await client.dataset_exists("tank/data"):
            ...     print("Dataset exists")
        """
        try:
            await self.get_dataset(dataset_name)
            return True
        except TrueNASNotFoundError:
            return False

    # SMB Share operations
    async def create_smb_share(
        self, path: str, name: str, comment: str = "", enabled: bool = True, **kwargs
    ) -> Dict[str, Any]:
        """
        Create SMB share

        Args:
            path: Full path to share (e.g., '/mnt/tank/mydata')
            name: Share name
            comment: Description of the share
            enabled: Enable share immediately
            **kwargs: Additional SMB share options

        Returns:
            Created SMB share information
        """
        params = {
            "path": path,
            "name": name,
            "comment": comment,
            "enabled": enabled,
        }

        # Merge additional parameters
        params.update(kwargs)

        return await self.call("sharing.smb.create", [params])

    async def update_smb_share(self, share_id: int, **kwargs) -> Dict[str, Any]:
        """
        Update existing SMB share

        Args:
            share_id: SMB share ID
            **kwargs: Parameters to update

        Returns:
            Updated SMB share information
        """
        return await self.call("sharing.smb.update", [share_id, kwargs])

    async def delete_smb_share(self, share_id: int) -> bool:
        """
        Delete SMB share (sharing.smb.delete)

        Args:
            share_id: SMB share ID

        Returns:
            True if deleted successfully

        Raises:
            ValueError: If share not found
        """
        # Verify share exists
        shares = await self.get_smb_shares()
        if not shares or not any(s.get("id") == share_id for s in shares):
            raise ValueError(f"SMB share with ID {share_id} not found")

        return await self.call("sharing.smb.delete", [share_id])

    async def get_smb_shares(self) -> List[Dict[str, Any]]:
        """
        Get all SMB shares

        Returns:
            List of SMB shares
        """
        return await self.query("sharing.smb")

    async def get_smb_presets(self) -> Dict[str, Any]:
        """
        Get available SMB share presets

        Returns:
            Dictionary of available SMB presets with their configurations
        """
        return await self.call("sharing.smb.presets")

    async def create_smb_share_with_preset(
        self, path: str, name: str, preset: str, comment: str = "", enabled: bool = True, **kwargs
    ) -> Dict[str, Any]:
        """
        Create SMB share using a preset

        Args:
            path: Full path to share (e.g., '/mnt/tank/mydata')
            name: Share name
            preset: Preset type (e.g., 'DEFAULT_SHARE', 'PRIVATE_DATASETS', 'TIMEMACHINE')
            comment: Description of the share
            enabled: Enable share immediately
            **kwargs: Additional SMB share options (will override preset defaults)

        Returns:
            Created SMB share information
        """
        # Get preset configuration
        presets = await self.get_smb_presets()

        if preset not in presets:
            available = ", ".join(presets.keys())
            raise ValueError(f"Invalid preset '{preset}'. Available: {available}")

        # Start with preset parameters
        params = presets[preset].copy()

        # Override with required parameters
        params.update(
            {
                "path": path,
                "name": name,
                "comment": comment,
                "enabled": enabled,
            }
        )

        # Merge additional parameters (these override preset defaults)
        params.update(kwargs)

        return await self.call("sharing.smb.create", [params])

    # Service operations
    async def get_service(self, service_name: str) -> Dict[str, Any]:
        """
        Get service information

        Args:
            service_name: Service name (e.g., 'cifs' for SMB, 'nfs' for NFS)

        Returns:
            Service information
        """
        try:
            # When get=True, query returns a single dict; otherwise returns list
            result: Any = await self.query(
                "service", [["service", "=", service_name]], {"get": True}
            )
            if isinstance(result, dict):
                return result
            if isinstance(result, list) and result:
                return result[0]
        except Exception as e:
            logger.debug(f"Query failed for service {service_name}: {e}")

        # Fallback: get all services and search
        try:
            all_services = await self.get_services()
            for svc in all_services:
                if svc.get("service") == service_name:
                    return svc
        except Exception as e:
            logger.debug(f"Fallback search failed: {e}")

        raise ValueError(f"Service '{service_name}' not found")

    async def start_service(self, service_name: str) -> bool:
        """
        Start a service

        Args:
            service_name: Service name (e.g., 'cifs' for SMB, 'nfs', 'ssh')

        Returns:
            Result from API call
        """
        return await self.call("service.start", [service_name])

    async def stop_service(self, service_name: str) -> bool:
        """
        Stop a service

        Args:
            service_name: Service name (e.g., 'cifs', 'nfs', 'ssh')

        Returns:
            Result from API call
        """
        return await self.call("service.stop", [service_name])

    async def restart_service(self, service_name: str) -> bool:
        """
        Restart a service

        Args:
            service_name: Service name (e.g., 'cifs', 'nfs', 'ssh')

        Returns:
            Result from API call
        """
        return await self.call("service.restart", [service_name])

    async def reload_service(self, service_name: str) -> bool:
        """
        Reload a service (reload configuration without restart)

        Args:
            service_name: Service name (e.g., 'cifs', 'nfs', 'ssh')

        Returns:
            Result from API call
        """
        return await self.call("service.reload", [service_name])

    async def enable_service(self, service_name: str) -> bool:
        """
        Enable service to start on boot

        Args:
            service_name: Service name (e.g., 'cifs', 'nfs')

        Returns:
            True if enabled successfully
        """
        service = await self.get_service(service_name)
        service_id = service.get("id")
        return await self.call("service.update", [service_id, {"enable": True}])

    async def ensure_smb_service_running(self) -> Dict[str, Any]:
        """
        Ensure SMB service is running and enabled

        Returns:
            Service status information
        """
        service = await self.get_service("cifs")

        if not service.get("state") == "RUNNING":
            logger.info("Starting SMB service...")
            await self.start_service("cifs")

        if not service.get("enable"):
            logger.info("Enabling SMB service on boot...")
            await self.enable_service("cifs")

        return await self.get_service("cifs")

    async def ensure_nfs_service_running(self) -> Dict[str, Any]:
        """
        Ensure NFS service is running and enabled

        Returns:
            Service status information
        """
        service = await self.get_service("nfs")

        if not service.get("state") == "RUNNING":
            logger.info("Starting NFS service...")
            await self.start_service("nfs")

        if not service.get("enable"):
            logger.info("Enabling NFS service on boot...")
            await self.enable_service("nfs")

        return await self.get_service("nfs")

    # Pool operations
    async def get_pools(self) -> List[Dict[str, Any]]:
        """Get all storage pools.

        Returns:
            List of pool dictionaries with info: name, status, size, allocated,
            free, health, and other ZFS properties.

        Raises:
            TrueNASConnectionError: If not connected
            TrueNASAPIError: If API call fails

        Example:
            >>> pools = await client.get_pools()
            >>> for pool in pools:
            ...     print(f"{pool['name']}: {pool['status']}")
        """
        return await self.query("pool")

    async def get_pool(self, pool_name: str) -> Dict[str, Any]:
        """Get pool information by name.

        Args:
            pool_name: Name of the pool (e.g., 'tank')

        Returns:
            Pool information dictionary

        Raises:
            TrueNASConnectionError: If not connected
            TrueNASNotFoundError: If pool doesn't exist
            TrueNASAPIError: If API call fails

        Example:
            >>> pool = await client.get_pool("tank")
            >>> print(f"Status: {pool['status']}")
        """
        # When get=True, query may return a single dict or a list
        pools: Any = await self.query("pool", [["name", "=", pool_name]], {"get": True})
        if isinstance(pools, dict):
            return pools
        if isinstance(pools, list) and pools:
            return pools[0]
        raise TrueNASNotFoundError(f"Pool '{pool_name}' not found")

    # Dataset operations - extended
    async def get_datasets(self, pool_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get all datasets, optionally filtered by pool"""
        if pool_name:
            filters = [["pool", "=", pool_name]]
            return await self.query("pool.dataset", filters)
        return await self.query("pool.dataset")

    async def get_dataset_shares(self, dataset_name: str) -> Dict[str, Any]:
        """
        Get shares for a dataset (SMB and NFS)

        Args:
            dataset_name: Dataset name

        Returns:
            Dict with 'smb' and 'nfs' keys containing lists of shares
        """
        shares: Dict[str, List[Dict[str, Any]]] = {"smb": [], "nfs": []}

        # Check SMB shares
        smb_shares = await self.get_smb_shares()
        if smb_shares:
            shares["smb"] = [
                s for s in smb_shares if s.get("path", "").startswith(f"/mnt/{dataset_name}")
            ]

        # Check NFS shares
        nfs_shares = await self.get_nfs_shares()
        if nfs_shares:
            prefix = f"/mnt/{dataset_name}"
            filtered = []
            for share in nfs_shares:
                direct_path = share.get("path", "")
                if isinstance(direct_path, str) and direct_path.startswith(prefix):
                    filtered.append(share)
                    continue
                path_list = share.get("paths") or []
                if any(
                    isinstance(candidate, str) and candidate.startswith(prefix)
                    for candidate in path_list
                ):
                    filtered.append(share)
            shares["nfs"] = filtered

        return shares

    async def delete_dataset(self, dataset_name: str, force: bool = False) -> bool:
        """
        Delete a dataset (pool.dataset.delete)

        Args:
            dataset_name: Full dataset name (e.g., 'tank/mydata')
            force: Force deletion (default: False)

        Returns:
            True if deleted successfully, raises exception on actual error
        """
        # Check if dataset exists first
        if not await self.dataset_exists(dataset_name):
            raise ValueError(f"Dataset '{dataset_name}' not found")

        params = {"force": force}
        try:
            return await self.call("pool.dataset.delete", [dataset_name, params])
        except Exception as e:
            # Re-raise with better error message
            if "not found" in str(e).lower() or "does not exist" in str(e).lower():
                raise ValueError(f"Dataset '{dataset_name}' not found")
            raise

    # NFS Share operations
    async def create_nfs_share(self, path: str, comment: str = "", **kwargs) -> Dict[str, Any]:
        """
        Create NFS share

        Args:
            path: Local path to be exported (e.g., /mnt/pool/dataset)
            comment: Share description (not used in NFS but kept for compatibility)
            **kwargs: Additional NFS share options (applied after creation via update)
                - networks: List of authorized networks (CIDR notation, default: empty = all)
                - hosts: List of IP/hostnames allowed (default: empty = all)
                - ro: Read-only flag (default: False)
                - maproot_user: Root user mapping (default: None)
                - maproot_group: Root group mapping (default: None)
                - mapall_user: Map all access to user (default: None)
                - mapall_group: Map all access to group (default: None)
                - security: Security options list (default: empty)
                - expose_snapshots: Enable snapshot access (requires enterprise license)

        Returns:
            Created NFS share information
        """
        # Check if share already exists for this path
        if await self.nfs_share_exists_for_path(path):
            raise ValueError(f"NFS share for path '{path}' already exists")

        # TrueNAS NFS API creation accepts only 'path' parameter
        # Other options must be set via update() after creation
        params = {
            "path": path,
        }

        logger.debug(f"Creating NFS share with params: {json.dumps(params, default=str)}")
        result = await self.call("sharing.nfs.create", [params])
        logger.debug(f"NFS share create result: {result}")

        # If result is valid and we have additional kwargs, update the share
        if result and kwargs:
            share_id = result.get("id")
            if share_id:
                try:
                    update_kwargs = {}
                    # Filter out invalid update parameters
                    valid_update_keys = {
                        "networks",
                        "hosts",
                        "ro",
                        "maproot_user",
                        "maproot_group",
                        "mapall_user",
                        "mapall_group",
                        "security",
                        "expose_snapshots",
                        "comment",
                        "enabled",
                        "aliases",
                    }
                    for key, value in kwargs.items():
                        if key in valid_update_keys:
                            update_kwargs[key] = value

                    if update_kwargs:
                        result = await self.update_nfs_share(share_id, **update_kwargs)
                except Exception as e:
                    logger.warning(f"Could not update NFS share after creation: {e}")

        # Return result or empty dict
        return result if result else {}

    async def get_nfs_shares(self) -> List[Dict[str, Any]]:
        """Get all NFS shares"""
        try:
            # Query returns a list of NFS shares
            result = await self.query("sharing.nfs")
            if result:
                return result
        except Exception as e:
            logger.debug(f"sharing.nfs query failed: {e}")

        try:
            # Fallback: try direct API call with empty filters
            result = await self.call("sharing.nfs.query", [[]])
            if result:
                if isinstance(result, list):
                    return result
                elif isinstance(result, dict) and result.get("shares"):
                    return (
                        result["shares"]
                        if isinstance(result["shares"], list)
                        else [result["shares"]]
                    )
        except Exception as e:
            logger.debug(f"sharing.nfs.query call failed: {e}")

        return []

    async def nfs_share_exists_for_path(self, path: str) -> bool:
        """Check if NFS share already exists for given path"""
        shares = await self.get_nfs_shares()
        for share in shares:
            if share.get("path") == path:
                return True
            paths = share.get("paths") or []
            if isinstance(paths, list) and path in paths:
                return True
        return False

    async def delete_nfs_share(self, share_id: int) -> bool:
        """
        Delete NFS share (sharing.nfs.delete)

        Args:
            share_id: NFS share ID

        Returns:
            True if deleted successfully

        Raises:
            ValueError: If share not found
        """
        # Verify share exists
        shares = await self.get_nfs_shares()
        if not shares or not any(s.get("id") == share_id for s in shares):
            raise ValueError(f"NFS share with ID {share_id} not found")

        return await self.call("sharing.nfs.delete", [share_id])

    async def update_nfs_share(self, share_id: int, **kwargs) -> Dict[str, Any]:
        """Update existing NFS share"""
        return await self.call("sharing.nfs.update", [share_id, kwargs])

    # Service operations - extended
    async def get_services(self) -> List[Dict[str, Any]]:
        """Get all services"""
        return await self.query("service")

    # Snapshot operations
    async def create_snapshot(
        self, dataset_name: str, snapshot_name: str, **kwargs
    ) -> Dict[str, Any]:
        """
        Create a snapshot (pool.snapshot.create)

        Args:
            dataset_name: Full dataset name (e.g., 'tank/mydata')
            snapshot_name: Snapshot name (e.g., 'backup-2024-01-01')

        Optional kwargs:
            recursive: Include child datasets (default: False)
            exclude: List of child datasets to exclude if recursive

        Returns:
            Created snapshot information
        """
        params = {
            "dataset": dataset_name,
            "name": snapshot_name,
        }
        params.update(kwargs)
        return await self.call("pool.snapshot.create", [params])

    async def get_snapshots(self, dataset_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get snapshots, optionally filtered by dataset (pool.snapshot.query)

        Args:
            dataset_name: Optional filter by dataset name

        Returns:
            List of snapshot information
        """
        if dataset_name:
            filters = [["dataset", "=", dataset_name]]
            return await self.query("pool.snapshot", filters)
        return await self.query("pool.snapshot")

    async def delete_snapshot(self, snapshot_path: str) -> bool:
        """
        Delete a snapshot (pool.snapshot.delete)

        Args:
            snapshot_path: Full snapshot path (e.g., 'tank/data@backup')

        Returns:
            True if deleted successfully

        Raises:
            ValueError: If snapshot not found
        """
        # Verify snapshot exists
        dataset_name = snapshot_path.split("@")[0] if "@" in snapshot_path else None
        if dataset_name:
            snapshots = await self.get_snapshots(dataset_name)
            if not snapshots or not any(s.get("name") == snapshot_path for s in snapshots):
                raise ValueError(f"Snapshot '{snapshot_path}' not found")

        return await self.call("pool.snapshot.delete", [snapshot_path])

    # Disk operations
    async def get_disks(self) -> List[Dict[str, Any]]:
        """Get all disks"""
        return await self.query("disk")

    async def get_disk(self, disk_name: str) -> Dict[str, Any]:
        """Get disk information by name"""
        disks = await self.query("disk", [["name", "=", disk_name]])
        if disks:
            return disks[0]
        raise ValueError(f"Disk '{disk_name}' not found")

    async def get_disk_temperatures(
        self,
        disk_names: Optional[List[str]] = None,
        include_thresholds: bool = False,
    ) -> Dict[str, Any]:
        """
        Retrieve disk temperatures (disk.temperatures)

        Args:
            disk_names: List of disk names (e.g., ["sda"]). Empty means all.
            include_thresholds: Include vendor thresholds.
        """
        names = disk_names or []
        return await self.call("disk.temperatures", [names, include_thresholds])

    # Alerts
    async def get_alerts(self) -> List[Dict[str, Any]]:
        """Get all alerts"""
        return await self.call("alert.list")

    # SMB Delete extended
    async def delete_smb_share_with_dataset(
        self, share_id: int, delete_dataset: bool = False, dataset_name: Optional[str] = None
    ) -> bool:
        """Delete SMB share and optionally its dataset"""
        await self.delete_smb_share(share_id)
        if delete_dataset and dataset_name:
            await self.delete_dataset(dataset_name)
        return True

    async def __aenter__(self):
        """Async context manager entry"""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.disconnect()

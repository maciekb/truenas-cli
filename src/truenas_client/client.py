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
                    logger.debug(
                        "Using default SSL context with certificate verification"
                    )
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
            logger.debug(
                f"Sending DDP handshake message: {_sanitize_for_logging(connect_msg)}"
            )
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
            logger.error(
                f"Connection failed after {elapsed:.2f}s: {type(e).__name__}: {e}"
            )
            raise TrueNASConnectionError(str(e)) from e

    async def disconnect(self) -> None:
        """Close WebSocket connection"""
        ws = self.ws
        if ws is None:
            return
        self.ws = None
        self._authenticated = False
        self._session_id = None
        assert ws is not None
        await ws.close()
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
        ws = self.ws
        if ws is None:
            raise TrueNASConnectionError("Not connected. Call connect() first.")
        assert ws is not None

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
        await ws.send(json.dumps(payload))
        logger.debug(f"Sent JSON-RPC request: {request_id}")

        try:
            # Receive response - blocks until response arrives
            # Note: DDP protocol sends one response per request with matching ID
            response = await ws.recv()
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
            logger.error(
                f"API key authentication failed: {type(e).__name__} ({elapsed:.2f}s)"
            )
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
        self,
        path: str,
        name: str,
        preset: str,
        comment: str = "",
        enabled: bool = True,
        **kwargs,
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
    async def get_datasets(
        self, pool_name: Optional[str] = None
    ) -> List[Dict[str, Any]]:
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
                s
                for s in smb_shares
                if s.get("path", "").startswith(f"/mnt/{dataset_name}")
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
    async def create_nfs_share(
        self, path: str, comment: str = "", **kwargs
    ) -> Dict[str, Any]:
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

        logger.debug(
            f"Creating NFS share with params: {json.dumps(params, default=str)}"
        )
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

    async def get_snapshots(
        self, dataset_name: Optional[str] = None
    ) -> List[Dict[str, Any]]:
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
            if not snapshots or not any(
                s.get("name") == snapshot_path for s in snapshots
            ):
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

    # App/Container operations (TrueNAS SCALE)
    async def get_apps(self) -> List[Dict[str, Any]]:
        """
        Get all installed applications (app.query)

        Returns:
            List of installed applications with their configuration and status

        Example:
            >>> apps = await client.get_apps()
            >>> for app in apps:
            ...     print(f"{app['name']}: {app['state']}")
        """
        return await self.query("app")

    async def get_app(self, app_name: str) -> Dict[str, Any]:
        """
        Get application information by name (app.get_instance)

        Args:
            app_name: Application name

        Returns:
            Application information dictionary

        Raises:
            TrueNASNotFoundError: If application doesn't exist
        """
        try:
            result = await self.call("app.get_instance", [app_name])
            if result is None:
                raise TrueNASNotFoundError(f"App '{app_name}' not found")
            return result
        except TrueNASAPIError as e:
            error_msg = str(e).lower()
            if "not found" in error_msg or "does not exist" in error_msg:
                raise TrueNASNotFoundError(f"App '{app_name}' not found") from e
            raise

    async def get_available_apps(self) -> Dict[str, Any]:
        """
        Get available applications from catalog (app.available)

        Returns:
            Dictionary of available applications organized by train/catalog

        Example:
            >>> available = await client.get_available_apps()
            >>> for train, apps in available.items():
            ...     print(f"Train: {train}")
        """
        return await self.call("app.available")

    async def get_app_categories(self) -> List[str]:
        """
        Get app categories (app.categories)

        Returns:
            List of application categories
        """
        return await self.call("app.categories")

    async def start_app(self, app_name: str) -> bool:
        """
        Start an application (app.start)

        Args:
            app_name: Application name

        Returns:
            True if started successfully
        """
        return await self.call("app.start", [app_name])

    async def stop_app(self, app_name: str) -> bool:
        """
        Stop an application (app.stop)

        Args:
            app_name: Application name

        Returns:
            True if stopped successfully
        """
        return await self.call("app.stop", [app_name])

    async def create_app(self, values: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create/install a new application (app.create)

        Args:
            values: Application configuration dictionary

        Returns:
            Created application information

        Example:
            >>> config = {
            ...     "app_name": "plex",
            ...     "release_name": "my-plex",
            ...     "version": "1.0.0",
            ...     "values": {}
            ... }
            >>> app = await client.create_app(config)
        """
        return await self.call("app.create", [values])

    async def delete_app(self, app_name: str) -> bool:
        """
        Delete/uninstall an application (app.delete)

        Args:
            app_name: Application name

        Returns:
            True if deleted successfully

        Example:
            >>> await client.delete_app("my-plex")
        """
        return await self.call("app.delete", [app_name])

    async def update_app(self, app_name: str, values: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update application configuration (app.update)

        Args:
            app_name: Application name
            values: Updated configuration values

        Returns:
            Updated application information
        """
        return await self.call("app.update", [app_name, values])

    async def upgrade_app(
        self, app_name: str, version: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Upgrade application to a new version (app.upgrade)

        Args:
            app_name: Application name
            version: Target version (if None, upgrades to latest)

        Returns:
            Upgraded application information
        """
        params: List[Any] = [app_name]
        if version:
            params.append({"app_version": version})
        return await self.call("app.upgrade", params)

    async def redeploy_app(self, app_name: str) -> Dict[str, Any]:
        """
        Redeploy an application (app.redeploy)

        Useful for applying configuration changes or restarting containers.

        Args:
            app_name: Application name

        Returns:
            Redeployed application information
        """
        return await self.call("app.redeploy", [app_name])

    async def get_app_config(self) -> Dict[str, Any]:
        """
        Get applications configuration (app.config)

        Returns:
            Global apps configuration including pool settings
        """
        return await self.call("app.config")

    # App image operations
    async def get_app_images(self) -> List[Dict[str, Any]]:
        """
        Get Docker images (app.image.query)

        Returns:
            List of available Docker images
        """
        return await self.query("app.image")

    async def pull_app_image(self, image: str, tag: str = "latest") -> bool:
        """
        Pull a Docker image (app.image.pull)

        Args:
            image: Image name (e.g., "nginx", "postgres")
            tag: Image tag (default: "latest")

        Returns:
            True if pulled successfully
        """
        params = {"from_image": image, "tag": tag}
        return await self.call("app.image.pull", [params])

    async def delete_app_image(self, image_id: str) -> bool:
        """
        Delete a Docker image (app.image.delete)

        Args:
            image_id: Image ID

        Returns:
            True if deleted successfully
        """
        return await self.call("app.image.delete", [image_id])

    # User operations
    async def get_users(self) -> List[Dict[str, Any]]:
        """
        Get all users (user.query)

        Returns:
            List of user dictionaries

        Example:
            >>> users = await client.get_users()
            >>> for user in users:
            ...     print(f"{user['username']}: {user['full_name']}")
        """
        return await self.query("user")

    async def get_user(self, user_id: int) -> Dict[str, Any]:
        """
        Get user information by ID (user.get_instance)

        Args:
            user_id: User ID

        Returns:
            User information dictionary

        Raises:
            TrueNASNotFoundError: If user doesn't exist
        """
        try:
            result = await self.call("user.get_instance", [user_id])
            if result is None:
                raise TrueNASNotFoundError(f"User with ID {user_id} not found")
            return result
        except TrueNASAPIError as e:
            error_msg = str(e).lower()
            if "not found" in error_msg or "does not exist" in error_msg:
                raise TrueNASNotFoundError(f"User with ID {user_id} not found") from e
            raise

    async def create_user(
        self,
        username: str,
        full_name: str,
        password: Optional[str] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Create a new user (user.create)

        Args:
            username: Username (login name)
            full_name: Full name of the user
            password: Password (optional, can set later)
            **kwargs: Additional user parameters:
                - uid: User ID (auto-assigned if not provided)
                - group: Primary group ID
                - groups: List of additional group IDs
                - home: Home directory path
                - shell: Shell path (use get_shell_choices() for options)
                - email: Email address
                - password_disabled: Disable password authentication
                - ssh_password_enabled: Enable SSH password auth
                - smbhash: SMB password hash
                - sudo_commands: List of sudo commands
                - sudo_commands_nopasswd: Sudo without password

        Returns:
            Created user information

        Example:
            >>> user = await client.create_user(
            ...     "john",
            ...     "John Doe",
            ...     password="secret123",
            ...     email="john@example.com"
            ... )
        """
        params = {"username": username, "full_name": full_name}

        if password:
            params["password"] = password

        params.update(kwargs)
        return await self.call("user.create", [params])

    async def update_user(self, user_id: int, **kwargs) -> Dict[str, Any]:
        """
        Update user information (user.update)

        Args:
            user_id: User ID
            **kwargs: Fields to update (same as create_user)

        Returns:
            Updated user information
        """
        return await self.call("user.update", [user_id, kwargs])

    async def delete_user(self, user_id: int, delete_group: bool = False) -> bool:
        """
        Delete a user (user.delete)

        Args:
            user_id: User ID
            delete_group: Also delete the user's primary group

        Returns:
            True if deleted successfully
        """
        params = {"delete_group": delete_group}
        return await self.call("user.delete", [user_id, params])

    async def set_user_password(self, user_id: int, password: str) -> bool:
        """
        Set user password (user.set_password)

        Args:
            user_id: User ID
            password: New password

        Returns:
            True if password set successfully
        """
        return await self.call("user.set_password", [user_id, password])

    async def get_shell_choices(self) -> List[str]:
        """
        Get available shell choices (user.shell_choices)

        Returns:
            List of available shell paths
        """
        return await self.call("user.shell_choices")

    # Group operations
    async def get_groups(self) -> List[Dict[str, Any]]:
        """
        Get all groups (group.query)

        Returns:
            List of group dictionaries

        Example:
            >>> groups = await client.get_groups()
            >>> for group in groups:
            ...     print(f"{group['group']}: GID {group['gid']}")
        """
        return await self.query("group")

    async def get_group(self, group_id: int) -> Dict[str, Any]:
        """
        Get group information by ID (group.get_instance)

        Args:
            group_id: Group ID

        Returns:
            Group information dictionary

        Raises:
            TrueNASNotFoundError: If group doesn't exist
        """
        try:
            result = await self.call("group.get_instance", [group_id])
            if result is None:
                raise TrueNASNotFoundError(f"Group with ID {group_id} not found")
            return result
        except TrueNASAPIError as e:
            error_msg = str(e).lower()
            if "not found" in error_msg or "does not exist" in error_msg:
                raise TrueNASNotFoundError(f"Group with ID {group_id} not found") from e
            raise

    async def create_group(
        self, name: str, gid: Optional[int] = None, **kwargs
    ) -> Dict[str, Any]:
        """
        Create a new group (group.create)

        Args:
            name: Group name
            gid: Group ID (auto-assigned if not provided)
            **kwargs: Additional group parameters:
                - sudo_commands: List of sudo commands
                - sudo_commands_nopasswd: Sudo without password
                - smb: Enable SMB access

        Returns:
            Created group information

        Example:
            >>> group = await client.create_group("developers", gid=1100)
        """
        params: Dict[str, Any] = {"name": name}

        if gid is not None:
            params["gid"] = gid

        params.update(kwargs)
        return await self.call("group.create", [params])

    async def update_group(self, group_id: int, **kwargs) -> Dict[str, Any]:
        """
        Update group information (group.update)

        Args:
            group_id: Group ID
            **kwargs: Fields to update

        Returns:
            Updated group information
        """
        return await self.call("group.update", [group_id, kwargs])

    async def delete_group(self, group_id: int) -> bool:
        """
        Delete a group (group.delete)

        Args:
            group_id: Group ID

        Returns:
            True if deleted successfully

        Raises:
            TrueNASAPIError: If group is in use
        """
        return await self.call("group.delete", [group_id])

    # Replication operations
    async def get_replications(self) -> List[Dict[str, Any]]:
        """
        Get all replication tasks (replication.query)

        Returns:
            List of replication task dictionaries

        Example:
            >>> tasks = await client.get_replications()
            >>> for task in tasks:
            ...     print(f"{task['name']}: {task['state']['state']}")
        """
        return await self.query("replication")

    async def get_replication(self, task_id: int) -> Dict[str, Any]:
        """
        Get replication task information by ID (replication.get_instance)

        Args:
            task_id: Replication task ID

        Returns:
            Replication task information dictionary

        Raises:
            TrueNASNotFoundError: If task doesn't exist
        """
        try:
            result = await self.call("replication.get_instance", [task_id])
            if result is None:
                raise TrueNASNotFoundError(
                    f"Replication task with ID {task_id} not found"
                )
            return result
        except TrueNASAPIError as e:
            error_msg = str(e).lower()
            if "not found" in error_msg or "does not exist" in error_msg:
                raise TrueNASNotFoundError(
                    f"Replication task with ID {task_id} not found"
                ) from e
            raise

    async def create_replication(
        self,
        name: str,
        direction: str,
        transport: str,
        source_datasets: List[str],
        target_dataset: str,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Create a new replication task (replication.create)

        Args:
            name: Name for the replication task
            direction: Replication direction ("PUSH" or "PULL")
            transport: Transport method ("SSH", "LOCAL", or "LEGACY")
            source_datasets: List of source dataset paths
            target_dataset: Target dataset path
            **kwargs: Additional replication parameters:
                - ssh_credentials: SSH credentials ID (required for SSH transport)
                - recursive: Recursively replicate child datasets (bool)
                - exclude: Dataset paths to exclude (list)
                - properties: Replicate dataset properties (bool)
                - properties_exclude: Properties to exclude (list)
                - properties_override: Override specific properties (dict)
                - encryption: Enable encryption (bool)
                - periodic_snapshot_tasks: Associated snapshot task IDs (list)
                - naming_schema: Snapshot naming schemas (list)
                - also_include_naming_schema: Additional schemas (list)
                - name_regex: Regular expression for snapshot names
                - auto: Automatically replicate on schedule (bool)
                - schedule: Cron schedule configuration (dict)
                - retention_policy: Snapshot retention policy
                - lifetime_value: Retention lifetime value (int)
                - lifetime_unit: Retention lifetime unit
                - enabled: Enable the replication task (bool)
                - readonly: Set readonly property on target
                - allow_from_scratch: Allow full replication from scratch (bool)
                - hold_pending_snapshots: Hold pending snapshots (bool)
                - logging_level: Logging level
                - speed_limit: Speed limit in KB/s (int)
                - compression: Compression algorithm
                - large_block: Enable large blocks (bool)
                - embed: Enable embedded data (bool)
                - compressed: Enable compressed send (bool)

        Returns:
            Created replication task information

        Example:
            >>> task = await client.create_replication(
            ...     name="backup-to-remote",
            ...     direction="PUSH",
            ...     transport="SSH",
            ...     source_datasets=["tank/data"],
            ...     target_dataset="backup/data",
            ...     ssh_credentials=1,
            ...     recursive=True
            ... )
        """
        params = {
            "name": name,
            "direction": direction,
            "transport": transport,
            "source_datasets": source_datasets,
            "target_dataset": target_dataset,
        }

        params.update(kwargs)
        return await self.call("replication.create", [params])

    async def update_replication(self, task_id: int, **kwargs) -> Dict[str, Any]:
        """
        Update replication task (replication.update)

        Args:
            task_id: Replication task ID
            **kwargs: Fields to update (same as create_replication)

        Returns:
            Updated replication task information
        """
        return await self.call("replication.update", [task_id, kwargs])

    async def delete_replication(self, task_id: int) -> bool:
        """
        Delete a replication task (replication.delete)

        Args:
            task_id: Replication task ID

        Returns:
            True if deleted successfully

        Raises:
            TrueNASAPIError: If task is running or in use
        """
        return await self.call("replication.delete", [task_id])

    async def run_replication(self, task_id: int) -> None:
        """
        Run a replication task immediately (replication.run)

        This starts a background job. Monitor job status via job API.

        Args:
            task_id: Replication task ID

        Example:
            >>> await client.run_replication(1)
        """
        await self.call("replication.run", [task_id])

    async def run_replication_onetime(
        self,
        direction: str,
        transport: str,
        source_datasets: List[str],
        target_dataset: str,
        **kwargs,
    ) -> None:
        """
        Run a one-time replication (not saved as a task) (replication.run_onetime)

        This starts a background job for a one-time replication without
        creating a saved replication task.

        Args:
            direction: Replication direction ("PUSH" or "PULL")
            transport: Transport method ("SSH" or "LOCAL")
            source_datasets: List of source dataset paths
            target_dataset: Target dataset path
            **kwargs: Additional parameters (same as create_replication,
                     except name, auto, schedule not applicable)

        Example:
            >>> await client.run_replication_onetime(
            ...     direction="PUSH",
            ...     transport="LOCAL",
            ...     source_datasets=["tank/data"],
            ...     target_dataset="backup/data"
            ... )
        """
        params = {
            "direction": direction,
            "transport": transport,
            "source_datasets": source_datasets,
            "target_dataset": target_dataset,
        }

        params.update(kwargs)
        await self.call("replication.run_onetime", [params])

    async def list_replication_datasets(
        self, transport: str = "LOCAL", ssh_credentials: Optional[int] = None
    ) -> List[str]:
        """
        List available datasets for replication (replication.list_datasets)

        Args:
            transport: Transport method ("SSH" or "LOCAL")
            ssh_credentials: SSH credentials ID (required for SSH transport)

        Returns:
            List of dataset paths

        Example:
            >>> datasets = await client.list_replication_datasets("LOCAL")
            >>> print(datasets)
            ['tank', 'tank/data', 'tank/media']
        """
        params: Dict[str, Any] = {"transport": transport}
        if ssh_credentials is not None:
            params["ssh_credentials"] = ssh_credentials

        return await self.call("replication.list_datasets", [params])

    async def list_replication_naming_schemas(self) -> List[str]:
        """
        List available snapshot naming schemas (replication.list_naming_schemas)

        Returns:
            List of naming schema patterns

        Example:
            >>> schemas = await client.list_replication_naming_schemas()
            >>> print(schemas)
            ['auto-%Y-%m-%d_%H-%M', 'manual-%Y%m%d']
        """
        return await self.call("replication.list_naming_schemas")

    # CloudSync operations
    async def get_cloudsync_tasks(self) -> List[Dict[str, Any]]:
        """
        Get all cloud sync tasks (cloudsync.query)

        Returns:
            List of cloud sync task dictionaries

        Example:
            >>> tasks = await client.get_cloudsync_tasks()
            >>> for task in tasks:
            ...     print(f"{task['description']}: {task['direction']}")
        """
        return await self.query("cloudsync")

    async def get_cloudsync_task(self, task_id: int) -> Dict[str, Any]:
        """
        Get cloud sync task information by ID (cloudsync.get_instance)

        Args:
            task_id: Cloud sync task ID

        Returns:
            Cloud sync task information dictionary

        Raises:
            TrueNASNotFoundError: If task doesn't exist
        """
        try:
            result = await self.call("cloudsync.get_instance", [task_id])
            if result is None:
                raise TrueNASNotFoundError(
                    f"CloudSync task with ID {task_id} not found"
                )
            return result
        except TrueNASAPIError as e:
            error_msg = str(e).lower()
            if "not found" in error_msg or "does not exist" in error_msg:
                raise TrueNASNotFoundError(
                    f"CloudSync task with ID {task_id} not found"
                ) from e
            raise

    async def create_cloudsync_task(
        self,
        path: str,
        credentials: int,
        direction: str,
        transfer_mode: str,
        attributes: Dict[str, Any],
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Create a new cloud sync task (cloudsync.create)

        Args:
            path: Local path (must start with /mnt or /dev/zvol)
            credentials: ID of cloud credential
            direction: Sync direction ("PUSH" or "PULL")
            transfer_mode: Transfer mode ("SYNC", "COPY", or "MOVE")
            attributes: Cloud provider-specific attributes (bucket, folder, etc.)
            **kwargs: Additional cloud sync parameters:
                - description: Task name to display in UI
                - schedule: Cron schedule configuration (dict)
                - encryption: Enable encryption (bool)
                - filename_encryption: Encrypt filenames (bool)
                - encryption_password: Password for encryption
                - encryption_salt: Salt for encryption
                - pre_script: Bash script to run before backup
                - post_script: Bash script to run after successful backup
                - snapshot: Create temporary snapshot before backup (bool)
                - include: Paths to include (list)
                - exclude: Paths to exclude (list)
                - enabled: Enable/disable task (bool)
                - bwlimit: Bandwidth limit schedule (list of dicts)
                - transfers: Max parallel file transfers (int)
                - create_empty_src_dirs: Create empty directories (bool)
                - follow_symlinks: Follow symbolic links (bool)

        Returns:
            Created cloud sync task information

        Example:
            >>> task = await client.create_cloudsync_task(
            ...     path="/mnt/tank/data",
            ...     credentials=1,
            ...     direction="PUSH",
            ...     transfer_mode="SYNC",
            ...     attributes={"bucket": "my-backup", "folder": "data"},
            ...     description="Daily backup to S3"
            ... )
        """
        params = {
            "path": path,
            "credentials": credentials,
            "direction": direction,
            "transfer_mode": transfer_mode,
            "attributes": attributes,
        }

        params.update(kwargs)
        return await self.call("cloudsync.create", [params])

    async def update_cloudsync_task(self, task_id: int, **kwargs) -> Dict[str, Any]:
        """
        Update cloud sync task (cloudsync.update)

        Args:
            task_id: Cloud sync task ID
            **kwargs: Fields to update (same as create_cloudsync_task)

        Returns:
            Updated cloud sync task information
        """
        return await self.call("cloudsync.update", [task_id, kwargs])

    async def delete_cloudsync_task(self, task_id: int) -> bool:
        """
        Delete a cloud sync task (cloudsync.delete)

        Args:
            task_id: Cloud sync task ID

        Returns:
            True if deleted successfully

        Raises:
            TrueNASAPIError: If task is running or in use
        """
        return await self.call("cloudsync.delete", [task_id])

    async def sync_cloudsync_task(self, task_id: int, dry_run: bool = False) -> None:
        """
        Run a cloud sync task (cloudsync.sync)

        This starts a background job.

        Args:
            task_id: Cloud sync task ID
            dry_run: Perform dry run without actual changes

        Example:
            >>> await client.sync_cloudsync_task(1, dry_run=True)
        """
        options = {"dry_run": dry_run}
        await self.call("cloudsync.sync", [task_id, options])

    async def sync_cloudsync_onetime(
        self,
        path: str,
        credentials: int,
        direction: str,
        transfer_mode: str,
        attributes: Dict[str, Any],
        dry_run: bool = False,
        **kwargs,
    ) -> None:
        """
        Run one-time cloud sync (not saved as a task) (cloudsync.sync_onetime)

        Args:
            path: Local path (must start with /mnt or /dev/zvol)
            credentials: ID of cloud credential
            direction: Sync direction ("PUSH" or "PULL")
            transfer_mode: Transfer mode ("SYNC", "COPY", or "MOVE")
            attributes: Cloud provider-specific attributes
            dry_run: Perform dry run without actual changes
            **kwargs: Additional parameters (same as create_cloudsync_task)

        Example:
            >>> await client.sync_cloudsync_onetime(
            ...     path="/mnt/tank/data",
            ...     credentials=1,
            ...     direction="PUSH",
            ...     transfer_mode="SYNC",
            ...     attributes={"bucket": "my-backup"},
            ...     dry_run=True
            ... )
        """
        params = {
            "path": path,
            "credentials": credentials,
            "direction": direction,
            "transfer_mode": transfer_mode,
            "attributes": attributes,
        }

        params.update(kwargs)
        options = {"dry_run": dry_run}
        await self.call("cloudsync.sync_onetime", [params, options])

    async def abort_cloudsync_task(self, task_id: int) -> bool:
        """
        Abort a running cloud sync task (cloudsync.abort)

        Args:
            task_id: Cloud sync task ID

        Returns:
            True if aborted successfully
        """
        return await self.call("cloudsync.abort", [task_id])

    async def list_cloudsync_providers(self) -> List[Dict[str, Any]]:
        """
        List supported cloud sync providers (cloudsync.providers)

        Returns:
            List of provider information dictionaries

        Example:
            >>> providers = await client.list_cloudsync_providers()
            >>> for provider in providers:
            ...     print(f"{provider['title']} ({provider['name']})")
        """
        return await self.call("cloudsync.providers")

    async def list_cloudsync_directory(
        self, credentials: int, attributes: Dict[str, Any], **kwargs
    ) -> List[Dict[str, Any]]:
        """
        List contents of remote directory/bucket (cloudsync.list_directory)

        Args:
            credentials: ID of cloud credential
            attributes: Cloud provider attributes (bucket, folder, etc.)
            **kwargs: Additional parameters:
                - encryption: Whether files are encrypted (bool)
                - filename_encryption: Whether filenames are encrypted (bool)
                - encryption_password: Password for decryption
                - encryption_salt: Salt for decryption
                - args: Additional arguments

        Returns:
            List of file/directory information

        Example:
            >>> files = await client.list_cloudsync_directory(
            ...     credentials=1,
            ...     attributes={"bucket": "my-backup", "folder": "data"}
            ... )
        """
        params = {"credentials": credentials, "attributes": attributes}
        params.update(kwargs)
        return await self.call("cloudsync.list_directory", [params])

    async def list_cloudsync_buckets(self, credentials: int) -> List[Dict[str, Any]]:
        """
        List all buckets for given credentials (cloudsync.list_buckets)

        Args:
            credentials: ID of cloud credential

        Returns:
            List of bucket information

        Example:
            >>> buckets = await client.list_cloudsync_buckets(1)
            >>> for bucket in buckets:
            ...     print(bucket['Name'])
        """
        return await self.call("cloudsync.list_buckets", [credentials])

    # CloudSync Credentials operations
    async def get_cloudsync_credentials(self) -> List[Dict[str, Any]]:
        """
        Get all cloud sync credentials (cloudsync.credentials.query)

        Returns:
            List of cloud sync credential dictionaries

        Example:
            >>> creds = await client.get_cloudsync_credentials()
            >>> for cred in creds:
            ...     print(f"{cred['name']}: {cred['provider']}")
        """
        return await self.query("cloudsync.credentials")

    async def get_cloudsync_credential(self, cred_id: int) -> Dict[str, Any]:
        """
        Get cloud sync credential by ID (cloudsync.credentials.get_instance)

        Args:
            cred_id: Credential ID

        Returns:
            Credential information dictionary

        Raises:
            TrueNASNotFoundError: If credential doesn't exist
        """
        try:
            result = await self.call("cloudsync.credentials.get_instance", [cred_id])
            if result is None:
                raise TrueNASNotFoundError(
                    f"CloudSync credential with ID {cred_id} not found"
                )
            return result
        except TrueNASAPIError as e:
            error_msg = str(e).lower()
            if "not found" in error_msg or "does not exist" in error_msg:
                raise TrueNASNotFoundError(
                    f"CloudSync credential with ID {cred_id} not found"
                ) from e
            raise

    async def create_cloudsync_credential(
        self, name: str, provider: str, attributes: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Create cloud sync credentials (cloudsync.credentials.create)

        Args:
            name: Name of the credential
            provider: Cloud provider name (e.g., "S3", "DROPBOX", "GOOGLE_DRIVE")
            attributes: Provider-specific authentication attributes

        Returns:
            Created credential information

        Example:
            >>> cred = await client.create_cloudsync_credential(
            ...     name="My S3 Credentials",
            ...     provider="S3",
            ...     attributes={
            ...         "access_key_id": "AKIAIOSFODNN7EXAMPLE",
            ...         "secret_access_key": "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
            ...     }
            ... )
        """
        params = {"name": name, "provider": provider, "attributes": attributes}
        return await self.call("cloudsync.credentials.create", [params])

    async def update_cloudsync_credential(
        self, cred_id: int, **kwargs
    ) -> Dict[str, Any]:
        """
        Update cloud sync credential (cloudsync.credentials.update)

        Args:
            cred_id: Credential ID
            **kwargs: Fields to update (name, provider, attributes)

        Returns:
            Updated credential information
        """
        return await self.call("cloudsync.credentials.update", [cred_id, kwargs])

    async def delete_cloudsync_credential(self, cred_id: int) -> bool:
        """
        Delete cloud sync credential (cloudsync.credentials.delete)

        Args:
            cred_id: Credential ID

        Returns:
            True if deleted successfully

        Raises:
            TrueNASAPIError: If credential is in use
        """
        return await self.call("cloudsync.credentials.delete", [cred_id])

    async def verify_cloudsync_credential(
        self, provider: str, attributes: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Verify cloud sync credentials (cloudsync.credentials.verify)

        Args:
            provider: Cloud provider name
            attributes: Provider-specific authentication attributes

        Returns:
            Verification result

        Example:
            >>> result = await client.verify_cloudsync_credential(
            ...     provider="S3",
            ...     attributes={"access_key_id": "...", "secret_access_key": "..."}
            ... )
            >>> if result['valid']:
            ...     print("Credentials are valid")
        """
        params = {"provider": provider, "attributes": attributes}
        return await self.call("cloudsync.credentials.verify", [params])

    # SMB Delete extended
    async def delete_smb_share_with_dataset(
        self,
        share_id: int,
        delete_dataset: bool = False,
        dataset_name: Optional[str] = None,
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

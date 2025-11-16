"""Pydantic models for TrueNAS API responses.

This module contains type-safe models for common API responses,
providing validation and easy attribute access.
"""

from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class SystemInfo(BaseModel):
    """System information response model.

    Contains general information about the TrueNAS system including
    hostname, version, uptime, and system resources.
    """

    version: str = Field(..., description="TrueNAS version")
    hostname: str = Field(..., description="System hostname")
    uptime_seconds: Optional[float] = Field(None, description="System uptime in seconds")
    datetime_: Optional[datetime] = Field(None, alias="datetime", description="Current system time")
    system_manufacturer: Optional[str] = Field(None, description="Hardware manufacturer")
    system_product: Optional[str] = Field(None, description="Hardware product name")
    timezone: Optional[str] = Field(None, description="System timezone")
    boottime: Optional[datetime] = Field(None, description="Boot time")

    class Config:
        """Pydantic configuration."""
        populate_by_name = True  # Allow using both 'datetime_' and 'datetime'


class SystemVersion(BaseModel):
    """System version information.

    Detailed version information including version string,
    stable status, and component versions.
    """

    version: str = Field(..., description="Full version string")
    stable: Optional[bool] = Field(None, description="Whether this is a stable release")


class PoolStatus(BaseModel):
    """Storage pool status information.

    Basic information about a storage pool's health and capacity.
    """

    name: str = Field(..., description="Pool name")
    status: str = Field(..., description="Pool status (ONLINE, DEGRADED, etc.)")
    healthy: bool = Field(..., description="Whether pool is healthy")
    size: Optional[int] = Field(None, description="Total pool size in bytes")
    allocated: Optional[int] = Field(None, description="Allocated space in bytes")
    free: Optional[int] = Field(None, description="Free space in bytes")


class Dataset(BaseModel):
    """Dataset information.

    Represents a ZFS dataset with its properties.
    """

    id: str = Field(..., description="Dataset identifier (full path)")
    name: str = Field(..., description="Dataset name")
    pool: str = Field(..., description="Parent pool name")
    type: str = Field(..., description="Dataset type (FILESYSTEM, VOLUME)")
    used: Optional[Dict[str, Any]] = Field(None, description="Space usage information")
    available: Optional[Dict[str, Any]] = Field(None, description="Available space")
    compression: Optional[str] = Field(None, description="Compression algorithm")
    readonly: Optional[bool] = Field(None, description="Whether dataset is readonly")


class Job(BaseModel):
    """Background job information.

    Represents a background job running on TrueNAS.
    """

    id: int = Field(..., description="Job ID")
    method: str = Field(..., description="Method being executed")
    state: str = Field(..., description="Job state (RUNNING, SUCCESS, FAILED, etc.)")
    progress: Optional[Dict[str, Any]] = Field(None, description="Progress information")
    result: Optional[Any] = Field(None, description="Job result (if completed)")
    error: Optional[str] = Field(None, description="Error message (if failed)")
    time_started: Optional[datetime] = Field(None, description="Job start time")
    time_finished: Optional[datetime] = Field(None, description="Job finish time")


class Alert(BaseModel):
    """System alert information.

    Represents a system alert or notification.
    """

    id: str = Field(..., description="Alert identifier")
    level: str = Field(..., description="Alert level (INFO, WARNING, CRITICAL)")
    formatted: str = Field(..., description="Formatted alert message")
    dismissed: bool = Field(..., description="Whether alert is dismissed")
    datetime_: datetime = Field(..., alias="datetime", description="Alert timestamp")

    class Config:
        """Pydantic configuration."""
        populate_by_name = True


class APIResponse(BaseModel):
    """Generic API response wrapper.

    Can be used for responses that don't have a specific model.
    """

    data: Any = Field(..., description="Response data")

    class Config:
        """Pydantic configuration."""
        extra = "allow"  # Allow additional fields


class SystemHealth(BaseModel):
    """System health status information."""

    status: str = Field(..., description="Overall health status")
    healthy: bool = Field(..., description="Whether system is healthy")

    class Config:
        """Pydantic configuration."""
        extra = "allow"


class SystemStats(BaseModel):
    """System resource usage statistics."""

    cpu_usage: Optional[float] = Field(None, description="CPU usage percentage")
    memory_used: Optional[int] = Field(None, description="Memory used in bytes")
    memory_total: Optional[int] = Field(None, description="Total memory in bytes")
    uptime_seconds: Optional[float] = Field(None, description="System uptime in seconds")

    class Config:
        """Pydantic configuration."""
        extra = "allow"


class PoolInfo(BaseModel):
    """Detailed pool information."""

    id: int = Field(..., description="Pool ID")
    name: str = Field(..., description="Pool name")
    guid: str = Field(..., description="Pool GUID")
    status: str = Field(..., description="Pool status")
    path: Optional[str] = Field(None, description="Pool path")
    scan: Optional[Dict[str, Any]] = Field(None, description="Scrub/scan information")
    healthy: bool = Field(..., description="Pool health status")
    warning: bool = Field(False, description="Pool has warnings")
    status_detail: Optional[str] = Field(None, description="Detailed status message")
    size: Optional[int] = Field(None, description="Total pool size")
    allocated: Optional[int] = Field(None, description="Allocated space")
    free: Optional[int] = Field(None, description="Free space")
    freeing: Optional[int] = Field(None, description="Space being freed")
    fragmentation: Optional[str] = Field(None, description="Fragmentation percentage")
    autotrim: Optional[Dict[str, Any]] = Field(None, description="Autotrim settings")
    topology: Optional[Dict[str, Any]] = Field(None, description="Pool topology")

    class Config:
        """Pydantic configuration."""
        extra = "allow"


class PoolTopology(BaseModel):
    """Pool topology information."""

    data: Optional[List[Dict[str, Any]]] = Field(None, description="Data vdevs")
    cache: Optional[List[Dict[str, Any]]] = Field(None, description="Cache vdevs")
    log: Optional[List[Dict[str, Any]]] = Field(None, description="Log vdevs")
    spare: Optional[List[Dict[str, Any]]] = Field(None, description="Spare vdevs")
    special: Optional[List[Dict[str, Any]]] = Field(None, description="Special vdevs")
    dedup: Optional[List[Dict[str, Any]]] = Field(None, description="Dedup vdevs")

    class Config:
        """Pydantic configuration."""
        extra = "allow"


class DatasetInfo(BaseModel):
    """Detailed dataset information."""

    id: str = Field(..., description="Dataset ID (full path)")
    name: str = Field(..., description="Dataset name")
    pool: str = Field(..., description="Parent pool")
    type: str = Field(..., description="Dataset type")
    mountpoint: Optional[str] = Field(None, description="Mount point")
    used: Optional[Dict[str, Any]] = Field(None, description="Space usage")
    available: Optional[Dict[str, Any]] = Field(None, description="Available space")
    compression: Optional[str] = Field(None, description="Compression algorithm")
    compressratio: Optional[str] = Field(None, description="Compression ratio")
    quota: Optional[Dict[str, Any]] = Field(None, description="Quota settings")
    refquota: Optional[Dict[str, Any]] = Field(None, description="Reference quota")
    reservation: Optional[Dict[str, Any]] = Field(None, description="Reservation")
    refreservation: Optional[Dict[str, Any]] = Field(None, description="Reference reservation")
    readonly: Optional[bool] = Field(None, description="Read-only status")
    deduplication: Optional[str] = Field(None, description="Deduplication setting")
    atime: Optional[str] = Field(None, description="Access time setting")
    recordsize: Optional[str] = Field(None, description="Record size")
    encryption: Optional[bool] = Field(None, description="Encryption enabled")
    key_loaded: Optional[bool] = Field(None, description="Encryption key loaded")

    class Config:
        """Pydantic configuration."""
        extra = "allow"


class NFSShare(BaseModel):
    """NFS share information."""

    id: int = Field(..., description="Share ID")
    path: str = Field(..., description="Shared path")
    comment: Optional[str] = Field(None, description="Share comment/description")
    networks: Optional[List[str]] = Field(None, description="Allowed networks")
    hosts: Optional[List[str]] = Field(None, description="Allowed hosts")
    alldirs: Optional[bool] = Field(None, description="Share all directories")
    ro: Optional[bool] = Field(None, description="Read-only")
    quiet: Optional[bool] = Field(None, description="Quiet mode")
    maproot_user: Optional[str] = Field(None, description="Map root to user")
    maproot_group: Optional[str] = Field(None, description="Map root to group")
    mapall_user: Optional[str] = Field(None, description="Map all to user")
    mapall_group: Optional[str] = Field(None, description="Map all to group")
    security: Optional[List[str]] = Field(None, description="Security modes")
    enabled: bool = Field(..., description="Share enabled status")
    locked: Optional[bool] = Field(None, description="Dataset locked")

    class Config:
        """Pydantic configuration."""
        extra = "allow"


class SMBShare(BaseModel):
    """SMB/CIFS share information."""

    id: int = Field(..., description="Share ID")
    name: str = Field(..., description="Share name")
    path: str = Field(..., description="Shared path")
    path_suffix: Optional[str] = Field(None, description="Path suffix")
    home: Optional[bool] = Field(None, description="Home share")
    purpose: Optional[str] = Field(None, description="Share purpose")
    comment: Optional[str] = Field(None, description="Share comment")
    ro: Optional[bool] = Field(None, description="Read-only")
    browsable: Optional[bool] = Field(None, description="Browsable")
    guestok: Optional[bool] = Field(None, description="Guest access allowed")
    hostsallow: Optional[List[str]] = Field(None, description="Allowed hosts")
    hostsdeny: Optional[List[str]] = Field(None, description="Denied hosts")
    enabled: bool = Field(..., description="Share enabled status")
    locked: Optional[bool] = Field(None, description="Dataset locked")

    class Config:
        """Pydantic configuration."""
        extra = "allow"


class ScrubTask(BaseModel):
    """Pool scrub task information."""

    pool: int = Field(..., description="Pool ID")
    pool_name: str = Field(..., description="Pool name")
    threshold: Optional[int] = Field(None, description="Threshold in days")
    description: Optional[str] = Field(None, description="Task description")
    schedule: Optional[Dict[str, Any]] = Field(None, description="Scrub schedule")
    enabled: bool = Field(..., description="Task enabled status")

    class Config:
        """Pydantic configuration."""
        extra = "allow"

"""Pydantic models for TrueNAS API responses.

This module contains type-safe models for common API responses,
providing validation and easy attribute access.
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class SystemInfo(BaseModel):
    """System information response model.

    Contains general information about the TrueNAS system including
    hostname, version, uptime, and system resources.
    """

    version: str = Field(..., description="TrueNAS version")
    hostname: str = Field(..., description="System hostname")
    uptime_seconds: float | None = Field(None, description="System uptime in seconds")
    datetime_: datetime | None = Field(None, alias="datetime", description="Current system time")
    system_manufacturer: str | None = Field(None, description="Hardware manufacturer")
    system_product: str | None = Field(None, description="Hardware product name")
    timezone: str | None = Field(None, description="System timezone")
    boottime: datetime | None = Field(None, description="Boot time")

    class Config:
        """Pydantic configuration."""
        populate_by_name = True  # Allow using both 'datetime_' and 'datetime'


class SystemVersion(BaseModel):
    """System version information.

    Detailed version information including version string,
    stable status, and component versions.
    """

    version: str = Field(..., description="Full version string")
    stable: bool | None = Field(None, description="Whether this is a stable release")


class PoolStatus(BaseModel):
    """Storage pool status information.

    Basic information about a storage pool's health and capacity.
    """

    name: str = Field(..., description="Pool name")
    status: str = Field(..., description="Pool status (ONLINE, DEGRADED, etc.)")
    healthy: bool = Field(..., description="Whether pool is healthy")
    size: int | None = Field(None, description="Total pool size in bytes")
    allocated: int | None = Field(None, description="Allocated space in bytes")
    free: int | None = Field(None, description="Free space in bytes")


class Dataset(BaseModel):
    """Dataset information.

    Represents a ZFS dataset with its properties.
    """

    id: str = Field(..., description="Dataset identifier (full path)")
    name: str = Field(..., description="Dataset name")
    pool: str = Field(..., description="Parent pool name")
    type: str = Field(..., description="Dataset type (FILESYSTEM, VOLUME)")
    used: dict[str, Any] | None = Field(None, description="Space usage information")
    available: dict[str, Any] | None = Field(None, description="Available space")
    compression: str | None = Field(None, description="Compression algorithm")
    readonly: bool | None = Field(None, description="Whether dataset is readonly")


class Job(BaseModel):
    """Background job information.

    Represents a background job running on TrueNAS.
    """

    id: int = Field(..., description="Job ID")
    method: str = Field(..., description="Method being executed")
    state: str = Field(..., description="Job state (RUNNING, SUCCESS, FAILED, etc.)")
    progress: dict[str, Any] | None = Field(None, description="Progress information")
    result: Any | None = Field(None, description="Job result (if completed)")
    error: str | None = Field(None, description="Error message (if failed)")
    time_started: datetime | None = Field(None, description="Job start time")
    time_finished: datetime | None = Field(None, description="Job finish time")


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

    cpu_usage: float | None = Field(None, description="CPU usage percentage")
    memory_used: int | None = Field(None, description="Memory used in bytes")
    memory_total: int | None = Field(None, description="Total memory in bytes")
    uptime_seconds: float | None = Field(None, description="System uptime in seconds")

    class Config:
        """Pydantic configuration."""
        extra = "allow"


class PoolInfo(BaseModel):
    """Detailed pool information."""

    id: int = Field(..., description="Pool ID")
    name: str = Field(..., description="Pool name")
    guid: str = Field(..., description="Pool GUID")
    status: str = Field(..., description="Pool status")
    path: str | None = Field(None, description="Pool path")
    scan: dict[str, Any] | None = Field(None, description="Scrub/scan information")
    healthy: bool = Field(..., description="Pool health status")
    warning: bool = Field(False, description="Pool has warnings")
    status_detail: str | None = Field(None, description="Detailed status message")
    size: int | None = Field(None, description="Total pool size")
    allocated: int | None = Field(None, description="Allocated space")
    free: int | None = Field(None, description="Free space")
    freeing: int | None = Field(None, description="Space being freed")
    fragmentation: str | None = Field(None, description="Fragmentation percentage")
    autotrim: dict[str, Any] | None = Field(None, description="Autotrim settings")
    topology: dict[str, Any] | None = Field(None, description="Pool topology")

    class Config:
        """Pydantic configuration."""
        extra = "allow"


class PoolTopology(BaseModel):
    """Pool topology information."""

    data: list[dict[str, Any]] | None = Field(None, description="Data vdevs")
    cache: list[dict[str, Any]] | None = Field(None, description="Cache vdevs")
    log: list[dict[str, Any]] | None = Field(None, description="Log vdevs")
    spare: list[dict[str, Any]] | None = Field(None, description="Spare vdevs")
    special: list[dict[str, Any]] | None = Field(None, description="Special vdevs")
    dedup: list[dict[str, Any]] | None = Field(None, description="Dedup vdevs")

    class Config:
        """Pydantic configuration."""
        extra = "allow"


class DatasetInfo(BaseModel):
    """Detailed dataset information."""

    id: str = Field(..., description="Dataset ID (full path)")
    name: str = Field(..., description="Dataset name")
    pool: str = Field(..., description="Parent pool")
    type: str = Field(..., description="Dataset type")
    mountpoint: str | None = Field(None, description="Mount point")
    used: dict[str, Any] | None = Field(None, description="Space usage")
    available: dict[str, Any] | None = Field(None, description="Available space")
    compression: str | None = Field(None, description="Compression algorithm")
    compressratio: str | None = Field(None, description="Compression ratio")
    quota: dict[str, Any] | None = Field(None, description="Quota settings")
    refquota: dict[str, Any] | None = Field(None, description="Reference quota")
    reservation: dict[str, Any] | None = Field(None, description="Reservation")
    refreservation: dict[str, Any] | None = Field(None, description="Reference reservation")
    readonly: bool | None = Field(None, description="Read-only status")
    deduplication: str | None = Field(None, description="Deduplication setting")
    atime: str | None = Field(None, description="Access time setting")
    recordsize: str | None = Field(None, description="Record size")
    encryption: bool | None = Field(None, description="Encryption enabled")
    key_loaded: bool | None = Field(None, description="Encryption key loaded")

    class Config:
        """Pydantic configuration."""
        extra = "allow"


class NFSShare(BaseModel):
    """NFS share information."""

    id: int = Field(..., description="Share ID")
    path: str = Field(..., description="Shared path")
    comment: str | None = Field(None, description="Share comment/description")
    networks: list[str] | None = Field(None, description="Allowed networks")
    hosts: list[str] | None = Field(None, description="Allowed hosts")
    alldirs: bool | None = Field(None, description="Share all directories")
    ro: bool | None = Field(None, description="Read-only")
    quiet: bool | None = Field(None, description="Quiet mode")
    maproot_user: str | None = Field(None, description="Map root to user")
    maproot_group: str | None = Field(None, description="Map root to group")
    mapall_user: str | None = Field(None, description="Map all to user")
    mapall_group: str | None = Field(None, description="Map all to group")
    security: list[str] | None = Field(None, description="Security modes")
    enabled: bool = Field(..., description="Share enabled status")
    locked: bool | None = Field(None, description="Dataset locked")

    class Config:
        """Pydantic configuration."""
        extra = "allow"


class SMBShare(BaseModel):
    """SMB/CIFS share information."""

    id: int = Field(..., description="Share ID")
    name: str = Field(..., description="Share name")
    path: str = Field(..., description="Shared path")
    path_suffix: str | None = Field(None, description="Path suffix")
    home: bool | None = Field(None, description="Home share")
    purpose: str | None = Field(None, description="Share purpose")
    comment: str | None = Field(None, description="Share comment")
    ro: bool | None = Field(None, description="Read-only")
    browsable: bool | None = Field(None, description="Browsable")
    guestok: bool | None = Field(None, description="Guest access allowed")
    hostsallow: list[str] | None = Field(None, description="Allowed hosts")
    hostsdeny: list[str] | None = Field(None, description="Denied hosts")
    enabled: bool = Field(..., description="Share enabled status")
    locked: bool | None = Field(None, description="Dataset locked")

    class Config:
        """Pydantic configuration."""
        extra = "allow"


class ScrubTask(BaseModel):
    """Pool scrub task information."""

    pool: int = Field(..., description="Pool ID")
    pool_name: str = Field(..., description="Pool name")
    threshold: int | None = Field(None, description="Threshold in days")
    description: str | None = Field(None, description="Task description")
    schedule: dict[str, Any] | None = Field(None, description="Scrub schedule")
    enabled: bool = Field(..., description="Task enabled status")

    class Config:
        """Pydantic configuration."""
        extra = "allow"


class Snapshot(BaseModel):
    """ZFS snapshot information.

    Represents a ZFS snapshot with its properties and metadata.
    """

    name: str = Field(..., description="Full snapshot name (dataset@snapshot)")
    dataset: str | None = Field(None, description="Parent dataset name")
    snapshot_name: str | None = Field(None, description="Snapshot name only")
    type: str | None = Field(None, description="Snapshot type")
    createtxg: int | None = Field(None, description="Creation transaction group")
    creation: dict[str, Any] | None = Field(None, description="Creation time information")
    used: dict[str, Any] | None = Field(None, description="Space used by snapshot")
    referenced: dict[str, Any] | None = Field(None, description="Referenced space")
    properties: dict[str, Any] | None = Field(None, description="Additional ZFS properties")

    class Config:
        """Pydantic configuration."""
        extra = "allow"

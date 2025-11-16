"""Configuration management for TrueNAS CLI.

This module handles loading, saving, and managing CLI configuration including
profiles for multiple TrueNAS instances. Configuration is stored in a JSON file
with secure file permissions.
"""

import json
import os
import stat
from pathlib import Path
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field, HttpUrl, field_validator
from rich.console import Console

from truenas_cli.client.exceptions import ConfigurationError

console = Console()


class ProfileConfig(BaseModel):
    """Configuration for a single TrueNAS profile.

    Attributes:
        url: Base URL of the TrueNAS instance (e.g., https://truenas.local)
        api_key: API key for authentication
        verify_ssl: Whether to verify SSL certificates
        timeout: Request timeout in seconds
    """

    url: str = Field(..., description="TrueNAS API base URL")
    api_key: str = Field(..., min_length=1, description="API key for authentication")
    verify_ssl: bool = Field(True, description="Verify SSL certificates")
    timeout: int = Field(30, ge=1, le=300, description="Request timeout in seconds")

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        """Ensure URL doesn't end with trailing slash and uses https."""
        v = v.rstrip("/")
        if not v.startswith(("http://", "https://")):
            raise ValueError("URL must start with http:// or https://")
        return v

    @field_validator("api_key")
    @classmethod
    def validate_api_key(cls, v: str) -> str:
        """Ensure API key is not obviously invalid."""
        if v.strip() != v:
            raise ValueError("API key cannot have leading/trailing whitespace")
        if len(v) < 10:
            raise ValueError("API key seems too short")
        return v


class Config(BaseModel):
    """Main configuration container.

    Attributes:
        active_profile: Name of the currently active profile
        profiles: Dictionary mapping profile names to their configurations
    """

    active_profile: str = Field("default", description="Active profile name")
    profiles: Dict[str, ProfileConfig] = Field(
        default_factory=dict, description="Profile configurations"
    )

    def get_active_profile(self) -> ProfileConfig:
        """Get the active profile configuration.

        Returns:
            The active profile configuration

        Raises:
            ConfigurationError: If active profile doesn't exist
        """
        if self.active_profile not in self.profiles:
            raise ConfigurationError(
                f"Active profile '{self.active_profile}' not found. "
                f"Available profiles: {', '.join(self.profiles.keys()) or 'none'}"
            )
        return self.profiles[self.active_profile]

    def get_profile(self, name: str) -> ProfileConfig:
        """Get a specific profile by name.

        Args:
            name: Profile name

        Returns:
            The profile configuration

        Raises:
            ConfigurationError: If profile doesn't exist
        """
        if name not in self.profiles:
            raise ConfigurationError(
                f"Profile '{name}' not found. "
                f"Available profiles: {', '.join(self.profiles.keys()) or 'none'}"
            )
        return self.profiles[name]


class ConfigManager:
    """Manages configuration file operations.

    This class handles reading, writing, and securing the configuration file.
    It ensures proper file permissions and validates configuration data.
    """

    def __init__(self, config_dir: Optional[Path] = None):
        """Initialize configuration manager.

        Args:
            config_dir: Custom configuration directory. If None, uses default
                       (~/.truenas-cli or $TRUENAS_CONFIG_DIR)
        """
        if config_dir is None:
            # Check environment variable first
            env_dir = os.getenv("TRUENAS_CONFIG_DIR")
            if env_dir:
                config_dir = Path(env_dir)
            else:
                config_dir = Path.home() / ".truenas-cli"

        self.config_dir = config_dir
        self.config_file = self.config_dir / "config.json"

    def ensure_config_dir(self) -> None:
        """Create configuration directory if it doesn't exist.

        Sets directory permissions to 700 (rwx------) for security.
        """
        if not self.config_dir.exists():
            self.config_dir.mkdir(mode=0o700, parents=True)
        else:
            # Ensure existing directory has correct permissions
            self.config_dir.chmod(0o700)

    def check_config_permissions(self) -> None:
        """Check and fix configuration file permissions.

        Warns user if permissions are too permissive and attempts to fix them.
        Configuration file should be 600 (rw-------) to protect API keys.
        """
        if not self.config_file.exists():
            return

        current_mode = stat.S_IMODE(os.stat(self.config_file).st_mode)
        expected_mode = 0o600

        if current_mode != expected_mode:
            console.print(
                f"[yellow]Warning:[/yellow] Config file has unsafe permissions "
                f"({oct(current_mode)}). Setting to {oct(expected_mode)}..."
            )
            try:
                self.config_file.chmod(expected_mode)
            except Exception as e:
                console.print(
                    f"[red]Error:[/red] Could not fix permissions: {e}\n"
                    f"Please manually set permissions: chmod 600 {self.config_file}"
                )

    def load(self) -> Config:
        """Load configuration from file.

        Returns:
            Configuration object

        Raises:
            ConfigurationError: If configuration file is invalid or cannot be read
        """
        if not self.config_file.exists():
            raise ConfigurationError(
                f"Configuration file not found: {self.config_file}\n"
                "Run 'truenas-cli config init' to create initial configuration"
            )

        self.check_config_permissions()

        try:
            with open(self.config_file, "r") as f:
                data = json.load(f)
            return Config.model_validate(data)
        except json.JSONDecodeError as e:
            raise ConfigurationError(f"Invalid JSON in configuration file: {e}")
        except Exception as e:
            raise ConfigurationError(f"Failed to load configuration: {e}")

    def save(self, config: Config) -> None:
        """Save configuration to file.

        Args:
            config: Configuration object to save

        Raises:
            ConfigurationError: If configuration cannot be saved
        """
        self.ensure_config_dir()

        try:
            # Write to temporary file first
            temp_file = self.config_file.with_suffix(".tmp")
            with open(temp_file, "w") as f:
                f.write(config.model_dump_json(indent=2))

            # Set correct permissions on temp file
            temp_file.chmod(0o600)

            # Atomic rename
            temp_file.replace(self.config_file)

        except Exception as e:
            raise ConfigurationError(f"Failed to save configuration: {e}")

    def exists(self) -> bool:
        """Check if configuration file exists.

        Returns:
            True if configuration file exists, False otherwise
        """
        return self.config_file.exists()

    def add_profile(
        self,
        config: Config,
        name: str,
        url: str,
        api_key: str,
        verify_ssl: bool = True,
        timeout: int = 30,
        set_active: bool = False,
    ) -> Config:
        """Add or update a profile in configuration.

        Args:
            config: Current configuration
            name: Profile name
            url: TrueNAS URL
            api_key: API key
            verify_ssl: Whether to verify SSL certificates
            timeout: Request timeout in seconds
            set_active: Whether to set this profile as active

        Returns:
            Updated configuration object
        """
        profile = ProfileConfig(
            url=url,
            api_key=api_key,
            verify_ssl=verify_ssl,
            timeout=timeout,
        )

        config.profiles[name] = profile

        if set_active or not config.profiles:
            config.active_profile = name

        return config

    def get_profile_or_active(
        self,
        profile_name: Optional[str] = None,
    ) -> tuple[Config, ProfileConfig, str]:
        """Get a specific profile or the active profile.

        Args:
            profile_name: Specific profile name, or None for active profile

        Returns:
            Tuple of (config, profile, profile_name)

        Raises:
            ConfigurationError: If profile doesn't exist or no configuration
        """
        config = self.load()

        if profile_name:
            profile = config.get_profile(profile_name)
            name = profile_name
        else:
            profile = config.get_active_profile()
            name = config.active_profile

        return config, profile, name

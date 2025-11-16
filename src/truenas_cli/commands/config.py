"""Configuration management commands.

This module provides commands for managing CLI configuration including
initializing profiles, listing profiles, and switching between them.
"""

import typer
from rich.console import Console
from rich.table import Table

from truenas_cli.client.exceptions import ConfigurationError
from truenas_cli.config import Config, ConfigManager

app = typer.Typer(
    help="Manage CLI configuration and profiles",
    no_args_is_help=True,
)
console = Console()


@app.command("init")
def init_config(
    profile: str = typer.Option(
        "default",
        "--profile",
        "-p",
        help="Profile name to create or update",
    ),
    url: str = typer.Option(
        ...,
        "--url",
        "-u",
        help="TrueNAS URL (e.g., https://truenas.local)",
        prompt="TrueNAS URL",
    ),
    api_key: str = typer.Option(
        ...,
        "--api-key",
        "-k",
        help="API key for authentication",
        prompt="API Key",
        hide_input=True,
    ),
    verify_ssl: bool = typer.Option(
        True,
        "--verify-ssl/--no-verify-ssl",
        help="Verify SSL certificates",
    ),
    timeout: int = typer.Option(
        30,
        "--timeout",
        "-t",
        help="Request timeout in seconds",
    ),
    set_active: bool = typer.Option(
        True,
        "--set-active/--no-set-active",
        help="Set this profile as active",
    ),
) -> None:
    """Initialize or update a configuration profile.

    This command creates a new profile or updates an existing one with
    the provided connection details. The configuration is stored securely
    with appropriate file permissions.

    Examples:
        # Interactive setup (recommended)
        truenas-cli config init

        # Non-interactive setup
        truenas-cli config init --url https://truenas.local --api-key YOUR_KEY

        # Create a production profile
        truenas-cli config init --profile production
    """
    config_mgr = ConfigManager()

    # Load existing config or create new
    try:
        config = config_mgr.load()
        is_new = False
    except ConfigurationError:
        config = Config(active_profile="default", profiles={})
        is_new = True

    # Check if updating existing profile
    is_update = profile in config.profiles

    # Add or update profile
    config = config_mgr.add_profile(
        config=config,
        name=profile,
        url=url,
        api_key=api_key,
        verify_ssl=verify_ssl,
        timeout=timeout,
        set_active=set_active,
    )

    # Save configuration
    config_mgr.save(config)

    # Show success message
    if is_new:
        console.print("[green]Configuration initialized successfully![/green]")
    elif is_update:
        console.print(f"[green]Profile '{profile}' updated successfully![/green]")
    else:
        console.print(f"[green]Profile '{profile}' created successfully![/green]")

    if set_active:
        console.print(f"[dim]Active profile set to: {profile}[/dim]")

    console.print(f"\n[dim]Configuration saved to: {config_mgr.config_file}[/dim]")

    # Show warning if SSL verification is disabled
    if not verify_ssl:
        console.print(
            "\n[yellow]Warning:[/yellow] SSL verification is disabled. "
            "This is not recommended for production use."
        )


@app.command("list")
def list_profiles() -> None:
    """List all configured profiles.

    Shows all available profiles with their connection details
    (API keys are hidden for security).

    Examples:
        truenas-cli config list
    """
    config_mgr = ConfigManager()

    try:
        config = config_mgr.load()
    except ConfigurationError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(3)

    if not config.profiles:
        console.print("[yellow]No profiles configured.[/yellow]")
        console.print("\nRun 'truenas-cli config init' to create your first profile.")
        return

    # Create table
    table = Table(title="TrueNAS CLI Profiles", show_header=True, header_style="bold magenta")
    table.add_column("Profile", style="cyan", no_wrap=True)
    table.add_column("URL", style="green")
    table.add_column("SSL", style="yellow")
    table.add_column("Timeout", style="blue")
    table.add_column("Active", style="bold green")

    # Add rows
    for name, profile in config.profiles.items():
        is_active = "✓" if name == config.active_profile else ""
        ssl_status = "✓" if profile.verify_ssl else "✗"

        table.add_row(
            name,
            profile.url,
            ssl_status,
            f"{profile.timeout}s",
            is_active,
        )

    console.print(table)


@app.command("show")
def show_config(
    profile: str = typer.Option(
        None,
        "--profile",
        "-p",
        help="Profile to show (defaults to active profile)",
    ),
) -> None:
    """Show configuration details for a profile.

    Displays connection details for the specified profile or the active profile.
    API key is partially masked for security.

    Examples:
        # Show active profile
        truenas-cli config show

        # Show specific profile
        truenas-cli config show --profile production
    """
    config_mgr = ConfigManager()

    try:
        config, profile_config, profile_name = config_mgr.get_profile_or_active(profile)
    except ConfigurationError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(3)

    # Mask API key (show first 8 and last 4 characters)
    api_key = profile_config.api_key
    if len(api_key) > 12:
        masked_key = f"{api_key[:8]}...{api_key[-4:]}"
    else:
        masked_key = "***"

    # Create info table
    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column("Property", style="cyan bold")
    table.add_column("Value", style="green")

    table.add_row("Profile", profile_name)
    table.add_row("URL", profile_config.url)
    table.add_row("API Key", masked_key)
    table.add_row("Verify SSL", "✓ Yes" if profile_config.verify_ssl else "✗ No")
    table.add_row("Timeout", f"{profile_config.timeout} seconds")
    table.add_row("Active", "✓ Yes" if profile_name == config.active_profile else "No")

    console.print(table)


@app.command("set-profile", no_args_is_help=True)
def set_active_profile(
    profile: str = typer.Argument(..., help="Profile name to activate"),
) -> None:
    """Set the active profile.

    Changes which profile is used by default for commands.

    Examples:
        truenas-cli config set-profile production
    """
    config_mgr = ConfigManager()

    try:
        config = config_mgr.load()
    except ConfigurationError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(3)

    # Check if profile exists
    if profile not in config.profiles:
        console.print(f"[red]Error:[/red] Profile '{profile}' not found.")
        console.print(f"\nAvailable profiles: {', '.join(config.profiles.keys())}")
        raise typer.Exit(3)

    # Update active profile
    config.active_profile = profile
    config_mgr.save(config)

    console.print(f"[green]Active profile set to:[/green] {profile}")


@app.command("delete", no_args_is_help=True)
def delete_profile(
    profile: str = typer.Argument(..., help="Profile name to delete"),
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="Delete without confirmation",
    ),
) -> None:
    """Delete a configuration profile.

    Removes a profile from the configuration. Cannot delete the active profile
    unless it's the only profile remaining.

    Examples:
        truenas-cli config delete old-server
        truenas-cli config delete test --force
    """
    config_mgr = ConfigManager()

    try:
        config = config_mgr.load()
    except ConfigurationError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(3)

    # Check if profile exists
    if profile not in config.profiles:
        console.print(f"[red]Error:[/red] Profile '{profile}' not found.")
        raise typer.Exit(3)

    # Prevent deleting active profile if there are others
    if profile == config.active_profile and len(config.profiles) > 1:
        console.print(
            f"[red]Error:[/red] Cannot delete active profile '{profile}'.\n"
            "Set another profile as active first using 'truenas-cli config set-profile'."
        )
        raise typer.Exit(3)

    # Confirm deletion
    if not force:
        confirm = typer.confirm(f"Are you sure you want to delete profile '{profile}'?")
        if not confirm:
            console.print("[yellow]Deletion cancelled.[/yellow]")
            return

    # Delete profile
    del config.profiles[profile]

    # If this was the last profile, clear active profile
    if not config.profiles:
        config.active_profile = "default"

    config_mgr.save(config)

    console.print(f"[green]Profile '{profile}' deleted successfully.[/green]")


@app.command("validate")
def validate_config() -> None:
    """Validate configuration file syntax and structure.

    Checks:
    - Configuration file exists and is readable
    - JSON syntax is valid
    - All required fields are present
    - File permissions are secure

    Examples:
        truenas-cli config validate
    """
    config_mgr = ConfigManager()

    issues = []

    # Check if config file exists
    if not config_mgr.config_file.exists():
        console.print("[red]Configuration file not found.[/red]")
        console.print(f"\nExpected location: {config_mgr.config_file}")
        console.print("\n[yellow]Tip:[/yellow] Run 'truenas-cli config init' to create configuration")
        raise typer.Exit(3)

    # Check file permissions
    import stat

    file_stat = config_mgr.config_file.stat()
    mode = file_stat.st_mode

    # Check if file is readable by owner only (600 or 400)
    if mode & (stat.S_IRWXG | stat.S_IRWXO):
        issues.append(
            "File permissions are too open. "
            f"Current: {oct(mode)[-3:]}, Expected: 600"
        )

    # Try to load configuration
    try:
        config = config_mgr.load()

        # Validate active profile exists
        if config.active_profile not in config.profiles:
            issues.append(f"Active profile '{config.active_profile}' not found in profiles")

        # Validate each profile
        for name, profile in config.profiles.items():
            if not profile.url:
                issues.append(f"Profile '{name}': Missing URL")
            elif not profile.url.startswith(("http://", "https://")):
                issues.append(f"Profile '{name}': Invalid URL format")

            if not profile.api_key:
                issues.append(f"Profile '{name}': Missing API key")

            if profile.timeout <= 0:
                issues.append(f"Profile '{name}': Invalid timeout value")

    except Exception as e:
        issues.append(f"Configuration file is invalid: {e}")

    # Print results
    if issues:
        console.print("[red]Configuration validation failed:[/red]\n")
        for issue in issues:
            console.print(f"  [red]✗[/red] {issue}")
        raise typer.Exit(1)
    else:
        console.print("[green]Configuration is valid![/green]")
        console.print(f"\n[dim]Configuration file: {config_mgr.config_file}[/dim]")
        console.print(f"[dim]Profiles: {len(config.profiles)}[/dim]")
        console.print(f"[dim]Active profile: {config.active_profile}[/dim]")


@app.command("test")
def test_connection(
    profile: str = typer.Option(
        None,
        "--profile",
        "-p",
        help="Profile to test (defaults to active profile)",
    ),
) -> None:
    """Test connection to TrueNAS API.

    Verifies:
    - Network connectivity
    - API endpoint is reachable
    - Authentication is successful
    - API version compatibility

    Examples:
        # Test active profile
        truenas-cli config test

        # Test specific profile
        truenas-cli config test --profile production
    """
    from truenas_cli.client.base import TrueNASClient

    config_mgr = ConfigManager()

    try:
        config, profile_config, profile_name = config_mgr.get_profile_or_active(profile)
    except ConfigurationError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(3)

    console.print(f"Testing connection to [cyan]{profile_name}[/cyan]...\n")

    # Create client
    client = TrueNASClient(profile_config, verbose=False)

    tests = []

    # Test 1: Network connectivity
    try:
        import httpx

        with httpx.Client(verify=profile_config.verify_ssl, timeout=5.0) as http_client:
            response = http_client.get(profile_config.url)
        tests.append(("Network connectivity", True, None))
    except Exception as e:
        tests.append(("Network connectivity", False, str(e)))

    # Test 2: API endpoint
    try:
        client.get("system/info")
        tests.append(("API endpoint", True, None))
    except Exception as e:
        tests.append(("API endpoint", False, str(e)))

    # Test 3: Authentication
    try:
        info = client.get("system/info")
        if info:
            tests.append(("Authentication", True, None))
        else:
            tests.append(("Authentication", False, "No response from API"))
    except Exception as e:
        tests.append(("Authentication", False, str(e)))

    # Test 4: API version
    try:
        version = client.get("system/version")
        if version:
            tests.append(("API version", True, f"TrueNAS {version}"))
        else:
            tests.append(("API version", False, "Could not retrieve version"))
    except Exception as e:
        tests.append(("API version", False, str(e)))

    # Print results
    from rich.table import Table

    table = Table(title="Connection Test Results", show_header=True)
    table.add_column("Test", style="cyan")
    table.add_column("Status", style="bold")
    table.add_column("Details", style="dim")

    all_passed = True
    for test_name, passed, details in tests:
        if passed:
            status = "[green]✓ PASS[/green]"
            detail_text = details or "OK"
        else:
            status = "[red]✗ FAIL[/red]"
            detail_text = details or "Failed"
            all_passed = False

        table.add_row(test_name, status, detail_text)

    console.print(table)

    if all_passed:
        console.print("\n[green]All tests passed![/green]")
    else:
        console.print("\n[red]Some tests failed.[/red]")
        console.print("\n[yellow]Troubleshooting tips:[/yellow]")
        console.print("  1. Verify TrueNAS URL is correct and accessible")
        console.print("  2. Check API key is valid and not revoked")
        console.print("  3. Ensure firewall allows connections")
        console.print("  4. Try disabling SSL verification if using self-signed certificate")
        raise typer.Exit(1)


@app.command("doctor")
def doctor() -> None:
    """Run comprehensive configuration health check.

    Performs:
    - Configuration validation
    - Connection test
    - Permission checks
    - Common issue detection

    This is a combination of validate and test with additional diagnostics.

    Examples:
        truenas-cli config doctor
    """
    from rich.panel import Panel

    console.print(Panel("[bold]TrueNAS CLI Configuration Doctor[/bold]", expand=False))
    console.print()

    issues = []
    warnings = []

    # Check 1: Configuration file
    console.print("[bold]1. Checking configuration file...[/bold]")
    config_mgr = ConfigManager()

    if not config_mgr.config_file.exists():
        issues.append("Configuration file does not exist")
        console.print("  [red]✗[/red] Configuration file not found")
        console.print("\n[yellow]Run 'truenas-cli config init' to create configuration[/yellow]")
        raise typer.Exit(1)
    else:
        console.print("  [green]✓[/green] Configuration file exists")

    # Check 2: File permissions
    console.print("\n[bold]2. Checking file permissions...[/bold]")
    import stat

    file_stat = config_mgr.config_file.stat()
    mode = file_stat.st_mode

    if mode & (stat.S_IRWXG | stat.S_IRWXO):
        warnings.append(
            f"Configuration file has insecure permissions: {oct(mode)[-3:]}"
        )
        console.print(f"  [yellow]⚠[/yellow] Insecure permissions: {oct(mode)[-3:]}")
        console.print(f"     Run: chmod 600 {config_mgr.config_file}")
    else:
        console.print("  [green]✓[/green] File permissions are secure")

    # Check 3: Configuration validity
    console.print("\n[bold]3. Validating configuration...[/bold]")
    try:
        config = config_mgr.load()
        console.print("  [green]✓[/green] Configuration is valid JSON")

        if not config.profiles:
            issues.append("No profiles configured")
            console.print("  [red]✗[/red] No profiles found")
        else:
            console.print(f"  [green]✓[/green] Found {len(config.profiles)} profile(s)")

        if config.active_profile not in config.profiles:
            issues.append(f"Active profile '{config.active_profile}' not found")
            console.print(f"  [red]✗[/red] Active profile '{config.active_profile}' not found")
        else:
            console.print(f"  [green]✓[/green] Active profile: {config.active_profile}")

    except Exception as e:
        issues.append(f"Configuration is invalid: {e}")
        console.print(f"  [red]✗[/red] Configuration error: {e}")

    # Check 4: Profile validation
    if config and config.profiles:
        console.print("\n[bold]4. Validating profiles...[/bold]")
        for name, profile in config.profiles.items():
            console.print(f"\n  Profile: [cyan]{name}[/cyan]")

            if not profile.url.startswith(("http://", "https://")):
                issues.append(f"Profile '{name}' has invalid URL")
                console.print("    [red]✗[/red] Invalid URL format")
            else:
                console.print("    [green]✓[/green] URL format OK")

            if not profile.verify_ssl:
                warnings.append(f"Profile '{name}' has SSL verification disabled")
                console.print("    [yellow]⚠[/yellow] SSL verification disabled")
            else:
                console.print("    [green]✓[/green] SSL verification enabled")

            if profile.timeout < 10:
                warnings.append(f"Profile '{name}' has low timeout value")
                console.print(f"    [yellow]⚠[/yellow] Timeout is low ({profile.timeout}s)")

    # Check 5: Environment variables
    console.print("\n[bold]5. Checking environment variables...[/bold]")
    import os

    env_vars = ["TRUENAS_URL", "TRUENAS_API_KEY", "TRUENAS_PROFILE"]
    env_set = [var for var in env_vars if os.getenv(var)]

    if env_set:
        console.print(f"  [yellow]⚠[/yellow] Found {len(env_set)} environment variable(s):")
        for var in env_set:
            console.print(f"     - {var}")
        warnings.append("Environment variables will override configuration file")
    else:
        console.print("  [green]✓[/green] No environment variables set")

    # Summary
    console.print("\n" + "=" * 50)
    if issues:
        console.print(f"\n[red]Found {len(issues)} issue(s):[/red]")
        for issue in issues:
            console.print(f"  • {issue}")

    if warnings:
        console.print(f"\n[yellow]Found {len(warnings)} warning(s):[/yellow]")
        for warning in warnings:
            console.print(f"  • {warning}")

    if not issues and not warnings:
        console.print("\n[green]Configuration is healthy![/green]")
    elif issues:
        console.print("\n[red]Please fix the issues above before using the CLI.[/red]")
        raise typer.Exit(1)
    else:
        console.print("\n[yellow]Configuration works but has some warnings.[/yellow]")

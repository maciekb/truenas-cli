"""Share management commands.

This module provides commands for managing NFS and SMB/CIFS shares.
"""


import typer
from rich.console import Console

from truenas_cli.client.base import TrueNASClient
from truenas_cli.client.exceptions import ConfigurationError, TrueNASError
from truenas_cli.config import ConfigManager
from truenas_cli.utils.formatters import format_json_output, format_key_value_output, output_data

app = typer.Typer(
    help="Share management (NFS and SMB)",
    no_args_is_help=True,
)
console = Console()


def get_client(ctx: typer.Context) -> TrueNASClient:
    """Get configured TrueNAS client from context."""
    config_mgr = ConfigManager()
    cli_ctx = ctx.obj

    try:
        _, profile, _ = config_mgr.get_profile_or_active(cli_ctx.profile)
    except ConfigurationError as e:
        console.print(f"[red]Configuration Error:[/red] {e}")
        raise typer.Exit(3)

    return TrueNASClient(profile=profile, verbose=cli_ctx.verbose)


@app.command("list")
def list_shares(
    ctx: typer.Context,
    share_type: str | None = typer.Option(None, "--type", "-t", help="Share type: nfs or smb"),
) -> None:
    """List all shares (NFS and/or SMB).

    Shows all configured shares with their paths and status.

    Examples:
        truenas-cli share list
        truenas-cli share list --type nfs
        truenas-cli share list --type smb
        truenas-cli --output-format json share list
    """
    client = get_client(ctx)
    cli_ctx = ctx.obj

    try:
        shares = []

        # Get NFS shares
        if not share_type or share_type.lower() == "nfs":
            try:
                nfs_shares = client.get_nfs_shares()
                for share in nfs_shares:
                    share["type"] = "NFS"
                    shares.extend(nfs_shares)
            except TrueNASError:
                pass  # NFS might not be configured

        # Get SMB shares
        if not share_type or share_type.lower() == "smb":
            try:
                smb_shares = client.get_smb_shares()
                for share in smb_shares:
                    share["type"] = "SMB"
                    shares.extend(smb_shares)
            except TrueNASError:
                pass  # SMB might not be configured

        if not shares:
            console.print("[yellow]No shares found[/yellow]")
            return

        # Prepare table columns
        table_columns = [
            {"key": "type", "header": "Type", "style": "cyan bold"},
            {"key": "name", "header": "Name", "style": ""},
            {"key": "path", "header": "Path", "style": ""},
            {"key": "enabled", "header": "Enabled", "style": "", "format": "boolean"},
            {"key": "comment", "header": "Comment", "style": "dim"},
        ]

        plain_columns = ["type", "name", "path", "enabled", "comment"]

        # Normalize share data for display
        for share in shares:
            if "name" not in share and "id" in share:
                # NFS shares don't have a name, use path
                share["name"] = share.get("path", f"share-{share['id']}")

        output_data(
            shares,
            output_format=cli_ctx.output_format,
            table_columns=table_columns,
            plain_columns=plain_columns,
            title="Shares",
        )

    except TrueNASError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


@app.command("create-nfs", no_args_is_help=True)
def create_nfs_share(
    ctx: typer.Context,
    path: str = typer.Argument(..., help="Path to share"),
    comment: str | None = typer.Option(None, "--comment", "-c", help="Share description"),
    readonly: bool = typer.Option(False, "--readonly", "-r", help="Read-only share"),
    maproot_user: str | None = typer.Option(None, "--maproot-user", help="Map root to user"),
    maproot_group: str | None = typer.Option(None, "--maproot-group", help="Map root to group"),
    networks: str | None = typer.Option(None, "--networks", help="Allowed networks (comma-separated)"),
) -> None:
    """Create a new NFS share.

    Creates an NFS share for the specified path.

    Examples:
        truenas-cli share create-nfs /mnt/tank/data
        truenas-cli share create-nfs /mnt/tank/data --comment "Public data"
        truenas-cli share create-nfs /mnt/tank/data --readonly
        truenas-cli share create-nfs /mnt/tank/data --networks "192.168.1.0/24,10.0.0.0/8"
    """
    client = get_client(ctx)
    cli_ctx = ctx.obj

    try:
        # Build share configuration
        share_config = {
            "path": path,
            "enabled": True,
        }

        if comment:
            share_config["comment"] = comment

        if readonly:
            share_config["ro"] = True

        if maproot_user:
            share_config["maproot_user"] = maproot_user

        if maproot_group:
            share_config["maproot_group"] = maproot_group

        if networks:
            share_config["networks"] = [n.strip() for n in networks.split(",")]

        # Create share
        result = client.create_nfs_share(share_config)

        if cli_ctx.output_format == "json":
            format_json_output(result)
        else:
            console.print(f"[green]NFS share created for '{path}'[/green]")

            if isinstance(result, dict):
                summary = {
                    "id": result.get("id"),
                    "path": result.get("path"),
                    "enabled": result.get("enabled", True),
                    "comment": result.get("comment", "N/A"),
                }
                format_key_value_output(summary, title="Created NFS Share")

    except TrueNASError as e:
        console.print(f"[red]Error:[/red] {e}")
        if "does not exist" in str(e).lower():
            console.print(f"[yellow]Tip:[/yellow] Ensure path '{path}' exists")
        raise typer.Exit(1)


@app.command("create-smb", no_args_is_help=True)
def create_smb_share(
    ctx: typer.Context,
    name: str = typer.Argument(..., help="Share name"),
    path: str = typer.Argument(..., help="Path to share"),
    comment: str | None = typer.Option(None, "--comment", "-c", help="Share description"),
    readonly: bool = typer.Option(False, "--readonly", "-r", help="Read-only share"),
    guestok: bool = typer.Option(False, "--guest", "-g", help="Allow guest access"),
    browsable: bool = typer.Option(True, "--browsable/--no-browsable", help="Make share browsable"),
) -> None:
    """Create a new SMB share.

    Creates an SMB/CIFS share with the specified name and path.

    Examples:
        truenas-cli share create-smb myshare /mnt/tank/data
        truenas-cli share create-smb myshare /mnt/tank/data --comment "Team files"
        truenas-cli share create-smb public /mnt/tank/public --guest
        truenas-cli share create-smb data /mnt/tank/data --readonly
    """
    client = get_client(ctx)
    cli_ctx = ctx.obj

    try:
        # Build share configuration
        share_config = {
            "name": name,
            "path": path,
            "enabled": True,
            "browsable": browsable,
        }

        if comment:
            share_config["comment"] = comment

        if readonly:
            share_config["ro"] = True

        if guestok:
            share_config["guestok"] = True

        # Create share
        result = client.create_smb_share(share_config)

        if cli_ctx.output_format == "json":
            format_json_output(result)
        else:
            console.print(f"[green]SMB share '{name}' created for '{path}'[/green]")

            if isinstance(result, dict):
                summary = {
                    "id": result.get("id"),
                    "name": result.get("name"),
                    "path": result.get("path"),
                    "enabled": result.get("enabled", True),
                    "comment": result.get("comment", "N/A"),
                }
                format_key_value_output(summary, title="Created SMB Share")

    except TrueNASError as e:
        console.print(f"[red]Error:[/red] {e}")
        if "does not exist" in str(e).lower():
            console.print(f"[yellow]Tip:[/yellow] Ensure path '{path}' exists")
        raise typer.Exit(1)


@app.command("delete", no_args_is_help=True)
def delete_share(
    ctx: typer.Context,
    share_id: int = typer.Argument(..., help="Share ID to delete"),
    share_type: str = typer.Option(..., "--type", "-t", help="Share type: nfs or smb"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
) -> None:
    """Delete a share.

    Deletes an NFS or SMB share by ID.

    Examples:
        truenas-cli share delete 1 --type nfs
        truenas-cli share delete 2 --type smb --yes
    """
    client = get_client(ctx)
    cli_ctx = ctx.obj

    try:
        # Validate share type
        if share_type.lower() not in ["nfs", "smb"]:
            console.print(f"[red]Error:[/red] Invalid share type '{share_type}'")
            console.print("[yellow]Valid types:[/yellow] nfs, smb")
            raise typer.Exit(1)

        # Get share info for confirmation
        try:
            if share_type.lower() == "nfs":
                share = client.get_nfs_share(share_id)
                share_name = share.get("path", f"NFS-{share_id}")
            else:
                share = client.get_smb_share(share_id)
                share_name = share.get("name", f"SMB-{share_id}")
        except TrueNASError:
            console.print(f"[red]Error:[/red] {share_type.upper()} share with ID {share_id} not found")
            raise typer.Exit(1)

        # Confirmation prompt unless --yes flag is used
        if not yes:
            console.print(f"[yellow]Warning:[/yellow] You are about to delete {share_type.upper()} share '{share_name}'")
            confirm = typer.confirm("Are you sure you want to continue?")
            if not confirm:
                console.print("[yellow]Operation cancelled[/yellow]")
                raise typer.Exit(0)

        # Delete share
        if share_type.lower() == "nfs":
            result = client.delete_nfs_share(share_id)
        else:
            result = client.delete_smb_share(share_id)

        if cli_ctx.output_format == "json":
            format_json_output({"status": "deleted", "id": share_id, "type": share_type})
        else:
            console.print(f"[green]{share_type.upper()} share '{share_name}' deleted successfully[/green]")

    except TrueNASError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


@app.command("info", no_args_is_help=True)
def share_info(
    ctx: typer.Context,
    share_id: int = typer.Argument(..., help="Share ID"),
    share_type: str = typer.Option(..., "--type", "-t", help="Share type: nfs or smb"),
) -> None:
    """Show detailed information about a share.

    Displays comprehensive information about an NFS or SMB share.

    Examples:
        truenas-cli share info 1 --type nfs
        truenas-cli share info 2 --type smb
        truenas-cli --output-format json share info 1 --type nfs
    """
    client = get_client(ctx)
    cli_ctx = ctx.obj

    try:
        # Validate share type
        if share_type.lower() not in ["nfs", "smb"]:
            console.print(f"[red]Error:[/red] Invalid share type '{share_type}'")
            console.print("[yellow]Valid types:[/yellow] nfs, smb")
            raise typer.Exit(1)

        # Get share info
        if share_type.lower() == "nfs":
            share = client.get_nfs_share(share_id)
        else:
            share = client.get_smb_share(share_id)

        if cli_ctx.output_format == "json":
            format_json_output(share)
        else:
            # Build summary
            if share_type.lower() == "nfs":
                summary = {
                    "id": share.get("id"),
                    "path": share.get("path"),
                    "enabled": share.get("enabled"),
                    "readonly": share.get("ro", False),
                    "comment": share.get("comment", "N/A"),
                }
                if share.get("networks"):
                    summary["networks"] = ", ".join(share["networks"])
                if share.get("maproot_user"):
                    summary["maproot_user"] = share["maproot_user"]
            else:
                summary = {
                    "id": share.get("id"),
                    "name": share.get("name"),
                    "path": share.get("path"),
                    "enabled": share.get("enabled"),
                    "readonly": share.get("ro", False),
                    "browsable": share.get("browsable", True),
                    "guestok": share.get("guestok", False),
                    "comment": share.get("comment", "N/A"),
                }

            format_key_value_output(summary, title=f"{share_type.upper()} Share Information")

    except TrueNASError as e:
        console.print(f"[red]Error:[/red] {e}")
        if "not found" in str(e).lower():
            console.print(f"[yellow]Tip:[/yellow] {share_type.upper()} share with ID {share_id} does not exist")
        raise typer.Exit(1)

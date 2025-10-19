"""Cloud Sync operations (cloudsync.* API)."""

from __future__ import annotations

import argparse
import json

from typing import Any, Dict

from truenas_client import TrueNASClient

from ..core import run_command
from ..validation import parse_json_argument
from .base import CommandGroup


class CloudSyncCommands(CommandGroup):
    """Cloud Sync operations (``cloudsync.*`` API)."""

    name = "cloudsync"

    def register_commands(
        self,
        subparsers: argparse._SubParsersAction,
        parent_parser: argparse.ArgumentParser,
    ) -> None:
        """Register cloudsync subcommands."""
        # List cloud sync tasks
        list_parser = self.add_command(
            subparsers,
            "list",
            "List all cloud sync tasks (cloudsync.query)",
            _cmd_cloudsync_list,
            parent_parser=parent_parser,
        )
        self.add_optional_argument(
            list_parser,
            "--full",
            "full",
            "Show all available fields",
            action="store_true",
        )

        # Get task info
        info_parser = self.add_command(
            subparsers,
            "info",
            "Get cloud sync task details (cloudsync.get_instance)",
            _cmd_cloudsync_info,
            parent_parser=parent_parser,
        )
        self.add_required_argument(
            info_parser,
            "task_id",
            "Cloud sync task ID",
            type=int,
        )

        # Create cloud sync task
        create_parser = self.add_command(
            subparsers,
            "create",
            "Create a new cloud sync task (cloudsync.create)",
            _cmd_cloudsync_create,
            parent_parser=parent_parser,
        )
        self.add_required_argument(
            create_parser,
            "path",
            "Local path (must start with /mnt)",
        )
        self.add_required_argument(
            create_parser,
            "credentials",
            "Credential ID",
            type=int,
        )
        self.add_required_argument(
            create_parser,
            "direction",
            "Sync direction (PUSH or PULL)",
        )
        self.add_required_argument(
            create_parser,
            "transfer_mode",
            "Transfer mode (SYNC, COPY, or MOVE)",
        )
        self.add_required_argument(
            create_parser,
            "bucket",
            "Bucket/container name",
        )
        self.add_optional_argument(
            create_parser,
            "--folder",
            "folder",
            "Remote folder path",
            default="",
        )
        self.add_optional_argument(
            create_parser,
            "--description",
            "description",
            "Task description",
        )
        self.add_optional_argument(
            create_parser,
            "--enabled",
            "enabled",
            "Enable the task",
            action="store_true",
        )

        # Update cloud sync task
        update_parser = self.add_command(
            subparsers,
            "update",
            "Update a cloud sync task (cloudsync.update)",
            _cmd_cloudsync_update,
            parent_parser=parent_parser,
        )
        self.add_required_argument(
            update_parser,
            "task_id",
            "Cloud sync task ID",
            type=int,
        )
        self.add_optional_argument(
            update_parser,
            "--description",
            "description",
            "New task description",
        )
        self.add_optional_argument(
            update_parser,
            "--enabled",
            "enabled",
            "Enable/disable task (true/false)",
        )

        # Delete cloud sync task
        delete_parser = self.add_command(
            subparsers,
            "delete",
            "Delete a cloud sync task (cloudsync.delete)",
            _cmd_cloudsync_delete,
            parent_parser=parent_parser,
        )
        self.add_required_argument(
            delete_parser,
            "task_id",
            "Cloud sync task ID",
            type=int,
        )

        # Run cloud sync task
        sync_parser = self.add_command(
            subparsers,
            "sync",
            "Run a cloud sync task (cloudsync.sync)",
            _cmd_cloudsync_sync,
            parent_parser=parent_parser,
        )
        self.add_required_argument(
            sync_parser,
            "task_id",
            "Cloud sync task ID",
            type=int,
        )
        # Note: --dry-run is inherited from parent_parser global options

        # Abort cloud sync task
        abort_parser = self.add_command(
            subparsers,
            "abort",
            "Abort a running cloud sync task (cloudsync.abort)",
            _cmd_cloudsync_abort,
            parent_parser=parent_parser,
        )
        self.add_required_argument(
            abort_parser,
            "task_id",
            "Cloud sync task ID",
            type=int,
        )

        # List providers
        self.add_command(
            subparsers,
            "providers",
            "List supported cloud providers (cloudsync.providers)",
            _cmd_cloudsync_providers,
            parent_parser=parent_parser,
        )

        # List buckets
        buckets_parser = self.add_command(
            subparsers,
            "list-buckets",
            "List buckets for credentials (cloudsync.list_buckets)",
            _cmd_cloudsync_list_buckets,
            parent_parser=parent_parser,
        )
        self.add_required_argument(
            buckets_parser,
            "credentials",
            "Credential ID",
            type=int,
        )

        # Credentials subcommands
        parents = [parent_parser] if parent_parser else []
        creds_parser = subparsers.add_parser(
            "creds",
            help="Cloud sync credentials operations",
            parents=parents,
        )
        creds_parser.set_defaults(
            func=_cmd_cloudsync_creds_root,
            _creds_parser=creds_parser,
        )
        creds_subparsers = creds_parser.add_subparsers(dest="creds_command")

        # List credentials
        creds_list_parser = creds_subparsers.add_parser(
            "list",
            help="List all cloud sync credentials",
            parents=[parent_parser] if parent_parser else [],
        )
        creds_list_parser.set_defaults(func=_cmd_cloudsync_creds_list)
        self.add_optional_argument(
            creds_list_parser,
            "--full",
            "full",
            "Show all available fields",
            action="store_true",
        )

        # Get credential info
        creds_info_parser = creds_subparsers.add_parser(
            "info",
            help="Get cloud sync credential details",
            parents=[parent_parser] if parent_parser else [],
        )
        creds_info_parser.set_defaults(func=_cmd_cloudsync_creds_info)
        self.add_required_argument(
            creds_info_parser,
            "cred_id",
            "Credential ID",
            type=int,
        )

        # Create credentials
        creds_create_parser = creds_subparsers.add_parser(
            "create",
            help="Create cloud sync credentials",
            parents=[parent_parser] if parent_parser else [],
        )
        creds_create_parser.set_defaults(func=_cmd_cloudsync_creds_create)
        self.add_required_argument(
            creds_create_parser,
            "name",
            "Credential name",
        )
        self.add_required_argument(
            creds_create_parser,
            "provider",
            "Cloud provider (S3, DROPBOX, GOOGLE_DRIVE, etc.)",
        )
        self.add_required_argument(
            creds_create_parser,
            "attributes",
            "Provider attributes as JSON string or @path to file",
        )

        # Delete credentials
        creds_delete_parser = creds_subparsers.add_parser(
            "delete",
            help="Delete cloud sync credentials",
            parents=[parent_parser] if parent_parser else [],
        )
        creds_delete_parser.set_defaults(func=_cmd_cloudsync_creds_delete)
        self.add_required_argument(
            creds_delete_parser,
            "cred_id",
            "Credential ID",
            type=int,
        )

        # Verify credentials
        creds_verify_parser = creds_subparsers.add_parser(
            "verify",
            help="Verify cloud sync credentials",
            parents=[parent_parser] if parent_parser else [],
        )
        creds_verify_parser.set_defaults(func=_cmd_cloudsync_creds_verify)
        self.add_required_argument(
            creds_verify_parser,
            "provider",
            "Cloud provider",
        )
        self.add_required_argument(
            creds_verify_parser,
            "attributes",
            "Provider attributes as JSON string or @path to file",
        )


async def _cmd_cloudsync_creds_root(args: argparse.Namespace) -> None:
    """Handle ``cloudsync creds`` root command by showing contextual help."""

    parser = getattr(args, "_creds_parser", None)
    if isinstance(parser, argparse.ArgumentParser):
        parser.print_help()
    else:
        print("Specify a credentials subcommand. Use --help for available options.")


async def _cmd_cloudsync_list(args: argparse.Namespace) -> None:
    """Handle ``cloudsync list`` command."""

    async def handler(client: TrueNASClient) -> None:
        tasks = await client.get_cloudsync_tasks()

        if args.json:
            print(json.dumps(tasks, indent=2))
            return

        print("\n=== Cloud Sync Tasks ===")
        if not tasks:
            print("No cloud sync tasks found.")
            return

        for task in tasks:
            task_id = task.get("id", "N/A")
            description = task.get("description", "N/A")
            direction = task.get("direction", "N/A")
            enabled = task.get("enabled", False)

            status_icon = "[✓]" if enabled else "[✗]"
            print(f"\n{status_icon} [{task_id}] {description}")
            print(f"  Direction: {direction}")

            if args.full:
                transfer_mode = task.get("transfer_mode", "N/A")
                path = task.get("path", "N/A")

                print(f"  Transfer Mode: {transfer_mode}")
                print(f"  Local Path: {path}")

                if task.get("attributes"):
                    attrs = task["attributes"]
                    if attrs.get("bucket"):
                        print(f"  Bucket: {attrs['bucket']}")
                    if attrs.get("folder"):
                        print(f"  Folder: {attrs['folder']}")

                if task.get("job"):
                    job = task["job"]
                    if job.get("state"):
                        print(f"  Job State: {job['state']}")

    await run_command(args, handler)


async def _cmd_cloudsync_info(args: argparse.Namespace) -> None:
    """Handle ``cloudsync info`` command."""

    async def handler(client: TrueNASClient) -> None:
        task = await client.get_cloudsync_task(args.task_id)

        if args.json:
            print(json.dumps(task, indent=2))
            return

        task_id = task.get("id", "N/A")
        description = task.get("description", "N/A")
        direction = task.get("direction", "N/A")
        transfer_mode = task.get("transfer_mode", "N/A")
        enabled = task.get("enabled", False)

        print(f"\n=== Cloud Sync Task: {description} (ID {task_id}) ===")
        print(f"Direction: {direction}")
        print(f"Transfer Mode: {transfer_mode}")
        print(f"Enabled: {'Yes' if enabled else 'No'}")

        # Local path
        path = task.get("path", "N/A")
        print(f"\nLocal Path: {path}")

        # Cloud attributes
        if task.get("attributes"):
            attrs = task["attributes"]
            print("\nCloud Storage:")
            if attrs.get("bucket"):
                print(f"  Bucket: {attrs['bucket']}")
            if attrs.get("folder"):
                print(f"  Folder: {attrs['folder']}")

        # Credentials
        if task.get("credentials"):
            creds = task["credentials"]
            if isinstance(creds, dict):
                print(f"Credentials: {creds.get('name', 'N/A')}")

        # Settings
        if task.get("encryption"):
            print("Encryption: Enabled")
        if task.get("snapshot"):
            print("Snapshot: Yes")

        # Job info
        if task.get("job"):
            job = task["job"]
            print("\nCurrent Job:")
            if job.get("state"):
                print(f"  State: {job['state']}")
            if job.get("progress"):
                progress = job["progress"]
                if isinstance(progress, dict) and progress.get("percent"):
                    print(f"  Progress: {progress['percent']}%")

    await run_command(args, handler)


async def _cmd_cloudsync_create(args: argparse.Namespace) -> None:
    """Handle ``cloudsync create`` command."""

    async def handler(client: TrueNASClient) -> None:
        # Validate direction
        direction = args.direction.upper()
        if direction not in ("PUSH", "PULL"):
            raise ValueError("Direction must be PUSH or PULL")

        # Validate transfer_mode
        transfer_mode = args.transfer_mode.upper()
        if transfer_mode not in ("SYNC", "COPY", "MOVE"):
            raise ValueError("Transfer mode must be SYNC, COPY, or MOVE")

        # Build attributes
        attributes = {"bucket": args.bucket}
        if args.folder:
            attributes["folder"] = args.folder

        # Build kwargs
        kwargs = {}
        if args.description:
            kwargs["description"] = args.description
        if args.enabled:
            kwargs["enabled"] = True

        print("Creating cloud sync task...")

        task = await client.create_cloudsync_task(
            path=args.path,
            credentials=args.credentials,
            direction=direction,
            transfer_mode=transfer_mode,
            attributes=attributes,
            **kwargs,
        )

        if args.json:
            print(json.dumps(task, indent=2))
            return

        task_id = task.get("id", "N/A")
        description = task.get("description", "Cloud sync task")
        print(f"✓ Cloud sync task '{description}' created successfully (ID {task_id})")

    await run_command(args, handler)


async def _cmd_cloudsync_update(args: argparse.Namespace) -> None:
    """Handle ``cloudsync update`` command."""

    async def handler(client: TrueNASClient) -> None:
        kwargs = {}

        if args.description:
            kwargs["description"] = args.description

        if args.enabled is not None:
            enabled_value = str(args.enabled) if args.enabled is not None else ""
            kwargs["enabled"] = enabled_value.lower() in ("true", "yes", "1")

        if not kwargs:
            raise ValueError("No update parameters provided")

        print(f"Updating cloud sync task ID {args.task_id}...")

        task = await client.update_cloudsync_task(args.task_id, **kwargs)

        if args.json:
            print(json.dumps(task, indent=2))
            return

        print(f"✓ Cloud sync task ID {args.task_id} updated successfully")

    await run_command(args, handler)


async def _cmd_cloudsync_delete(args: argparse.Namespace) -> None:
    """Handle ``cloudsync delete`` command."""

    async def handler(client: TrueNASClient) -> None:
        print(f"Deleting cloud sync task ID {args.task_id}...")

        result = await client.delete_cloudsync_task(args.task_id)

        if args.json:
            print(json.dumps({"success": result}, indent=2))
            return

        print(f"✓ Cloud sync task ID {args.task_id} deleted successfully")

    await run_command(args, handler)


async def _cmd_cloudsync_sync(args: argparse.Namespace) -> None:
    """Handle ``cloudsync sync`` command."""

    async def handler(client: TrueNASClient) -> None:
        dry_run_msg = " (dry run)" if args.dry_run else ""
        print(f"Running cloud sync task ID {args.task_id}{dry_run_msg}...")

        await client.sync_cloudsync_task(args.task_id, dry_run=args.dry_run)

        if args.json:
            print(json.dumps({"success": True, "message": "Job started"}, indent=2))
            return

        print(f"✓ Cloud sync task ID {args.task_id} started successfully")
        print("  Monitor job progress via the TrueNAS web interface")

    await run_command(args, handler)


async def _cmd_cloudsync_abort(args: argparse.Namespace) -> None:
    """Handle ``cloudsync abort`` command."""

    async def handler(client: TrueNASClient) -> None:
        print(f"Aborting cloud sync task ID {args.task_id}...")

        result = await client.abort_cloudsync_task(args.task_id)

        if args.json:
            print(json.dumps({"success": result}, indent=2))
            return

        print(f"✓ Cloud sync task ID {args.task_id} aborted successfully")

    await run_command(args, handler)


async def _cmd_cloudsync_providers(args: argparse.Namespace) -> None:
    """Handle ``cloudsync providers`` command."""

    async def handler(client: TrueNASClient) -> None:
        providers = await client.list_cloudsync_providers()

        if args.json:
            print(json.dumps(providers, indent=2))
            return

        print("\n=== Supported Cloud Providers ===")
        for provider in providers:
            name = provider.get("name", "N/A")
            title = provider.get("title", "N/A")
            buckets = provider.get("buckets", False)

            print(f"\n{title} ({name})")
            if buckets:
                bucket_title = provider.get("bucket_title", "bucket")
                print(f"  Supports {bucket_title}s")
            if provider.get("credentials_oauth"):
                print("  OAuth supported")

    await run_command(args, handler)


async def _cmd_cloudsync_list_buckets(args: argparse.Namespace) -> None:
    """Handle ``cloudsync list-buckets`` command."""

    async def handler(client: TrueNASClient) -> None:
        buckets = await client.list_cloudsync_buckets(args.credentials)

        if args.json:
            print(json.dumps(buckets, indent=2))
            return

        print("\n=== Buckets ===")
        for bucket in buckets:
            if isinstance(bucket, dict):
                name = bucket.get("Name", bucket.get("name", "N/A"))
                print(f"  {name}")
            else:
                print(f"  {bucket}")

    await run_command(args, handler)


# Credentials commands
async def _cmd_cloudsync_creds_list(args: argparse.Namespace) -> None:
    """Handle ``cloudsync creds list`` command."""

    async def handler(client: TrueNASClient) -> None:
        creds = await client.get_cloudsync_credentials()

        if args.json:
            print(json.dumps(creds, indent=2))
            return

        print("\n=== Cloud Sync Credentials ===")
        if not creds:
            print("No cloud sync credentials found.")
            return

        for cred in creds:
            cred_id = cred.get("id", "N/A")
            name = cred.get("name", "N/A")
            provider = cred.get("provider", "N/A")

            print(f"\n[{cred_id}] {name}")
            print(f"  Provider: {provider}")

            if args.full and cred.get("attributes"):
                attrs = cred["attributes"]
                print(f"  Attributes: {len(attrs)} configured")

    await run_command(args, handler)


async def _cmd_cloudsync_creds_info(args: argparse.Namespace) -> None:
    """Handle ``cloudsync creds info`` command."""

    async def handler(client: TrueNASClient) -> None:
        cred = await client.get_cloudsync_credential(args.cred_id)

        if args.json:
            print(json.dumps(cred, indent=2))
            return

        cred_id = cred.get("id", "N/A")
        name = cred.get("name", "N/A")
        provider = cred.get("provider", "N/A")

        print(f"\n=== Cloud Sync Credential: {name} (ID {cred_id}) ===")
        print(f"Provider: {provider}")

        if cred.get("attributes"):
            attrs = cred["attributes"]
            print("\nConfigured Attributes:")
            for key in attrs:
                # Hide sensitive values
                if "secret" in key.lower() or "password" in key.lower():
                    print(f"  {key}: ********")
                else:
                    print(f"  {key}: {attrs[key]}")

    await run_command(args, handler)


async def _cmd_cloudsync_creds_create(args: argparse.Namespace) -> None:
    """Handle ``cloudsync creds create`` command."""

    async def handler(client: TrueNASClient) -> None:
        attributes = parse_json_argument(args.attributes, name="attributes")

        print(f"Creating cloud sync credentials: {args.name}...")

        cred = await client.create_cloudsync_credential(
            name=args.name, provider=args.provider, attributes=attributes
        )

        if args.json:
            print(json.dumps(cred, indent=2))
            return

        cred_id = cred.get("id", "N/A")
        print(
            f"✓ Cloud sync credentials '{args.name}' created successfully (ID {cred_id})"
        )

    await run_command(args, handler)


async def _cmd_cloudsync_creds_delete(args: argparse.Namespace) -> None:
    """Handle ``cloudsync creds delete`` command."""

    async def handler(client: TrueNASClient) -> None:
        print(f"Deleting cloud sync credentials ID {args.cred_id}...")

        result = await client.delete_cloudsync_credential(args.cred_id)

        if args.json:
            payload: Dict[str, Any] = {"success": bool(result)}
            if not result:
                payload["error"] = (
                    "TrueNAS did not confirm removal. Verify the credential is not in use."
                )
            print(json.dumps(payload, indent=2))
            if not result:
                raise ValueError(payload["error"])
            return

        if not result:
            raise ValueError(
                "Deletion failed: TrueNAS did not confirm removal. "
                "Verify the credential is not in use."
            )

        print(f"✓ Cloud sync credentials ID {args.cred_id} deleted successfully")

    await run_command(args, handler)


async def _cmd_cloudsync_creds_verify(args: argparse.Namespace) -> None:
    """Handle ``cloudsync creds verify`` command."""

    async def handler(client: TrueNASClient) -> None:
        attributes = parse_json_argument(args.attributes, name="attributes")

        print(f"Verifying cloud sync credentials for {args.provider}...")

        result = await client.verify_cloudsync_credential(
            provider=args.provider, attributes=attributes
        )

        if args.json:
            print(json.dumps(result, indent=2))
            return

        # Check verification result
        valid = result.get("valid", False)
        if valid:
            print("✓ Credentials are valid")
        else:
            print("✗ Credentials are invalid")
            if result.get("error"):
                print(f"  Error: {result['error']}")

    await run_command(args, handler)

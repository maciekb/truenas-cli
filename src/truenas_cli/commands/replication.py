"""Replication task operations (replication.* API)."""

from __future__ import annotations

import argparse
import json

from truenas_client import TrueNASClient

from ..core import run_command
from .base import CommandGroup


class ReplicationCommands(CommandGroup):
    """Replication task operations (``replication.*`` API)."""

    name = "replication"

    def register_commands(
        self,
        subparsers: argparse._SubParsersAction,
        parent_parser: argparse.ArgumentParser,
    ) -> None:
        """Register replication subcommands."""
        # List replication tasks
        list_parser = self.add_command(
            subparsers,
            "list",
            "List all replication tasks (replication.query)",
            _cmd_replication_list,
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
            "Get replication task details (replication.get_instance)",
            _cmd_replication_info,
            parent_parser=parent_parser,
        )
        self.add_required_argument(
            info_parser,
            "task_id",
            "Replication task ID",
            type=int,
        )

        # Create replication task
        create_parser = self.add_command(
            subparsers,
            "create",
            "Create a new replication task (replication.create)",
            _cmd_replication_create,
            parent_parser=parent_parser,
        )
        self.add_required_argument(
            create_parser,
            "name",
            "Task name",
        )
        self.add_required_argument(
            create_parser,
            "direction",
            "Replication direction (PUSH or PULL)",
        )
        self.add_required_argument(
            create_parser,
            "transport",
            "Transport method (SSH, LOCAL, or LEGACY)",
        )
        self.add_required_argument(
            create_parser,
            "source_datasets",
            "Source datasets (comma-separated)",
        )
        self.add_required_argument(
            create_parser,
            "target_dataset",
            "Target dataset path",
        )
        self.add_optional_argument(
            create_parser,
            "--ssh-credentials",
            "ssh_credentials",
            "SSH credentials ID (required for SSH transport)",
            type=int,
        )
        self.add_optional_argument(
            create_parser,
            "--recursive",
            "recursive",
            "Recursively replicate child datasets",
            action="store_true",
        )
        self.add_optional_argument(
            create_parser,
            "--auto",
            "auto",
            "Automatically replicate on schedule",
            action="store_true",
        )
        self.add_optional_argument(
            create_parser,
            "--enabled",
            "enabled",
            "Enable the replication task",
            action="store_true",
        )

        # Update replication task
        update_parser = self.add_command(
            subparsers,
            "update",
            "Update a replication task (replication.update)",
            _cmd_replication_update,
            parent_parser=parent_parser,
        )
        self.add_required_argument(
            update_parser,
            "task_id",
            "Replication task ID",
            type=int,
        )
        self.add_optional_argument(
            update_parser,
            "--name",
            "name",
            "New task name",
        )
        self.add_optional_argument(
            update_parser,
            "--enabled",
            "enabled",
            "Enable/disable task (true/false)",
        )

        # Delete replication task
        delete_parser = self.add_command(
            subparsers,
            "delete",
            "Delete a replication task (replication.delete)",
            _cmd_replication_delete,
            parent_parser=parent_parser,
        )
        self.add_required_argument(
            delete_parser,
            "task_id",
            "Replication task ID",
            type=int,
        )

        # Run replication task
        run_parser = self.add_command(
            subparsers,
            "run",
            "Run a replication task immediately (replication.run)",
            _cmd_replication_run,
            parent_parser=parent_parser,
        )
        self.add_required_argument(
            run_parser,
            "task_id",
            "Replication task ID",
            type=int,
        )

        # Run one-time replication
        run_once_parser = self.add_command(
            subparsers,
            "run-once",
            "Run a one-time replication (replication.run_onetime)",
            _cmd_replication_run_once,
            parent_parser=parent_parser,
        )
        self.add_required_argument(
            run_once_parser,
            "direction",
            "Replication direction (PUSH or PULL)",
        )
        self.add_required_argument(
            run_once_parser,
            "transport",
            "Transport method (SSH or LOCAL)",
        )
        self.add_required_argument(
            run_once_parser,
            "source_datasets",
            "Source datasets (comma-separated)",
        )
        self.add_required_argument(
            run_once_parser,
            "target_dataset",
            "Target dataset path",
        )
        self.add_optional_argument(
            run_once_parser,
            "--ssh-credentials",
            "ssh_credentials",
            "SSH credentials ID (required for SSH transport)",
            type=int,
        )
        self.add_optional_argument(
            run_once_parser,
            "--recursive",
            "recursive",
            "Recursively replicate child datasets",
            action="store_true",
        )

        # List datasets
        datasets_parser = self.add_command(
            subparsers,
            "datasets",
            "List available datasets (replication.list_datasets)",
            _cmd_replication_datasets,
            parent_parser=parent_parser,
        )
        self.add_optional_argument(
            datasets_parser,
            "--transport",
            "transport",
            "Transport method (SSH or LOCAL)",
            default="LOCAL",
        )
        self.add_optional_argument(
            datasets_parser,
            "--ssh-credentials",
            "ssh_credentials",
            "SSH credentials ID (for SSH transport)",
            type=int,
        )

        # List naming schemas
        self.add_command(
            subparsers,
            "schemas",
            "List snapshot naming schemas (replication.list_naming_schemas)",
            _cmd_replication_schemas,
            parent_parser=parent_parser,
        )


async def _cmd_replication_list(args: argparse.Namespace) -> None:
    """Handle ``replication list`` command."""

    async def handler(client: TrueNASClient) -> None:
        tasks = await client.get_replications()

        if args.json:
            print(json.dumps(tasks, indent=2))
            return

        print("\n=== Replication Tasks ===")
        if not tasks:
            print("No replication tasks found.")
            return

        for task in tasks:
            task_id = task.get("id", "N/A")
            name = task.get("name", "N/A")
            direction = task.get("direction", "N/A")
            enabled = task.get("enabled", False)

            status_icon = "[✓]" if enabled else "[✗]"
            print(f"\n{status_icon} [{task_id}] {name}")
            print(f"  Direction: {direction}")

            if args.full:
                transport = task.get("transport", "N/A")
                source_datasets = task.get("source_datasets", [])
                target_dataset = task.get("target_dataset", "N/A")

                print(f"  Transport: {transport}")
                print(f"  Source: {', '.join(source_datasets)}")
                print(f"  Target: {target_dataset}")

                if task.get("state"):
                    state = task["state"]
                    state_str = state.get("state", "UNKNOWN")
                    print(f"  State: {state_str}")

                if task.get("job"):
                    job = task["job"]
                    if job.get("state"):
                        print(f"  Job State: {job['state']}")

    await run_command(args, handler)


async def _cmd_replication_info(args: argparse.Namespace) -> None:
    """Handle ``replication info`` command."""

    async def handler(client: TrueNASClient) -> None:
        task = await client.get_replication(args.task_id)

        if args.json:
            print(json.dumps(task, indent=2))
            return

        task_id = task.get("id", "N/A")
        name = task.get("name", "N/A")
        direction = task.get("direction", "N/A")
        transport = task.get("transport", "N/A")
        enabled = task.get("enabled", False)

        print(f"\n=== Replication Task: {name} (ID {task_id}) ===")
        print(f"Direction: {direction}")
        print(f"Transport: {transport}")
        print(f"Enabled: {'Yes' if enabled else 'No'}")

        # Source/target
        source_datasets = task.get("source_datasets", [])
        target_dataset = task.get("target_dataset", "N/A")
        print("\nSource Datasets:")
        for dataset in source_datasets:
            print(f"  - {dataset}")
        print(f"Target Dataset: {target_dataset}")

        # Settings
        if task.get("recursive"):
            print("Recursive: Yes")
        if task.get("auto"):
            print("Auto-schedule: Yes")
            if task.get("schedule"):
                schedule = task["schedule"]
                print(f"  Schedule: {schedule}")

        # State
        if task.get("state"):
            state = task["state"]
            state_str = state.get("state", "UNKNOWN")
            print(f"\nState: {state_str}")

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


async def _cmd_replication_create(args: argparse.Namespace) -> None:
    """Handle ``replication create`` command."""

    async def handler(client: TrueNASClient) -> None:
        # Parse source datasets
        source_datasets = [ds.strip() for ds in args.source_datasets.split(",")]

        # Validate direction
        direction = args.direction.upper()
        if direction not in ("PUSH", "PULL"):
            raise ValueError("Direction must be PUSH or PULL")

        # Validate transport
        transport = args.transport.upper()
        if transport not in ("SSH", "LOCAL", "LEGACY"):
            raise ValueError("Transport must be SSH, LOCAL, or LEGACY")

        # Build kwargs
        kwargs = {}
        if args.ssh_credentials is not None:
            kwargs["ssh_credentials"] = args.ssh_credentials
        if args.recursive:
            kwargs["recursive"] = True
        if args.auto:
            kwargs["auto"] = True
        if args.enabled:
            kwargs["enabled"] = True

        print(f"Creating replication task: {args.name}...")

        task = await client.create_replication(
            name=args.name,
            direction=direction,
            transport=transport,
            source_datasets=source_datasets,
            target_dataset=args.target_dataset,
            **kwargs,
        )

        if args.json:
            print(json.dumps(task, indent=2))
            return

        task_id = task.get("id", "N/A")
        print(f"✓ Replication task '{args.name}' created successfully (ID {task_id})")

    await run_command(args, handler)


async def _cmd_replication_update(args: argparse.Namespace) -> None:
    """Handle ``replication update`` command."""

    async def handler(client: TrueNASClient) -> None:
        kwargs = {}

        if args.name:
            kwargs["name"] = args.name

        if args.enabled is not None:
            enabled_value = str(args.enabled) if args.enabled is not None else ""
            kwargs["enabled"] = enabled_value.lower() in ("true", "yes", "1")

        if not kwargs:
            raise ValueError("No update parameters provided")

        print(f"Updating replication task ID {args.task_id}...")

        task = await client.update_replication(args.task_id, **kwargs)

        if args.json:
            print(json.dumps(task, indent=2))
            return

        print(f"✓ Replication task ID {args.task_id} updated successfully")

    await run_command(args, handler)


async def _cmd_replication_delete(args: argparse.Namespace) -> None:
    """Handle ``replication delete`` command."""

    async def handler(client: TrueNASClient) -> None:
        print(f"Deleting replication task ID {args.task_id}...")

        result = await client.delete_replication(args.task_id)

        if args.json:
            print(json.dumps({"success": result}, indent=2))
            return

        print(f"✓ Replication task ID {args.task_id} deleted successfully")

    await run_command(args, handler)


async def _cmd_replication_run(args: argparse.Namespace) -> None:
    """Handle ``replication run`` command."""

    async def handler(client: TrueNASClient) -> None:
        print(f"Running replication task ID {args.task_id}...")

        await client.run_replication(args.task_id)

        if args.json:
            print(json.dumps({"success": True, "message": "Job started"}, indent=2))
            return

        print(f"✓ Replication task ID {args.task_id} started successfully")
        print("  Monitor job progress via the TrueNAS web interface")

    await run_command(args, handler)


async def _cmd_replication_run_once(args: argparse.Namespace) -> None:
    """Handle ``replication run-once`` command."""

    async def handler(client: TrueNASClient) -> None:
        # Parse source datasets
        source_datasets = [ds.strip() for ds in args.source_datasets.split(",")]

        # Validate direction
        direction = args.direction.upper()
        if direction not in ("PUSH", "PULL"):
            raise ValueError("Direction must be PUSH or PULL")

        # Validate transport
        transport = args.transport.upper()
        if transport not in ("SSH", "LOCAL"):
            raise ValueError("Transport must be SSH or LOCAL for one-time replication")

        # Build kwargs
        kwargs = {}
        if args.ssh_credentials is not None:
            kwargs["ssh_credentials"] = args.ssh_credentials
        if args.recursive:
            kwargs["recursive"] = True

        print("Starting one-time replication...")

        await client.run_replication_onetime(
            direction=direction,
            transport=transport,
            source_datasets=source_datasets,
            target_dataset=args.target_dataset,
            **kwargs,
        )

        if args.json:
            print(json.dumps({"success": True, "message": "Job started"}, indent=2))
            return

        print("✓ One-time replication started successfully")
        print("  Monitor job progress via the TrueNAS web interface")

    await run_command(args, handler)


async def _cmd_replication_datasets(args: argparse.Namespace) -> None:
    """Handle ``replication datasets`` command."""

    async def handler(client: TrueNASClient) -> None:
        datasets = await client.list_replication_datasets(
            transport=args.transport, ssh_credentials=args.ssh_credentials
        )

        if args.json:
            print(json.dumps(datasets, indent=2))
            return

        print(f"\n=== Available Datasets ({args.transport}) ===")
        for dataset in datasets:
            print(f"  {dataset}")

    await run_command(args, handler)


async def _cmd_replication_schemas(args: argparse.Namespace) -> None:
    """Handle ``replication schemas`` command."""

    async def handler(client: TrueNASClient) -> None:
        schemas = await client.list_replication_naming_schemas()

        if args.json:
            print(json.dumps(schemas, indent=2))
            return

        print("\n=== Snapshot Naming Schemas ===")
        for schema in schemas:
            print(f"  {schema}")

    await run_command(args, handler)

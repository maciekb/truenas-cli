from __future__ import annotations

import argparse
import asyncio
import json
from datetime import datetime
from typing import Any, Dict, Iterable, List, Set, Tuple

from truenas_client import TrueNASClient

from ..core import format_size, run_command, safe_get
from .base import CommandGroup

EMPTY_DATASET_THRESHOLD = 128 * 1024  # 128 KiB metadata allowance

_UNIT_MAP = {
    "B": 1,
    "BYTES": 1,
    "KIB": 1024,
    "MIB": 1024**2,
    "GIB": 1024**3,
    "TIB": 1024**4,
    "PIB": 1024**5,
}


def _parse_size_to_bytes(text: str) -> int:
    if not text:
        return 0
    stripped = text.replace(",", "").strip()
    if not stripped:
        return 0

    parts = stripped.split()
    try:
        value = float(parts[0])
    except ValueError:
        return 0

    unit = parts[1].upper() if len(parts) > 1 else "B"
    unit = unit.replace("BYTE", "B")
    multiplier = _UNIT_MAP.get(unit, 1)
    return int(value * multiplier)


def _value_to_bytes(value: Any) -> int:
    if value is None:
        return 0
    if isinstance(value, (int, float)):
        return int(value)
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            try:
                return _parse_size_to_bytes(value)
            except Exception:
                return 0
    if isinstance(value, dict):
        for key in ("rawvalue", "value"):
            if key in value:
                result = _value_to_bytes(value[key])
                if result is not None:
                    return result
        parsed = value.get("parsed")
        if isinstance(parsed, str):
            return _parse_size_to_bytes(parsed)
    return 0


async def _fetch_share_snapshot_context(
    client: TrueNASClient,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], Set[str]]:
    try:
        smb_shares = await client.get_smb_shares()
    except Exception:
        smb_shares = []
    try:
        nfs_shares = await client.get_nfs_shares()
    except Exception:
        nfs_shares = []
    snapshots_by_dataset: Set[str] = set()
    try:
        all_snapshots = await client.get_snapshots()
    except Exception:
        all_snapshots = []
    for snap in all_snapshots:
        ds_name = snap.get("dataset") or ""
        if not ds_name:
            snap_name = snap.get("name", "")
            if "@" in snap_name:
                ds_name = snap_name.split("@", 1)[0]
        if ds_name:
            snapshots_by_dataset.add(ds_name)
    return smb_shares, nfs_shares, snapshots_by_dataset


def _dataset_has_share(
    mountpoint: str,
    smb_shares: Iterable[Dict[str, Any]],
    nfs_shares: Iterable[Dict[str, Any]],
) -> bool:
    if not mountpoint:
        return False
    norm = mountpoint.rstrip("/")
    prefix = norm + "/"
    for share in smb_shares:
        path = share.get("path", "")
        if path == norm or path.startswith(prefix):
            return True
    for share in nfs_shares:
        paths = []
        path = safe_get(share, "path")
        if path:
            paths.append(path)
        extra = safe_get(share, "paths", [])
        if isinstance(extra, list):
            paths.extend([p for p in extra if p])
        for p in paths:
            if p == norm or p.startswith(prefix):
                return True
    return False


def _collect_share_details(
    mountpoint: str,
    smb_shares: Iterable[Dict[str, Any]],
    nfs_shares: Iterable[Dict[str, Any]],
) -> Dict[str, List[str]]:
    details = {"smb": [], "nfs": []}
    if not mountpoint:
        return details
    norm = mountpoint.rstrip("/")
    prefix = norm + "/"
    for share in smb_shares:
        path = share.get("path", "")
        if path == norm or path.startswith(prefix):
            details["smb"].append(
                f"{share.get('name', 'N/A')} ({share.get('path', 'N/A')})"
            )
    for share in nfs_shares:
        entries = []
        path = safe_get(share, "path")
        if path:
            entries.append(path)
        extra = safe_get(share, "paths", [])
        if isinstance(extra, list):
            entries.extend([p for p in extra if p])
        for entry in entries:
            if entry == norm or entry.startswith(prefix):
                details["nfs"].append(entry)
    return details


def _is_dataset_empty(
    dataset: Dict[str, Any],
    smb_shares: Iterable[Dict[str, Any]],
    nfs_shares: Iterable[Dict[str, Any]],
    snapshots_by_dataset: Set[str],
) -> bool:
    name = dataset.get("name") or ""
    mountpoint = dataset.get("mountpoint") or ""
    used_dataset_bytes = _value_to_bytes(dataset.get("usedbydataset"))
    used_children_bytes = _value_to_bytes(dataset.get("usedbychildren"))
    used_snapshots_bytes = _value_to_bytes(dataset.get("usedbysnapshots"))
    refreservation_bytes = _value_to_bytes(dataset.get("refreservation"))

    minimal_usage = (
        used_dataset_bytes <= EMPTY_DATASET_THRESHOLD
        and used_children_bytes == 0
        and used_snapshots_bytes == 0
        and refreservation_bytes == 0
    )
    has_shares = _dataset_has_share(mountpoint, smb_shares, nfs_shares)
    has_snapshots = name in snapshots_by_dataset
    return minimal_usage and not has_shares and not has_snapshots


class DatasetCommands(CommandGroup):
    """Dataset operations based on the ``pool.dataset`` namespace."""

    name = "dataset"

    def register_commands(
        self,
        subparsers: argparse._SubParsersAction,
        parent_parser: argparse.ArgumentParser,
    ) -> None:
        """Register dataset subcommands."""
        # List datasets
        list_parser = self.add_command(
            subparsers,
            "list",
            "List datasets (pool.dataset.query)",
            _cmd_dataset_list,
            parent_parser=parent_parser,
        )
        self.add_optional_argument(
            list_parser, "-p", "pool", "Pool name (optional filter)"
        )
        self.add_optional_argument(
            list_parser,
            "--empty",
            "empty",
            "Show only empty datasets (no used space, snapshots, or shares)",
            action="store_true",
        )
        self.add_optional_argument(
            list_parser,
            "--full",
            "full",
            "Show all available fields",
            action="store_true",
        )

        # Create dataset
        create_parser = self.add_command(
            subparsers,
            "create",
            "Create dataset (pool.dataset.create)",
            _cmd_dataset_create,
            parent_parser=parent_parser,
        )
        self.add_optional_argument(
            create_parser, "-p", "pool", "Pool name", required=True
        )
        self.add_optional_argument(
            create_parser, "-d", "dataset", "Dataset name", required=True
        )
        self.add_optional_argument(
            create_parser,
            "--type",
            "type",
            "Dataset type (default: FILESYSTEM)",
            choices=["FILESYSTEM", "VOLUME"],
            default="FILESYSTEM",
        )
        self.add_optional_argument(
            create_parser,
            "--comment",
            "comment",
            "Dataset comment (optional)",
        )

        # Delete datasets
        delete_parser = self.add_command(
            subparsers,
            "delete",
            "Delete dataset(s) (pool.dataset.delete)",
            _cmd_dataset_delete,
            parent_parser=parent_parser,
        )
        delete_parser.add_argument(
            "datasets",
            nargs="*",
            type=str,
            help="Dataset path(s) to delete",
        )
        self.add_optional_argument(
            delete_parser,
            "-f",
            "force",
            "Force delete without confirmation",
            action="store_true",
        )
        self.add_optional_argument(
            delete_parser,
            "--allow-with-shares",
            "allow_with_shares",
            "Allow deletion even if active shares exist",
            action="store_true",
        )
        self.add_optional_argument(
            delete_parser,
            "--empty",
            "empty",
            "Delete only empty datasets (optionally filtered by names)",
            action="store_true",
        )
        self.add_optional_argument(
            delete_parser,
            "-p",
            "pool",
            "Restrict deletion to datasets in this pool",
        )

        # Rename dataset
        rename_parser = self.add_command(
            subparsers,
            "rename",
            "Rename a dataset (pool.dataset.update)",
            _cmd_dataset_rename,
            parent_parser=parent_parser,
        )
        self.add_required_argument(
            rename_parser,
            "dataset",
            "Current dataset name",
        )
        self.add_required_argument(
            rename_parser,
            "new_name",
            "New dataset name",
        )
        self.add_optional_argument(
            rename_parser,
            "--recursive",
            "recursive",
            "Recursively rename child datasets (if applicable)",
            action="store_true",
        )


async def _cmd_dataset_list(args):
    async def handler(client: TrueNASClient):
        datasets = await client.get_datasets(args.pool if args.pool else None)

        (
            smb_shares,
            nfs_shares,
            snapshots_by_dataset,
        ) = await _fetch_share_snapshot_context(client)

        if args.empty:
            filtered = []
            for ds in datasets:
                name = ds.get("name") or ""
                mountpoint = ds.get("mountpoint") or ""
                if _is_dataset_empty(
                    ds,
                    smb_shares,
                    nfs_shares,
                    snapshots_by_dataset,
                ):
                    filtered.append(ds)
            datasets = filtered

        if args.json:
            print(json.dumps(datasets, indent=2))
            return

        print("\n=== Datasets ===")
        if not datasets:
            print("No datasets found.")
            return

        for ds in datasets:
            ds_name = ds.get("name")
            mountpoint_value = ds.get("mountpoint")
            ds_mountpoint: str = (
                mountpoint_value if isinstance(mountpoint_value, str) else ""
            )

            print(f"\nDataset: {ds_name}")
            print(f"  Type: {ds.get('type')}")
            print(f"  Mountpoint: {ds_mountpoint or 'N/A'}")
            creation = ds.get("creation", {}).get("parsed")
            if creation:
                timestamp = (
                    creation.get("$date") if isinstance(creation, dict) else None
                )
                if isinstance(timestamp, (int, float)):
                    try:
                        dt = datetime.fromtimestamp(timestamp / 1000)
                        print(f"  Created: {dt.isoformat(sep=' ', timespec='seconds')}")
                    except Exception:
                        pass
            print(f"  Used: {format_size(ds.get('used'))}")

            available = ds.get("available")
            if available:
                print(f"  Available: {format_size(available)}")

            if ds.get("comments"):
                print(f"  Comments: {ds.get('comments')}")

            if args.full:
                # Show all available fields
                excluded_keys = {
                    "name",
                    "type",
                    "mountpoint",
                    "creation",
                    "used",
                    "available",
                    "comments",
                }
                for key, value in sorted(ds.items()):
                    if key not in excluded_keys:
                        if isinstance(value, bool):
                            value = "Yes" if value else "No"
                        elif isinstance(value, dict):
                            value = json.dumps(value)
                        elif isinstance(value, list):
                            value = ", ".join(map(str, value)) if value else "None"
                        print(f"  {key}: {value}")
            else:
                # Show shares if any
                share_details = _collect_share_details(
                    ds_mountpoint,
                    smb_shares,
                    nfs_shares,
                )
                ds_shares = []
                if share_details["smb"]:
                    ds_shares.extend(
                        [f"SMB: {entry}" for entry in share_details["smb"]]
                    )
                if share_details["nfs"]:
                    ds_shares.extend(
                        [f"NFS: {entry}" for entry in share_details["nfs"]]
                    )

                if ds_shares:
                    print("  Shares:")
                    for share_info in ds_shares:
                        print(f"    - {share_info}")

    await run_command(args, handler)


async def _cmd_dataset_create(args):
    async def handler(client: TrueNASClient):
        dataset_name = f"{args.pool}/{args.dataset}"

        if await client.dataset_exists(dataset_name):
            raise ValueError(f"Dataset '{dataset_name}' already exists")

        payload = {
            "name": dataset_name,
            "dataset_type": args.type,
        }
        if args.comment:
            payload["comments"] = args.comment

        dataset = await client.create_dataset(**payload)

        if args.json:
            print(json.dumps(dataset, indent=2))
            return

        print(f"\n✓ Dataset created: {safe_get(dataset, 'name', dataset_name)}")
        print(
            f"  Mountpoint: {safe_get(dataset, 'mountpoint', f'/mnt/{dataset_name}')}"
        )

    await run_command(args, handler)


async def _cmd_dataset_delete(args):
    async def handler(client: TrueNASClient):
        all_datasets = await client.get_datasets()
        dataset_map_all: Dict[str, Dict[str, Any]] = {}
        for ds in all_datasets:
            name = ds.get("name")
            if isinstance(name, str):
                dataset_map_all[name] = ds

        dataset_map: Dict[str, Dict[str, Any]]
        if args.pool:
            dataset_map: Dict[str, Dict[str, Any]] = {
                name: info
                for name, info in dataset_map_all.items()
                if info.get("pool") == args.pool
            }
        else:
            dataset_map = dict(dataset_map_all)

        if args.pool and not dataset_map and not args.datasets:
            print(f"No datasets found in pool '{args.pool}'.")
            return

        (
            smb_shares,
            nfs_shares,
            snapshots_by_dataset,
        ) = await _fetch_share_snapshot_context(client)

        if not args.datasets and not args.empty:
            print(
                "Error: specify dataset names or use --empty to target empty datasets."
            )
            raise SystemExit(1)

        targets: List[str] = []
        empty_dataset_map: Dict[str, Dict[str, Any]] = {}

        if args.empty:
            for name, ds in dataset_map.items():
                if _is_dataset_empty(ds, smb_shares, nfs_shares, snapshots_by_dataset):
                    empty_dataset_map[name] = ds

            if args.datasets:
                if args.pool:
                    wrong_pool = [
                        name
                        for name in args.datasets
                        if name in dataset_map_all
                        and dataset_map_all[name].get("pool") != args.pool
                    ]
                    if wrong_pool:
                        print(f"Skipping datasets outside pool '{args.pool}':")
                        for item in wrong_pool:
                            print(f"  • {item}")

                missing = [
                    name for name in args.datasets if name not in empty_dataset_map
                ]
                if missing:
                    print("Skipping non-empty datasets:")
                    for item in missing:
                        print(f"  • {item}")
                targets = [name for name in args.datasets if name in empty_dataset_map]
            else:
                targets = sorted(empty_dataset_map.keys())

            if not targets:
                print("No empty datasets found to delete.")
                return
        else:
            targets = list(args.datasets)

        if args.pool and args.datasets:
            wrong_pool = [
                name
                for name in targets
                if name in dataset_map_all
                and dataset_map_all[name].get("pool") != args.pool
            ]
            if wrong_pool:
                print(f"Skipping datasets outside pool '{args.pool}':")
                for item in wrong_pool:
                    print(f"  • {item}")
            targets = [name for name in targets if name in dataset_map]

        missing_global = [name for name in targets if name not in dataset_map_all]
        if missing_global:
            print("The following dataset(s) do not exist:")
            for item in missing_global:
                print(f"  • {item}")
            raise SystemExit(1)

        if not targets:
            print("No datasets to delete in the selected pool.")
            return

        datasets_with_shares = {}
        for name in targets:
            ds = dataset_map.get(name) or dataset_map_all.get(name)
            if not ds:
                continue
            mountpoint_value = ds.get("mountpoint")
            mountpoint = mountpoint_value if isinstance(mountpoint_value, str) else ""
            details = _collect_share_details(
                mountpoint,
                smb_shares,
                nfs_shares,
            )
            if details["smb"] or details["nfs"]:
                datasets_with_shares[name] = details

        if datasets_with_shares:
            print("⚠️  WARNING: The following dataset(s) have active shares:\n")
            for dataset, shares in datasets_with_shares.items():
                print(f"  {dataset}:")
                if shares.get("smb"):
                    print(f"    • SMB shares: {len(shares['smb'])} active")
                    for share in shares["smb"]:
                        print(f"      - {share}")
                if shares.get("nfs"):
                    print(f"    • NFS shares: {len(shares['nfs'])} active")
                    for share in shares["nfs"]:
                        print(f"      - {share}")
            print()

            if not args.allow_with_shares:
                raise ValueError(
                    "Deletion blocked: dataset(s) with active shares cannot be "
                    "deleted. Remove the shares first or use --allow-with-shares."
                )

        final_targets: List[str] = []
        if args.empty:
            targets_list = list(targets)
            print(f"Empty datasets to delete ({len(targets_list)}):")
            for item in targets_list:
                print(f"  • {item}")

            if not args.force:
                countdown = 10
                print(
                    f"Deleting {len(targets_list)} empty dataset(s) in {countdown}s... "
                    "Press Ctrl+C to cancel."
                )
                try:
                    for remaining in range(countdown, 0, -1):
                        print(f"  {remaining}s remaining...", end="\r", flush=True)
                        await asyncio.sleep(1)
                    print("  Proceeding...        ")
                except (KeyboardInterrupt, asyncio.CancelledError):
                    print("\nCancelled by user.")
                    raise SystemExit(1)
            else:
                print("Proceeding immediately (force).")

            final_targets = targets_list
        else:
            final_targets = list(targets)
            if final_targets and not args.force:
                try:
                    response = (
                        input(
                            f"Delete {len(final_targets)} dataset(s): {', '.join(final_targets)}? (yes/no): "
                        )
                        .strip()
                        .lower()
                    )
                except KeyboardInterrupt:
                    print("\nCancelled by user.")
                    raise SystemExit(1)
                if response in ("quit", "q"):
                    print("Cancelled by user.")
                    raise SystemExit(1)
                if response not in ("yes", "y"):
                    print("Cancelled.")
                    return

        if not final_targets:
            print("No datasets to delete.")
            return

        results = []
        errors = []

        for dataset in final_targets:
            try:
                if getattr(args, "dry_run", False):
                    if args.json:
                        results.append(dataset)
                    else:
                        print(f"[dry-run] Would delete dataset: {dataset}")
                        results.append(dataset)
                else:
                    await client.delete_dataset(dataset, force=args.force)
                    results.append(dataset)
            except Exception as exc:
                errors.append({"dataset": dataset, "error": str(exc)})

        if args.json:
            print(
                json.dumps(
                    {"deleted": results, "errors": errors or None},
                    indent=2,
                )
            )
            if errors:
                raise SystemExit(1)
            return

        if results:
            verb = "Would delete" if getattr(args, "dry_run", False) else "Deleted"
            print(f"✓ {verb} {len(results)} dataset(s):")
            for ds in results:
                print(f"  • {ds}")

        if errors:
            print(f"\n✗ Failed to delete {len(errors)} dataset(s):")
            for err in errors:
                print(f"  • {err['dataset']}: {err['error']}")
            raise SystemExit(1)

    await run_command(args, handler)


async def _cmd_dataset_rename(args):
    """Handle ``dataset rename`` using ``pool.dataset.update``."""

    async def handler(client: TrueNASClient):
        dataset_name = args.dataset
        new_name = args.new_name

        # Check if dataset exists
        datasets = await client.get_datasets()
        dataset_map = {ds.get("name"): ds for ds in datasets if ds.get("name")}

        if dataset_name not in dataset_map:
            print(f"Error: Dataset '{dataset_name}' not found")
            return

        print(f"Renaming dataset '{dataset_name}' to '{new_name}'...")

        rename_params = {
            "name": new_name,
            "recursive": args.recursive,
        }

        result = await client.call("pool.dataset.update", [dataset_name, rename_params])

        if args.json:
            print(json.dumps(result, indent=2))
            return

        print("✓ Dataset renamed successfully")
        print(f"  Old name: {dataset_name}")
        print(f"  New name: {new_name}")

    await run_command(args, handler)

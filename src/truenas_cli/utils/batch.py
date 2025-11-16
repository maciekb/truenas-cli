"""Batch operations utilities for processing multiple commands.

This module provides utilities for batch processing of CLI operations
from YAML or JSON files, with support for parallel execution and progress tracking.
"""

import json
import sys
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml
from rich.console import Console
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
    TimeRemainingColumn,
)
from rich.table import Table


@dataclass
class BatchOperation:
    """Represents a single batch operation."""

    command: str
    args: dict[str, Any]
    id: str | None = None


@dataclass
class BatchResult:
    """Result of a batch operation."""

    operation: BatchOperation
    success: bool
    result: Any = None
    error: str | None = None


class BatchProcessor:
    """Process batch operations with progress tracking."""

    def __init__(
        self,
        operations: list[BatchOperation],
        executor: Callable[[BatchOperation], Any],
        parallel: bool = False,
        max_workers: int = 4,
        console: Console | None = None,
    ):
        """Initialize batch processor.

        Args:
            operations: List of batch operations to execute
            executor: Function to execute each operation
            parallel: Execute operations in parallel
            max_workers: Maximum parallel workers
            console: Rich console instance
        """
        self.operations = operations
        self.executor = executor
        self.parallel = parallel
        self.max_workers = max_workers
        self.console = console or Console()

    def _execute_operation(self, operation: BatchOperation) -> BatchResult:
        """Execute a single operation.

        Args:
            operation: Operation to execute

        Returns:
            Result of the operation
        """
        try:
            result = self.executor(operation)
            return BatchResult(operation=operation, success=True, result=result)
        except Exception as e:
            return BatchResult(operation=operation, success=False, error=str(e))

    def execute(self, stop_on_error: bool = False) -> list[BatchResult]:
        """Execute all batch operations.

        Args:
            stop_on_error: Stop processing if an error occurs

        Returns:
            List of batch results
        """
        results: list[BatchResult] = []

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            TimeRemainingColumn(),
            console=self.console,
        ) as progress:
            task = progress.add_task("Processing operations", total=len(self.operations))

            if self.parallel:
                # Parallel execution
                with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                    futures = {
                        executor.submit(self._execute_operation, op): op
                        for op in self.operations
                    }

                    for future in as_completed(futures):
                        result = future.result()
                        results.append(result)
                        progress.advance(task)

                        if not result.success and stop_on_error:
                            self.console.print(
                                f"[red]Error in operation: {result.error}[/red]"
                            )
                            break
            else:
                # Sequential execution
                for operation in self.operations:
                    result = self._execute_operation(operation)
                    results.append(result)
                    progress.advance(task)

                    if not result.success and stop_on_error:
                        self.console.print(f"[red]Error in operation: {result.error}[/red]")
                        break

        return results

    def print_summary(self, results: list[BatchResult]) -> None:
        """Print summary of batch execution.

        Args:
            results: List of batch results
        """
        success_count = sum(1 for r in results if r.success)
        error_count = len(results) - success_count

        # Create summary table
        table = Table(title="Batch Execution Summary", show_header=True)
        table.add_column("Metric", style="cyan")
        table.add_column("Count", style="magenta")

        table.add_row("Total Operations", str(len(results)))
        table.add_row("Successful", f"[green]{success_count}[/green]")
        table.add_row("Failed", f"[red]{error_count}[/red]")

        self.console.print(table)

        # Show errors if any
        if error_count > 0:
            self.console.print("\n[bold red]Errors:[/bold red]")
            for result in results:
                if not result.success:
                    op_id = result.operation.id or result.operation.command
                    self.console.print(f"  - {op_id}: {result.error}")


def load_batch_file(file_path: Path) -> list[BatchOperation]:
    """Load batch operations from YAML or JSON file.

    Args:
        file_path: Path to batch file

    Returns:
        List of batch operations

    Raises:
        ValueError: If file format is invalid
    """
    content = file_path.read_text()

    # Determine format from extension
    if file_path.suffix in [".yaml", ".yml"]:
        data = yaml.safe_load(content)
    elif file_path.suffix == ".json":
        data = json.loads(content)
    else:
        raise ValueError(f"Unsupported file format: {file_path.suffix}")

    # Parse operations
    if not isinstance(data, dict) or "operations" not in data:
        raise ValueError("Batch file must contain 'operations' key")

    operations = []
    for i, op_data in enumerate(data["operations"]):
        if not isinstance(op_data, dict):
            raise ValueError(f"Operation {i} must be a dictionary")

        if "command" not in op_data:
            raise ValueError(f"Operation {i} missing 'command' field")

        operation = BatchOperation(
            id=op_data.get("id", f"op_{i}"),
            command=op_data["command"],
            args=op_data.get("args", {}),
        )
        operations.append(operation)

    return operations


def load_batch_from_stdin() -> list[BatchOperation]:
    """Load batch operations from stdin.

    Expects one JSON object per line.

    Returns:
        List of batch operations
    """
    operations = []

    for i, line in enumerate(sys.stdin):
        line = line.strip()
        if not line:
            continue

        try:
            op_data = json.loads(line)
            operation = BatchOperation(
                id=op_data.get("id", f"stdin_{i}"),
                command=op_data["command"],
                args=op_data.get("args", {}),
            )
            operations.append(operation)
        except (json.JSONDecodeError, KeyError) as e:
            raise ValueError(f"Invalid operation at line {i + 1}: {e}")

    return operations


def create_sample_batch_file(file_path: Path, format: str = "yaml") -> None:
    """Create a sample batch operations file.

    Args:
        file_path: Path to create file at
        format: File format ('yaml' or 'json')
    """
    sample_operations = {
        "operations": [
            {
                "id": "create_dataset_1",
                "command": "dataset create",
                "args": {"path": "tank/data", "compression": "lz4"},
            },
            {
                "id": "create_dataset_2",
                "command": "dataset create",
                "args": {"path": "tank/backup", "compression": "zstd"},
            },
            {
                "id": "list_datasets",
                "command": "dataset list",
                "args": {"pool": "tank"},
            },
        ]
    }

    if format == "yaml":
        content = yaml.dump(sample_operations, default_flow_style=False, sort_keys=False)
    else:
        content = json.dumps(sample_operations, indent=2)

    file_path.write_text(content)

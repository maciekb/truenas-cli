"""Watch mode utilities for live-updating CLI output.

This module provides utilities for implementing watch mode (auto-refresh)
functionality using Rich's Live display.
"""

import time
from collections.abc import Callable
from datetime import datetime
from typing import Any

from rich.console import Console, RenderableType
from rich.live import Live
from rich.text import Text


class WatchMode:
    """Manages watch mode for auto-refreshing command output.

    Displays command output that refreshes at a specified interval
    until interrupted by user (Ctrl+C).
    """

    def __init__(
        self,
        refresh_callback: Callable[[], RenderableType],
        interval: float = 2.0,
        console: Console | None = None,
    ):
        """Initialize watch mode.

        Args:
            refresh_callback: Function to call for each refresh, should return Rich renderable
            interval: Refresh interval in seconds
            console: Rich console instance (creates new one if None)
        """
        self.refresh_callback = refresh_callback
        self.interval = interval
        self.console = console or Console()
        self.iteration = 0

    def _create_header(self) -> Text:
        """Create header showing refresh info.

        Returns:
            Rich Text object with header
        """
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        header = Text()
        header.append("Every ", style="dim")
        header.append(f"{self.interval}s", style="bold cyan")
        header.append(f"  {now}", style="dim")
        header.append(f"  (Iteration: {self.iteration})", style="dim italic")
        return header

    def _create_display(self) -> RenderableType:
        """Create full display with header and content.

        Returns:
            Rich renderable for display
        """
        header = self._create_header()
        content = self.refresh_callback()

        # Combine header and content
        from rich.console import Group

        return Group(header, Text(""), content)

    def run(self) -> None:
        """Run watch mode until interrupted.

        Continuously refreshes display at specified interval.
        Exits cleanly on KeyboardInterrupt (Ctrl+C).
        """
        try:
            with Live(
                self._create_display(),
                console=self.console,
                refresh_per_second=4,
                transient=False,
            ) as live:
                while True:
                    time.sleep(self.interval)
                    self.iteration += 1
                    live.update(self._create_display())

        except KeyboardInterrupt:
            # Show final message
            self.console.print("\n[yellow]Watch mode stopped[/yellow]")


def watch(
    callback: Callable[[], RenderableType],
    interval: float = 2.0,
    console: Console | None = None,
) -> None:
    """Convenience function to run watch mode.

    Args:
        callback: Function to call for each refresh
        interval: Refresh interval in seconds
        console: Rich console instance
    """
    watcher = WatchMode(callback, interval, console)
    watcher.run()


class Spinner:
    """Simple spinner for long-running operations."""

    def __init__(self, message: str = "Working", console: Console | None = None):
        """Initialize spinner.

        Args:
            message: Message to display
            console: Rich console instance
        """
        self.message = message
        self.console = console or Console()

    def __enter__(self) -> "Spinner":
        """Enter context manager."""

        self._spinner = self.console.status(self.message, spinner="dots")
        self._spinner.__enter__()
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Exit context manager."""
        if self._spinner:
            self._spinner.__exit__(exc_type, exc_val, exc_tb)

    def update(self, message: str) -> None:
        """Update spinner message.

        Args:
            message: New message to display
        """
        if hasattr(self, "_spinner") and self._spinner:
            self._spinner.update(message)

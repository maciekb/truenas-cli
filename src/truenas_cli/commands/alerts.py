from __future__ import annotations

import argparse
import json
from datetime import datetime

from truenas_client import TrueNASClient

from ..core import run_command
from .base import CommandGroup


def _extract_alert_timestamp(alert):
    """Extract alert creation timestamp as datetime object."""
    # Try common datetime field names
    for field in ["datetime", "created", "timestamp", "date"]:
        value = alert.get(field)
        if value:
            try:
                # Handle dict with $date key (MongoDB format)
                if isinstance(value, dict):
                    if "$date" in value:
                        ts = value["$date"]
                        if isinstance(ts, (int, float)):
                            # Timestamp is in milliseconds
                            return datetime.fromtimestamp(ts / 1000)
                    elif "parsed" in value:
                        parsed = value["parsed"]
                        if isinstance(parsed, dict) and "$date" in parsed:
                            ts = parsed["$date"]
                            if isinstance(ts, (int, float)):
                                return datetime.fromtimestamp(ts / 1000)
                # Handle Unix timestamp (seconds)
                elif isinstance(value, (int, float)):
                    return datetime.fromtimestamp(value)
                # Handle ISO string
                elif isinstance(value, str):
                    try:
                        return datetime.fromisoformat(value.replace("Z", "+00:00"))
                    except ValueError:
                        pass
            except Exception:
                pass
    return None


def _format_alert_datetime(alert):
    """Extract and format alert creation datetime as string."""
    dt = _extract_alert_timestamp(alert)
    if dt:
        return dt.isoformat(sep=" ", timespec="seconds")
    return "N/A"


def _format_alert_duration(alert):
    """Calculate and format how long alert has been active."""
    dt = _extract_alert_timestamp(alert)
    if not dt:
        return "N/A"

    now = datetime.now()
    if dt.tzinfo is not None:
        # Make now timezone-aware if dt is
        from datetime import timezone

        now = now.replace(tzinfo=timezone.utc).astimezone()

    delta = now - dt

    days = delta.days
    seconds = delta.seconds
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60

    if days > 0:
        return f"{days}d {hours}h {minutes}m"
    elif hours > 0:
        return f"{hours}h {minutes}m"
    else:
        return f"{minutes}m"


class AlertsCommands(CommandGroup):
    """Alert operations (``alert.list`` API)."""

    name = "alerts"

    def register_commands(
        self,
        subparsers: argparse._SubParsersAction,
        parent_parser: argparse.ArgumentParser,
    ) -> None:
        """Register alert subcommands."""
        # List alerts
        list_parser = self.add_command(
            subparsers,
            "list",
            "List alerts (alert.list)",
            _cmd_alerts_list,
            parent_parser=parent_parser,
        )
        self.add_optional_argument(
            list_parser,
            "--full",
            "full",
            "Show all available fields (including dismissed alerts)",
            action="store_true",
        )

        # Dismiss alert
        dismiss_parser = self.add_command(
            subparsers,
            "dismiss",
            "Dismiss an alert (alert.dismiss)",
            _cmd_alerts_list,
            parent_parser=parent_parser,
        )
        self.add_required_argument(
            dismiss_parser,
            "alert_id",
            "Alert ID to dismiss",
        )


async def _cmd_alerts_list(args):
    async def handler(client: TrueNASClient):
        alerts = await client.get_alerts()

        if args.json:
            print(json.dumps(alerts, indent=2))
            return

        # Filter out dismissed alerts by default (unless --full is used)
        display_alerts = (
            alerts
            if args.full
            else [a for a in alerts if not a.get("dismissed", False)]
            if alerts
            else []
        )

        print("\n=== Alerts ===")
        if not display_alerts:
            print("No alerts found." if args.full else "No active alerts.")
            return

        for alert in display_alerts:
            alert_id = alert.get("id", "N/A")
            level = alert.get("level", "INFO")
            icon = "⚠️" if level == "WARNING" else "🔴" if level == "CRITICAL" else "ℹ️"
            # Use formatted message if available, otherwise use text or klass
            message = alert.get("formatted") or alert.get(
                "text", alert.get("klass", "Unknown alert")
            )
            created = _format_alert_datetime(alert)
            duration = _format_alert_duration(alert)

            print(f"\n{icon} Alert: {alert_id}")
            print(f"  ID: {alert_id}")
            print(f"  Level: {level}")
            print(f"  Created: {created}")
            print(f"  Active for: {duration}")
            print(f"  Message: {message}")

            if args.full:
                # Show all available fields
                excluded_keys = {
                    "id",
                    "level",
                    "formatted",
                    "text",
                    "klass",
                    "datetime",
                    "created",
                    "timestamp",
                    "date",
                }
                for key, value in sorted(alert.items()):
                    if key not in excluded_keys:
                        if isinstance(value, bool):
                            value = "Yes" if value else "No"
                        elif isinstance(value, dict):
                            value = json.dumps(value)
                        elif isinstance(value, list):
                            value = ", ".join(map(str, value)) if value else "None"
                        print(f"  {key}: {value}")
            else:
                # Show source if available
                if alert.get("source"):
                    print(f"  Source: {alert['source']}")
                # Show dismissed status if true
                if alert.get("dismissed"):
                    print("  Dismissed: Yes")

    await run_command(args, handler)


async def _cmd_alerts_acknowledge(args):
    """Handle ``alerts ack`` using ``alert.dismiss``."""

    async def handler(client: TrueNASClient):
        alert_id = args.alert_id

        print(f"Dismissing alert: {alert_id}...")

        result = await client.call("alert.dismiss", [alert_id])

        if args.json:
            print(json.dumps(result, indent=2))
            return

        print(f"✓ Alert dismissed: {alert_id}")

    await run_command(args, handler)

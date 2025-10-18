"""Base class for CLI command groups.

This module provides :class:`CommandGroup`, an abstract base class that reduces
boilerplate when implementing command groups for the TrueNAS CLI. All command
modules (system.py, pool.py, smb.py, etc.) should inherit from CommandGroup.

Key Benefits:
    - Reduces ~60% of command registration boilerplate
    - Consistent argument parsing across commands
    - Uniform error handling and logging
    - Easier to add new commands

Command Group Architecture:
    CommandGroup (this module)
        ↓ (subclass)
    SystemCommands, PoolCommands, etc. (commands/*.py)
        ↓ (register called by)
    CLI Parser (cli.py)

How It Works:
    1. Subclass CommandGroup
    2. Set name attribute (used for command ordering)
    3. Implement register_commands() method
    4. Use add_command() and helper methods to add subcommands

Command Handler Pattern:
    All handlers must be async functions taking parsed args:

    >>> async def _cmd_list(args):
    ...     async def handler(client: TrueNASClient):
    ...         items = await client.get_items()
    ...         print(json.dumps(items, indent=2))
    ...     await run_command(args, handler)

Helper Methods:
    - add_command(): Add a subcommand with handler
    - add_required_argument(): Add positional argument
    - add_optional_argument(): Add optional flag argument
    - get_group_help(): Customize help text

Example Usage:
    >>> class MyCommands(CommandGroup):
    ...     name = "mycommand"
    ...
    ...     def register_commands(self, subparsers, parent_parser):
    ...         self.add_command(
    ...             subparsers,
    ...             "list",
    ...             "List items",
    ...             _cmd_list,
    ...             parent_parser=parent_parser,
    ...         )

Integration:
    Command groups are registered in commands/__init__.py:

    >>> from .mycommand import MyCommands
    >>> COMMAND_GROUPS = [
    ...     # ... other groups
    ...     MyCommands(),
    ... ]

See Also:
    - DEVELOPMENT.md: CLI command development guidelines
    - cli.py: Parser bootstrap and command execution
    - core.py: Command handler utilities
"""

from __future__ import annotations

import argparse
from abc import ABC, abstractmethod
from typing import Any, Callable, Optional


class CommandGroup(ABC):
    """Abstract base class for command groups.

    Subclasses should:
    1. Set the `name` attribute (used for ordering)
    2. Implement `register_commands()` to add subcommands
    3. Define async handler functions following the pattern:
       - Async function taking `args` parameter
       - Inner `handler()` function taking `TrueNASClient`
       - Call `await run_command(args, handler)`

    Example:
        class MyCommands(CommandGroup):
            name = "mycommand"

            def register_commands(self, sub: _SubparsersAction):
                self.add_command(
                    sub,
                    "subcommand",
                    "Help text",
                    _cmd_handler,
                    [("--option", {"help": "Option help"})]
                )
    """

    name: str = "unnamed"

    def register(
        self,
        subparsers: argparse._SubParsersAction,
        parent_parser: argparse.ArgumentParser,
    ) -> None:
        """Register command group and subcommands.

        This method is called by the CLI framework to register this
        command group. It handles the boilerplate of creating the
        main parser and subparsers, then delegates to register_commands().

        Args:
            subparsers: Parent subparsers action
            parent_parser: Parent argument parser with global options
        """
        # Create main command parser
        parser = subparsers.add_parser(
            self.name,
            help=self.get_group_help(),
            parents=[parent_parser],
        )

        # Create subcommands parser
        sub = parser.add_subparsers(dest=f"{self.name}_command")
        parser.set_defaults(_subparser_attr=(parser, f"{self.name}_command"))

        # Let subclass register its commands
        self.register_commands(sub, parent_parser)

    @abstractmethod
    def register_commands(
        self,
        subparsers: argparse._SubParsersAction,
        parent_parser: argparse.ArgumentParser,
    ) -> None:
        """Register subcommands for this group.

        Subclasses must implement this method to define their subcommands.

        Args:
            subparsers: Subparsers action for adding commands
            parent_parser: Parent parser with global options
        """
        pass

    def get_group_help(self) -> str:
        """Get help text for this command group.

        Override to provide custom help text.
        Returns docstring first line by default.
        """
        if self.__class__.__doc__:
            return self.__class__.__doc__.split("\n")[0]
        return f"{self.name} operations"

    @staticmethod
    def add_command(
        subparsers: argparse._SubParsersAction,
        name: str,
        help_text: str,
        handler: Callable,
        arguments: Optional[list] = None,
        parent_parser: Optional[argparse.ArgumentParser] = None,
    ) -> argparse.ArgumentParser:
        """Add a subcommand with optional arguments.

        Args:
            subparsers: Subparsers action for this group
            name: Command name (e.g., 'list', 'create')
            help_text: Help text for the command
            handler: Async handler function
            arguments: List of tuples for add_argument() calls
            parent_parser: Parent parser for inheriting global options

        Returns:
            Created argument parser

        Example:
            >>> CommandGroup.add_command(
            ...     subparsers,
            ...     "list",
            ...     "List items",
            ...     _cmd_list,
            ...     [
            ...         ("--filter", {"help": "Filter items"}),
            ...         ("--limit", {"type": int, "help": "Limit results"}),
            ...     ],
            ...     parent_parser,
            ... )
        """
        parents = [parent_parser] if parent_parser else []
        parser = subparsers.add_parser(
            name,
            help=help_text,
            parents=parents,
        )
        parser.set_defaults(func=handler)

        # Add optional arguments
        if arguments:
            for arg_item in arguments:
                if isinstance(arg_item, tuple) and len(arg_item) == 2:
                    arg_name, arg_kwargs = arg_item
                    parser.add_argument(arg_name, **arg_kwargs)

        return parser

    @staticmethod
    def add_required_argument(
        parser: argparse.ArgumentParser,
        name: str,
        help_text: str,
        **kwargs: Any,
    ) -> None:
        """Add a required positional argument to a parser.

        Args:
            parser: Argument parser
            name: Argument name
            help_text: Help text
            **kwargs: Additional arguments for add_argument()
        """
        parser.add_argument(name, help=help_text, **kwargs)

    @staticmethod
    def add_optional_argument(
        parser: argparse.ArgumentParser,
        flag: str,
        name: str,
        help_text: str,
        **kwargs: Any,
    ) -> None:
        """Add an optional flag argument to a parser.

        Args:
            parser: Argument parser
            flag: Flag (e.g., '-p', '--pool')
            name: Destination variable name
            help_text: Help text
            **kwargs: Additional arguments for add_argument()
        """
        parser.add_argument(flag, dest=name, help=help_text, **kwargs)

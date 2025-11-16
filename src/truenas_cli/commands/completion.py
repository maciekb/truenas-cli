"""Shell completion installation commands.

This module provides commands for installing and managing shell completion
for bash, zsh, and fish shells.
"""

import os
import subprocess
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax

app = typer.Typer(
    help="Manage shell completion",
    no_args_is_help=True,
)
console = Console()


def get_shell() -> str:
    """Detect current shell from environment.

    Returns:
        Shell name (bash, zsh, fish) or 'unknown'
    """
    shell = os.environ.get("SHELL", "")
    if "bash" in shell:
        return "bash"
    elif "zsh" in shell:
        return "zsh"
    elif "fish" in shell:
        return "fish"
    return "unknown"


@app.command("install")
def install_completion(
    shell: Optional[str] = typer.Option(
        None,
        "--shell",
        "-s",
        help="Shell to install completion for (bash, zsh, fish)",
    ),
    show_only: bool = typer.Option(
        False,
        "--show",
        help="Only show installation instructions without installing",
    ),
) -> None:
    """Install shell completion for truenas-cli.

    Detects your shell and installs appropriate completion scripts.
    Supports bash, zsh, and fish shells.

    Examples:
        # Auto-detect shell and install
        truenas-cli completion install

        # Install for specific shell
        truenas-cli completion install --shell bash

        # Show instructions only
        truenas-cli completion install --show
    """
    # Detect shell if not specified
    if not shell:
        shell = get_shell()
        if shell == "unknown":
            console.print(
                "[red]Error:[/red] Could not detect shell. "
                "Please specify with --shell option."
            )
            raise typer.Exit(1)
        console.print(f"[dim]Detected shell: {shell}[/dim]\n")

    # Validate shell
    if shell not in ["bash", "zsh", "fish"]:
        console.print(
            f"[red]Error:[/red] Unsupported shell '{shell}'. "
            "Supported shells: bash, zsh, fish"
        )
        raise typer.Exit(1)

    # Get completion script
    if shell == "bash":
        script, instructions = get_bash_completion()
    elif shell == "zsh":
        script, instructions = get_zsh_completion()
    else:  # fish
        script, instructions = get_fish_completion()

    if show_only:
        # Show script and instructions
        console.print(Panel(instructions, title=f"{shell.title()} Completion"))
        console.print("\n[bold]Completion Script:[/bold]")
        syntax = Syntax(script, "bash", theme="monokai", line_numbers=False)
        console.print(syntax)
    else:
        # Install completion
        try:
            install_completion_script(shell, script)
            console.print(f"[green]Shell completion installed for {shell}![/green]\n")
            console.print(Panel(instructions, title="Next Steps"))
        except Exception as e:
            console.print(f"[red]Error installing completion:[/red] {e}")
            console.print("\n[yellow]Try running with --show to see manual instructions.[/yellow]")
            raise typer.Exit(1)


def get_bash_completion() -> tuple[str, str]:
    """Get bash completion script and instructions.

    Returns:
        Tuple of (script, instructions)
    """
    script = """# truenas-cli completion for bash
_truenas_cli_completion() {
    local IFS=$'\\n'
    local response

    response=$(env COMP_WORDS="${COMP_WORDS[*]}" COMP_CWORD=$COMP_CWORD _TRUENAS_CLI_COMPLETE=bash_complete $1)

    for completion in $response; do
        IFS=',' read type value <<< "$completion"

        if [[ $type == 'dir' ]]; then
            COMPREPLY=()
            compopt -o dirnames
        elif [[ $type == 'file' ]]; then
            COMPREPLY=()
            compopt -o default
        elif [[ $type == 'plain' ]]; then
            COMPREPLY+=($value)
        fi
    done

    return 0
}

_truenas_cli_completion_setup() {
    complete -o nosort -F _truenas_cli_completion truenas-cli
}

_truenas_cli_completion_setup;
"""

    instructions = """To enable completion, restart your shell or run:

    source ~/.bash_completion.d/truenas-cli

For permanent installation, the script has been added to your bash completion directory."""

    return script, instructions


def get_zsh_completion() -> tuple[str, str]:
    """Get zsh completion script and instructions.

    Returns:
        Tuple of (script, instructions)
    """
    script = """#compdef truenas-cli

_truenas_cli_completion() {
    local -a completions
    local -a completions_with_descriptions
    local -a response
    (( ! $+commands[truenas-cli] )) && return 1

    response=("${(@f)$(env COMP_WORDS="${words[*]}" COMP_CWORD=$((CURRENT-1)) _TRUENAS_CLI_COMPLETE=zsh_complete truenas-cli)}")

    for type key descr in ${response}; do
        if [[ "$type" == "plain" ]]; then
            if [[ "$descr" == "_" ]]; then
                completions+=("$key")
            else
                completions_with_descriptions+=("$key":"$descr")
            fi
        elif [[ "$type" == "dir" ]]; then
            _path_files -/
        elif [[ "$type" == "file" ]]; then
            _path_files -f
        fi
    done

    if [ -n "$completions_with_descriptions" ]; then
        _describe -V unsorted completions_with_descriptions -U
    fi

    if [ -n "$completions" ]; then
        compadd -U -V unsorted -a completions
    fi
}

compdef _truenas_cli_completion truenas-cli;
"""

    instructions = """To enable completion, restart your shell or run:

    source ~/.zfunc/_truenas-cli

For permanent installation, ensure ~/.zfunc is in your $fpath before compinit."""

    return script, instructions


def get_fish_completion() -> tuple[str, str]:
    """Get fish completion script and instructions.

    Returns:
        Tuple of (script, instructions)
    """
    script = """# truenas-cli completion for fish

function _truenas_cli_completion
    set -l response (env _TRUENAS_CLI_COMPLETE=fish_complete COMP_WORDS=(commandline -opc) COMP_CWORD=(commandline -t) truenas-cli)

    for completion in $response
        set -l metadata (string split "," $completion)

        if test $metadata[1] = "dir"
            __fish_complete_directories $metadata[2]
        else if test $metadata[1] = "file"
            __fish_complete_path $metadata[2]
        else if test $metadata[1] = "plain"
            echo $metadata[2]
        end
    end
end

complete --no-files --command truenas-cli --arguments '(_truenas_cli_completion)'
"""

    instructions = """To enable completion, restart your shell.

The completion script has been installed to:
    ~/.config/fish/completions/truenas-cli.fish"""

    return script, instructions


def install_completion_script(shell: str, script: str) -> None:
    """Install completion script for specified shell.

    Args:
        shell: Shell name (bash, zsh, fish)
        script: Completion script content

    Raises:
        Exception: If installation fails
    """
    home = Path.home()

    if shell == "bash":
        # Install to ~/.bash_completion.d/
        completion_dir = home / ".bash_completion.d"
        completion_dir.mkdir(parents=True, exist_ok=True)
        completion_file = completion_dir / "truenas-cli"

        # Also add sourcing to .bashrc if not present
        bashrc = home / ".bashrc"
        if bashrc.exists():
            bashrc_content = bashrc.read_text()
            if ".bash_completion.d/truenas-cli" not in bashrc_content:
                with bashrc.open("a") as f:
                    f.write("\n# TrueNAS CLI completion\n")
                    f.write("[ -f ~/.bash_completion.d/truenas-cli ] && ")
                    f.write("source ~/.bash_completion.d/truenas-cli\n")

    elif shell == "zsh":
        # Install to ~/.zfunc/
        completion_dir = home / ".zfunc"
        completion_dir.mkdir(parents=True, exist_ok=True)
        completion_file = completion_dir / "_truenas-cli"

        # Add to fpath in .zshrc if not present
        zshrc = home / ".zshrc"
        if zshrc.exists():
            zshrc_content = zshrc.read_text()
            if "fpath=(~/.zfunc" not in zshrc_content:
                with zshrc.open("a") as f:
                    f.write("\n# TrueNAS CLI completion\n")
                    f.write("fpath=(~/.zfunc $fpath)\n")

    else:  # fish
        # Install to ~/.config/fish/completions/
        completion_dir = home / ".config" / "fish" / "completions"
        completion_dir.mkdir(parents=True, exist_ok=True)
        completion_file = completion_dir / "truenas-cli.fish"

    # Write completion file
    completion_file.write_text(script)
    completion_file.chmod(0o644)


@app.command("uninstall")
def uninstall_completion(
    shell: Optional[str] = typer.Option(
        None,
        "--shell",
        "-s",
        help="Shell to uninstall completion from",
    ),
) -> None:
    """Uninstall shell completion.

    Examples:
        truenas-cli completion uninstall
        truenas-cli completion uninstall --shell bash
    """
    if not shell:
        shell = get_shell()
        if shell == "unknown":
            console.print("[red]Error:[/red] Could not detect shell. Please specify with --shell.")
            raise typer.Exit(1)

    home = Path.home()

    if shell == "bash":
        completion_file = home / ".bash_completion.d" / "truenas-cli"
    elif shell == "zsh":
        completion_file = home / ".zfunc" / "_truenas-cli"
    elif shell == "fish":
        completion_file = home / ".config" / "fish" / "completions" / "truenas-cli.fish"
    else:
        console.print(f"[red]Error:[/red] Unsupported shell '{shell}'")
        raise typer.Exit(1)

    if completion_file.exists():
        completion_file.unlink()
        console.print(f"[green]Shell completion uninstalled for {shell}[/green]")
    else:
        console.print(f"[yellow]No completion found for {shell}[/yellow]")


@app.command("show")
def show_completion(
    shell: Optional[str] = typer.Option(
        None,
        "--shell",
        "-s",
        help="Shell to show completion for",
    ),
) -> None:
    """Show completion script for a shell.

    Examples:
        truenas-cli completion show --shell bash
    """
    if not shell:
        shell = get_shell()

    if shell == "bash":
        script, _ = get_bash_completion()
    elif shell == "zsh":
        script, _ = get_zsh_completion()
    elif shell == "fish":
        script, _ = get_fish_completion()
    else:
        console.print(f"[red]Error:[/red] Unsupported shell '{shell}'")
        raise typer.Exit(1)

    syntax = Syntax(script, "bash", theme="monokai", line_numbers=True)
    console.print(Panel(syntax, title=f"{shell.title()} Completion Script"))

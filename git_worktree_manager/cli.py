"""CLI entry point for Git Worktree Manager."""

import sys
from typing import Optional

import click
from rich.console import Console
from rich.panel import Panel

from .exceptions import (
    GitRepositoryError,
)
from .git_ops import GitOperations

console = Console()


class GitWorktreeCLI:
    """Main CLI class for Git Worktree Manager."""

    def __init__(self):
        """Initialize the CLI with Git operations."""
        self.git_ops = GitOperations()

    def validate_git_repository(self) -> bool:
        """Validate that we're in a Git repository.

        Returns:
            True if in a valid Git repository, False otherwise
        """
        try:
            return self.git_ops.is_git_repository()
        except GitRepositoryError as e:
            console.print(f"[red]Error:[/red] {e}")
            return False


@click.group(invoke_without_command=True)
@click.pass_context
def cli(ctx: click.Context) -> None:
    """Git Worktree Manager - Interactive CLI tool for managing Git worktrees.

    This tool helps you create and manage Git worktrees with an intuitive interface.
    Run commands from within a Git repository to get started.
    """
    # Initialize CLI instance
    cli_instance = GitWorktreeCLI()
    ctx.ensure_object(dict)
    ctx.obj["cli"] = cli_instance

    # Validate Git repository if a subcommand is being called
    if ctx.invoked_subcommand is not None:
        if not cli_instance.validate_git_repository():
            console.print(
                Panel(
                    "[red]Not in a Git repository[/red]\n\n"
                    "Please run this command from within a Git repository.\n"
                    "To initialize a new Git repository, run: [cyan]git init[/cyan]",
                    title="Git Repository Required",
                    border_style="red",
                )
            )
            ctx.exit(1)
    else:
        # Show help when no command is provided
        console.print(
            Panel(
                "[bold blue]Git Worktree Manager[/bold blue]\n\n"
                "Interactive CLI tool for managing Git worktrees with Rich UI.\n\n"
                "Available commands:\n"
                "  [cyan]create[/cyan]     Create a new worktree interactively\n"
                "  [cyan]list[/cyan]       List all worktrees with status information\n"
                "  [cyan]configure[/cyan]  Configure worktree preferences\n\n"
                "Use [cyan]--help[/cyan] with any command for more information.",
                title="Welcome to Git Worktree Manager",
                border_style="blue",
            )
        )


@cli.command()
@click.pass_context
def create(ctx: click.Context) -> None:
    """Create a new worktree interactively.

    This command will guide you through creating a new worktree by prompting
    for branch name, base branch selection, and worktree location.
    """
    from .worktree_manager import WorktreeCreationError, WorktreeManager

    try:
        # Initialize WorktreeManager
        worktree_manager = WorktreeManager()

        # Create worktree with interactive prompts
        console.print(
            Panel(
                "[bold blue]Creating New Worktree[/bold blue]\n\n"
                "This will guide you through creating a new Git worktree.\n"
                "You'll be prompted for branch name, base branch, and location.",
                title="Worktree Creation",
                border_style="blue",
            )
        )

        worktree_info = worktree_manager.create_worktree()

        # Display success information
        console.print()
        console.print(
            Panel(
                f"[bold green]✓ Worktree Created Successfully![/bold green]\n\n"
                f"Branch: [cyan]{worktree_info.branch}[/cyan]\n"
                f"Location: [dim]{worktree_info.path}[/dim]\n"
                f"Base Branch: [cyan]{worktree_info.base_branch or 'N/A'}[/cyan]",
                title="Success",
                border_style="green",
            )
        )

    except WorktreeCreationError as e:
        console.print(
            Panel(
                f"[red]Failed to create worktree:[/red]\n\n{e}",
                title="Creation Failed",
                border_style="red",
            )
        )
        ctx.exit(1)
    except KeyboardInterrupt:
        console.print("\n[yellow]Worktree creation cancelled by user.[/yellow]")
        ctx.exit(1)
    except Exception as e:
        console.print(
            Panel(
                f"[red]Unexpected error:[/red]\n\n{e}",
                title="Error",
                border_style="red",
            )
        )
        ctx.exit(1)


@cli.command()
@click.option("--diff", is_flag=True, help="Show diff summaries for each worktree")
@click.option(
    "--details", is_flag=True, help="Show detailed information for each worktree"
)
@click.pass_context
def list(ctx: click.Context, diff: bool, details: bool) -> None:
    """List all worktrees with comprehensive status information.

    Shows all existing worktrees with their branch names, commit information,
    file paths, and change status.
    """
    from .git_ops import GitRepositoryError
    from .worktree_manager import WorktreeManager

    try:
        # Initialize WorktreeManager
        worktree_manager = WorktreeManager()

        console.print(
            Panel(
                "[bold blue]Git Worktrees[/bold blue]\n\n"
                "Listing all worktrees in this repository with status information.",
                title="Worktree List",
                border_style="blue",
            )
        )

        # Get worktree list
        console.print("[dim]Loading worktree information...[/dim]")
        worktrees = worktree_manager.list_worktrees()

        if not worktrees:
            console.print(
                Panel(
                    "[yellow]No worktrees found in this repository.[/yellow]\n\n"
                    "Use [cyan]create[/cyan] command to create your first worktree.",
                    title="No Worktrees",
                    border_style="yellow",
                )
            )
            return

        # Display worktree summary
        worktree_manager.ui_controller.display_worktree_summary(worktrees)
        console.print()

        # Display worktree list
        worktree_manager.ui_controller.display_worktree_list(worktrees)

        # Show detailed information if requested
        if details:
            console.print()
            console.print("[bold]Detailed Information:[/bold]")
            for worktree in worktrees:
                console.print()
                worktree_manager.ui_controller.display_worktree_details(worktree)

        # Show diff summaries if requested
        if diff:
            console.print()
            console.print("[bold]Diff Summaries:[/bold]")
            for worktree in worktrees:
                console.print()
                try:
                    diff_summary = worktree_manager.calculate_diff_summary(worktree)
                    if diff_summary:
                        worktree_manager.ui_controller.display_diff_summary(
                            diff_summary,
                            worktree.branch,
                            worktree.base_branch or "unknown",
                        )
                    else:
                        console.print(
                            f"[dim]No diff information available for {worktree.branch}[/dim]"
                        )
                except GitRepositoryError as e:
                    console.print(
                        f"[red]Error calculating diff for {worktree.branch}: {e}[/red]"
                    )

    except GitRepositoryError as e:
        console.print(
            Panel(
                f"[red]Git operation failed:[/red]\n\n{e}",
                title="Git Error",
                border_style="red",
            )
        )
        ctx.exit(1)
    except KeyboardInterrupt:
        console.print("\n[yellow]Worktree listing cancelled by user.[/yellow]")
        ctx.exit(1)
    except Exception as e:
        console.print(
            Panel(
                f"[red]Unexpected error:[/red]\n\n{e}",
                title="Error",
                border_style="red",
            )
        )
        ctx.exit(1)


@cli.command()
@click.option(
    "--show", is_flag=True, help="Show current configuration without making changes"
)
@click.option("--reset", is_flag=True, help="Reset configuration to defaults")
@click.pass_context
def configure(ctx: click.Context, show: bool, reset: bool) -> None:
    """Configure worktree preferences interactively.

    Set default worktree storage locations and other preferences that will
    be persisted across sessions.
    """
    from rich.prompt import Confirm, Prompt

    from .config import ConfigError, ConfigManager

    try:
        # Initialize ConfigManager
        config_manager = ConfigManager()

        console.print(
            Panel(
                "[bold blue]Worktree Configuration[/bold blue]\n\n"
                "Configure default settings for Git worktree management.",
                title="Configuration",
                border_style="blue",
            )
        )

        # Show current configuration if requested
        if show:
            try:
                current_config = config_manager.load_user_preferences()
                default_location = config_manager.get_default_worktree_location()

                console.print()
                console.print("[bold]Current Configuration:[/bold]")
                console.print(
                    f"Default Worktree Location: [cyan]{default_location}[/cyan]"
                )

                if current_config:
                    console.print()
                    console.print("[bold]All Settings:[/bold]")
                    for key, value in current_config.items():
                        console.print(f"  {key}: [dim]{value}[/dim]")
                else:
                    console.print(
                        "[dim]No custom configuration found (using defaults)[/dim]"
                    )

                return

            except ConfigError as e:
                console.print(f"[red]Error loading configuration: {e}[/red]")
                ctx.exit(1)

        # Reset configuration if requested
        if reset:
            if Confirm.ask(
                "[yellow]Are you sure you want to reset all configuration to defaults?[/yellow]",
                default=False,
                console=console,
            ):
                try:
                    # Reset by saving empty preferences
                    config_manager.save_user_preferences({})
                    console.print(
                        Panel(
                            "[green]Configuration reset to defaults successfully![/green]",
                            title="Reset Complete",
                            border_style="green",
                        )
                    )
                    return
                except ConfigError as e:
                    console.print(f"[red]Error resetting configuration: {e}[/red]")
                    ctx.exit(1)
            else:
                console.print("[yellow]Configuration reset cancelled.[/yellow]")
                return

        # Interactive configuration setup
        console.print()
        console.print("[bold]Interactive Configuration Setup[/bold]")
        console.print("[dim]Press Ctrl+C at any time to cancel[/dim]")

        # Get current settings
        try:
            current_location = config_manager.get_default_worktree_location()
            current_prefs = config_manager.load_user_preferences()
        except ConfigError as e:
            console.print(f"[red]Error loading current configuration: {e}[/red]")
            ctx.exit(1)

        console.print()
        console.print(
            f"[bold]Current default worktree location:[/bold] [cyan]{current_location}[/cyan]"
        )

        # Prompt for new default location
        if Confirm.ask(
            "Would you like to change the default worktree location?",
            default=False,
            console=console,
        ):
            while True:
                try:
                    new_location = Prompt.ask(
                        "[cyan]Enter new default worktree location[/cyan]",
                        default=current_location,
                        console=console,
                    )

                    # Validate the path
                    import os
                    from pathlib import Path

                    expanded_path = os.path.expanduser(
                        os.path.expandvars(new_location.strip())
                    )
                    abs_path = os.path.abspath(expanded_path)

                    # Check if parent directory exists or can be created
                    parent_dir = os.path.dirname(abs_path)
                    if not os.path.exists(parent_dir):
                        if Confirm.ask(
                            f"Parent directory [path]{parent_dir}[/path] doesn't exist. Create it?",
                            default=True,
                            console=console,
                        ):
                            try:
                                Path(parent_dir).mkdir(parents=True, exist_ok=True)
                            except OSError as e:
                                console.print(
                                    f"[red]Error creating directory: {e}[/red]"
                                )
                                continue
                        else:
                            console.print(
                                "[yellow]Please choose a different location.[/yellow]"
                            )
                            continue

                    # Save the new location
                    try:
                        new_prefs = current_prefs.copy()
                        new_prefs["default_worktree_location"] = abs_path
                        config_manager.save_user_preferences(new_prefs)

                        console.print(
                            f"[green]Default location updated to:[/green] [cyan]{abs_path}[/cyan]"
                        )
                        break

                    except ConfigError as e:
                        console.print(f"[red]Error saving configuration: {e}[/red]")
                        continue

                except KeyboardInterrupt:
                    console.print("\n[yellow]Configuration cancelled by user.[/yellow]")
                    ctx.exit(1)
                except Exception as e:
                    console.print(f"[red]Invalid path: {e}[/red]")
                    continue

        # Show final configuration
        console.print()
        try:
            final_location = config_manager.get_default_worktree_location()
            console.print(
                Panel(
                    f"[green]Configuration updated successfully![/green]\n\n"
                    f"Default Worktree Location: [cyan]{final_location}[/cyan]",
                    title="Configuration Complete",
                    border_style="green",
                )
            )
        except ConfigError as e:
            console.print(f"[red]Error reading final configuration: {e}[/red]")
            ctx.exit(1)

    except KeyboardInterrupt:
        console.print("\n[yellow]Configuration cancelled by user.[/yellow]")
        ctx.exit(1)
    except Exception as e:
        console.print(
            Panel(
                f"[red]Unexpected error:[/red]\n\n{e}",
                title="Error",
                border_style="red",
            )
        )
        ctx.exit(1)


def main(args: Optional[list] = None) -> int:
    """Main CLI entry point.

    Args:
        args: Command line arguments (defaults to sys.argv)

    Returns:
        Exit code (0 for success, non-zero for error)
    """
    try:
        if args is None:
            cli()
        else:
            cli(args)
        return 0
    except click.ClickException as e:
        e.show()
        return e.exit_code
    except KeyboardInterrupt:
        console.print("\n[yellow]Operation cancelled by user.[/yellow]")
        return 1
    except Exception as e:
        console.print(f"[red]Unexpected error:[/red] {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())

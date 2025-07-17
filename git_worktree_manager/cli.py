"""CLI entry point for Git Worktree Manager."""

import sys
import os
from typing import Optional

import click
from rich.console import Console
from rich.panel import Panel

from .git_ops import GitOperations, GitRepositoryError


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
    ctx.obj['cli'] = cli_instance
    
    # Validate Git repository if a subcommand is being called
    if ctx.invoked_subcommand is not None:
        if not cli_instance.validate_git_repository():
            console.print(
                Panel(
                    "[red]Not in a Git repository[/red]\n\n"
                    "Please run this command from within a Git repository.\n"
                    "To initialize a new Git repository, run: [cyan]git init[/cyan]",
                    title="Git Repository Required",
                    border_style="red"
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
                border_style="blue"
            )
        )


@cli.command()
@click.pass_context
def create(ctx: click.Context) -> None:
    """Create a new worktree interactively.
    
    This command will guide you through creating a new worktree by prompting
    for branch name, base branch selection, and worktree location.
    """
    from .worktree_manager import WorktreeManager, WorktreeCreationError
    
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
                border_style="blue"
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
                border_style="green"
            )
        )
        
    except WorktreeCreationError as e:
        console.print(
            Panel(
                f"[red]Failed to create worktree:[/red]\n\n{e}",
                title="Creation Failed",
                border_style="red"
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
                border_style="red"
            )
        )
        ctx.exit(1)


@cli.command()
@click.pass_context
def list(ctx: click.Context) -> None:
    """List all worktrees with comprehensive status information.
    
    Shows all existing worktrees with their branch names, commit information,
    file paths, and change status.
    """
    console.print("[yellow]Worktree listing command - Coming in next task![/yellow]")


@cli.command()
@click.pass_context
def configure(ctx: click.Context) -> None:
    """Configure worktree preferences interactively.
    
    Set default worktree storage locations and other preferences that will
    be persisted across sessions.
    """
    console.print("[yellow]Configuration command - Coming in next task![/yellow]")


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
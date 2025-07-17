#!/usr/bin/env python3
"""
Demo script for Git Worktree Manager

This script demonstrates the key features of the git-worktree-manager tool
by showing example outputs and usage patterns.
"""

import sys
from pathlib import Path

# Add the package to the path for demo purposes
sys.path.insert(0, str(Path(__file__).parent))

from rich.columns import Columns
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

console = Console()


def show_header():
    """Show the demo header."""
    header = Text("Git Worktree Manager Demo", style="bold blue")
    console.print(Panel(header, expand=False))
    console.print()


def show_installation_demo():
    """Show installation commands."""
    console.print("[bold green]🚀 Quick Installation & Setup[/bold green]")
    console.print()

    install_commands = """
```bash
# Clone and install in development mode
git clone https://github.com/JoshYG-TheKey/git-worktree-manager.git
cd git-worktree-manager
make install-dev

# Set up convenient 'gitwm' alias
make setup-alias

# Test the installation
gitwm --help
```
"""
    console.print(Markdown(install_commands))
    console.print()


def show_usage_demo():
    """Show usage examples."""
    console.print("[bold green]🎮 Usage Examples[/bold green]")
    console.print()

    # Create a sample worktree table
    table = Table(title="Sample Worktree List Output")
    table.add_column("Name", style="cyan")
    table.add_column("Branch", style="magenta")
    table.add_column("Status", style="green")
    table.add_column("Changes", style="yellow")
    table.add_column("Path", style="blue")

    table.add_row("main", "main", "Clean", "0", "~/repo")
    table.add_row(
        "feature-auth", "feature-auth", "Modified", "3", "~/worktrees/feature-auth"
    )
    table.add_row("bugfix-123", "bugfix-123", "Clean", "0", "~/worktrees/bugfix-123")
    table.add_row("experiment", "experiment", "Staged", "7", "~/worktrees/experiment")

    console.print(table)
    console.print()

    # Show diff summary example
    diff_panel = Panel(
        "[green]📊 Diff Summary for feature-auth:[/green]\n"
        "  • 2 files modified\n"
        "  • 1 file added\n"
        "  • 0 files deleted\n"
        "  • +45 insertions, -12 deletions",
        title="Diff Summary Example",
        border_style="green",
    )
    console.print(diff_panel)
    console.print()


def show_features_demo():
    """Show key features."""
    console.print("[bold green]✨ Key Features[/bold green]")
    console.print()

    features = [
        Panel("🎯 Interactive Creation\nGuided worktree setup", style="cyan"),
        Panel("📊 Status Display\nComprehensive info", style="magenta"),
        Panel("🔍 Diff Summaries\nSee changes at a glance", style="green"),
        Panel("⚙️ Configurable\nCustom storage paths", style="yellow"),
        Panel("🎨 Rich UI\nBeautiful terminal interface", style="blue"),
        Panel("⚡ Performance\nOptimized for large repos", style="red"),
    ]

    console.print(Columns(features, equal=True, expand=True))
    console.print()


def show_makefile_demo():
    """Show Makefile commands."""
    console.print("[bold green]🛠️ Development Commands[/bold green]")
    console.print()

    make_table = Table(title="Available Make Commands")
    make_table.add_column("Command", style="cyan")
    make_table.add_column("Description", style="white")

    make_table.add_row("make install-dev", "Install with dev dependencies")
    make_table.add_row("make setup-alias", "Create 'gitwm' shell alias")
    make_table.add_row("make test", "Run all tests")
    make_table.add_row("make test-coverage", "Run tests with coverage")
    make_table.add_row("make lint", "Run code linting")
    make_table.add_row("make format", "Format code with Black")
    make_table.add_row("make clean", "Clean build artifacts")
    make_table.add_row("make remove-alias", "Remove shell alias")

    console.print(make_table)
    console.print()


def show_workflow_demo():
    """Show typical workflow."""
    console.print("[bold green]🔄 Typical Workflow[/bold green]")
    console.print()

    workflow = """
```bash
# 1. Navigate to your Git repository
cd ~/my-project

# 2. Launch the tool
gitwm

# 3. Create a new worktree
# Select "Create new worktree"
# Enter name: feature-new-ui
# Select base branch: main
# Confirm location: ~/worktrees/feature-new-ui

# 4. Work in the new worktree
cd ~/worktrees/feature-new-ui
# Make your changes...

# 5. Check status of all worktrees
gitwm
# Select "List worktrees" to see status

# 6. Configure preferences
gitwm
# Select "Configure" to set default paths
```
"""
    console.print(Markdown(workflow))
    console.print()


def show_alias_demo():
    """Show alias benefits."""
    console.print("[bold green]🎯 Shell Alias Benefits[/bold green]")
    console.print()

    alias_comparison = Table(title="Command Comparison")
    alias_comparison.add_column("Without Alias", style="red")
    alias_comparison.add_column("With Alias", style="green")

    alias_comparison.add_row("git-worktree-manager", "gitwm")
    alias_comparison.add_row("git-worktree-manager --help", "gitwm --help")
    alias_comparison.add_row("git-worktree-manager create", "gitwm create")
    alias_comparison.add_row("git-worktree-manager list", "gitwm list")

    console.print(alias_comparison)
    console.print()

    console.print(
        "[dim]The alias is automatically added to both ~/.zshrc and ~/.bashrc[/dim]"
    )
    console.print()


def main():
    """Run the demo."""
    show_header()
    show_installation_demo()
    show_usage_demo()
    show_features_demo()
    show_makefile_demo()
    show_workflow_demo()
    show_alias_demo()

    console.print("[bold blue]🎉 Ready to get started?[/bold blue]")
    console.print("Run: [bold cyan]make install-dev && make setup-alias[/bold cyan]")
    console.print()


if __name__ == "__main__":
    main()

"""UI Controller for Git Worktree Manager using Rich library."""

import os
from typing import Any, List, Optional

from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.prompt import Confirm, IntPrompt, Prompt
from rich.table import Table
from rich.text import Text
from rich.theme import Theme

from .models import DiffSummary, WorktreeInfo


class UIController:
    """Controller for Rich-based user interface components."""

    def __init__(self, console: Optional[Console] = None):
        """Initialize UIController with Rich console and theme.

        Args:
            console: Optional Rich console instance. If None, creates a new one.
        """
        # Define custom theme for the application
        custom_theme = Theme(
            {
                "info": "cyan",
                "warning": "yellow",
                "error": "bold red",
                "success": "bold green",
                "branch": "bold blue",
                "path": "dim cyan",
                "commit": "magenta",
                "modified": "yellow",
                "added": "green",
                "deleted": "red",
                "unchanged": "dim white",
            }
        )

        self.console = console or Console(theme=custom_theme)
        self._progress: Optional[Progress] = None

    def display_error(self, message: str, title: str = "Error") -> None:
        """Display an error message with Rich formatting.

        Args:
            message: The error message to display
            title: The title for the error panel
        """
        error_panel = Panel(
            Text(message, style="error"),
            title=f"[error]{title}[/error]",
            border_style="error",
            box=box.ROUNDED,
        )
        self.console.print(error_panel)

    def display_warning(self, message: str, title: str = "Warning") -> None:
        """Display a warning message with Rich formatting.

        Args:
            message: The warning message to display
            title: The title for the warning panel
        """
        warning_panel = Panel(
            Text(message, style="warning"),
            title=f"[warning]{title}[/warning]",
            border_style="warning",
            box=box.ROUNDED,
        )
        self.console.print(warning_panel)

    def display_success(self, message: str, title: str = "Success") -> None:
        """Display a success message with Rich formatting.

        Args:
            message: The success message to display
            title: The title for the success panel
        """
        success_panel = Panel(
            Text(message, style="success"),
            title=f"[success]{title}[/success]",
            border_style="success",
            box=box.ROUNDED,
        )
        self.console.print(success_panel)

    def display_info(self, message: str, title: str = "Info") -> None:
        """Display an info message with Rich formatting.

        Args:
            message: The info message to display
            title: The title for the info panel
        """
        info_panel = Panel(
            Text(message, style="info"),
            title=f"[info]{title}[/info]",
            border_style="info",
            box=box.ROUNDED,
        )
        self.console.print(info_panel)

    def start_progress(self, description: str = "Working...") -> None:
        """Start a progress indicator.

        Args:
            description: Description text to show with the progress indicator
        """
        if self._progress is None:
            self._progress = Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=self.console,
                transient=True,
            )
            self._progress.start()

        self._progress.add_task(description=description)

    def update_progress(self, description: str) -> None:
        """Update the progress indicator description.

        Args:
            description: New description text
        """
        if self._progress is not None:
            # Get the first (and likely only) task and update it
            tasks = list(self._progress.tasks)
            if tasks:
                task_id = tasks[0].id
                self._progress.update(task_id, description=description)

    def stop_progress(self) -> None:
        """Stop the progress indicator."""
        if self._progress is not None:
            self._progress.stop()
            self._progress = None

    def clear_screen(self) -> None:
        """Clear the console screen."""
        self.console.clear()

    def print(self, *args: Any, **kwargs: Any) -> None:
        """Print to the console with Rich formatting.

        Args:
            *args: Arguments to pass to console.print
            **kwargs: Keyword arguments to pass to console.print
        """
        self.console.print(*args, **kwargs)

    def confirm(self, message: str, default: bool = False) -> bool:
        """Display a confirmation prompt.

        Args:
            message: The confirmation message
            default: Default value if user just presses Enter

        Returns:
            True if user confirms, False otherwise
        """
        return Confirm.ask(message, default=default, console=self.console)

    def get_console_width(self) -> int:
        """Get the current console width.

        Returns:
            Console width in characters
        """
        return self.console.size.width

    def get_console_height(self) -> int:
        """Get the current console height.

        Returns:
            Console height in lines
        """
        return self.console.size.height

    def prompt_branch_name(self, default: str = "") -> str:
        """Prompt user for a branch name with validation.

        Args:
            default: Default branch name if user just presses Enter

        Returns:
            Valid branch name entered by user

        Raises:
            KeyboardInterrupt: If user cancels the prompt
        """

        def validate_branch_name(name: str) -> str:
            """Validate branch name according to Git rules."""
            if not name.strip():
                raise ValueError("Branch name cannot be empty")

            name = name.strip()

            # Basic Git branch name validation
            invalid_chars = [" ", "~", "^", ":", "?", "*", "[", "\\", ".."]
            for char in invalid_chars:
                if char in name:
                    raise ValueError(f"Branch name cannot contain '{char}'")

            if name.startswith("-") or name.endswith("-"):
                raise ValueError("Branch name cannot start or end with '-'")

            if name.startswith(".") or name.endswith("."):
                raise ValueError("Branch name cannot start or end with '.'")

            if "//" in name:
                raise ValueError("Branch name cannot contain consecutive slashes")

            if name.endswith("/"):
                raise ValueError("Branch name cannot end with '/'")

            return name

        while True:
            try:
                prompt_text = "[branch]Branch name[/branch]"
                if default:
                    prompt_text += f" (default: [dim]{default}[/dim])"

                branch_name = Prompt.ask(
                    prompt_text,
                    default=default if default else None,
                    console=self.console,
                )

                return validate_branch_name(branch_name)

            except ValueError as e:
                self.display_error(str(e), "Invalid Branch Name")
                continue
            except KeyboardInterrupt:
                self.console.print("\n[warning]Operation cancelled by user[/warning]")
                raise

    def select_base_branch(
        self, branches: List[str], current_branch: Optional[str] = None
    ) -> str:
        """Interactive selection of base branch from available branches.

        Args:
            branches: List of available branch names
            current_branch: Current branch name (will be highlighted)

        Returns:
            Selected branch name

        Raises:
            KeyboardInterrupt: If user cancels the selection
            ValueError: If no branches are available
        """
        if not branches:
            raise ValueError("No branches available for selection")

        # Display available branches in a table
        table = Table(
            title="[branch]Available Branches[/branch]",
            show_header=True,
            header_style="bold blue",
            box=box.ROUNDED,
        )
        table.add_column("Index", style="dim", width=6)
        table.add_column("Branch Name", style="branch")
        table.add_column("Status", style="dim")

        for i, branch in enumerate(branches, 1):
            status = "current" if branch == current_branch else ""
            style = "bold green" if branch == current_branch else "branch"
            table.add_row(str(i), f"[{style}]{branch}[/{style}]", status)

        self.console.print(table)

        while True:
            try:
                choice = IntPrompt.ask(
                    f"[info]Select base branch (1-{len(branches)})[/info]",
                    console=self.console,
                )

                if 1 <= choice <= len(branches):
                    selected_branch = branches[choice - 1]
                    self.console.print(
                        f"[success]Selected:[/success] [branch]{selected_branch}[/branch]"
                    )
                    return selected_branch
                else:
                    self.display_error(
                        f"Please enter a number between 1 and {len(branches)}"
                    )

            except ValueError:
                self.display_error("Please enter a valid number")
                continue
            except KeyboardInterrupt:
                self.console.print("\n[warning]Operation cancelled by user[/warning]")
                raise

    def select_worktree_location(self, default_path: str = "") -> str:
        """Interactive selection of worktree location with path validation.

        Args:
            default_path: Default path if user just presses Enter

        Returns:
            Valid absolute path for worktree location

        Raises:
            KeyboardInterrupt: If user cancels the prompt
        """

        def validate_path(path: str) -> str:
            """Validate and normalize the path."""
            if not path.strip():
                raise ValueError("Path cannot be empty")

            # Expand user home directory and environment variables
            expanded_path = os.path.expanduser(os.path.expandvars(path.strip()))

            # Convert to absolute path
            abs_path = os.path.abspath(expanded_path)

            # Check if parent directory exists or can be created
            parent_dir = os.path.dirname(abs_path)
            if not os.path.exists(parent_dir):
                # Ask if user wants to create parent directories
                create_parent = self.confirm(
                    f"Parent directory [path]{parent_dir}[/path] doesn't exist. Create it?",
                    default=True,
                )
                if not create_parent:
                    raise ValueError("Cannot create worktree without parent directory")

            # Check if target path already exists
            if os.path.exists(abs_path):
                if os.path.isfile(abs_path):
                    raise ValueError(
                        f"Path [path]{abs_path}[/path] is a file, not a directory"
                    )
                elif os.path.isdir(abs_path) and os.listdir(abs_path):
                    raise ValueError(
                        f"Directory [path]{abs_path}[/path] already exists and is not empty"
                    )

            return abs_path

        while True:
            try:
                prompt_text = "[path]Worktree location[/path]"
                if default_path:
                    prompt_text += f" (default: [dim]{default_path}[/dim])"

                path = Prompt.ask(
                    prompt_text,
                    default=default_path if default_path else None,
                    console=self.console,
                )

                validated_path = validate_path(path)
                self.console.print(
                    f"[success]Location:[/success] [path]{validated_path}[/path]"
                )
                return validated_path

            except ValueError as e:
                self.display_error(str(e), "Invalid Path")
                continue
            except KeyboardInterrupt:
                self.console.print("\n[warning]Operation cancelled by user[/warning]")
                raise

    def display_worktree_list(self, worktrees: List[WorktreeInfo]) -> None:
        """Display a list of worktrees in a formatted table.

        Args:
            worktrees: List of WorktreeInfo objects to display
        """
        if not worktrees:
            self.display_info("No worktrees found in this repository.")
            return

        # Create main table for worktree list
        table = Table(
            title=f"[branch]Git Worktrees[/branch] ({len(worktrees)} found)",
            show_header=True,
            header_style="bold blue",
            box=box.ROUNDED,
            expand=True,
        )

        table.add_column("Branch", style="branch", width=20)
        table.add_column("Path", style="path", width=40)
        table.add_column("Commit", style="commit", width=15)
        table.add_column("Status", style="info", width=15)

        for worktree in worktrees:
            # Format branch name
            branch_display = worktree.branch
            if worktree.is_bare:
                branch_display = f"[dim]{branch_display} (bare)[/dim]"

            # Format path (show relative to home if possible)
            path_display = worktree.path
            home_path = os.path.expanduser("~")
            if path_display.startswith(home_path):
                path_display = "~" + path_display[len(home_path) :]

            # Format commit info
            commit_display = (
                worktree.commit_hash[:8] if worktree.commit_hash else "unknown"
            )

            # Format status
            status_parts = []
            if worktree.has_uncommitted_changes:
                status_parts.append("[modified]modified[/modified]")
            else:
                status_parts.append("[unchanged]clean[/unchanged]")

            status_display = " ".join(status_parts)

            table.add_row(branch_display, path_display, commit_display, status_display)

        self.console.print(table)

    def display_worktree_details(self, worktree: WorktreeInfo) -> None:
        """Display detailed information about a single worktree.

        Args:
            worktree: WorktreeInfo object to display details for
        """
        # Create main panel for worktree details
        details_content = []

        # Branch information
        branch_info = f"[branch]{worktree.branch}[/branch]"
        if worktree.is_bare:
            branch_info += " [dim](bare repository)[/dim]"
        details_content.append(f"Branch: {branch_info}")

        # Path information
        path_display = worktree.path
        home_path = os.path.expanduser("~")
        if path_display.startswith(home_path):
            path_display = "~" + path_display[len(home_path) :]
        details_content.append(f"Path: [path]{path_display}[/path]")

        # Commit information
        if worktree.commit_hash:
            commit_short = worktree.commit_hash[:8]
            commit_info = f"[commit]{commit_short}[/commit]"
            if worktree.commit_message:
                # Truncate long commit messages
                message = worktree.commit_message
                if len(message) > 60:
                    message = message[:57] + "..."
                commit_info += f" - {message}"
            details_content.append(f"Commit: {commit_info}")

        # Base branch information
        if worktree.base_branch:
            details_content.append(
                f"Base Branch: [branch]{worktree.base_branch}[/branch]"
            )

        # Status information
        status_info = []
        if worktree.has_uncommitted_changes:
            status_info.append("[modified]Has uncommitted changes[/modified]")
        else:
            status_info.append("[unchanged]Working directory clean[/unchanged]")

        if status_info:
            details_content.append(f"Status: {' | '.join(status_info)}")

        # Create and display the panel
        panel_content = "\n".join(details_content)
        panel = Panel(
            panel_content,
            title="[branch]Worktree Details[/branch]",
            border_style="blue",
            box=box.ROUNDED,
            padding=(1, 2),
        )

        self.console.print(panel)

    def display_worktree_summary(self, worktrees: List[WorktreeInfo]) -> None:
        """Display a summary of worktree statistics.

        Args:
            worktrees: List of WorktreeInfo objects to summarize
        """
        if not worktrees:
            return

        # Calculate statistics
        total_worktrees = len(worktrees)
        modified_count = sum(1 for w in worktrees if w.has_uncommitted_changes)
        clean_count = total_worktrees - modified_count
        bare_count = sum(1 for w in worktrees if w.is_bare)

        # Create summary content
        summary_lines = [
            f"Total Worktrees: [info]{total_worktrees}[/info]",
            f"Clean: [unchanged]{clean_count}[/unchanged]",
            f"Modified: [modified]{modified_count}[/modified]",
        ]

        if bare_count > 0:
            summary_lines.append(f"Bare: [dim]{bare_count}[/dim]")

        # Display in a compact panel
        summary_panel = Panel(
            " | ".join(summary_lines),
            title="[info]Summary[/info]",
            border_style="dim",
            box=box.MINIMAL,
            padding=(0, 1),
        )

        self.console.print(summary_panel)

    def display_diff_summary(
        self,
        diff_summary: DiffSummary,
        worktree_branch: str = "",
        base_branch: str = "",
    ) -> None:
        """Display diff summary with color coding and visual formatting.

        Args:
            diff_summary: DiffSummary object containing diff statistics
            worktree_branch: Name of the worktree branch (optional)
            base_branch: Name of the base branch (optional)
        """
        if not diff_summary:
            self.display_info("No diff information available.")
            return

        # Create title for the diff panel
        title_parts = ["Diff Summary"]
        if worktree_branch and base_branch:
            title_parts.append(f"({worktree_branch} ← {base_branch})")
        elif worktree_branch:
            title_parts.append(f"({worktree_branch})")

        title = " ".join(title_parts)

        # Build diff content
        diff_content = []

        # File change statistics
        total_files = (
            diff_summary.files_modified
            + diff_summary.files_added
            + diff_summary.files_deleted
        )
        if total_files == 0:
            diff_content.append("[unchanged]No changes detected[/unchanged]")
        else:
            file_stats = []
            if diff_summary.files_added > 0:
                file_stats.append(f"[added]{diff_summary.files_added} added[/added]")
            if diff_summary.files_modified > 0:
                file_stats.append(
                    f"[modified]{diff_summary.files_modified} modified[/modified]"
                )
            if diff_summary.files_deleted > 0:
                file_stats.append(
                    f"[deleted]{diff_summary.files_deleted} deleted[/deleted]"
                )

            diff_content.append(f"Files: {', '.join(file_stats)}")

        # Line change statistics
        if diff_summary.total_insertions > 0 or diff_summary.total_deletions > 0:
            line_stats = []
            if diff_summary.total_insertions > 0:
                line_stats.append(f"[added]+{diff_summary.total_insertions}[/added]")
            if diff_summary.total_deletions > 0:
                line_stats.append(f"[deleted]-{diff_summary.total_deletions}[/deleted]")

            diff_content.append(f"Lines: {', '.join(line_stats)}")

        # Summary text if available
        if diff_summary.summary_text and diff_summary.summary_text.strip():
            diff_content.append("")
            diff_content.append("[dim]Details:[/dim]")
            diff_content.append(diff_summary.summary_text)

        # Create and display the panel
        panel_content = "\n".join(diff_content)
        panel = Panel(
            panel_content,
            title=f"[info]{title}[/info]",
            border_style="blue",
            box=box.ROUNDED,
            padding=(1, 2),
        )

        self.console.print(panel)

    def display_diff_summary_compact(self, diff_summary: DiffSummary) -> str:
        """Create a compact diff summary string for inline display.

        Args:
            diff_summary: DiffSummary object containing diff statistics

        Returns:
            Formatted string with diff statistics
        """
        if not diff_summary:
            return "[dim]no diff[/dim]"

        total_files = (
            diff_summary.files_modified
            + diff_summary.files_added
            + diff_summary.files_deleted
        )
        if total_files == 0:
            return "[unchanged]no changes[/unchanged]"

        # Build compact representation
        parts = []

        if diff_summary.files_added > 0:
            parts.append(f"[added]+{diff_summary.files_added}[/added]")
        if diff_summary.files_modified > 0:
            parts.append(f"[modified]~{diff_summary.files_modified}[/modified]")
        if diff_summary.files_deleted > 0:
            parts.append(f"[deleted]-{diff_summary.files_deleted}[/deleted]")

        return " ".join(parts)

    def display_diff_visualization(
        self, diff_summary: DiffSummary, max_width: int = 50
    ) -> None:
        """Display a visual bar chart representation of diff changes.

        Args:
            diff_summary: DiffSummary object containing diff statistics
            max_width: Maximum width for the visualization bars
        """
        if not diff_summary:
            return

        total_changes = diff_summary.total_insertions + diff_summary.total_deletions
        if total_changes == 0:
            self.console.print("[unchanged]No line changes to visualize[/unchanged]")
            return

        # Calculate bar lengths
        if total_changes <= max_width:
            # Direct representation
            additions_width = diff_summary.total_insertions
            deletions_width = diff_summary.total_deletions
        else:
            # Scale down proportionally
            scale = max_width / total_changes
            additions_width = int(diff_summary.total_insertions * scale)
            deletions_width = int(diff_summary.total_deletions * scale)

            # Ensure at least 1 character if there are changes
            if diff_summary.total_insertions > 0 and additions_width == 0:
                additions_width = 1
            if diff_summary.total_deletions > 0 and deletions_width == 0:
                deletions_width = 1

        # Create visualization bars
        additions_bar = "[added]" + "+" * additions_width + "[/added]"
        deletions_bar = "[deleted]" + "-" * deletions_width + "[/deleted]"

        # Display the visualization
        viz_content = []
        if additions_width > 0:
            viz_content.append(
                f"Additions ({diff_summary.total_insertions}): {additions_bar}"
            )
        if deletions_width > 0:
            viz_content.append(
                f"Deletions ({diff_summary.total_deletions}): {deletions_bar}"
            )

        if viz_content:
            panel = Panel(
                "\n".join(viz_content),
                title="[info]Change Visualization[/info]",
                border_style="dim",
                box=box.MINIMAL,
                padding=(0, 1),
            )
            self.console.print(panel)

    def display_file_change_indicators(
        self, files_added: int, files_modified: int, files_deleted: int
    ) -> str:
        """Create visual indicators for file changes.

        Args:
            files_added: Number of files added
            files_modified: Number of files modified
            files_deleted: Number of files deleted

        Returns:
            String with visual indicators for file changes
        """
        indicators = []

        if files_added > 0:
            # Use + symbols for added files
            indicator = "[added]" + "●" * min(files_added, 5)
            if files_added > 5:
                indicator += f" (+{files_added - 5})"
            indicator += "[/added]"
            indicators.append(indicator)

        if files_modified > 0:
            # Use ~ symbols for modified files
            indicator = "[modified]" + "◐" * min(files_modified, 5)
            if files_modified > 5:
                indicator += f" (+{files_modified - 5})"
            indicator += "[/modified]"
            indicators.append(indicator)

        if files_deleted > 0:
            # Use - symbols for deleted files
            indicator = "[deleted]" + "○" * min(files_deleted, 5)
            if files_deleted > 5:
                indicator += f" (+{files_deleted - 5})"
            indicator += "[/deleted]"
            indicators.append(indicator)

        return (
            " ".join(indicators) if indicators else "[unchanged]no changes[/unchanged]"
        )

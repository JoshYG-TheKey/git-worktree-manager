"""Git Worktree Manager - A CLI tool for managing Git worktrees with Rich UI."""

__version__ = "0.1.0"
__author__ = "Git Worktree Manager"
__description__ = "Interactive CLI tool for managing Git worktrees"

from .models import CommitInfo, DiffSummary, WorktreeInfo

__all__ = ["WorktreeInfo", "DiffSummary", "CommitInfo"]

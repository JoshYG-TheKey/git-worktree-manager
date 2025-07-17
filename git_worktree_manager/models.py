"""Data models for Git Worktree Manager."""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class WorktreeInfo:
    """Information about a Git worktree."""
    path: str
    branch: str
    commit_hash: str
    commit_message: str
    base_branch: Optional[str] = None
    is_bare: bool = False
    has_uncommitted_changes: bool = False


@dataclass
class DiffSummary:
    """Summary of differences between branches."""
    files_modified: int
    files_added: int
    files_deleted: int
    total_insertions: int
    total_deletions: int
    summary_text: str


@dataclass
class CommitInfo:
    """Information about a Git commit."""
    hash: str
    message: str
    author: str
    date: datetime
    short_hash: str
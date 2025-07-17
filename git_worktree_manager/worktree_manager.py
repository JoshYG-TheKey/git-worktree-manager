"""Core WorktreeManager business logic for Git Worktree Manager."""

import os
from typing import List, Optional, Dict, Any
from pathlib import Path

from .models import WorktreeInfo, DiffSummary
from .git_ops import GitOperations, GitRepositoryError
from .ui_controller import UIController
from .config import ConfigManager, ConfigError
from .exceptions import (
    WorktreeManagerError,
    WorktreeCreationError,
    WorktreeListingError,
    FileSystemError,
    UserInputError
)
from .error_recovery import get_error_recovery_manager


class WorktreeManager:
    """Core business logic for managing Git worktrees."""

    def __init__(
        self,
        git_ops: Optional[GitOperations] = None,
        ui_controller: Optional[UIController] = None,
        config_manager: Optional[ConfigManager] = None,
    ):
        """Initialize WorktreeManager with dependencies.

        Args:
            git_ops: GitOperations instance for Git commands
            ui_controller: UIController instance for user interaction
            config_manager: ConfigManager instance for configuration
        """
        self.git_ops = git_ops or GitOperations()
        self.ui_controller = ui_controller or UIController()
        self.config_manager = config_manager or ConfigManager()

        # Cache for performance optimization
        self._branch_cache: Optional[List[str]] = None
        self._worktree_cache: Optional[List[WorktreeInfo]] = None
        self._diff_cache: Dict[str, DiffSummary] = {}

    def create_worktree(
        self,
        branch_name: Optional[str] = None,
        base_branch: Optional[str] = None,
        location: Optional[str] = None,
    ) -> WorktreeInfo:
        """Create a new worktree with interactive prompts and validation.

        Args:
            branch_name: Name for the new branch (prompts if None)
            base_branch: Base branch to create from (prompts if None)
            location: Path for worktree (prompts if None)

        Returns:
            WorktreeInfo object for the created worktree

        Raises:
            WorktreeCreationError: If worktree creation fails
            GitRepositoryError: If Git operations fail
        """
        try:
            # Validate we're in a Git repository
            if not self.git_ops.is_git_repository():
                raise WorktreeCreationError("Not in a Git repository")

            self.ui_controller.start_progress("Preparing worktree creation...")

            # Get available branches for selection
            try:
                available_branches = self._get_branches_cached()
                current_branch = self.git_ops.get_current_branch()
            except GitRepositoryError as e:
                self.ui_controller.stop_progress()
                raise WorktreeCreationError(f"Failed to get branch information: {e}")

            self.ui_controller.update_progress("Getting user input...")

            # Interactive prompts for missing parameters
            if branch_name is None:
                try:
                    branch_name = self.ui_controller.prompt_branch_name()
                except KeyboardInterrupt:
                    self.ui_controller.stop_progress()
                    raise WorktreeCreationError("Operation cancelled by user")

            if base_branch is None:
                try:
                    base_branch = self.ui_controller.select_base_branch(
                        available_branches, current_branch
                    )
                except (KeyboardInterrupt, ValueError) as e:
                    self.ui_controller.stop_progress()
                    raise WorktreeCreationError(f"Base branch selection failed: {e}")

            if location is None:
                try:
                    default_location = self._get_default_worktree_path(branch_name)
                    location = self.ui_controller.select_worktree_location(
                        default_location
                    )
                except KeyboardInterrupt:
                    self.ui_controller.stop_progress()
                    raise WorktreeCreationError("Operation cancelled by user")

            # Validate inputs
            self._validate_worktree_creation_inputs(branch_name, base_branch, location)

            self.ui_controller.update_progress(f"Creating worktree '{branch_name}'...")

            # Create parent directories if needed
            self._ensure_parent_directory(location)

            # Create the worktree using error recovery mechanisms
            try:
                recovery_manager = get_error_recovery_manager()
                
                def _create_operation():
                    return self.git_ops.create_worktree(location, branch_name, base_branch)
                
                # Use safe worktree creation with comprehensive error handling
                recovery_manager.safe_worktree_creation(
                    _create_operation,
                    location,
                    branch_name,
                    cleanup_on_failure=True
                )
            except Exception as e:
                self.ui_controller.stop_progress()
                if isinstance(e, WorktreeCreationError):
                    raise
                else:
                    raise WorktreeCreationError(f"Failed to create worktree: {e}")

            self.ui_controller.update_progress("Retrieving worktree information...")

            # Get information about the created worktree
            try:
                worktree_info = self._get_worktree_info(
                    location, branch_name, base_branch
                )
            except Exception as e:
                self.ui_controller.stop_progress()
                # Worktree was created but we can't get info - not critical
                self.ui_controller.display_warning(
                    f"Worktree created but failed to retrieve info: {e}",
                    "Partial Success",
                )
                # Return basic info
                worktree_info = WorktreeInfo(
                    path=location,
                    branch=branch_name,
                    commit_hash="",
                    commit_message="",
                    base_branch=base_branch,
                )

            self.ui_controller.stop_progress()

            # Clear caches since we've added a new worktree
            self._clear_caches()

            # Display success message
            self.ui_controller.display_success(
                f"Worktree '{branch_name}' created successfully at {location}",
                "Worktree Created",
            )

            return worktree_info

        except (WorktreeCreationError, GitRepositoryError):
            # Re-raise our own exceptions
            raise
        except Exception as e:
            # Catch any unexpected errors
            self.ui_controller.stop_progress()
            raise WorktreeCreationError(
                f"Unexpected error during worktree creation: {e}"
            )

    def list_worktrees(self) -> List[WorktreeInfo]:
        """List all worktrees with status aggregation.

        Returns:
            List of WorktreeInfo objects with current status

        Raises:
            GitRepositoryError: If Git operations fail
        """
        try:
            # Use cached worktrees if available
            if self._worktree_cache is not None:
                return self._worktree_cache

            # Get worktrees from Git
            worktrees = self.git_ops.list_worktrees()

            # Enhance with additional status information
            enhanced_worktrees = []
            for worktree in worktrees:
                enhanced_worktree = self._enhance_worktree_info(worktree)
                enhanced_worktrees.append(enhanced_worktree)

            # Cache the results
            self._worktree_cache = enhanced_worktrees

            return enhanced_worktrees

        except GitRepositoryError:
            # Re-raise Git errors
            raise
        except Exception as e:
            raise GitRepositoryError(f"Unexpected error listing worktrees: {e}")

    def get_worktree_status(self, worktree: WorktreeInfo) -> WorktreeInfo:
        """Get detailed status for an individual worktree.

        Args:
            worktree: WorktreeInfo object to get status for

        Returns:
            Updated WorktreeInfo with current status

        Raises:
            GitRepositoryError: If Git operations fail
        """
        try:
            # Create a copy to avoid modifying the original
            updated_worktree = WorktreeInfo(
                path=worktree.path,
                branch=worktree.branch,
                commit_hash=worktree.commit_hash,
                commit_message=worktree.commit_message,
                base_branch=worktree.base_branch,
                is_bare=worktree.is_bare,
                has_uncommitted_changes=worktree.has_uncommitted_changes,
            )

            # Update with current status
            return self._enhance_worktree_info(updated_worktree)

        except Exception as e:
            raise GitRepositoryError(f"Failed to get worktree status: {e}")

    def calculate_diff_summary(
        self, worktree: WorktreeInfo, base_branch: Optional[str] = None
    ) -> Optional[DiffSummary]:
        """Calculate diff summary with base branch tracking and caching.

        Args:
            worktree: WorktreeInfo object to calculate diff for
            base_branch: Base branch to compare against (uses worktree.base_branch if None)

        Returns:
            DiffSummary object or None if diff cannot be calculated

        Raises:
            GitRepositoryError: If Git operations fail
        """
        try:
            # Determine base branch
            if base_branch is None:
                base_branch = worktree.base_branch

            if base_branch is None:
                # Try to determine base branch from current branch
                try:
                    current_branch = self.git_ops.get_current_branch()
                    if current_branch != worktree.branch:
                        base_branch = current_branch
                    else:
                        # Use main/master as fallback
                        available_branches = self._get_branches_cached()
                        for fallback in ["main", "master", "develop"]:
                            if (
                                fallback in available_branches
                                and fallback != worktree.branch
                            ):
                                base_branch = fallback
                                break
                except GitRepositoryError:
                    pass

            if base_branch is None:
                return None

            # Check cache first
            cache_key = f"{worktree.branch}:{base_branch}"
            if cache_key in self._diff_cache:
                return self._diff_cache[cache_key]

            # Calculate diff summary
            try:
                diff_summary = self.git_ops.get_diff_summary(
                    base_branch, worktree.branch
                )

                # Cache the result
                self._diff_cache[cache_key] = diff_summary

                return diff_summary

            except GitRepositoryError as e:
                # Handle missing base branch gracefully
                if (
                    "unknown revision" in str(e).lower()
                    or "bad revision" in str(e).lower()
                ):
                    return None
                raise

        except GitRepositoryError:
            # Re-raise Git errors
            raise
        except Exception as e:
            raise GitRepositoryError(f"Failed to calculate diff summary: {e}")

    def _get_branches_cached(self) -> List[str]:
        """Get branches with caching for performance."""
        if self._branch_cache is None:
            self._branch_cache = self.git_ops.get_branches()
        return self._branch_cache

    def _get_default_worktree_path(self, branch_name: str) -> str:
        """Get default path for a new worktree."""
        try:
            base_path = self.config_manager.get_default_worktree_location()
            return str(Path(base_path) / branch_name)
        except ConfigError:
            # Fallback to ~/worktrees if config fails
            return str(Path.home() / "worktrees" / branch_name)

    def _validate_worktree_creation_inputs(
        self, branch_name: str, base_branch: str, location: str
    ) -> None:
        """Validate inputs for worktree creation."""
        if not branch_name or not branch_name.strip():
            raise WorktreeCreationError("Branch name cannot be empty")

        if not base_branch or not base_branch.strip():
            raise WorktreeCreationError("Base branch cannot be empty")

        if not location or not location.strip():
            raise WorktreeCreationError("Location cannot be empty")

        # Validate location path
        try:
            location_path = Path(location)
            if location_path.exists() and location_path.is_file():
                raise WorktreeCreationError(
                    f"Location is a file, not a directory: {location}"
                )

            if (
                location_path.exists()
                and location_path.is_dir()
                and any(location_path.iterdir())
            ):
                raise WorktreeCreationError(
                    f"Location already exists and is not empty: {location}"
                )

        except OSError as e:
            raise WorktreeCreationError(f"Invalid location path: {e}")

    def _ensure_parent_directory(self, location: str) -> None:
        """Ensure parent directory exists for worktree location."""
        try:
            parent_dir = Path(location).parent
            parent_dir.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            raise WorktreeCreationError(f"Failed to create parent directory: {e}")

    def _get_worktree_info(
        self, location: str, branch_name: str, base_branch: str
    ) -> WorktreeInfo:
        """Get detailed information about a newly created worktree."""
        try:
            # Get commit information for the branch
            commit_info = self.git_ops.get_commit_info(branch_name)

            # Check for uncommitted changes
            has_uncommitted = self.git_ops._has_uncommitted_changes(location)

            return WorktreeInfo(
                path=location,
                branch=branch_name,
                commit_hash=commit_info.hash,
                commit_message=commit_info.message,
                base_branch=base_branch,
                is_bare=False,  # New worktrees are never bare
                has_uncommitted_changes=has_uncommitted,
            )

        except GitRepositoryError as e:
            # Return basic info if detailed info fails
            return WorktreeInfo(
                path=location,
                branch=branch_name,
                commit_hash="",
                commit_message="",
                base_branch=base_branch,
                is_bare=False,
                has_uncommitted_changes=False,
            )

    def _enhance_worktree_info(self, worktree: WorktreeInfo) -> WorktreeInfo:
        """Enhance worktree info with additional status information."""
        try:
            # Update uncommitted changes status
            has_uncommitted = self.git_ops._has_uncommitted_changes(worktree.path)

            # Create enhanced worktree info
            enhanced = WorktreeInfo(
                path=worktree.path,
                branch=worktree.branch,
                commit_hash=worktree.commit_hash,
                commit_message=worktree.commit_message,
                base_branch=worktree.base_branch,
                is_bare=worktree.is_bare,
                has_uncommitted_changes=has_uncommitted,
            )

            return enhanced

        except Exception:
            # Return original if enhancement fails
            return worktree

    def _clear_caches(self) -> None:
        """Clear all caches to force refresh."""
        self._branch_cache = None
        self._worktree_cache = None
        self._diff_cache.clear()

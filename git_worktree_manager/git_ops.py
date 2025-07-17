"""Git operations module for worktree management."""

import subprocess
from typing import List, Dict, Optional
from datetime import datetime

from .models import WorktreeInfo, CommitInfo, DiffSummary
from .exceptions import (
    GitRepositoryError,
    git_not_installed_error,
)
from .error_recovery import get_error_recovery_manager
from .cache import GitOperationsCache, CacheConfig, create_cache_key


class GitOperations:
    """Handles all Git operations for worktree management."""

    def __init__(self, repo_path: str = ".", enable_cache: bool = True):
        """Initialize GitOperations with repository path.

        Args:
            repo_path: Path to the Git repository (default: current directory)
            enable_cache: Whether to enable caching for Git operations
        """
        self.repo_path = repo_path
        self.enable_cache = enable_cache
        self._cache = GitOperationsCache() if enable_cache else None

    def is_git_repository(self) -> bool:
        """Check if the current directory is a Git repository.

        Returns:
            True if current directory is a Git repository, False otherwise

        Raises:
            GitRepositoryError: If Git command fails unexpectedly
        """
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--git-dir"],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                check=False,
            )
            return result.returncode == 0
        except FileNotFoundError:
            raise git_not_installed_error()
        except Exception as e:
            raise GitRepositoryError(
                f"Unexpected error checking Git repository: {e}",
                user_guidance="Ensure you have proper permissions and the directory is accessible",
                error_code="UNEXPECTED_GIT_ERROR",
            )

    def get_branches(self) -> List[str]:
        """Get list of all branches in the repository.

        Returns:
            List of branch names (both local and remote)

        Raises:
            GitRepositoryError: If Git command fails or repository is invalid
        """
        if not self.enable_cache or self._cache is None:
            return self._get_branches_uncached()

        cache_key = create_cache_key("branches", self.repo_path)
        return self._cache.cached_call(
            cache_key, self._get_branches_uncached, CacheConfig.BRANCHES_TTL
        )

    def _get_branches_uncached(self) -> List[str]:
        """Get list of all branches without caching."""
        try:
            # Get local branches
            local_result = subprocess.run(
                ["git", "branch", "--format=%(refname:short)"],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                check=True,
            )

            # Get remote branches
            remote_result = subprocess.run(
                ["git", "branch", "-r", "--format=%(refname:short)"],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                check=True,
            )

            branches = []

            # Parse local branches
            if local_result.stdout.strip():
                branches.extend(
                    [
                        branch.strip()
                        for branch in local_result.stdout.strip().split("\n")
                        if branch.strip()
                    ]
                )

            # Parse remote branches (exclude HEAD references)
            if remote_result.stdout.strip():
                remote_branches = [
                    branch.strip()
                    for branch in remote_result.stdout.strip().split("\n")
                    if branch.strip() and not branch.strip().endswith("/HEAD")
                ]
                branches.extend(remote_branches)

            return sorted(set(branches))  # Remove duplicates and sort

        except subprocess.CalledProcessError as e:
            raise GitRepositoryError(
                f"Failed to get branches: {e.stderr.decode() if e.stderr else str(e)}",
                user_guidance="Ensure you are in a valid Git repository with proper permissions",
                error_code="GET_BRANCHES_FAILED",
                git_command="git branch",
                exit_code=e.returncode,
                stderr=e.stderr.decode() if e.stderr else None,
            ) from e
        except FileNotFoundError:
            raise git_not_installed_error() from None
        except Exception as e:
            raise GitRepositoryError(
                f"Unexpected error getting branches: {e}",
                user_guidance="Check repository integrity and permissions",
                error_code="UNEXPECTED_BRANCHES_ERROR",
            ) from e

    def get_current_branch(self) -> str:
        """Get the name of the current branch.

        Returns:
            Name of the current branch

        Raises:
            GitRepositoryError: If Git command fails or repository is invalid
        """
        if not self.enable_cache or self._cache is None:
            return self._get_current_branch_uncached()

        cache_key = create_cache_key("current_branch", self.repo_path)
        return self._cache.cached_call(
            cache_key, self._get_current_branch_uncached, CacheConfig.CURRENT_BRANCH_TTL
        )

    def _get_current_branch_uncached(self) -> str:
        """Get the name of the current branch without caching."""
        try:
            result = subprocess.run(
                ["git", "branch", "--show-current"],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                check=True,
            )

            current_branch = result.stdout.strip()
            if not current_branch:
                # Fallback for detached HEAD state
                result = subprocess.run(
                    ["git", "rev-parse", "--short", "HEAD"],
                    cwd=self.repo_path,
                    capture_output=True,
                    text=True,
                    check=True,
                )
                return f"HEAD ({result.stdout.strip()})"

            return current_branch

        except subprocess.CalledProcessError as e:
            raise GitRepositoryError(
                f"Failed to get current branch: {e.stderr.decode() if e.stderr else str(e)}",
                user_guidance="Ensure you are in a valid Git repository",
                error_code="GET_CURRENT_BRANCH_FAILED",
                git_command="git branch --show-current",
                exit_code=e.returncode,
                stderr=e.stderr.decode() if e.stderr else None,
            ) from e
        except FileNotFoundError:
            raise git_not_installed_error() from None
        except Exception as e:
            raise GitRepositoryError(
                f"Unexpected error getting current branch: {e}",
                user_guidance="Check repository integrity and permissions",
                error_code="UNEXPECTED_CURRENT_BRANCH_ERROR",
            ) from e

    def list_worktrees(self) -> List[WorktreeInfo]:
        """List all worktrees in the repository.

        Returns:
            List of WorktreeInfo objects containing worktree details

        Raises:
            GitRepositoryError: If Git command fails or repository is invalid
        """
        try:
            result = subprocess.run(
                ["git", "worktree", "list", "--porcelain"],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                check=True,
            )

            return self._parse_worktree_list(result.stdout)

        except subprocess.CalledProcessError as e:
            raise GitRepositoryError(
                f"Failed to list worktrees: {e.stderr.decode() if e.stderr else str(e)}",
                user_guidance="Ensure you are in a valid Git repository with worktrees",
                error_code="LIST_WORKTREES_FAILED",
                git_command="git worktree list --porcelain",
                exit_code=e.returncode,
                stderr=e.stderr.decode() if e.stderr else None,
            )
        except FileNotFoundError:
            raise git_not_installed_error()
        except Exception as e:
            raise GitRepositoryError(
                f"Unexpected error listing worktrees: {e}",
                user_guidance="Check repository integrity and permissions",
                error_code="UNEXPECTED_WORKTREES_ERROR",
            )

    def _parse_worktree_list(self, output: str) -> List[WorktreeInfo]:
        """Parse the output of 'git worktree list --porcelain'.

        Args:
            output: Raw output from git worktree list --porcelain

        Returns:
            List of WorktreeInfo objects
        """
        worktrees = []
        current_worktree = {}

        for line in output.strip().split("\n"):
            if not line.strip():
                # Empty line indicates end of worktree entry
                if current_worktree:
                    worktree_info = self._create_worktree_info(current_worktree)
                    if worktree_info:
                        worktrees.append(worktree_info)
                    current_worktree = {}
                continue

            if line.startswith("worktree "):
                current_worktree["path"] = line[9:]  # Remove 'worktree ' prefix
            elif line.startswith("HEAD "):
                current_worktree["commit_hash"] = line[5:]  # Remove 'HEAD ' prefix
            elif line.startswith("branch "):
                # Extract branch name, removing 'refs/heads/' prefix if present
                branch_ref = line[7:]  # Remove 'branch ' prefix
                if branch_ref.startswith("refs/heads/"):
                    current_worktree["branch"] = branch_ref[
                        11:
                    ]  # Remove 'refs/heads/' prefix
                else:
                    current_worktree["branch"] = branch_ref
            elif line.startswith("bare"):
                current_worktree["is_bare"] = True
            elif line.startswith("detached"):
                current_worktree["detached"] = True

        # Handle the last worktree if output doesn't end with empty line
        if current_worktree:
            worktree_info = self._create_worktree_info(current_worktree)
            if worktree_info:
                worktrees.append(worktree_info)

        return worktrees

    def _create_worktree_info(self, worktree_data: Dict) -> Optional[WorktreeInfo]:
        """Create WorktreeInfo object from parsed worktree data.

        Args:
            worktree_data: Dictionary containing parsed worktree information

        Returns:
            WorktreeInfo object or None if required data is missing
        """
        if "path" not in worktree_data:
            return None

        # Handle detached HEAD state
        if worktree_data.get("detached", False):
            branch = f"HEAD ({worktree_data.get('commit_hash', 'unknown')[:7]})"
        else:
            branch = worktree_data.get("branch", "unknown")

        # Get commit message for the commit hash
        commit_message = self._get_commit_message(worktree_data.get("commit_hash", ""))

        # Check for uncommitted changes
        has_uncommitted_changes = self._has_uncommitted_changes(worktree_data["path"])

        return WorktreeInfo(
            path=worktree_data["path"],
            branch=branch,
            commit_hash=worktree_data.get("commit_hash", ""),
            commit_message=commit_message,
            is_bare=worktree_data.get("is_bare", False),
            has_uncommitted_changes=has_uncommitted_changes,
        )

    def _get_commit_message(self, commit_hash: str) -> str:
        """Get commit message for a given commit hash.

        Args:
            commit_hash: The commit hash to get message for

        Returns:
            Commit message or empty string if not found
        """
        if not commit_hash:
            return ""

        try:
            result = subprocess.run(
                ["git", "log", "--format=%s", "-n", "1", commit_hash],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                check=True,
            )
            return result.stdout.strip()
        except (subprocess.CalledProcessError, Exception):
            return ""

    def _has_uncommitted_changes(self, worktree_path: str) -> bool:
        """Check if a worktree has uncommitted changes.

        Args:
            worktree_path: Path to the worktree to check

        Returns:
            True if there are uncommitted changes, False otherwise
        """
        try:
            # Check for staged and unstaged changes
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=worktree_path,
                capture_output=True,
                text=True,
                check=True,
            )
            return bool(result.stdout.strip())
        except (subprocess.CalledProcessError, Exception):
            return False

    def get_commit_info(self, branch_or_hash: str) -> CommitInfo:
        """Get detailed commit information for a branch or commit hash.

        Args:
            branch_or_hash: Branch name or commit hash to get information for

        Returns:
            CommitInfo object with detailed commit information

        Raises:
            GitRepositoryError: If Git command fails or commit not found
        """
        if not self.enable_cache or self._cache is None:
            return self._get_commit_info_uncached(branch_or_hash)

        cache_key = create_cache_key("commit_info", self.repo_path, branch_or_hash)
        return self._cache.cached_call(
            cache_key,
            lambda: self._get_commit_info_uncached(branch_or_hash),
            CacheConfig.COMMIT_INFO_TTL,
        )

    def _get_commit_info_uncached(self, branch_or_hash: str) -> CommitInfo:
        """Get detailed commit information without caching."""
        try:
            # Use git log with custom format to get all needed information
            result = subprocess.run(
                ["git", "log", "--format=%H|%s|%an|%ai|%h", "-n", "1", branch_or_hash],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                check=True,
            )

            if not result.stdout.strip():
                raise GitRepositoryError(f"No commit found for '{branch_or_hash}'")

            return self._parse_commit_info(result.stdout.strip())

        except subprocess.CalledProcessError as e:
            error_msg = e.stderr.decode() if e.stderr else str(e)
            raise GitRepositoryError(
                f"Failed to get commit info for '{branch_or_hash}': {error_msg}",
                user_guidance="Ensure the branch or commit hash exists and is accessible",
                error_code="GET_COMMIT_INFO_FAILED",
                git_command=f"git log -n 1 {branch_or_hash}",
                exit_code=e.returncode,
                stderr=error_msg,
            ) from e
        except FileNotFoundError:
            raise git_not_installed_error() from None
        except Exception as e:
            raise GitRepositoryError(
                f"Unexpected error getting commit info: {e}",
                user_guidance="Check repository integrity and permissions",
                error_code="UNEXPECTED_COMMIT_INFO_ERROR",
            ) from e

    def _parse_commit_info(self, commit_line: str) -> CommitInfo:
        """Parse commit information from git log output.

        Args:
            commit_line: Single line of git log output with custom format

        Returns:
            CommitInfo object

        Raises:
            GitRepositoryError: If parsing fails
        """
        try:
            parts = commit_line.split("|")
            if len(parts) != 5:
                raise GitRepositoryError(f"Invalid commit info format: {commit_line}")

            full_hash, message, author, date_str, short_hash = parts

            # Parse the date string (ISO format from git)
            try:
                commit_date = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
            except ValueError:
                # Fallback for different date formats
                commit_date = datetime.now()  # Use current time as fallback

            return CommitInfo(
                hash=full_hash,
                message=message,
                author=author,
                date=commit_date,
                short_hash=short_hash,
            )

        except Exception as e:
            raise GitRepositoryError(f"Failed to parse commit info: {e}")

    def create_worktree(
        self, path: str, branch: str, base_branch: Optional[str] = None
    ) -> None:
        """Create a new worktree at the specified path.

        Args:
            path: Path where the new worktree should be created
            branch: Name of the branch for the new worktree
            base_branch: Base branch to create the new branch from (if branch doesn't exist)

        Raises:
            GitRepositoryError: If worktree creation fails
        """
        recovery_manager = get_error_recovery_manager(self.repo_path)

        def _create_worktree_operation():
            # Check if the branch already exists
            existing_branches = self.get_branches()
            branch_exists = branch in existing_branches

            if branch_exists:
                # Create worktree from existing branch
                result = subprocess.run(
                    ["git", "worktree", "add", path, branch],
                    cwd=self.repo_path,
                    capture_output=True,
                    text=True,
                    check=True,
                    timeout=60,  # Add timeout for safety
                )
            else:
                # Create worktree with new branch
                effective_base_branch = base_branch
                if effective_base_branch is None:
                    # Use current branch as base if not specified
                    effective_base_branch = self.get_current_branch()
                    # Handle detached HEAD case
                    if effective_base_branch.startswith("HEAD ("):
                        effective_base_branch = "HEAD"

                # Create worktree with new branch based on base_branch
                result = subprocess.run(
                    [
                        "git",
                        "worktree",
                        "add",
                        "-b",
                        branch,
                        path,
                        effective_base_branch,
                    ],
                    cwd=self.repo_path,
                    capture_output=True,
                    text=True,
                    check=True,
                    timeout=60,  # Add timeout for safety
                )

            return result

        # Use the error recovery manager for safe worktree creation
        recovery_manager.safe_worktree_creation(
            _create_worktree_operation, path, branch, cleanup_on_failure=True
        )

    def _cleanup_failed_worktree(self, path: str) -> None:
        """Clean up a partially created worktree after failure.

        Args:
            path: Path of the worktree to clean up
        """
        try:
            import os
            import shutil

            # Remove the directory if it was created
            if os.path.exists(path):
                shutil.rmtree(path)

            # Try to remove the worktree from Git's tracking
            subprocess.run(
                ["git", "worktree", "remove", "--force", path],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                check=False,  # Don't fail if this cleanup fails
            )

        except Exception:
            # Ignore cleanup errors - they're not critical
            pass

    def get_diff_summary(self, branch1: str, branch2: str) -> DiffSummary:
        """Get diff summary between two branches or commits.

        Args:
            branch1: First branch/commit to compare
            branch2: Second branch/commit to compare

        Returns:
            DiffSummary object with diff statistics

        Raises:
            GitRepositoryError: If Git command fails or branches not found
        """
        if not self.enable_cache or self._cache is None:
            return self._get_diff_summary_uncached(branch1, branch2)

        cache_key = create_cache_key("diff_summary", self.repo_path, branch1, branch2)
        return self._cache.cached_call(
            cache_key,
            lambda: self._get_diff_summary_uncached(branch1, branch2),
            CacheConfig.DIFF_SUMMARY_TTL,
        )

    def _get_diff_summary_uncached(self, branch1: str, branch2: str) -> DiffSummary:
        """Get diff summary between two branches without caching."""
        import time

        start_time = time.time()

        try:
            # Use optimized git diff command with --numstat for better performance
            # and --find-renames to handle file renames efficiently
            result = subprocess.run(
                [
                    "git",
                    "diff",
                    "--numstat",
                    "--find-renames",
                    f"{branch1}...{branch2}",
                ],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                check=True,
                timeout=30,  # Add timeout to prevent hanging on large diffs
            )

            diff_summary = self._parse_diff_numstat(result.stdout)

            # Record performance metrics
            execution_time = time.time() - start_time
            self._record_performance_metric(
                "diff_summary", execution_time, len(result.stdout)
            )

            return diff_summary

        except subprocess.TimeoutExpired:
            raise GitRepositoryError(
                f"Diff calculation timed out between '{branch1}' and '{branch2}'",
                user_guidance="The diff is too large. Consider using a more specific comparison or checking repository size",
                error_code="DIFF_TIMEOUT",
            ) from None
        except subprocess.CalledProcessError as e:
            error_msg = e.stderr.decode() if e.stderr else str(e)
            raise GitRepositoryError(
                f"Failed to get diff summary between '{branch1}' and '{branch2}': {error_msg}",
                user_guidance="Ensure both branches exist and are accessible",
                error_code="GET_DIFF_SUMMARY_FAILED",
                git_command=f"git diff --numstat {branch1}...{branch2}",
                exit_code=e.returncode,
                stderr=error_msg,
            ) from e
        except FileNotFoundError:
            raise git_not_installed_error() from None
        except Exception as e:
            raise GitRepositoryError(
                f"Unexpected error getting diff summary: {e}",
                user_guidance="Check repository integrity and permissions",
                error_code="UNEXPECTED_DIFF_SUMMARY_ERROR",
            ) from e

    def _parse_diff_summary(self, diff_output: str) -> DiffSummary:
        """Parse the output of 'git diff --stat'.

        Args:
            diff_output: Raw output from git diff --stat

        Returns:
            DiffSummary object with parsed statistics
        """
        if not diff_output.strip():
            # No differences
            return DiffSummary(
                files_modified=0,
                files_added=0,
                files_deleted=0,
                total_insertions=0,
                total_deletions=0,
                summary_text="No changes",
            )

        lines = diff_output.strip().split("\n")

        # Initialize counters
        files_modified = 0
        files_added = 0
        files_deleted = 0
        total_insertions = 0
        total_deletions = 0

        # Parse each line except the last summary line
        for line in lines[:-1]:
            if not line.strip():
                continue

            # Check for file additions/deletions/modifications
            if " | " in line:
                # Extract file status and changes
                parts = line.split(" | ")
                if len(parts) >= 2:
                    file_path = parts[0].strip()
                    changes_part = parts[1].strip()

                    # Determine if file is added, deleted, or modified
                    if file_path.endswith(" (new file)") or "new file" in line:
                        files_added += 1
                    elif file_path.endswith(" (deleted)") or "deleted" in line:
                        files_deleted += 1
                    else:
                        files_modified += 1

        # Parse the summary line (last line)
        summary_line = lines[-1].strip() if lines else ""
        if summary_line:
            # Extract insertions and deletions from summary
            # Format: "X files changed, Y insertions(+), Z deletions(-)"
            import re

            # Match insertions
            insertion_match = re.search(r"(\d+) insertion", summary_line)
            if insertion_match:
                total_insertions = int(insertion_match.group(1))

            # Match deletions
            deletion_match = re.search(r"(\d+) deletion", summary_line)
            if deletion_match:
                total_deletions = int(deletion_match.group(1))

            # If no explicit file counts were found, try to extract from summary
            if files_modified == 0 and files_added == 0 and files_deleted == 0:
                file_match = re.search(r"(\d+) files? changed", summary_line)
                if file_match:
                    # Assume all are modifications if not specified otherwise
                    files_modified = int(file_match.group(1))

        # Create summary text
        if total_insertions == 0 and total_deletions == 0:
            summary_text = "No changes"
        else:
            parts = []
            if total_insertions > 0:
                parts.append(f"+{total_insertions}")
            if total_deletions > 0:
                parts.append(f"-{total_deletions}")
            summary_text = ", ".join(parts)

        return DiffSummary(
            files_modified=files_modified,
            files_added=files_added,
            files_deleted=files_deleted,
            total_insertions=total_insertions,
            total_deletions=total_deletions,
            summary_text=summary_text,
        )

    # Cache management methods
    def invalidate_cache(self, pattern: Optional[str] = None) -> int:
        """Invalidate cache entries.

        Args:
            pattern: Pattern to match cache keys (invalidates all if None)

        Returns:
            Number of entries invalidated
        """
        if not self.enable_cache or self._cache is None:
            return 0

        if pattern is None:
            self._cache.clear()
            return 0  # clear() doesn't return count
        else:
            return self._cache.invalidate_pattern(pattern)

    def invalidate_branches_cache(self) -> bool:
        """Invalidate cached branch information.

        Returns:
            True if cache entry was found and removed
        """
        if not self.enable_cache or self._cache is None:
            return False

        cache_key = create_cache_key("branches", self.repo_path)
        return self._cache.invalidate(cache_key)

    def invalidate_current_branch_cache(self) -> bool:
        """Invalidate cached current branch information.

        Returns:
            True if cache entry was found and removed
        """
        if not self.enable_cache or self._cache is None:
            return False

        cache_key = create_cache_key("current_branch", self.repo_path)
        return self._cache.invalidate(cache_key)

    def invalidate_commit_info_cache(self, branch_or_hash: Optional[str] = None) -> int:
        """Invalidate cached commit information.

        Args:
            branch_or_hash: Specific branch/hash to invalidate (all if None)

        Returns:
            Number of entries invalidated
        """
        if not self.enable_cache or self._cache is None:
            return 0

        if branch_or_hash is None:
            return self._cache.invalidate_pattern("commit_info")
        else:
            cache_key = create_cache_key("commit_info", self.repo_path, branch_or_hash)
            return 1 if self._cache.invalidate(cache_key) else 0

    def invalidate_diff_summary_cache(
        self, branch1: Optional[str] = None, branch2: Optional[str] = None
    ) -> int:
        """Invalidate cached diff summary information.

        Args:
            branch1: First branch to invalidate (all if None)
            branch2: Second branch to invalidate (all if None)

        Returns:
            Number of entries invalidated
        """
        if not self.enable_cache or self._cache is None:
            return 0

        if branch1 is None or branch2 is None:
            return self._cache.invalidate_pattern("diff_summary")
        else:
            cache_key = create_cache_key(
                "diff_summary", self.repo_path, branch1, branch2
            )
            return 1 if self._cache.invalidate(cache_key) else 0

    def get_cache_stats(self) -> Dict[str, any]:
        """Get cache performance statistics.

        Returns:
            Dictionary with cache statistics
        """
        if not self.enable_cache or self._cache is None:
            return {
                "enabled": False,
                "hits": 0,
                "misses": 0,
                "hit_rate": 0.0,
                "cache_size": 0,
            }

        stats = self._cache.get_stats()
        stats["enabled"] = True
        return stats

    def cleanup_expired_cache(self) -> int:
        """Remove expired entries from cache.

        Returns:
            Number of entries removed
        """
        if not self.enable_cache or self._cache is None:
            return 0

        return self._cache.cleanup_expired()

    def _parse_diff_numstat(self, numstat_output: str) -> DiffSummary:
        """Parse the output of 'git diff --numstat' for better performance.

        Args:
            numstat_output: Raw output from git diff --numstat

        Returns:
            DiffSummary object with parsed statistics
        """
        if not numstat_output.strip():
            return DiffSummary(
                files_modified=0,
                files_added=0,
                files_deleted=0,
                total_insertions=0,
                total_deletions=0,
                summary_text="No changes",
            )

        lines = numstat_output.strip().split("\n")

        files_modified = 0
        files_added = 0
        files_deleted = 0
        total_insertions = 0
        total_deletions = 0

        for line in lines:
            if not line.strip():
                continue

            # Format: "insertions\tdeletions\tfilename"
            parts = line.split("\t")
            if len(parts) >= 3:
                insertions_str, deletions_str, filename = parts[0], parts[1], parts[2]

                # Handle binary files (marked with "-")
                if insertions_str == "-" or deletions_str == "-":
                    # Binary file - count as modified
                    files_modified += 1
                    continue

                try:
                    insertions = int(insertions_str) if insertions_str != "-" else 0
                    deletions = int(deletions_str) if deletions_str != "-" else 0

                    total_insertions += insertions
                    total_deletions += deletions

                    # Determine file status
                    if insertions > 0 and deletions == 0:
                        files_added += 1
                    elif insertions == 0 and deletions > 0:
                        files_deleted += 1
                    else:
                        files_modified += 1

                except ValueError:
                    # Handle malformed lines
                    files_modified += 1

        # Create summary text
        if total_insertions == 0 and total_deletions == 0:
            summary_text = "No changes"
        else:
            parts = []
            if total_insertions > 0:
                parts.append(f"+{total_insertions}")
            if total_deletions > 0:
                parts.append(f"-{total_deletions}")
            summary_text = ", ".join(parts)

        return DiffSummary(
            files_modified=files_modified,
            files_added=files_added,
            files_deleted=files_deleted,
            total_insertions=total_insertions,
            total_deletions=total_deletions,
            summary_text=summary_text,
        )

    def _record_performance_metric(
        self, operation: str, execution_time: float, data_size: int
    ) -> None:
        """Record performance metrics for operations.

        Args:
            operation: Name of the operation
            execution_time: Time taken to execute in seconds
            data_size: Size of data processed (e.g., output length)
        """
        if not hasattr(self, "_performance_metrics"):
            self._performance_metrics = {}

        if operation not in self._performance_metrics:
            self._performance_metrics[operation] = {
                "total_calls": 0,
                "total_time": 0.0,
                "total_data_size": 0,
                "max_time": 0.0,
                "min_time": float("inf"),
            }

        metrics = self._performance_metrics[operation]
        metrics["total_calls"] += 1
        metrics["total_time"] += execution_time
        metrics["total_data_size"] += data_size
        metrics["max_time"] = max(metrics["max_time"], execution_time)
        metrics["min_time"] = min(metrics["min_time"], execution_time)

    def get_performance_metrics(self) -> Dict[str, Dict[str, float]]:
        """Get performance metrics for Git operations.

        Returns:
            Dictionary with performance statistics for each operation
        """
        if not hasattr(self, "_performance_metrics"):
            return {}

        result = {}
        for operation, metrics in self._performance_metrics.items():
            if metrics["total_calls"] > 0:
                result[operation] = {
                    "total_calls": metrics["total_calls"],
                    "total_time": metrics["total_time"],
                    "average_time": metrics["total_time"] / metrics["total_calls"],
                    "max_time": metrics["max_time"],
                    "min_time": (
                        metrics["min_time"]
                        if metrics["min_time"] != float("inf")
                        else 0.0
                    ),
                    "total_data_size": metrics["total_data_size"],
                    "average_data_size": metrics["total_data_size"]
                    / metrics["total_calls"],
                }

        return result

    def reset_performance_metrics(self) -> None:
        """Reset all performance metrics."""
        self._performance_metrics = {}

    def get_diff_summary_progressive(
        self, branch1: str, branch2: str, max_files: Optional[int] = None
    ) -> DiffSummary:
        """Get diff summary with progressive loading for large datasets.

        Args:
            branch1: First branch/commit to compare
            branch2: Second branch/commit to compare
            max_files: Maximum number of files to process (None for all)

        Returns:
            DiffSummary object with diff statistics

        Raises:
            GitRepositoryError: If Git command fails or branches not found
        """
        import time

        start_time = time.time()

        try:
            # Build command with optional file limit
            cmd = [
                "git",
                "diff",
                "--numstat",
                "--find-renames",
                f"{branch1}...{branch2}",
            ]

            # Add file limit if specified
            if max_files is not None:
                # Use git diff with pathspec to limit files processed
                # This is a simplified approach - in practice you might want to
                # implement more sophisticated progressive loading
                pass

            result = subprocess.run(
                cmd,
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                check=True,
                timeout=30,
            )

            # If max_files is specified, limit the processing
            output = result.stdout
            if max_files is not None and output.strip():
                lines = output.strip().split("\n")
                if len(lines) > max_files:
                    # Process only the first max_files lines
                    output = "\n".join(lines[:max_files])

            diff_summary = self._parse_diff_numstat(output)

            # Record performance metrics
            execution_time = time.time() - start_time
            self._record_performance_metric(
                "diff_summary_progressive", execution_time, len(output)
            )

            return diff_summary

        except subprocess.TimeoutExpired:
            raise GitRepositoryError(
                f"Progressive diff calculation timed out between '{branch1}' and '{branch2}'",
                user_guidance="The diff is too large. Try reducing max_files parameter or use a more specific comparison",
                error_code="DIFF_PROGRESSIVE_TIMEOUT",
            ) from None
        except subprocess.CalledProcessError as e:
            error_msg = e.stderr.decode() if e.stderr else str(e)
            raise GitRepositoryError(
                f"Failed to get progressive diff summary between '{branch1}' and '{branch2}': {error_msg}",
                user_guidance="Ensure both branches exist and are accessible",
                error_code="GET_DIFF_PROGRESSIVE_FAILED",
                git_command=f"git diff --numstat {branch1}...{branch2}",
                exit_code=e.returncode,
                stderr=error_msg,
            ) from e
        except FileNotFoundError:
            raise git_not_installed_error() from None
        except Exception as e:
            raise GitRepositoryError(
                f"Unexpected error getting progressive diff summary: {e}",
                user_guidance="Check repository integrity and permissions",
                error_code="UNEXPECTED_DIFF_PROGRESSIVE_ERROR",
            ) from e

"""Git operations module for worktree management."""

import subprocess
from typing import List, Dict, Optional
from dataclasses import dataclass
from datetime import datetime

from .models import WorktreeInfo, CommitInfo, DiffSummary


class GitRepositoryError(Exception):
    """Git repository related errors."""
    pass


class GitOperations:
    """Handles all Git operations for worktree management."""
    
    def __init__(self, repo_path: str = "."):
        """Initialize GitOperations with repository path.
        
        Args:
            repo_path: Path to the Git repository (default: current directory)
        """
        self.repo_path = repo_path
    
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
                check=False
            )
            return result.returncode == 0
        except FileNotFoundError:
            raise GitRepositoryError("Git is not installed or not available in PATH")
        except Exception as e:
            raise GitRepositoryError(f"Unexpected error checking Git repository: {e}")
    
    def get_branches(self) -> List[str]:
        """Get list of all branches in the repository.
        
        Returns:
            List of branch names (both local and remote)
            
        Raises:
            GitRepositoryError: If Git command fails or repository is invalid
        """
        try:
            # Get local branches
            local_result = subprocess.run(
                ["git", "branch", "--format=%(refname:short)"],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                check=True
            )
            
            # Get remote branches
            remote_result = subprocess.run(
                ["git", "branch", "-r", "--format=%(refname:short)"],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                check=True
            )
            
            branches = []
            
            # Parse local branches
            if local_result.stdout.strip():
                branches.extend([
                    branch.strip() 
                    for branch in local_result.stdout.strip().split('\n')
                    if branch.strip()
                ])
            
            # Parse remote branches (exclude HEAD references)
            if remote_result.stdout.strip():
                remote_branches = [
                    branch.strip() 
                    for branch in remote_result.stdout.strip().split('\n')
                    if branch.strip() and not branch.strip().endswith('/HEAD')
                ]
                branches.extend(remote_branches)
            
            return sorted(list(set(branches)))  # Remove duplicates and sort
            
        except subprocess.CalledProcessError as e:
            raise GitRepositoryError(f"Failed to get branches: {e.stderr.decode() if e.stderr else str(e)}")
        except FileNotFoundError:
            raise GitRepositoryError("Git is not installed or not available in PATH")
        except Exception as e:
            raise GitRepositoryError(f"Unexpected error getting branches: {e}")
    
    def get_current_branch(self) -> str:
        """Get the name of the current branch.
        
        Returns:
            Name of the current branch
            
        Raises:
            GitRepositoryError: If Git command fails or repository is invalid
        """
        try:
            result = subprocess.run(
                ["git", "branch", "--show-current"],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                check=True
            )
            
            current_branch = result.stdout.strip()
            if not current_branch:
                # Fallback for detached HEAD state
                result = subprocess.run(
                    ["git", "rev-parse", "--short", "HEAD"],
                    cwd=self.repo_path,
                    capture_output=True,
                    text=True,
                    check=True
                )
                return f"HEAD ({result.stdout.strip()})"
            
            return current_branch
            
        except subprocess.CalledProcessError as e:
            raise GitRepositoryError(f"Failed to get current branch: {e.stderr.decode() if e.stderr else str(e)}")
        except FileNotFoundError:
            raise GitRepositoryError("Git is not installed or not available in PATH")
        except Exception as e:
            raise GitRepositoryError(f"Unexpected error getting current branch: {e}")
    
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
                check=True
            )
            
            return self._parse_worktree_list(result.stdout)
            
        except subprocess.CalledProcessError as e:
            raise GitRepositoryError(f"Failed to list worktrees: {e.stderr.decode() if e.stderr else str(e)}")
        except FileNotFoundError:
            raise GitRepositoryError("Git is not installed or not available in PATH")
        except Exception as e:
            raise GitRepositoryError(f"Unexpected error listing worktrees: {e}")
    
    def _parse_worktree_list(self, output: str) -> List[WorktreeInfo]:
        """Parse the output of 'git worktree list --porcelain'.
        
        Args:
            output: Raw output from git worktree list --porcelain
            
        Returns:
            List of WorktreeInfo objects
        """
        worktrees = []
        current_worktree = {}
        
        for line in output.strip().split('\n'):
            if not line.strip():
                # Empty line indicates end of worktree entry
                if current_worktree:
                    worktree_info = self._create_worktree_info(current_worktree)
                    if worktree_info:
                        worktrees.append(worktree_info)
                    current_worktree = {}
                continue
            
            if line.startswith('worktree '):
                current_worktree['path'] = line[9:]  # Remove 'worktree ' prefix
            elif line.startswith('HEAD '):
                current_worktree['commit_hash'] = line[5:]  # Remove 'HEAD ' prefix
            elif line.startswith('branch '):
                # Extract branch name, removing 'refs/heads/' prefix if present
                branch_ref = line[7:]  # Remove 'branch ' prefix
                if branch_ref.startswith('refs/heads/'):
                    current_worktree['branch'] = branch_ref[11:]  # Remove 'refs/heads/' prefix
                else:
                    current_worktree['branch'] = branch_ref
            elif line.startswith('bare'):
                current_worktree['is_bare'] = True
            elif line.startswith('detached'):
                current_worktree['detached'] = True
        
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
        if 'path' not in worktree_data:
            return None
        
        # Handle detached HEAD state
        if worktree_data.get('detached', False):
            branch = f"HEAD ({worktree_data.get('commit_hash', 'unknown')[:7]})"
        else:
            branch = worktree_data.get('branch', 'unknown')
        
        # Get commit message for the commit hash
        commit_message = self._get_commit_message(worktree_data.get('commit_hash', ''))
        
        # Check for uncommitted changes
        has_uncommitted_changes = self._has_uncommitted_changes(worktree_data['path'])
        
        return WorktreeInfo(
            path=worktree_data['path'],
            branch=branch,
            commit_hash=worktree_data.get('commit_hash', ''),
            commit_message=commit_message,
            is_bare=worktree_data.get('is_bare', False),
            has_uncommitted_changes=has_uncommitted_changes
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
                check=True
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
                check=True
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
        try:
            # Use git log with custom format to get all needed information
            result = subprocess.run(
                ["git", "log", "--format=%H|%s|%an|%ai|%h", "-n", "1", branch_or_hash],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                check=True
            )
            
            if not result.stdout.strip():
                raise GitRepositoryError(f"No commit found for '{branch_or_hash}'")
            
            return self._parse_commit_info(result.stdout.strip())
            
        except subprocess.CalledProcessError as e:
            error_msg = e.stderr.decode() if e.stderr else str(e)
            raise GitRepositoryError(f"Failed to get commit info for '{branch_or_hash}': {error_msg}")
        except FileNotFoundError:
            raise GitRepositoryError("Git is not installed or not available in PATH")
        except Exception as e:
            raise GitRepositoryError(f"Unexpected error getting commit info: {e}")
    
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
            parts = commit_line.split('|')
            if len(parts) != 5:
                raise GitRepositoryError(f"Invalid commit info format: {commit_line}")
            
            full_hash, message, author, date_str, short_hash = parts
            
            # Parse the date string (ISO format from git)
            try:
                commit_date = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            except ValueError:
                # Fallback for different date formats
                commit_date = datetime.now()  # Use current time as fallback
            
            return CommitInfo(
                hash=full_hash,
                message=message,
                author=author,
                date=commit_date,
                short_hash=short_hash
            )
            
        except Exception as e:
            raise GitRepositoryError(f"Failed to parse commit info: {e}")
    
    def create_worktree(self, path: str, branch: str, base_branch: Optional[str] = None) -> None:
        """Create a new worktree at the specified path.
        
        Args:
            path: Path where the new worktree should be created
            branch: Name of the branch for the new worktree
            base_branch: Base branch to create the new branch from (if branch doesn't exist)
            
        Raises:
            GitRepositoryError: If worktree creation fails
        """
        try:
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
                    check=True
                )
            else:
                # Create worktree with new branch
                if base_branch is None:
                    # Use current branch as base if not specified
                    base_branch = self.get_current_branch()
                    # Handle detached HEAD case
                    if base_branch.startswith("HEAD ("):
                        base_branch = "HEAD"
                
                # Create worktree with new branch based on base_branch
                result = subprocess.run(
                    ["git", "worktree", "add", "-b", branch, path, base_branch],
                    cwd=self.repo_path,
                    capture_output=True,
                    text=True,
                    check=True
                )
            
        except subprocess.CalledProcessError as e:
            error_msg = e.stderr.decode() if e.stderr else str(e)
            
            # Clean up partially created worktree if it exists
            self._cleanup_failed_worktree(path)
            
            raise GitRepositoryError(f"Failed to create worktree at '{path}': {error_msg}")
        except FileNotFoundError:
            raise GitRepositoryError("Git is not installed or not available in PATH")
        except Exception as e:
            # Clean up partially created worktree if it exists
            self._cleanup_failed_worktree(path)
            raise GitRepositoryError(f"Unexpected error creating worktree: {e}")
    
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
                check=False  # Don't fail if this cleanup fails
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
        try:
            # Use git diff --stat to get summary statistics
            result = subprocess.run(
                ["git", "diff", "--stat", f"{branch1}...{branch2}"],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                check=True
            )
            
            return self._parse_diff_summary(result.stdout)
            
        except subprocess.CalledProcessError as e:
            error_msg = e.stderr.decode() if e.stderr else str(e)
            raise GitRepositoryError(f"Failed to get diff summary between '{branch1}' and '{branch2}': {error_msg}")
        except FileNotFoundError:
            raise GitRepositoryError("Git is not installed or not available in PATH")
        except Exception as e:
            raise GitRepositoryError(f"Unexpected error getting diff summary: {e}")
    
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
                summary_text="No changes"
            )
        
        lines = diff_output.strip().split('\n')
        
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
            if ' | ' in line:
                # Extract file status and changes
                parts = line.split(' | ')
                if len(parts) >= 2:
                    file_path = parts[0].strip()
                    changes_part = parts[1].strip()
                    
                    # Determine if file is added, deleted, or modified
                    if file_path.endswith(' (new file)') or 'new file' in line:
                        files_added += 1
                    elif file_path.endswith(' (deleted)') or 'deleted' in line:
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
            insertion_match = re.search(r'(\d+) insertion', summary_line)
            if insertion_match:
                total_insertions = int(insertion_match.group(1))
            
            # Match deletions
            deletion_match = re.search(r'(\d+) deletion', summary_line)
            if deletion_match:
                total_deletions = int(deletion_match.group(1))
            
            # If no explicit file counts were found, try to extract from summary
            if files_modified == 0 and files_added == 0 and files_deleted == 0:
                file_match = re.search(r'(\d+) files? changed', summary_line)
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
            summary_text=summary_text
        )
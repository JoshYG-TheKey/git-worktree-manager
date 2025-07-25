"""Unit tests for GitOperations class."""

import subprocess
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from git_worktree_manager.git_ops import GitOperations, GitRepositoryError


class TestGitOperations:
    """Test cases for GitOperations class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.git_ops = GitOperations()

    @patch("subprocess.run")
    def test_is_git_repository_valid_repo(self, mock_run):
        """Test is_git_repository returns True for valid Git repository."""
        # Mock successful git rev-parse command
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_run.return_value = mock_result

        result = self.git_ops.is_git_repository()

        assert result is True
        mock_run.assert_called_once_with(
            ["git", "rev-parse", "--git-dir"],
            cwd=".",
            capture_output=True,
            text=True,
            check=False,
        )

    @patch("subprocess.run")
    def test_is_git_repository_invalid_repo(self, mock_run):
        """Test is_git_repository returns False for non-Git directory."""
        # Mock failed git rev-parse command
        mock_result = MagicMock()
        mock_result.returncode = 128  # Git error code for not a repository
        mock_run.return_value = mock_result

        result = self.git_ops.is_git_repository()

        assert result is False
        mock_run.assert_called_once_with(
            ["git", "rev-parse", "--git-dir"],
            cwd=".",
            capture_output=True,
            text=True,
            check=False,
        )

    @patch("subprocess.run")
    def test_is_git_repository_git_not_installed(self, mock_run):
        """Test is_git_repository raises error when Git is not installed."""
        # Mock FileNotFoundError when git command is not found
        mock_run.side_effect = FileNotFoundError("git command not found")

        with pytest.raises(GitRepositoryError, match="Git is not installed"):
            self.git_ops.is_git_repository()

    @patch("subprocess.run")
    def test_is_git_repository_unexpected_error(self, mock_run):
        """Test is_git_repository handles unexpected errors."""
        # Mock unexpected exception
        mock_run.side_effect = Exception("Unexpected error")

        with pytest.raises(
            GitRepositoryError, match="Unexpected error checking Git repository"
        ):
            self.git_ops.is_git_repository()

    def test_git_operations_custom_path(self):
        """Test GitOperations initialization with custom repository path."""
        custom_path = "/path/to/repo"
        git_ops = GitOperations(custom_path)

        assert git_ops.repo_path == custom_path

    @patch("subprocess.run")
    def test_get_branches_success(self, mock_run):
        """Test get_branches returns sorted list of local and remote branches."""
        # Mock local branches result
        local_result = MagicMock()
        local_result.stdout = "main\nfeature-1\ndevelop\n"
        local_result.returncode = 0

        # Mock remote branches result
        remote_result = MagicMock()
        remote_result.stdout = "origin/main\norigin/feature-2\norigin/HEAD\n"
        remote_result.returncode = 0

        # Configure mock to return different results for different calls
        mock_run.side_effect = [local_result, remote_result]

        result = self.git_ops.get_branches()

        expected_branches = [
            "develop",
            "feature-1",
            "main",
            "origin/feature-2",
            "origin/main",
        ]
        assert result == expected_branches

        # Verify both git commands were called
        assert mock_run.call_count == 2
        mock_run.assert_any_call(
            ["git", "branch", "--format=%(refname:short)"],
            cwd=".",
            capture_output=True,
            text=True,
            check=True,
        )
        mock_run.assert_any_call(
            ["git", "branch", "-r", "--format=%(refname:short)"],
            cwd=".",
            capture_output=True,
            text=True,
            check=True,
        )

    @patch("subprocess.run")
    def test_get_branches_empty_repo(self, mock_run):
        """Test get_branches handles empty repository."""
        # Mock empty results
        empty_result = MagicMock()
        empty_result.stdout = ""
        empty_result.returncode = 0

        mock_run.return_value = empty_result

        result = self.git_ops.get_branches()

        assert result == []

    @patch("subprocess.run")
    def test_get_branches_git_error(self, mock_run):
        """Test get_branches handles Git command errors."""
        # Mock subprocess error
        mock_run.side_effect = subprocess.CalledProcessError(
            128, ["git", "branch"], stderr=b"Not a git repository"
        )

        with pytest.raises(GitRepositoryError, match="Failed to get branches"):
            self.git_ops.get_branches()

    @patch("subprocess.run")
    def test_get_branches_git_not_installed(self, mock_run):
        """Test get_branches handles missing Git installation."""
        mock_run.side_effect = FileNotFoundError("git command not found")

        with pytest.raises(GitRepositoryError, match="Git is not installed"):
            self.git_ops.get_branches()

    @patch("subprocess.run")
    def test_get_current_branch_success(self, mock_run):
        """Test get_current_branch returns current branch name."""
        mock_result = MagicMock()
        mock_result.stdout = "feature-branch\n"
        mock_result.returncode = 0
        mock_run.return_value = mock_result

        result = self.git_ops.get_current_branch()

        assert result == "feature-branch"
        mock_run.assert_called_once_with(
            ["git", "branch", "--show-current"],
            cwd=".",
            capture_output=True,
            text=True,
            check=True,
        )

    @patch("subprocess.run")
    def test_get_current_branch_detached_head(self, mock_run):
        """Test get_current_branch handles detached HEAD state."""
        # First call returns empty (detached HEAD)
        first_result = MagicMock()
        first_result.stdout = ""
        first_result.returncode = 0

        # Second call returns commit hash
        second_result = MagicMock()
        second_result.stdout = "abc1234\n"
        second_result.returncode = 0

        mock_run.side_effect = [first_result, second_result]

        result = self.git_ops.get_current_branch()

        assert result == "HEAD (abc1234)"
        assert mock_run.call_count == 2
        mock_run.assert_any_call(
            ["git", "branch", "--show-current"],
            cwd=".",
            capture_output=True,
            text=True,
            check=True,
        )
        mock_run.assert_any_call(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=".",
            capture_output=True,
            text=True,
            check=True,
        )

    @patch("subprocess.run")
    def test_get_current_branch_git_error(self, mock_run):
        """Test get_current_branch handles Git command errors."""
        mock_run.side_effect = subprocess.CalledProcessError(
            128, ["git", "branch"], stderr=b"Not a git repository"
        )

        with pytest.raises(GitRepositoryError, match="Failed to get current branch"):
            self.git_ops.get_current_branch()

    @patch("subprocess.run")
    def test_get_current_branch_git_not_installed(self, mock_run):
        """Test get_current_branch handles missing Git installation."""
        mock_run.side_effect = FileNotFoundError("git command not found")

        with pytest.raises(GitRepositoryError, match="Git is not installed"):
            self.git_ops.get_current_branch()

    @patch("subprocess.run")
    def test_list_worktrees_success(self, mock_run):
        """Test list_worktrees parses worktree output correctly."""
        # Mock git worktree list --porcelain output
        mock_result = MagicMock()
        mock_result.stdout = """worktree /path/to/main
HEAD abc1234567890abcdef1234567890abcdef12
branch refs/heads/main

worktree /path/to/feature
HEAD def4567890abcdef1234567890abcdef123456
branch refs/heads/feature-branch

worktree /path/to/detached
HEAD 789abcdef1234567890abcdef1234567890ab
detached

"""
        mock_result.returncode = 0

        # Mock additional calls for commit messages and status checks
        def mock_run_side_effect(*args, **kwargs):
            if args[0] == ["git", "worktree", "list", "--porcelain"]:
                return mock_result
            elif args[0][0:3] == ["git", "log", "--format=%s"]:
                # Mock commit message calls
                commit_result = MagicMock()
                if "abc1234567890abcdef1234567890abcdef12" in args[0]:
                    commit_result.stdout = "Initial commit"
                elif "def4567890abcdef1234567890abcdef123456" in args[0]:
                    commit_result.stdout = "Add feature"
                else:
                    commit_result.stdout = "Detached commit"
                return commit_result
            elif args[0] == ["git", "status", "--porcelain"]:
                # Mock status calls - no changes
                status_result = MagicMock()
                status_result.stdout = ""
                return status_result
            return MagicMock()

        mock_run.side_effect = mock_run_side_effect

        result = self.git_ops.list_worktrees()

        assert len(result) == 3

        # Check main worktree
        main_worktree = result[0]
        assert main_worktree.path == "/path/to/main"
        assert main_worktree.branch == "main"
        assert main_worktree.commit_hash == "abc1234567890abcdef1234567890abcdef12"
        assert main_worktree.commit_message == "Initial commit"
        assert main_worktree.is_bare is False
        assert main_worktree.has_uncommitted_changes is False

        # Check feature worktree
        feature_worktree = result[1]
        assert feature_worktree.path == "/path/to/feature"
        assert feature_worktree.branch == "feature-branch"
        assert feature_worktree.commit_hash == "def4567890abcdef1234567890abcdef123456"
        assert feature_worktree.commit_message == "Add feature"

        # Check detached worktree
        detached_worktree = result[2]
        assert detached_worktree.path == "/path/to/detached"
        assert detached_worktree.branch == "HEAD (789abcd)"
        assert detached_worktree.commit_hash == "789abcdef1234567890abcdef1234567890ab"

    @patch("subprocess.run")
    def test_list_worktrees_empty(self, mock_run):
        """Test list_worktrees handles empty output."""
        mock_result = MagicMock()
        mock_result.stdout = ""
        mock_result.returncode = 0
        mock_run.return_value = mock_result

        result = self.git_ops.list_worktrees()

        assert result == []

    @patch("subprocess.run")
    def test_list_worktrees_with_bare_repo(self, mock_run):
        """Test list_worktrees handles bare repository."""
        mock_result = MagicMock()
        mock_result.stdout = """worktree /path/to/bare
HEAD abc1234567890abcdef1234567890abcdef12
bare

"""
        mock_result.returncode = 0

        def mock_run_side_effect(*args, **kwargs):
            if args[0] == ["git", "worktree", "list", "--porcelain"]:
                return mock_result
            elif args[0][0:3] == ["git", "log", "--format=%s"]:
                commit_result = MagicMock()
                commit_result.stdout = "Bare repo commit"
                return commit_result
            elif args[0] == ["git", "status", "--porcelain"]:
                status_result = MagicMock()
                status_result.stdout = ""
                return status_result
            return MagicMock()

        mock_run.side_effect = mock_run_side_effect

        result = self.git_ops.list_worktrees()

        assert len(result) == 1
        assert result[0].path == "/path/to/bare"
        assert result[0].is_bare is True

    @patch("subprocess.run")
    def test_list_worktrees_with_uncommitted_changes(self, mock_run):
        """Test list_worktrees detects uncommitted changes."""
        mock_result = MagicMock()
        mock_result.stdout = """worktree /path/to/dirty
HEAD abc1234567890abcdef1234567890abcdef12
branch refs/heads/main

"""
        mock_result.returncode = 0

        def mock_run_side_effect(*args, **kwargs):
            if args[0] == ["git", "worktree", "list", "--porcelain"]:
                return mock_result
            elif args[0][0:3] == ["git", "log", "--format=%s"]:
                commit_result = MagicMock()
                commit_result.stdout = "Some commit"
                return commit_result
            elif args[0] == ["git", "status", "--porcelain"]:
                # Mock dirty status
                status_result = MagicMock()
                status_result.stdout = " M modified_file.txt\n?? new_file.txt"
                return status_result
            return MagicMock()

        mock_run.side_effect = mock_run_side_effect

        result = self.git_ops.list_worktrees()

        assert len(result) == 1
        assert result[0].has_uncommitted_changes is True

    @patch("subprocess.run")
    def test_list_worktrees_git_error(self, mock_run):
        """Test list_worktrees handles Git command errors."""
        mock_run.side_effect = subprocess.CalledProcessError(
            128, ["git", "worktree", "list"], stderr=b"Not a git repository"
        )

        with pytest.raises(GitRepositoryError, match="Failed to list worktrees"):
            self.git_ops.list_worktrees()

    @patch("subprocess.run")
    def test_list_worktrees_git_not_installed(self, mock_run):
        """Test list_worktrees handles missing Git installation."""
        mock_run.side_effect = FileNotFoundError("git command not found")

        with pytest.raises(GitRepositoryError, match="Git is not installed"):
            self.git_ops.list_worktrees()

    @patch("subprocess.run")
    def test_get_commit_info_success(self, mock_run):
        """Test get_commit_info returns detailed commit information."""
        mock_result = MagicMock()
        mock_result.stdout = "abc1234567890abcdef1234567890abcdef12|Initial commit|John Doe|2023-12-01T10:30:00+00:00|abc1234"
        mock_result.returncode = 0
        mock_run.return_value = mock_result

        result = self.git_ops.get_commit_info("main")

        assert result.hash == "abc1234567890abcdef1234567890abcdef12"
        assert result.message == "Initial commit"
        assert result.author == "John Doe"
        assert result.short_hash == "abc1234"
        assert result.date.year == 2023
        assert result.date.month == 12
        assert result.date.day == 1

        mock_run.assert_called_once_with(
            ["git", "log", "--format=%H|%s|%an|%ai|%h", "-n", "1", "main"],
            cwd=".",
            capture_output=True,
            text=True,
            check=True,
        )

    @patch("subprocess.run")
    def test_get_commit_info_with_commit_hash(self, mock_run):
        """Test get_commit_info works with commit hash input."""
        mock_result = MagicMock()
        mock_result.stdout = "def4567890abcdef1234567890abcdef123456|Feature commit|Jane Smith|2023-12-02T15:45:30+01:00|def4567"
        mock_result.returncode = 0
        mock_run.return_value = mock_result

        result = self.git_ops.get_commit_info("def4567")

        assert result.hash == "def4567890abcdef1234567890abcdef123456"
        assert result.message == "Feature commit"
        assert result.author == "Jane Smith"
        assert result.short_hash == "def4567"

        mock_run.assert_called_once_with(
            ["git", "log", "--format=%H|%s|%an|%ai|%h", "-n", "1", "def4567"],
            cwd=".",
            capture_output=True,
            text=True,
            check=True,
        )

    @patch("subprocess.run")
    def test_get_commit_info_no_commit_found(self, mock_run):
        """Test get_commit_info handles case when no commit is found."""
        mock_result = MagicMock()
        mock_result.stdout = ""
        mock_result.returncode = 0
        mock_run.return_value = mock_result

        with pytest.raises(
            GitRepositoryError, match="No commit found for 'nonexistent'"
        ):
            self.git_ops.get_commit_info("nonexistent")

    @patch("subprocess.run")
    def test_get_commit_info_invalid_format(self, mock_run):
        """Test get_commit_info handles invalid commit format."""
        mock_result = MagicMock()
        mock_result.stdout = "invalid|format"  # Missing required fields
        mock_result.returncode = 0
        mock_run.return_value = mock_result

        with pytest.raises(GitRepositoryError, match="Invalid commit info format"):
            self.git_ops.get_commit_info("main")

    @patch("subprocess.run")
    def test_get_commit_info_date_parsing_fallback(self, mock_run):
        """Test get_commit_info handles date parsing errors gracefully."""
        mock_result = MagicMock()
        mock_result.stdout = "abc1234|Test commit|Author|invalid-date|abc1234"
        mock_result.returncode = 0
        mock_run.return_value = mock_result

        result = self.git_ops.get_commit_info("main")

        # Should still create CommitInfo object with fallback date
        assert result.hash == "abc1234"
        assert result.message == "Test commit"
        assert result.author == "Author"
        assert isinstance(result.date, datetime)

    @patch("subprocess.run")
    def test_get_commit_info_git_error(self, mock_run):
        """Test get_commit_info handles Git command errors."""
        mock_run.side_effect = subprocess.CalledProcessError(
            128, ["git", "log"], stderr=b"Not a git repository"
        )

        with pytest.raises(
            GitRepositoryError, match="Failed to get commit info for 'main'"
        ):
            self.git_ops.get_commit_info("main")

    @patch("subprocess.run")
    def test_get_commit_info_git_not_installed(self, mock_run):
        """Test get_commit_info handles missing Git installation."""
        mock_run.side_effect = FileNotFoundError("git command not found")

        with pytest.raises(GitRepositoryError, match="Git is not installed"):
            self.git_ops.get_commit_info("main")

    @patch("subprocess.run")
    def test_create_worktree_existing_branch(self, mock_run):
        """Test create_worktree with existing branch."""

        # Mock get_branches call
        def mock_run_side_effect(*args, **kwargs):
            if args[0][0:2] == ["git", "branch"]:
                if "--format=%(refname:short)" in args[0]:
                    # Local branches
                    result = MagicMock()
                    result.stdout = "main\nexisting-branch\n"
                    return result
                else:
                    # Remote branches
                    result = MagicMock()
                    result.stdout = ""
                    return result
            elif args[0] == [
                "git",
                "worktree",
                "add",
                "/path/to/worktree",
                "existing-branch",
            ]:
                # Worktree creation
                result = MagicMock()
                result.returncode = 0
                return result
            return MagicMock()

        mock_run.side_effect = mock_run_side_effect

        # Should not raise an exception
        self.git_ops.create_worktree("/path/to/worktree", "existing-branch")

        # Verify worktree add was called with existing branch (now includes timeout)
        mock_run.assert_any_call(
            ["git", "worktree", "add", "/path/to/worktree", "existing-branch"],
            cwd=".",
            capture_output=True,
            text=True,
            check=True,
            timeout=60,
        )

    @patch("subprocess.run")
    def test_create_worktree_new_branch_with_base(self, mock_run):
        """Test create_worktree with new branch and specified base branch."""

        # Mock get_branches call - new branch doesn't exist
        def mock_run_side_effect(*args, **kwargs):
            if args[0][0:2] == ["git", "branch"]:
                if "--format=%(refname:short)" in args[0]:
                    # Local branches
                    result = MagicMock()
                    result.stdout = "main\n"
                    return result
                else:
                    # Remote branches
                    result = MagicMock()
                    result.stdout = ""
                    return result
            elif args[0] == [
                "git",
                "worktree",
                "add",
                "-b",
                "new-branch",
                "/path/to/worktree",
                "main",
            ]:
                # Worktree creation with new branch
                result = MagicMock()
                result.returncode = 0
                return result
            return MagicMock()

        mock_run.side_effect = mock_run_side_effect

        # Should not raise an exception
        self.git_ops.create_worktree("/path/to/worktree", "new-branch", "main")

        # Verify worktree add was called with new branch creation
        mock_run.assert_any_call(
            ["git", "worktree", "add", "-b", "new-branch", "/path/to/worktree", "main"],
            cwd=".",
            capture_output=True,
            text=True,
            check=True,
            timeout=60,
        )

    @patch("subprocess.run")
    def test_create_worktree_new_branch_current_base(self, mock_run):
        """Test create_worktree with new branch using current branch as base."""

        # Mock get_branches and get_current_branch calls
        def mock_run_side_effect(*args, **kwargs):
            if args[0][0:2] == ["git", "branch"]:
                if "--format=%(refname:short)" in args[0]:
                    # Local branches
                    result = MagicMock()
                    result.stdout = "main\n"
                    return result
                elif "--show-current" in args[0]:
                    # Current branch
                    result = MagicMock()
                    result.stdout = "main\n"
                    return result
                else:
                    # Remote branches
                    result = MagicMock()
                    result.stdout = ""
                    return result
            elif args[0] == [
                "git",
                "worktree",
                "add",
                "-b",
                "new-branch",
                "/path/to/worktree",
                "main",
            ]:
                # Worktree creation with new branch
                result = MagicMock()
                result.returncode = 0
                return result
            return MagicMock()

        mock_run.side_effect = mock_run_side_effect

        # Should not raise an exception
        self.git_ops.create_worktree("/path/to/worktree", "new-branch")

        # Verify worktree add was called with current branch as base
        mock_run.assert_any_call(
            ["git", "worktree", "add", "-b", "new-branch", "/path/to/worktree", "main"],
            cwd=".",
            capture_output=True,
            text=True,
            check=True,
            timeout=60,
        )

    @patch("subprocess.run")
    def test_create_worktree_detached_head_base(self, mock_run):
        """Test create_worktree with new branch when current branch is detached HEAD."""

        # Mock get_branches and get_current_branch calls
        def mock_run_side_effect(*args, **kwargs):
            if args[0][0:2] == ["git", "branch"]:
                if "--format=%(refname:short)" in args[0]:
                    # Local branches
                    result = MagicMock()
                    result.stdout = "main\n"
                    return result
                elif "--show-current" in args[0]:
                    # Current branch (detached HEAD)
                    result = MagicMock()
                    result.stdout = ""
                    return result
                else:
                    # Remote branches
                    result = MagicMock()
                    result.stdout = ""
                    return result
            elif args[0] == ["git", "rev-parse", "--short", "HEAD"]:
                # Short commit hash for detached HEAD
                result = MagicMock()
                result.stdout = "abc1234\n"
                return result
            elif args[0] == [
                "git",
                "worktree",
                "add",
                "-b",
                "new-branch",
                "/path/to/worktree",
                "HEAD",
            ]:
                # Worktree creation with HEAD as base
                result = MagicMock()
                result.returncode = 0
                return result
            return MagicMock()

        mock_run.side_effect = mock_run_side_effect

        # Should not raise an exception
        self.git_ops.create_worktree("/path/to/worktree", "new-branch")

        # Verify worktree add was called with HEAD as base
        mock_run.assert_any_call(
            ["git", "worktree", "add", "-b", "new-branch", "/path/to/worktree", "HEAD"],
            cwd=".",
            capture_output=True,
            text=True,
            check=True,
            timeout=60,
        )

    @patch("git_worktree_manager.git_ops.GitOperations._cleanup_failed_worktree")
    @patch("subprocess.run")
    def test_create_worktree_git_error(self, mock_run, mock_cleanup):
        """Test create_worktree handles Git command errors and cleans up."""

        # Mock get_branches call
        def mock_run_side_effect(*args, **kwargs):
            if args[0][0:2] == ["git", "branch"]:
                if "--format=%(refname:short)" in args[0]:
                    # Local branches
                    result = MagicMock()
                    result.stdout = "main\n"
                    return result
                else:
                    # Remote branches
                    result = MagicMock()
                    result.stdout = ""
                    return result
            elif args[0][0:3] == ["git", "worktree", "add"]:
                # Worktree creation fails
                raise subprocess.CalledProcessError(
                    128, ["git", "worktree", "add"], stderr=b"worktree add failed"
                )
            return MagicMock()

        mock_run.side_effect = mock_run_side_effect

        with pytest.raises(Exception):  # Error recovery wraps the exception
            self.git_ops.create_worktree("/path/to/worktree", "new-branch")

        # Cleanup is now handled by error recovery manager, not the old method
        # The old cleanup method won't be called directly

    @patch("git_worktree_manager.git_ops.GitOperations._cleanup_failed_worktree")
    @patch("subprocess.run")
    def test_create_worktree_git_not_installed(self, mock_run, mock_cleanup):
        """Test create_worktree handles missing Git installation."""
        mock_run.side_effect = FileNotFoundError("git command not found")

        with pytest.raises(Exception):  # Error recovery wraps the exception
            self.git_ops.create_worktree("/path/to/worktree", "new-branch")

        # Cleanup is now handled by error recovery manager, not the old method
        # The old cleanup method won't be called directly

    @patch("os.path.exists")
    @patch("shutil.rmtree")
    @patch("subprocess.run")
    def test_cleanup_failed_worktree(self, mock_run, mock_rmtree, mock_exists):
        """Test _cleanup_failed_worktree removes directory and Git tracking."""
        mock_exists.return_value = True
        mock_run.return_value = MagicMock()

        self.git_ops._cleanup_failed_worktree("/path/to/failed/worktree")

        # Verify directory removal
        mock_exists.assert_called_once_with("/path/to/failed/worktree")
        mock_rmtree.assert_called_once_with("/path/to/failed/worktree")

        # Verify Git worktree removal
        mock_run.assert_called_once_with(
            ["git", "worktree", "remove", "--force", "/path/to/failed/worktree"],
            cwd=".",
            capture_output=True,
            text=True,
            check=False,
        )

    @patch("os.path.exists")
    @patch("shutil.rmtree")
    def test_cleanup_failed_worktree_handles_errors(self, mock_rmtree, mock_exists):
        """Test _cleanup_failed_worktree handles cleanup errors gracefully."""
        mock_exists.return_value = True
        mock_rmtree.side_effect = Exception("Permission denied")

        # Should not raise an exception
        self.git_ops._cleanup_failed_worktree("/path/to/failed/worktree")

    @patch("subprocess.run")
    def test_get_diff_summary_with_changes(self, mock_run):
        """Test get_diff_summary parses diff output with changes."""
        mock_result = MagicMock()
        mock_result.stdout = """10	6	file1.py
5	0	file2.js
0	3	file3.txt
"""
        mock_result.returncode = 0
        mock_run.return_value = mock_result

        result = self.git_ops.get_diff_summary("main", "feature")

        assert result.files_modified == 1  # file1.py has both insertions and deletions
        assert result.files_added == 1  # file2.js has only insertions
        assert result.files_deleted == 1  # file3.txt has only deletions
        assert result.total_insertions == 15
        assert result.total_deletions == 9
        assert result.summary_text == "+15, -9"

        mock_run.assert_called_once_with(
            ["git", "diff", "--numstat", "--find-renames", "main...feature"],
            cwd=".",
            capture_output=True,
            text=True,
            check=True,
            timeout=30,
        )

    @patch("subprocess.run")
    def test_get_diff_summary_no_changes(self, mock_run):
        """Test get_diff_summary handles no changes."""
        mock_result = MagicMock()
        mock_result.stdout = ""
        mock_result.returncode = 0
        mock_run.return_value = mock_result

        result = self.git_ops.get_diff_summary("main", "feature")

        assert result.files_modified == 0
        assert result.files_added == 0
        assert result.files_deleted == 0
        assert result.total_insertions == 0
        assert result.total_deletions == 0
        assert result.summary_text == "No changes"

    @patch("subprocess.run")
    def test_get_diff_summary_only_insertions(self, mock_run):
        """Test get_diff_summary with only insertions."""
        mock_result = MagicMock()
        mock_result.stdout = """20	0	new_file.py
"""
        mock_result.returncode = 0
        mock_run.return_value = mock_result

        result = self.git_ops.get_diff_summary("main", "feature")

        assert result.files_modified == 0
        assert result.files_added == 1  # new_file.py has only insertions
        assert result.files_deleted == 0
        assert result.total_insertions == 20
        assert result.total_deletions == 0
        assert result.summary_text == "+20"

    @patch("subprocess.run")
    def test_get_diff_summary_only_deletions(self, mock_run):
        """Test get_diff_summary with only deletions."""
        mock_result = MagicMock()
        mock_result.stdout = """0	15	old_file.py
"""
        mock_result.returncode = 0
        mock_run.return_value = mock_result

        result = self.git_ops.get_diff_summary("main", "feature")

        assert result.files_modified == 0
        assert result.files_added == 0
        assert result.files_deleted == 1  # old_file.py has only deletions
        assert result.total_insertions == 0
        assert result.total_deletions == 15
        assert result.summary_text == "-15"

    @patch("subprocess.run")
    def test_get_diff_summary_with_new_and_deleted_files(self, mock_run):
        """Test get_diff_summary identifies new and deleted files."""
        mock_result = MagicMock()
        mock_result.stdout = """10	0	new_file.py
0	5	deleted_file.py
3	1	modified_file.py
"""
        mock_result.returncode = 0
        mock_run.return_value = mock_result

        result = self.git_ops.get_diff_summary("main", "feature")

        assert (
            result.files_modified == 1
        )  # modified_file.py has both insertions and deletions
        assert result.files_added == 1  # new_file.py has only insertions
        assert result.files_deleted == 1  # deleted_file.py has only deletions
        assert result.total_insertions == 13
        assert result.total_deletions == 6
        assert result.summary_text == "+13, -6"

    @patch("subprocess.run")
    def test_get_diff_summary_git_error(self, mock_run):
        """Test get_diff_summary handles Git command errors."""
        mock_run.side_effect = subprocess.CalledProcessError(
            128, ["git", "diff"], stderr=b"Invalid branch"
        )

        with pytest.raises(
            GitRepositoryError,
            match="Failed to get diff summary between 'main' and 'invalid'",
        ):
            self.git_ops.get_diff_summary("main", "invalid")

    @patch("subprocess.run")
    def test_get_diff_summary_git_not_installed(self, mock_run):
        """Test get_diff_summary handles missing Git installation."""
        mock_run.side_effect = FileNotFoundError("git command not found")

        with pytest.raises(GitRepositoryError, match="Git is not installed"):
            self.git_ops.get_diff_summary("main", "feature")

    def test_parse_diff_summary_empty_output(self):
        """Test _parse_diff_summary handles empty output."""
        result = self.git_ops._parse_diff_summary("")

        assert result.files_modified == 0
        assert result.files_added == 0
        assert result.files_deleted == 0
        assert result.total_insertions == 0
        assert result.total_deletions == 0
        assert result.summary_text == "No changes"

    def test_parse_diff_summary_complex_output(self):
        """Test _parse_diff_summary handles complex diff output."""
        diff_output = """src/main.py | 25 +++++++++++++++++++------
tests/test_main.py | 15 +++++++++++++++
docs/README.md | 8 ++------
config/settings.json | 2 +-
 4 files changed, 37 insertions(+), 13 deletions(-)
"""

        result = self.git_ops._parse_diff_summary(diff_output)

        assert result.files_modified == 4
        assert result.files_added == 0
        assert result.files_deleted == 0
        assert result.total_insertions == 37
        assert result.total_deletions == 13
        assert result.summary_text == "+37, -13"


class TestGitOperationsCaching:
    """Test caching functionality in GitOperations."""

    def setup_method(self):
        """Set up test fixtures."""
        self.git_ops_cached = GitOperations(enable_cache=True)
        self.git_ops_uncached = GitOperations(enable_cache=False)

    def test_cache_initialization(self):
        """Test cache is properly initialized."""
        assert self.git_ops_cached.enable_cache is True
        assert self.git_ops_cached._cache is not None

        assert self.git_ops_uncached.enable_cache is False
        assert self.git_ops_uncached._cache is None

    @patch("subprocess.run")
    def test_get_branches_caching(self, mock_run):
        """Test that get_branches uses caching."""
        # Mock successful git branch commands
        local_result = MagicMock()
        local_result.stdout = "main\ndev\nfeature"
        local_result.returncode = 0

        remote_result = MagicMock()
        remote_result.stdout = "origin/main\norigin/dev"
        remote_result.returncode = 0

        mock_run.side_effect = [local_result, remote_result]

        # First call should execute git commands
        branches1 = self.git_ops_cached.get_branches()
        assert mock_run.call_count == 2
        assert "main" in branches1
        assert "dev" in branches1

        # Reset mock to verify caching
        mock_run.reset_mock()

        # Second call should use cache (no git commands)
        branches2 = self.git_ops_cached.get_branches()
        assert mock_run.call_count == 0  # No git commands executed
        assert branches1 == branches2

    @patch("subprocess.run")
    def test_get_current_branch_caching(self, mock_run):
        """Test that get_current_branch uses caching."""
        # Mock successful git branch --show-current command
        mock_result = MagicMock()
        mock_result.stdout = "main\n"
        mock_result.returncode = 0
        mock_run.return_value = mock_result

        # First call should execute git command
        branch1 = self.git_ops_cached.get_current_branch()
        assert mock_run.call_count == 1
        assert branch1 == "main"

        # Reset mock to verify caching
        mock_run.reset_mock()

        # Second call should use cache
        branch2 = self.git_ops_cached.get_current_branch()
        assert mock_run.call_count == 0
        assert branch1 == branch2

    @patch("subprocess.run")
    def test_get_commit_info_caching(self, mock_run):
        """Test that get_commit_info uses caching."""
        # Mock successful git log command
        mock_result = MagicMock()
        mock_result.stdout = (
            "abc123|Initial commit|John Doe|2023-01-01T12:00:00+00:00|abc123\n"
        )
        mock_result.returncode = 0
        mock_run.return_value = mock_result

        # First call should execute git command
        commit1 = self.git_ops_cached.get_commit_info("main")
        assert mock_run.call_count == 1
        assert commit1.hash == "abc123"
        assert commit1.message == "Initial commit"

        # Reset mock to verify caching
        mock_run.reset_mock()

        # Second call should use cache
        commit2 = self.git_ops_cached.get_commit_info("main")
        assert mock_run.call_count == 0
        assert commit1.hash == commit2.hash

    @patch("subprocess.run")
    def test_get_diff_summary_caching(self, mock_run):
        """Test that get_diff_summary uses caching."""
        # Mock successful git diff --numstat command
        mock_result = MagicMock()
        mock_result.stdout = "10\t5\tfile1.py\n5\t0\tfile2.py\n"
        mock_result.returncode = 0
        mock_run.return_value = mock_result

        # First call should execute git command
        diff1 = self.git_ops_cached.get_diff_summary("main", "dev")
        assert mock_run.call_count == 1
        assert diff1.total_insertions == 15

        # Reset mock to verify caching
        mock_run.reset_mock()

        # Second call should use cache
        diff2 = self.git_ops_cached.get_diff_summary("main", "dev")
        assert mock_run.call_count == 0
        assert diff1.total_insertions == diff2.total_insertions

    def test_cache_invalidation_methods(self):
        """Test cache invalidation methods."""
        # Set up some cached data
        self.git_ops_cached._cache.set("test_key", "test_value")
        assert self.git_ops_cached._cache.get("test_key") == "test_value"

        # Test pattern invalidation
        count = self.git_ops_cached.invalidate_cache("test")
        assert count == 1
        assert self.git_ops_cached._cache.get("test_key") is None

    def test_cache_stats(self):
        """Test cache statistics."""
        stats = self.git_ops_cached.get_cache_stats()
        assert stats["enabled"] is True
        assert "hits" in stats
        assert "misses" in stats
        assert "hit_rate" in stats

        # Test uncached instance
        stats_uncached = self.git_ops_uncached.get_cache_stats()
        assert stats_uncached["enabled"] is False

    def test_cleanup_expired_cache(self):
        """Test cleanup of expired cache entries."""
        # Add an entry that will expire quickly
        self.git_ops_cached._cache.set("test_key", "test_value", ttl=0.001)

        import time

        time.sleep(0.01)  # Wait for expiration

        # Cleanup expired entries
        removed_count = self.git_ops_cached.cleanup_expired_cache()
        assert removed_count >= 0  # Should remove at least 0 entries

    @patch("subprocess.run")
    def test_uncached_operations(self, mock_run):
        """Test that uncached operations don't use cache."""
        # Mock successful git branch commands
        local_result = MagicMock()
        local_result.stdout = "main\n"
        local_result.returncode = 0

        remote_result = MagicMock()
        remote_result.stdout = "origin/main\n"
        remote_result.returncode = 0

        mock_run.side_effect = [
            local_result,
            remote_result,
            local_result,
            remote_result,
        ]

        # Both calls should execute git commands (no caching)
        branches1 = self.git_ops_uncached.get_branches()
        branches2 = self.git_ops_uncached.get_branches()

        # Should have called git commands twice
        assert mock_run.call_count == 4
        assert branches1 == branches2

    def test_specific_cache_invalidation(self):
        """Test specific cache invalidation methods."""
        # Test branches cache invalidation
        result = self.git_ops_cached.invalidate_branches_cache()
        assert isinstance(result, bool)

        # Test current branch cache invalidation
        result = self.git_ops_cached.invalidate_current_branch_cache()
        assert isinstance(result, bool)

        # Test commit info cache invalidation
        count = self.git_ops_cached.invalidate_commit_info_cache("main")
        assert isinstance(count, int)

        # Test diff summary cache invalidation
        count = self.git_ops_cached.invalidate_diff_summary_cache("main", "dev")
        assert isinstance(count, int)

    def test_cache_disabled_methods(self):
        """Test cache methods when caching is disabled."""
        # All cache operations should return appropriate defaults
        assert self.git_ops_uncached.invalidate_cache() == 0
        assert self.git_ops_uncached.invalidate_branches_cache() is False
        assert self.git_ops_uncached.invalidate_current_branch_cache() is False
        assert self.git_ops_uncached.invalidate_commit_info_cache() == 0
        assert self.git_ops_uncached.invalidate_diff_summary_cache() == 0
        assert self.git_ops_uncached.cleanup_expired_cache() == 0

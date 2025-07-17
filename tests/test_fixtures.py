"""Test fixtures and utilities for Git Worktree Manager tests."""

import shutil
import tempfile
from datetime import datetime
from pathlib import Path
from typing import List
from unittest.mock import MagicMock, Mock

import pytest

from git_worktree_manager.config import ConfigManager
from git_worktree_manager.git_ops import GitOperations
from git_worktree_manager.models import CommitInfo, DiffSummary, WorktreeInfo
from git_worktree_manager.ui_controller import UIController


class TestFixtures:
    """Collection of test fixtures and utilities."""

    @staticmethod
    def create_sample_worktree_info(
        path: str = "/test/worktree",
        branch: str = "feature/test",
        commit_hash: str = "abc123def456",
        commit_message: str = "Test commit",
        base_branch: str = "main",
        is_bare: bool = False,
        has_uncommitted_changes: bool = False,
    ) -> WorktreeInfo:
        """Create a sample WorktreeInfo for testing."""
        return WorktreeInfo(
            path=path,
            branch=branch,
            commit_hash=commit_hash,
            commit_message=commit_message,
            base_branch=base_branch,
            is_bare=is_bare,
            has_uncommitted_changes=has_uncommitted_changes,
        )

    @staticmethod
    def create_sample_diff_summary(
        files_modified: int = 2,
        files_added: int = 1,
        files_deleted: int = 0,
        total_insertions: int = 50,
        total_deletions: int = 10,
        summary_text: str = "+50, -10",
    ) -> DiffSummary:
        """Create a sample DiffSummary for testing."""
        return DiffSummary(
            files_modified=files_modified,
            files_added=files_added,
            files_deleted=files_deleted,
            total_insertions=total_insertions,
            total_deletions=total_deletions,
            summary_text=summary_text,
        )

    @staticmethod
    def create_sample_commit_info(
        hash: str = "abc123def456789",
        message: str = "Test commit",
        author: str = "Test Author",
        date: datetime = None,
        short_hash: str = "abc123d",
    ) -> CommitInfo:
        """Create a sample CommitInfo for testing."""
        if date is None:
            date = datetime(2023, 12, 1, 10, 30, 0)

        return CommitInfo(
            hash=hash, message=message, author=author, date=date, short_hash=short_hash
        )

    @staticmethod
    def create_sample_worktree_list() -> List[WorktreeInfo]:
        """Create a sample list of WorktreeInfo objects for testing."""
        return [
            TestFixtures.create_sample_worktree_info(
                path="/repo",
                branch="main",
                commit_hash="abc123",
                commit_message="Initial commit",
                base_branch=None,
                is_bare=True,
            ),
            TestFixtures.create_sample_worktree_info(
                path="/worktrees/feature1",
                branch="feature/feature1",
                commit_hash="def456",
                commit_message="Feature 1 implementation",
                base_branch="main",
                has_uncommitted_changes=True,
            ),
            TestFixtures.create_sample_worktree_info(
                path="/worktrees/feature2",
                branch="feature/feature2",
                commit_hash="ghi789",
                commit_message="Feature 2 implementation",
                base_branch="main",
            ),
        ]


class MockGitOperations:
    """Mock GitOperations for testing."""

    def __init__(self):
        """Initialize mock with default behaviors."""
        self.mock = Mock(spec=GitOperations)
        self._setup_default_behaviors()

    def _setup_default_behaviors(self):
        """Set up default mock behaviors."""
        # Repository validation
        self.mock.is_git_repository.return_value = True

        # Branch operations
        self.mock.get_branches.return_value = ["main", "develop", "feature/test"]
        self.mock.get_current_branch.return_value = "main"

        # Worktree operations
        self.mock.list_worktrees.return_value = (
            TestFixtures.create_sample_worktree_list()
        )
        self.mock.create_worktree.return_value = None

        # Commit operations
        self.mock.get_commit_info.return_value = (
            TestFixtures.create_sample_commit_info()
        )

        # Diff operations
        self.mock.get_diff_summary.return_value = (
            TestFixtures.create_sample_diff_summary()
        )

        # Status operations
        self.mock._has_uncommitted_changes.return_value = False

    def get_mock(self) -> Mock:
        """Get the configured mock object."""
        return self.mock


class MockUIController:
    """Mock UIController for testing."""

    def __init__(self):
        """Initialize mock with default behaviors."""
        self.mock = Mock(spec=UIController)
        self._setup_default_behaviors()

    def _setup_default_behaviors(self):
        """Set up default mock behaviors."""
        # Display methods
        self.mock.display_error.return_value = None
        self.mock.display_warning.return_value = None
        self.mock.display_success.return_value = None
        self.mock.display_info.return_value = None

        # Progress methods
        self.mock.start_progress.return_value = None
        self.mock.update_progress.return_value = None
        self.mock.stop_progress.return_value = None

        # Interactive prompts
        self.mock.prompt_branch_name.return_value = "feature/test"
        self.mock.select_base_branch.return_value = "main"
        self.mock.select_worktree_location.return_value = "/test/worktree"
        self.mock.confirm.return_value = True

        # Display methods
        self.mock.display_worktree_list.return_value = None
        self.mock.display_worktree_details.return_value = None
        self.mock.display_worktree_summary.return_value = None
        self.mock.display_diff_summary.return_value = None

    def get_mock(self) -> Mock:
        """Get the configured mock object."""
        return self.mock


class MockConfigManager:
    """Mock ConfigManager for testing."""

    def __init__(self):
        """Initialize mock with default behaviors."""
        self.mock = Mock(spec=ConfigManager)
        self._setup_default_behaviors()

    def _setup_default_behaviors(self):
        """Set up default mock behaviors."""
        # Configuration methods
        self.mock.get_default_worktree_location.return_value = "/home/user/worktrees"
        self.mock.set_default_worktree_location.return_value = None
        self.mock.load_user_preferences.return_value = {}
        self.mock.save_user_preferences.return_value = None
        self.mock.load_config.return_value = Mock()
        self.mock.save_config.return_value = None

    def get_mock(self) -> Mock:
        """Get the configured mock object."""
        return self.mock


class GitCommandMocker:
    """Utility for mocking Git command subprocess calls."""

    @staticmethod
    def mock_git_command_success(stdout: str = "", returncode: int = 0) -> MagicMock:
        """Create a mock for successful Git command."""
        mock_result = MagicMock()
        mock_result.stdout = stdout
        mock_result.returncode = returncode
        return mock_result

    @staticmethod
    def mock_git_command_failure(
        returncode: int = 128, stderr: str = "Git error"
    ) -> MagicMock:
        """Create a mock for failed Git command."""
        mock_result = MagicMock()
        mock_result.returncode = returncode
        mock_result.stderr = stderr
        return mock_result

    @staticmethod
    def mock_git_branches_output() -> str:
        """Mock output for git branch command."""
        return "main\nfeature/test\ndevelop\n"

    @staticmethod
    def mock_git_worktree_list_output() -> str:
        """Mock output for git worktree list --porcelain command."""
        return """worktree /repo
HEAD abc123456789abcdef123456789abcdef12345678
branch refs/heads/main

worktree /worktrees/feature
HEAD def456789abcdef123456789abcdef123456789a
branch refs/heads/feature/test

"""

    @staticmethod
    def mock_git_diff_stat_output() -> str:
        """Mock output for git diff --stat command."""
        return """file1.py | 10 +++++++---
file2.js | 5 +++++
file3.txt | 3 ---
 3 files changed, 15 insertions(+), 6 deletions(-)
"""

    @staticmethod
    def mock_git_commit_info_output() -> str:
        """Mock output for git log command."""
        return "abc123def456|Test commit|Test Author|2023-12-01T10:30:00+00:00|abc123d"


class TempDirectoryManager:
    """Utility for managing temporary directories in tests."""

    def __init__(self):
        """Initialize temporary directory manager."""
        self.temp_dirs: List[str] = []

    def create_temp_dir(self, prefix: str = "test_") -> str:
        """Create a temporary directory and track it for cleanup."""
        temp_dir = tempfile.mkdtemp(prefix=prefix)
        self.temp_dirs.append(temp_dir)
        return temp_dir

    def create_temp_git_repo(self) -> str:
        """Create a temporary directory with basic Git repository structure."""
        temp_dir = self.create_temp_dir("git_repo_")
        git_dir = Path(temp_dir) / ".git"
        git_dir.mkdir()

        # Create basic Git structure
        (git_dir / "HEAD").write_text("ref: refs/heads/main\n")
        (git_dir / "refs" / "heads").mkdir(parents=True)
        (git_dir / "refs" / "heads" / "main").write_text("abc123def456\n")

        return temp_dir

    def cleanup_all(self):
        """Clean up all created temporary directories."""
        for temp_dir in self.temp_dirs:
            if Path(temp_dir).exists():
                shutil.rmtree(temp_dir, ignore_errors=True)
        self.temp_dirs.clear()


@pytest.fixture
def sample_worktree_info():
    """Pytest fixture for sample WorktreeInfo."""
    return TestFixtures.create_sample_worktree_info()


@pytest.fixture
def sample_diff_summary():
    """Pytest fixture for sample DiffSummary."""
    return TestFixtures.create_sample_diff_summary()


@pytest.fixture
def sample_commit_info():
    """Pytest fixture for sample CommitInfo."""
    return TestFixtures.create_sample_commit_info()


@pytest.fixture
def sample_worktree_list():
    """Pytest fixture for sample worktree list."""
    return TestFixtures.create_sample_worktree_list()


@pytest.fixture
def mock_git_ops():
    """Pytest fixture for mock GitOperations."""
    return MockGitOperations().get_mock()


@pytest.fixture
def mock_ui_controller():
    """Pytest fixture for mock UIController."""
    return MockUIController().get_mock()


@pytest.fixture
def mock_config_manager():
    """Pytest fixture for mock ConfigManager."""
    return MockConfigManager().get_mock()


@pytest.fixture
def temp_dir_manager():
    """Pytest fixture for temporary directory manager."""
    manager = TempDirectoryManager()
    yield manager
    manager.cleanup_all()


@pytest.fixture
def temp_git_repo(temp_dir_manager):
    """Pytest fixture for temporary Git repository."""
    return temp_dir_manager.create_temp_git_repo()


class AssertionHelpers:
    """Helper methods for common test assertions."""

    @staticmethod
    def assert_worktree_info_valid(worktree: WorktreeInfo):
        """Assert that a WorktreeInfo object has valid data."""
        assert isinstance(worktree, WorktreeInfo)
        assert isinstance(worktree.path, str)
        assert len(worktree.path) > 0
        assert isinstance(worktree.branch, str)
        assert len(worktree.branch) > 0
        assert isinstance(worktree.commit_hash, str)
        assert len(worktree.commit_hash) > 0
        assert isinstance(worktree.commit_message, str)
        assert isinstance(worktree.is_bare, bool)
        assert isinstance(worktree.has_uncommitted_changes, bool)

    @staticmethod
    def assert_diff_summary_valid(diff: DiffSummary):
        """Assert that a DiffSummary object has valid data."""
        assert isinstance(diff, DiffSummary)
        assert isinstance(diff.files_modified, int)
        assert isinstance(diff.files_added, int)
        assert isinstance(diff.files_deleted, int)
        assert isinstance(diff.total_insertions, int)
        assert isinstance(diff.total_deletions, int)
        assert isinstance(diff.summary_text, str)
        assert diff.files_modified >= 0
        assert diff.files_added >= 0
        assert diff.files_deleted >= 0
        assert diff.total_insertions >= 0
        assert diff.total_deletions >= 0

    @staticmethod
    def assert_commit_info_valid(commit: CommitInfo):
        """Assert that a CommitInfo object has valid data."""
        assert isinstance(commit, CommitInfo)
        assert isinstance(commit.hash, str)
        assert len(commit.hash) > 0
        assert isinstance(commit.message, str)
        assert len(commit.message) > 0
        assert isinstance(commit.author, str)
        assert len(commit.author) > 0
        assert isinstance(commit.date, datetime)
        assert isinstance(commit.short_hash, str)
        assert len(commit.short_hash) > 0

    @staticmethod
    def assert_mock_called_with_timeout(mock_call, expected_timeout: int = 60):
        """Assert that a mock was called with the expected timeout."""
        call_kwargs = mock_call.call_args[1] if mock_call.call_args else {}
        assert "timeout" in call_kwargs
        assert call_kwargs["timeout"] == expected_timeout


# Export commonly used classes and functions
__all__ = [
    "TestFixtures",
    "MockGitOperations",
    "MockUIController",
    "MockConfigManager",
    "GitCommandMocker",
    "TempDirectoryManager",
    "AssertionHelpers",
]

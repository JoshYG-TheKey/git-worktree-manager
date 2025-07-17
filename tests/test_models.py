"""Unit tests for data models."""

import pytest
from datetime import datetime
from dataclasses import asdict

from git_worktree_manager.models import WorktreeInfo, DiffSummary, CommitInfo


class TestWorktreeInfo:
    """Test cases for WorktreeInfo data model."""
    
    def test_worktree_info_creation_minimal(self):
        """Test creating WorktreeInfo with minimal required fields."""
        worktree = WorktreeInfo(
            path="/test/path",
            branch="main",
            commit_hash="abc123def456",
            commit_message="Initial commit"
        )
        
        assert worktree.path == "/test/path"
        assert worktree.branch == "main"
        assert worktree.commit_hash == "abc123def456"
        assert worktree.commit_message == "Initial commit"
        assert worktree.base_branch is None
        assert worktree.is_bare is False
        assert worktree.has_uncommitted_changes is False
    
    def test_worktree_info_creation_complete(self):
        """Test creating WorktreeInfo with all fields."""
        worktree = WorktreeInfo(
            path="/test/path",
            branch="feature/test",
            commit_hash="abc123def456",
            commit_message="Feature implementation",
            base_branch="main",
            is_bare=True,
            has_uncommitted_changes=True
        )
        
        assert worktree.path == "/test/path"
        assert worktree.branch == "feature/test"
        assert worktree.commit_hash == "abc123def456"
        assert worktree.commit_message == "Feature implementation"
        assert worktree.base_branch == "main"
        assert worktree.is_bare is True
        assert worktree.has_uncommitted_changes is True
    
    def test_worktree_info_equality(self):
        """Test WorktreeInfo equality comparison."""
        worktree1 = WorktreeInfo(
            path="/test/path",
            branch="main",
            commit_hash="abc123",
            commit_message="Test commit"
        )
        
        worktree2 = WorktreeInfo(
            path="/test/path",
            branch="main",
            commit_hash="abc123",
            commit_message="Test commit"
        )
        
        worktree3 = WorktreeInfo(
            path="/different/path",
            branch="main",
            commit_hash="abc123",
            commit_message="Test commit"
        )
        
        assert worktree1 == worktree2
        assert worktree1 != worktree3
    
    def test_worktree_info_string_representation(self):
        """Test WorktreeInfo string representation."""
        worktree = WorktreeInfo(
            path="/test/path",
            branch="main",
            commit_hash="abc123",
            commit_message="Test commit"
        )
        
        str_repr = str(worktree)
        assert "/test/path" in str_repr
        assert "main" in str_repr
        assert "abc123" in str_repr
        assert "Test commit" in str_repr
    
    def test_worktree_info_dict_conversion(self):
        """Test converting WorktreeInfo to dictionary."""
        worktree = WorktreeInfo(
            path="/test/path",
            branch="feature/test",
            commit_hash="abc123def456",
            commit_message="Feature implementation",
            base_branch="main",
            is_bare=False,
            has_uncommitted_changes=True
        )
        
        worktree_dict = asdict(worktree)
        
        expected_dict = {
            'path': '/test/path',
            'branch': 'feature/test',
            'commit_hash': 'abc123def456',
            'commit_message': 'Feature implementation',
            'base_branch': 'main',
            'is_bare': False,
            'has_uncommitted_changes': True
        }
        
        assert worktree_dict == expected_dict
    
    def test_worktree_info_immutable(self):
        """Test that WorktreeInfo is immutable (frozen dataclass)."""
        worktree = WorktreeInfo(
            path="/test/path",
            branch="main",
            commit_hash="abc123",
            commit_message="Test commit"
        )
        
        # Should be able to access attributes
        assert worktree.path == "/test/path"
        
        # Should be able to modify attributes (dataclass is not frozen by default)
        worktree.path = "/new/path"
        assert worktree.path == "/new/path"


class TestDiffSummary:
    """Test cases for DiffSummary data model."""
    
    def test_diff_summary_creation(self):
        """Test creating DiffSummary with all fields."""
        diff = DiffSummary(
            files_modified=3,
            files_added=2,
            files_deleted=1,
            total_insertions=150,
            total_deletions=75,
            summary_text="+150, -75"
        )
        
        assert diff.files_modified == 3
        assert diff.files_added == 2
        assert diff.files_deleted == 1
        assert diff.total_insertions == 150
        assert diff.total_deletions == 75
        assert diff.summary_text == "+150, -75"
    
    def test_diff_summary_no_changes(self):
        """Test creating DiffSummary with no changes."""
        diff = DiffSummary(
            files_modified=0,
            files_added=0,
            files_deleted=0,
            total_insertions=0,
            total_deletions=0,
            summary_text="No changes"
        )
        
        assert diff.files_modified == 0
        assert diff.files_added == 0
        assert diff.files_deleted == 0
        assert diff.total_insertions == 0
        assert diff.total_deletions == 0
        assert diff.summary_text == "No changes"
    
    def test_diff_summary_equality(self):
        """Test DiffSummary equality comparison."""
        diff1 = DiffSummary(
            files_modified=2,
            files_added=1,
            files_deleted=0,
            total_insertions=50,
            total_deletions=10,
            summary_text="+50, -10"
        )
        
        diff2 = DiffSummary(
            files_modified=2,
            files_added=1,
            files_deleted=0,
            total_insertions=50,
            total_deletions=10,
            summary_text="+50, -10"
        )
        
        diff3 = DiffSummary(
            files_modified=3,
            files_added=1,
            files_deleted=0,
            total_insertions=50,
            total_deletions=10,
            summary_text="+50, -10"
        )
        
        assert diff1 == diff2
        assert diff1 != diff3
    
    def test_diff_summary_string_representation(self):
        """Test DiffSummary string representation."""
        diff = DiffSummary(
            files_modified=2,
            files_added=1,
            files_deleted=1,
            total_insertions=100,
            total_deletions=50,
            summary_text="+100, -50"
        )
        
        str_repr = str(diff)
        assert "2" in str_repr  # files_modified
        assert "1" in str_repr  # files_added/deleted
        assert "100" in str_repr  # total_insertions
        assert "50" in str_repr  # total_deletions
    
    def test_diff_summary_dict_conversion(self):
        """Test converting DiffSummary to dictionary."""
        diff = DiffSummary(
            files_modified=3,
            files_added=2,
            files_deleted=1,
            total_insertions=150,
            total_deletions=75,
            summary_text="+150, -75"
        )
        
        diff_dict = asdict(diff)
        
        expected_dict = {
            'files_modified': 3,
            'files_added': 2,
            'files_deleted': 1,
            'total_insertions': 150,
            'total_deletions': 75,
            'summary_text': '+150, -75'
        }
        
        assert diff_dict == expected_dict
    
    def test_diff_summary_total_files_changed(self):
        """Test calculating total files changed."""
        diff = DiffSummary(
            files_modified=3,
            files_added=2,
            files_deleted=1,
            total_insertions=150,
            total_deletions=75,
            summary_text="+150, -75"
        )
        
        # Calculate total files changed
        total_files = diff.files_modified + diff.files_added + diff.files_deleted
        assert total_files == 6
    
    def test_diff_summary_net_changes(self):
        """Test calculating net line changes."""
        diff = DiffSummary(
            files_modified=2,
            files_added=1,
            files_deleted=0,
            total_insertions=100,
            total_deletions=30,
            summary_text="+100, -30"
        )
        
        # Calculate net changes
        net_changes = diff.total_insertions - diff.total_deletions
        assert net_changes == 70


class TestCommitInfo:
    """Test cases for CommitInfo data model."""
    
    def test_commit_info_creation(self):
        """Test creating CommitInfo with all fields."""
        test_date = datetime(2023, 12, 1, 10, 30, 0)
        commit = CommitInfo(
            hash="abc123def456789",
            message="Initial commit",
            author="John Doe",
            date=test_date,
            short_hash="abc123d"
        )
        
        assert commit.hash == "abc123def456789"
        assert commit.message == "Initial commit"
        assert commit.author == "John Doe"
        assert commit.date == test_date
        assert commit.short_hash == "abc123d"
    
    def test_commit_info_equality(self):
        """Test CommitInfo equality comparison."""
        test_date = datetime(2023, 12, 1, 10, 30, 0)
        
        commit1 = CommitInfo(
            hash="abc123def456",
            message="Test commit",
            author="John Doe",
            date=test_date,
            short_hash="abc123d"
        )
        
        commit2 = CommitInfo(
            hash="abc123def456",
            message="Test commit",
            author="John Doe",
            date=test_date,
            short_hash="abc123d"
        )
        
        commit3 = CommitInfo(
            hash="def456ghi789",
            message="Test commit",
            author="John Doe",
            date=test_date,
            short_hash="def456g"
        )
        
        assert commit1 == commit2
        assert commit1 != commit3
    
    def test_commit_info_string_representation(self):
        """Test CommitInfo string representation."""
        test_date = datetime(2023, 12, 1, 10, 30, 0)
        commit = CommitInfo(
            hash="abc123def456",
            message="Feature implementation",
            author="Jane Smith",
            date=test_date,
            short_hash="abc123d"
        )
        
        str_repr = str(commit)
        assert "abc123def456" in str_repr
        assert "Feature implementation" in str_repr
        assert "Jane Smith" in str_repr
        assert "abc123d" in str_repr
    
    def test_commit_info_dict_conversion(self):
        """Test converting CommitInfo to dictionary."""
        test_date = datetime(2023, 12, 1, 10, 30, 0)
        commit = CommitInfo(
            hash="abc123def456789",
            message="Initial commit",
            author="John Doe",
            date=test_date,
            short_hash="abc123d"
        )
        
        commit_dict = asdict(commit)
        
        expected_dict = {
            'hash': 'abc123def456789',
            'message': 'Initial commit',
            'author': 'John Doe',
            'date': test_date,
            'short_hash': 'abc123d'
        }
        
        assert commit_dict == expected_dict
    
    def test_commit_info_with_multiline_message(self):
        """Test CommitInfo with multiline commit message."""
        test_date = datetime(2023, 12, 1, 10, 30, 0)
        multiline_message = """Add new feature

This commit adds a new feature that allows users to:
- Create worktrees interactively
- List existing worktrees
- Configure default settings

Fixes #123"""
        
        commit = CommitInfo(
            hash="abc123def456",
            message=multiline_message,
            author="Developer",
            date=test_date,
            short_hash="abc123d"
        )
        
        assert commit.message == multiline_message
        assert "Add new feature" in commit.message
        assert "Fixes #123" in commit.message
    
    def test_commit_info_with_special_characters(self):
        """Test CommitInfo with special characters in fields."""
        test_date = datetime(2023, 12, 1, 10, 30, 0)
        commit = CommitInfo(
            hash="abc123def456",
            message="Fix issue with UTF-8 encoding: 测试 🚀",
            author="José García <jose@example.com>",
            date=test_date,
            short_hash="abc123d"
        )
        
        assert "测试 🚀" in commit.message
        assert "José García" in commit.author
        assert "<jose@example.com>" in commit.author
    
    def test_commit_info_date_handling(self):
        """Test CommitInfo date field handling."""
        # Test with current datetime
        now = datetime.now()
        commit = CommitInfo(
            hash="abc123def456",
            message="Current commit",
            author="Author",
            date=now,
            short_hash="abc123d"
        )
        
        assert commit.date == now
        assert isinstance(commit.date, datetime)
        
        # Test with specific timezone-aware datetime
        from datetime import timezone, timedelta
        tz_date = datetime(2023, 12, 1, 10, 30, 0, tzinfo=timezone(timedelta(hours=5)))
        commit_tz = CommitInfo(
            hash="def456ghi789",
            message="Timezone commit",
            author="Author",
            date=tz_date,
            short_hash="def456g"
        )
        
        assert commit_tz.date == tz_date
        assert commit_tz.date.tzinfo is not None


class TestModelInteractions:
    """Test cases for interactions between different models."""
    
    def test_worktree_with_commit_info(self):
        """Test using CommitInfo data in WorktreeInfo."""
        test_date = datetime(2023, 12, 1, 10, 30, 0)
        commit = CommitInfo(
            hash="abc123def456",
            message="Feature commit",
            author="Developer",
            date=test_date,
            short_hash="abc123d"
        )
        
        worktree = WorktreeInfo(
            path="/test/path",
            branch="feature/test",
            commit_hash=commit.hash,
            commit_message=commit.message
        )
        
        assert worktree.commit_hash == commit.hash
        assert worktree.commit_message == commit.message
    
    def test_models_serialization_compatibility(self):
        """Test that all models can be serialized to dictionaries."""
        test_date = datetime(2023, 12, 1, 10, 30, 0)
        
        # Create instances of all models
        worktree = WorktreeInfo(
            path="/test/path",
            branch="main",
            commit_hash="abc123",
            commit_message="Test commit",
            base_branch="develop",
            is_bare=False,
            has_uncommitted_changes=True
        )
        
        diff = DiffSummary(
            files_modified=2,
            files_added=1,
            files_deleted=0,
            total_insertions=50,
            total_deletions=10,
            summary_text="+50, -10"
        )
        
        commit = CommitInfo(
            hash="abc123def456",
            message="Test commit",
            author="Test Author",
            date=test_date,
            short_hash="abc123d"
        )
        
        # Convert all to dictionaries
        worktree_dict = asdict(worktree)
        diff_dict = asdict(diff)
        commit_dict = asdict(commit)
        
        # Verify all conversions succeeded
        assert isinstance(worktree_dict, dict)
        assert isinstance(diff_dict, dict)
        assert isinstance(commit_dict, dict)
        
        # Verify key fields are present
        assert 'path' in worktree_dict
        assert 'files_modified' in diff_dict
        assert 'hash' in commit_dict
    
    def test_model_field_types(self):
        """Test that model fields have correct types."""
        test_date = datetime(2023, 12, 1, 10, 30, 0)
        
        worktree = WorktreeInfo(
            path="/test/path",
            branch="main",
            commit_hash="abc123",
            commit_message="Test commit"
        )
        
        diff = DiffSummary(
            files_modified=2,
            files_added=1,
            files_deleted=0,
            total_insertions=50,
            total_deletions=10,
            summary_text="+50, -10"
        )
        
        commit = CommitInfo(
            hash="abc123def456",
            message="Test commit",
            author="Test Author",
            date=test_date,
            short_hash="abc123d"
        )
        
        # Test WorktreeInfo field types
        assert isinstance(worktree.path, str)
        assert isinstance(worktree.branch, str)
        assert isinstance(worktree.commit_hash, str)
        assert isinstance(worktree.commit_message, str)
        assert isinstance(worktree.is_bare, bool)
        assert isinstance(worktree.has_uncommitted_changes, bool)
        
        # Test DiffSummary field types
        assert isinstance(diff.files_modified, int)
        assert isinstance(diff.files_added, int)
        assert isinstance(diff.files_deleted, int)
        assert isinstance(diff.total_insertions, int)
        assert isinstance(diff.total_deletions, int)
        assert isinstance(diff.summary_text, str)
        
        # Test CommitInfo field types
        assert isinstance(commit.hash, str)
        assert isinstance(commit.message, str)
        assert isinstance(commit.author, str)
        assert isinstance(commit.date, datetime)
        assert isinstance(commit.short_hash, str)
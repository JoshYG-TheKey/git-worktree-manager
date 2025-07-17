"""Unit tests for WorktreeManager class."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

from git_worktree_manager.worktree_manager import (
    WorktreeManager, 
    WorktreeManagerError, 
    WorktreeCreationError
)
from git_worktree_manager.models import WorktreeInfo, DiffSummary, CommitInfo
from git_worktree_manager.git_ops import GitRepositoryError


class TestWorktreeManager:
    """Test cases for WorktreeManager class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_git_ops = Mock()
        self.mock_ui_controller = Mock()
        self.mock_config_manager = Mock()
        
        self.manager = WorktreeManager(
            git_ops=self.mock_git_ops,
            ui_controller=self.mock_ui_controller,
            config_manager=self.mock_config_manager
        )
    
    def test_init_with_defaults(self):
        """Test WorktreeManager initialization with default dependencies."""
        manager = WorktreeManager()
        assert manager.git_ops is not None
        assert manager.ui_controller is not None
        assert manager.config_manager is not None
    
    def test_init_with_custom_dependencies(self):
        """Test WorktreeManager initialization with custom dependencies."""
        assert self.manager.git_ops == self.mock_git_ops
        assert self.manager.ui_controller == self.mock_ui_controller
        assert self.manager.config_manager == self.mock_config_manager


class TestCreateWorktree:
    """Test cases for create_worktree method."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_git_ops = Mock()
        self.mock_ui_controller = Mock()
        self.mock_config_manager = Mock()
        
        self.manager = WorktreeManager(
            git_ops=self.mock_git_ops,
            ui_controller=self.mock_ui_controller,
            config_manager=self.mock_config_manager
        )
        
        # Default mock responses
        self.mock_git_ops.is_git_repository.return_value = True
        self.mock_git_ops.get_branches.return_value = ['main', 'develop', 'feature/test']
        self.mock_git_ops.get_current_branch.return_value = 'main'
        self.mock_git_ops.create_worktree.return_value = None
        self.mock_git_ops.get_commit_info.return_value = CommitInfo(
            hash='abc123def456',
            message='Test commit',
            author='Test Author',
            date=None,
            short_hash='abc123d'
        )
        self.mock_git_ops._has_uncommitted_changes.return_value = False
        
        self.mock_config_manager.get_default_worktree_location.return_value = '/home/user/worktrees'
        
        self.mock_ui_controller.prompt_branch_name.return_value = 'feature/new-feature'
        self.mock_ui_controller.select_base_branch.return_value = 'main'
        self.mock_ui_controller.select_worktree_location.return_value = '/home/user/worktrees/feature-new-feature'
    
    def test_create_worktree_with_all_parameters(self):
        """Test creating worktree with all parameters provided."""
        result = self.manager.create_worktree(
            branch_name='feature/test',
            base_branch='main',
            location='/tmp/test-worktree'
        )
        
        # Verify Git operations were called
        self.mock_git_ops.is_git_repository.assert_called_once()
        self.mock_git_ops.create_worktree.assert_called_once_with(
            '/tmp/test-worktree', 'feature/test', 'main'
        )
        
        # Verify UI interactions
        self.mock_ui_controller.start_progress.assert_called()
        self.mock_ui_controller.stop_progress.assert_called()
        self.mock_ui_controller.display_success.assert_called()
        
        # Verify result
        assert isinstance(result, WorktreeInfo)
        assert result.branch == 'feature/test'
        assert result.path == '/tmp/test-worktree'
    
    def test_create_worktree_with_interactive_prompts(self):
        """Test creating worktree with interactive prompts."""
        # Mock the _get_default_worktree_path method directly
        with patch.object(self.manager, '_get_default_worktree_path') as mock_get_path:
            mock_get_path.return_value = '/home/user/worktrees/feature-new-feature'
            
            # Mock the _ensure_parent_directory method to avoid filesystem operations
            with patch.object(self.manager, '_ensure_parent_directory') as mock_ensure_dir:
                result = self.manager.create_worktree()
                
                # Verify interactive prompts were called
                self.mock_ui_controller.prompt_branch_name.assert_called_once()
                self.mock_ui_controller.select_base_branch.assert_called_once()
                self.mock_ui_controller.select_worktree_location.assert_called_once()
                
                # Verify Git operations
                self.mock_git_ops.create_worktree.assert_called_once_with(
                    '/home/user/worktrees/feature-new-feature',
                    'feature/new-feature',
                    'main'
                )
                
                # Verify parent directory creation was attempted
                mock_ensure_dir.assert_called_once_with('/home/user/worktrees/feature-new-feature')
                
                assert isinstance(result, WorktreeInfo)
    
    def test_create_worktree_not_in_git_repository(self):
        """Test creating worktree when not in a Git repository."""
        self.mock_git_ops.is_git_repository.return_value = False
        
        with pytest.raises(WorktreeCreationError, match="Not in a Git repository"):
            self.manager.create_worktree()
    
    def test_create_worktree_git_operations_fail(self):
        """Test creating worktree when Git operations fail."""
        self.mock_git_ops.get_branches.side_effect = GitRepositoryError("Git command failed")
        
        with pytest.raises(WorktreeCreationError, match="Failed to get branch information"):
            self.manager.create_worktree()
    
    def test_create_worktree_user_cancellation(self):
        """Test creating worktree when user cancels operation."""
        self.mock_ui_controller.prompt_branch_name.side_effect = KeyboardInterrupt()
        
        with pytest.raises(WorktreeCreationError, match="Operation cancelled by user"):
            self.manager.create_worktree()
    
    def test_create_worktree_creation_fails(self):
        """Test creating worktree when Git worktree creation fails."""
        self.mock_git_ops.create_worktree.side_effect = GitRepositoryError("Worktree creation failed")
        
        with pytest.raises(WorktreeCreationError, match="Failed to create worktree"):
            self.manager.create_worktree(
                branch_name='test',
                base_branch='main',
                location='/tmp/test'
            )
    
    def test_create_worktree_validation_errors(self):
        """Test worktree creation with invalid inputs."""
        # Empty branch name
        with pytest.raises(WorktreeCreationError, match="Branch name cannot be empty"):
            self.manager.create_worktree(
                branch_name='',
                base_branch='main',
                location='/tmp/test'
            )
        
        # Empty base branch
        with pytest.raises(WorktreeCreationError, match="Base branch cannot be empty"):
            self.manager.create_worktree(
                branch_name='test',
                base_branch='',
                location='/tmp/test'
            )
        
        # Empty location
        with pytest.raises(WorktreeCreationError, match="Location cannot be empty"):
            self.manager.create_worktree(
                branch_name='test',
                base_branch='main',
                location=''
            )
    
    @patch('git_worktree_manager.worktree_manager.Path')
    def test_create_worktree_location_is_file(self, mock_path):
        """Test worktree creation when location is an existing file."""
        mock_location = Mock()
        mock_location.exists.return_value = True
        mock_location.is_file.return_value = True
        mock_path.return_value = mock_location
        
        with pytest.raises(WorktreeCreationError, match="Location is a file"):
            self.manager.create_worktree(
                branch_name='test',
                base_branch='main',
                location='/tmp/existing-file'
            )
    
    @patch('git_worktree_manager.worktree_manager.Path')
    def test_create_worktree_location_not_empty(self, mock_path):
        """Test worktree creation when location is a non-empty directory."""
        mock_location = Mock()
        mock_location.exists.return_value = True
        mock_location.is_file.return_value = False
        mock_location.is_dir.return_value = True
        mock_location.iterdir.return_value = ['some_file']  # Non-empty
        mock_path.return_value = mock_location
        
        with pytest.raises(WorktreeCreationError, match="already exists and is not empty"):
            self.manager.create_worktree(
                branch_name='test',
                base_branch='main',
                location='/tmp/non-empty-dir'
            )


class TestListWorktrees:
    """Test cases for list_worktrees method."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_git_ops = Mock()
        self.mock_ui_controller = Mock()
        self.mock_config_manager = Mock()
        
        self.manager = WorktreeManager(
            git_ops=self.mock_git_ops,
            ui_controller=self.mock_ui_controller,
            config_manager=self.mock_config_manager
        )
        
        # Sample worktree data
        self.sample_worktrees = [
            WorktreeInfo(
                path='/repo',
                branch='main',
                commit_hash='abc123',
                commit_message='Initial commit',
                is_bare=True
            ),
            WorktreeInfo(
                path='/worktrees/feature',
                branch='feature/test',
                commit_hash='def456',
                commit_message='Feature commit'
            )
        ]
        
        self.mock_git_ops.list_worktrees.return_value = self.sample_worktrees
        self.mock_git_ops._has_uncommitted_changes.return_value = False
    
    def test_list_worktrees_success(self):
        """Test successful worktree listing."""
        result = self.manager.list_worktrees()
        
        self.mock_git_ops.list_worktrees.assert_called_once()
        assert len(result) == 2
        assert all(isinstance(wt, WorktreeInfo) for wt in result)
    
    def test_list_worktrees_with_caching(self):
        """Test worktree listing with caching."""
        # First call
        result1 = self.manager.list_worktrees()
        
        # Second call should use cache
        result2 = self.manager.list_worktrees()
        
        # Git operations should only be called once
        self.mock_git_ops.list_worktrees.assert_called_once()
        assert result1 == result2
    
    def test_list_worktrees_git_error(self):
        """Test worktree listing when Git operations fail."""
        self.mock_git_ops.list_worktrees.side_effect = GitRepositoryError("Git command failed")
        
        with pytest.raises(GitRepositoryError):
            self.manager.list_worktrees()
    
    def test_list_worktrees_enhancement_error(self):
        """Test worktree listing when enhancement fails gracefully."""
        self.mock_git_ops._has_uncommitted_changes.side_effect = Exception("Enhancement failed")
        
        # Should not raise exception, but return original worktrees
        result = self.manager.list_worktrees()
        assert len(result) == 2


class TestGetWorktreeStatus:
    """Test cases for get_worktree_status method."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_git_ops = Mock()
        self.mock_ui_controller = Mock()
        self.mock_config_manager = Mock()
        
        self.manager = WorktreeManager(
            git_ops=self.mock_git_ops,
            ui_controller=self.mock_ui_controller,
            config_manager=self.mock_config_manager
        )
        
        self.sample_worktree = WorktreeInfo(
            path='/worktrees/feature',
            branch='feature/test',
            commit_hash='def456',
            commit_message='Feature commit'
        )
        
        self.mock_git_ops._has_uncommitted_changes.return_value = True
    
    def test_get_worktree_status_success(self):
        """Test successful worktree status retrieval."""
        result = self.manager.get_worktree_status(self.sample_worktree)
        
        self.mock_git_ops._has_uncommitted_changes.assert_called_once_with('/worktrees/feature')
        assert isinstance(result, WorktreeInfo)
        assert result.has_uncommitted_changes is True
        assert result.path == self.sample_worktree.path
        assert result.branch == self.sample_worktree.branch
    
    def test_get_worktree_status_error(self):
        """Test worktree status when operations fail gracefully."""
        self.mock_git_ops._has_uncommitted_changes.side_effect = Exception("Status check failed")
        
        # Should not raise exception, but return original worktree due to graceful error handling
        result = self.manager.get_worktree_status(self.sample_worktree)
        
        assert isinstance(result, WorktreeInfo)
        assert result.path == self.sample_worktree.path
        assert result.branch == self.sample_worktree.branch


class TestCalculateDiffSummary:
    """Test cases for calculate_diff_summary method."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_git_ops = Mock()
        self.mock_ui_controller = Mock()
        self.mock_config_manager = Mock()
        
        self.manager = WorktreeManager(
            git_ops=self.mock_git_ops,
            ui_controller=self.mock_ui_controller,
            config_manager=self.mock_config_manager
        )
        
        self.sample_worktree = WorktreeInfo(
            path='/worktrees/feature',
            branch='feature/test',
            commit_hash='def456',
            commit_message='Feature commit',
            base_branch='main'
        )
        
        self.sample_diff = DiffSummary(
            files_modified=2,
            files_added=1,
            files_deleted=0,
            total_insertions=15,
            total_deletions=5,
            summary_text='+15, -5'
        )
        
        self.mock_git_ops.get_diff_summary.return_value = self.sample_diff
    
    def test_calculate_diff_summary_with_base_branch(self):
        """Test diff calculation with explicit base branch."""
        result = self.manager.calculate_diff_summary(self.sample_worktree, 'develop')
        
        self.mock_git_ops.get_diff_summary.assert_called_once_with('develop', 'feature/test')
        assert result == self.sample_diff
    
    def test_calculate_diff_summary_with_worktree_base_branch(self):
        """Test diff calculation using worktree's base branch."""
        result = self.manager.calculate_diff_summary(self.sample_worktree)
        
        self.mock_git_ops.get_diff_summary.assert_called_once_with('main', 'feature/test')
        assert result == self.sample_diff
    
    def test_calculate_diff_summary_no_base_branch(self):
        """Test diff calculation when no base branch is available."""
        worktree_no_base = WorktreeInfo(
            path='/worktrees/feature',
            branch='feature/test',
            commit_hash='def456',
            commit_message='Feature commit'
        )
        
        self.mock_git_ops.get_current_branch.return_value = 'main'
        
        result = self.manager.calculate_diff_summary(worktree_no_base)
        
        self.mock_git_ops.get_diff_summary.assert_called_once_with('main', 'feature/test')
        assert result == self.sample_diff
    
    def test_calculate_diff_summary_fallback_to_main(self):
        """Test diff calculation fallback to main branch."""
        worktree_no_base = WorktreeInfo(
            path='/worktrees/feature',
            branch='feature/test',
            commit_hash='def456',
            commit_message='Feature commit'
        )
        
        self.mock_git_ops.get_current_branch.return_value = 'feature/test'  # Same as worktree
        self.mock_git_ops.get_branches.return_value = ['main', 'develop', 'feature/test']
        
        result = self.manager.calculate_diff_summary(worktree_no_base)
        
        self.mock_git_ops.get_diff_summary.assert_called_once_with('main', 'feature/test')
        assert result == self.sample_diff
    
    def test_calculate_diff_summary_no_suitable_base(self):
        """Test diff calculation when no suitable base branch found."""
        worktree_no_base = WorktreeInfo(
            path='/worktrees/feature',
            branch='feature/test',
            commit_hash='def456',
            commit_message='Feature commit'
        )
        
        self.mock_git_ops.get_current_branch.return_value = 'feature/test'
        self.mock_git_ops.get_branches.return_value = ['feature/test', 'feature/other']
        
        result = self.manager.calculate_diff_summary(worktree_no_base)
        
        assert result is None
    
    def test_calculate_diff_summary_with_caching(self):
        """Test diff calculation with caching."""
        # First call
        result1 = self.manager.calculate_diff_summary(self.sample_worktree)
        
        # Second call should use cache
        result2 = self.manager.calculate_diff_summary(self.sample_worktree)
        
        # Git operations should only be called once
        self.mock_git_ops.get_diff_summary.assert_called_once()
        assert result1 == result2
    
    def test_calculate_diff_summary_missing_branch_error(self):
        """Test diff calculation when base branch doesn't exist."""
        self.mock_git_ops.get_diff_summary.side_effect = GitRepositoryError("unknown revision")
        
        result = self.manager.calculate_diff_summary(self.sample_worktree)
        
        # Should return None for missing branch errors
        assert result is None
    
    def test_calculate_diff_summary_other_git_error(self):
        """Test diff calculation with other Git errors."""
        self.mock_git_ops.get_diff_summary.side_effect = GitRepositoryError("Other Git error")
        
        with pytest.raises(GitRepositoryError):
            self.manager.calculate_diff_summary(self.sample_worktree)


class TestCacheManagement:
    """Test cases for cache management functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_git_ops = Mock()
        self.mock_ui_controller = Mock()
        self.mock_config_manager = Mock()
        
        self.manager = WorktreeManager(
            git_ops=self.mock_git_ops,
            ui_controller=self.mock_ui_controller,
            config_manager=self.mock_config_manager
        )
    
    def test_clear_caches(self):
        """Test cache clearing functionality."""
        # Set up some cached data
        self.manager._branch_cache = ['main', 'develop']
        self.manager._worktree_cache = [Mock()]
        self.manager._diff_cache = {'key': Mock()}
        
        # Clear caches
        self.manager._clear_caches()
        
        # Verify caches are cleared
        assert self.manager._branch_cache is None
        assert self.manager._worktree_cache is None
        assert len(self.manager._diff_cache) == 0
    
    def test_get_branches_cached(self):
        """Test cached branch retrieval."""
        self.mock_git_ops.get_branches.return_value = ['main', 'develop']
        
        # First call
        result1 = self.manager._get_branches_cached()
        
        # Second call should use cache
        result2 = self.manager._get_branches_cached()
        
        # Git operations should only be called once
        self.mock_git_ops.get_branches.assert_called_once()
        assert result1 == result2 == ['main', 'develop']


class TestHelperMethods:
    """Test cases for helper methods."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_git_ops = Mock()
        self.mock_ui_controller = Mock()
        self.mock_config_manager = Mock()
        
        self.manager = WorktreeManager(
            git_ops=self.mock_git_ops,
            ui_controller=self.mock_ui_controller,
            config_manager=self.mock_config_manager
        )
    
    def test_get_default_worktree_path(self):
        """Test default worktree path generation."""
        self.mock_config_manager.get_default_worktree_location.return_value = '/home/user/worktrees'
        
        result = self.manager._get_default_worktree_path('feature/test')
        
        assert result == '/home/user/worktrees/feature/test'
    
    def test_get_default_worktree_path_config_error(self):
        """Test default worktree path with config error fallback."""
        from git_worktree_manager.config import ConfigError
        self.mock_config_manager.get_default_worktree_location.side_effect = ConfigError("Config failed")
        
        with patch('git_worktree_manager.worktree_manager.Path') as mock_path:
            mock_path.home.return_value = Path('/home/user')
            
            result = self.manager._get_default_worktree_path('feature/test')
            
            assert '/home/user/worktrees/feature/test' in result
    
    @patch('git_worktree_manager.worktree_manager.Path')
    def test_ensure_parent_directory_success(self, mock_path):
        """Test successful parent directory creation."""
        mock_location = Mock()
        mock_parent = Mock()
        mock_location.parent = mock_parent
        mock_path.return_value = mock_location
        
        self.manager._ensure_parent_directory('/tmp/test/worktree')
        
        mock_parent.mkdir.assert_called_once_with(parents=True, exist_ok=True)
    
    @patch('git_worktree_manager.worktree_manager.Path')
    def test_ensure_parent_directory_error(self, mock_path):
        """Test parent directory creation error."""
        mock_location = Mock()
        mock_parent = Mock()
        mock_parent.mkdir.side_effect = OSError("Permission denied")
        mock_location.parent = mock_parent
        mock_path.return_value = mock_location
        
        with pytest.raises(WorktreeCreationError, match="Failed to create parent directory"):
            self.manager._ensure_parent_directory('/tmp/test/worktree')
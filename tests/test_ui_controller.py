"""Tests for UIController class."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from io import StringIO

from git_worktree_manager.ui_controller import UIController
from git_worktree_manager.models import WorktreeInfo, DiffSummary
from rich.console import Console
from rich.theme import Theme


class TestUIController:
    """Test cases for UIController class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        # Create a mock console for testing
        self.mock_console = Mock(spec=Console)
        self.mock_console.size.width = 80
        self.mock_console.size.height = 24
        # Add required attributes for Progress
        self.mock_console.get_time = Mock(return_value=0.0)
        self.mock_console.is_terminal = True
        self.ui_controller = UIController(console=self.mock_console)
    
    def test_init_with_custom_console(self):
        """Test UIController initialization with custom console."""
        custom_console = Mock(spec=Console)
        ui = UIController(console=custom_console)
        assert ui.console is custom_console
    
    def test_init_without_console(self):
        """Test UIController initialization without console creates new one."""
        ui = UIController()
        assert ui.console is not None
        assert isinstance(ui.console, Console)
        # Check that custom theme is applied by checking if we can get a style
        assert ui.console.get_style("error") is not None
    
    def test_display_error(self):
        """Test error message display."""
        self.ui_controller.display_error("Test error message", "Test Error")
        
        # Verify console.print was called
        self.mock_console.print.assert_called_once()
        
        # Get the panel that was printed
        call_args = self.mock_console.print.call_args[0]
        panel = call_args[0]
        
        # Verify it's a Panel with correct styling
        assert hasattr(panel, 'renderable')
        assert hasattr(panel, 'title')
    
    def test_display_warning(self):
        """Test warning message display."""
        self.ui_controller.display_warning("Test warning message", "Test Warning")
        
        self.mock_console.print.assert_called_once()
        call_args = self.mock_console.print.call_args[0]
        panel = call_args[0]
        assert hasattr(panel, 'renderable')
        assert hasattr(panel, 'title')
    
    def test_display_success(self):
        """Test success message display."""
        self.ui_controller.display_success("Test success message", "Test Success")
        
        self.mock_console.print.assert_called_once()
        call_args = self.mock_console.print.call_args[0]
        panel = call_args[0]
        assert hasattr(panel, 'renderable')
        assert hasattr(panel, 'title')
    
    def test_display_info(self):
        """Test info message display."""
        self.ui_controller.display_info("Test info message", "Test Info")
        
        self.mock_console.print.assert_called_once()
        call_args = self.mock_console.print.call_args[0]
        panel = call_args[0]
        assert hasattr(panel, 'renderable')
        assert hasattr(panel, 'title')
    
    @patch('git_worktree_manager.ui_controller.Progress')
    def test_start_progress(self, mock_progress_class):
        """Test starting progress indicator."""
        mock_progress = Mock()
        mock_progress_class.return_value = mock_progress
        
        self.ui_controller.start_progress("Testing progress")
        
        # Verify progress was created and started
        assert self.ui_controller._progress is not None
        mock_progress.start.assert_called_once()
        mock_progress.add_task.assert_called_once_with(description="Testing progress")
    
    @patch('git_worktree_manager.ui_controller.Progress')
    def test_update_progress(self, mock_progress_class):
        """Test updating progress indicator."""
        mock_progress = Mock()
        mock_progress_class.return_value = mock_progress
        
        # Mock the progress tasks
        mock_task = Mock()
        mock_task.id = 1
        mock_progress.tasks = [mock_task]
        
        # Start progress first
        self.ui_controller.start_progress("Initial description")
        
        # Update progress
        self.ui_controller.update_progress("Updated description")
        
        # Verify update was called
        mock_progress.update.assert_called_once_with(1, description="Updated description")
    
    def test_update_progress_without_starting(self):
        """Test updating progress when not started doesn't crash."""
        # Should not raise an exception
        self.ui_controller.update_progress("Test description")
    
    @patch('git_worktree_manager.ui_controller.Progress')
    def test_stop_progress(self, mock_progress_class):
        """Test stopping progress indicator."""
        mock_progress = Mock()
        mock_progress_class.return_value = mock_progress
        
        # Start progress first
        self.ui_controller.start_progress("Test progress")
        
        # Stop progress
        self.ui_controller.stop_progress()
        
        # Verify progress was stopped and cleared
        mock_progress.stop.assert_called_once()
        assert self.ui_controller._progress is None
    
    def test_stop_progress_without_starting(self):
        """Test stopping progress when not started doesn't crash."""
        # Should not raise an exception
        self.ui_controller.stop_progress()
    
    def test_clear_screen(self):
        """Test clearing the screen."""
        self.ui_controller.clear_screen()
        self.mock_console.clear.assert_called_once()
    
    def test_print(self):
        """Test printing to console."""
        self.ui_controller.print("Test message", style="info")
        self.mock_console.print.assert_called_once_with("Test message", style="info")
    
    @patch('git_worktree_manager.ui_controller.Confirm.ask')
    def test_confirm(self, mock_confirm):
        """Test confirmation prompt."""
        mock_confirm.return_value = True
        
        result = self.ui_controller.confirm("Are you sure?", default=False)
        
        assert result is True
        mock_confirm.assert_called_once_with("Are you sure?", default=False, console=self.mock_console)
    
    def test_get_console_width(self):
        """Test getting console width."""
        width = self.ui_controller.get_console_width()
        assert width == 80
    
    def test_get_console_height(self):
        """Test getting console height."""
        height = self.ui_controller.get_console_height()
        assert height == 24


class TestUIControllerIntegration:
    """Integration tests for UIController with real Rich components."""
    
    def test_real_console_creation(self):
        """Test that UIController creates a working Rich console."""
        ui = UIController()
        
        # Test that we can capture output
        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            ui.print("Test message")
            # The output should contain our message (though with Rich formatting)
            # We just verify that print was called without errors
    
    def test_theme_configuration(self):
        """Test that custom theme is properly configured."""
        ui = UIController()
        
        # Verify we can get custom styles (which means theme is applied)
        error_style = ui.console.get_style("error")
        success_style = ui.console.get_style("success")
        branch_style = ui.console.get_style("branch")
        modified_style = ui.console.get_style("modified")
        
        # These should not be None if the theme is properly applied
        assert error_style is not None
        assert success_style is not None
        assert branch_style is not None
        assert modified_style is not None


class TestUIControllerInteractivePrompts:
    """Test cases for interactive prompt methods."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_console = Mock(spec=Console)
        self.mock_console.size.width = 80
        self.mock_console.size.height = 24
        self.ui_controller = UIController(console=self.mock_console)
    
    @patch('git_worktree_manager.ui_controller.Prompt.ask')
    def test_prompt_branch_name_valid(self, mock_prompt):
        """Test prompting for valid branch name."""
        mock_prompt.return_value = "feature/new-feature"
        
        result = self.ui_controller.prompt_branch_name()
        
        assert result == "feature/new-feature"
        mock_prompt.assert_called_once()
    
    @patch('git_worktree_manager.ui_controller.Prompt.ask')
    def test_prompt_branch_name_with_default(self, mock_prompt):
        """Test prompting for branch name with default value."""
        mock_prompt.return_value = "default-branch"
        
        result = self.ui_controller.prompt_branch_name(default="default-branch")
        
        assert result == "default-branch"
        mock_prompt.assert_called_once()
    
    @patch('git_worktree_manager.ui_controller.Prompt.ask')
    def test_prompt_branch_name_invalid_chars(self, mock_prompt):
        """Test branch name validation with invalid characters."""
        # First call returns invalid name, second call returns valid name
        mock_prompt.side_effect = ["invalid name", "valid-name"]
        
        result = self.ui_controller.prompt_branch_name()
        
        assert result == "valid-name"
        assert mock_prompt.call_count == 2
        # Verify error was displayed
        self.mock_console.print.assert_called()
    
    @patch('git_worktree_manager.ui_controller.Prompt.ask')
    def test_prompt_branch_name_keyboard_interrupt(self, mock_prompt):
        """Test handling keyboard interrupt during branch name prompt."""
        mock_prompt.side_effect = KeyboardInterrupt()
        
        with pytest.raises(KeyboardInterrupt):
            self.ui_controller.prompt_branch_name()
    
    @patch('git_worktree_manager.ui_controller.IntPrompt.ask')
    def test_select_base_branch_valid(self, mock_int_prompt):
        """Test selecting a valid base branch."""
        branches = ["main", "develop", "feature/test"]
        mock_int_prompt.return_value = 2
        
        result = self.ui_controller.select_base_branch(branches, current_branch="main")
        
        assert result == "develop"
        mock_int_prompt.assert_called_once()
        # Verify table was printed
        self.mock_console.print.assert_called()
    
    @patch('git_worktree_manager.ui_controller.IntPrompt.ask')
    def test_select_base_branch_invalid_choice(self, mock_int_prompt):
        """Test selecting invalid branch index."""
        branches = ["main", "develop"]
        # First call returns invalid choice, second call returns valid choice
        mock_int_prompt.side_effect = [5, 1]
        
        result = self.ui_controller.select_base_branch(branches)
        
        assert result == "main"
        assert mock_int_prompt.call_count == 2
    
    def test_select_base_branch_empty_list(self):
        """Test selecting from empty branch list raises error."""
        with pytest.raises(ValueError, match="No branches available"):
            self.ui_controller.select_base_branch([])
    
    @patch('git_worktree_manager.ui_controller.IntPrompt.ask')
    def test_select_base_branch_keyboard_interrupt(self, mock_int_prompt):
        """Test handling keyboard interrupt during branch selection."""
        branches = ["main", "develop"]
        mock_int_prompt.side_effect = KeyboardInterrupt()
        
        with pytest.raises(KeyboardInterrupt):
            self.ui_controller.select_base_branch(branches)
    
    @patch('git_worktree_manager.ui_controller.Prompt.ask')
    @patch('os.path.exists')
    @patch('os.path.abspath')
    @patch('os.path.expanduser')
    def test_select_worktree_location_valid(self, mock_expanduser, mock_abspath, mock_exists, mock_prompt):
        """Test selecting valid worktree location."""
        mock_prompt.return_value = "~/worktrees/test"
        mock_expanduser.return_value = "/home/user/worktrees/test"
        mock_abspath.return_value = "/home/user/worktrees/test"
        mock_exists.return_value = True  # Parent directory exists
        
        result = self.ui_controller.select_worktree_location()
        
        assert result == "/home/user/worktrees/test"
        mock_prompt.assert_called_once()
    
    @patch('git_worktree_manager.ui_controller.Prompt.ask')
    @patch('os.path.exists')
    @patch('os.path.abspath')
    @patch('os.path.expanduser')
    def test_select_worktree_location_with_default(self, mock_expanduser, mock_abspath, mock_exists, mock_prompt):
        """Test selecting worktree location with default path."""
        default_path = "/default/path"
        mock_prompt.return_value = default_path
        mock_expanduser.return_value = default_path
        mock_abspath.return_value = default_path
        mock_exists.return_value = True
        
        result = self.ui_controller.select_worktree_location(default_path=default_path)
        
        assert result == default_path
        mock_prompt.assert_called_once()
    
    @patch('git_worktree_manager.ui_controller.Prompt.ask')
    def test_select_worktree_location_empty_path(self, mock_prompt):
        """Test selecting empty worktree location."""
        # First call returns empty string, second call returns valid path
        mock_prompt.side_effect = ["", "/valid/path"]
        
        with patch('os.path.exists', return_value=True), \
             patch('os.path.abspath', return_value="/valid/path"), \
             patch('os.path.expanduser', return_value="/valid/path"):
            
            result = self.ui_controller.select_worktree_location()
            
            assert result == "/valid/path"
            assert mock_prompt.call_count == 2
    
    @patch('git_worktree_manager.ui_controller.Prompt.ask')
    def test_select_worktree_location_keyboard_interrupt(self, mock_prompt):
        """Test handling keyboard interrupt during location selection."""
        mock_prompt.side_effect = KeyboardInterrupt()
        
        with pytest.raises(KeyboardInterrupt):
            self.ui_controller.select_worktree_location()


class TestUIControllerWorktreeDisplay:
    """Test cases for worktree display methods."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_console = Mock(spec=Console)
        self.mock_console.size.width = 80
        self.mock_console.size.height = 24
        self.ui_controller = UIController(console=self.mock_console)
        
        # Create sample worktree data for testing
        self.sample_worktrees = [
            WorktreeInfo(
                path="/home/user/project",
                branch="main",
                commit_hash="abc123def456",
                commit_message="Initial commit",
                base_branch=None,
                is_bare=False,
                has_uncommitted_changes=False
            ),
            WorktreeInfo(
                path="/home/user/worktrees/feature-branch",
                branch="feature/new-feature",
                commit_hash="def456ghi789",
                commit_message="Add new feature implementation",
                base_branch="main",
                is_bare=False,
                has_uncommitted_changes=True
            ),
            WorktreeInfo(
                path="/home/user/worktrees/bare-repo",
                branch="develop",
                commit_hash="ghi789jkl012",
                commit_message="Development branch",
                base_branch=None,
                is_bare=True,
                has_uncommitted_changes=False
            )
        ]
    
    def test_display_worktree_list_with_worktrees(self):
        """Test displaying a list of worktrees."""
        self.ui_controller.display_worktree_list(self.sample_worktrees)
        
        # Verify console.print was called (for the table)
        self.mock_console.print.assert_called_once()
        
        # Get the table that was printed
        call_args = self.mock_console.print.call_args[0]
        table = call_args[0]
        
        # Verify it's a Table with correct properties
        assert hasattr(table, 'columns')
        assert hasattr(table, 'rows')
    
    def test_display_worktree_list_empty(self):
        """Test displaying empty worktree list."""
        self.ui_controller.display_worktree_list([])
        
        # Should display info message about no worktrees
        self.mock_console.print.assert_called_once()
        call_args = self.mock_console.print.call_args[0]
        panel = call_args[0]
        assert hasattr(panel, 'renderable')
    
    def test_display_worktree_details(self):
        """Test displaying detailed worktree information."""
        worktree = self.sample_worktrees[1]  # Feature branch with changes
        
        self.ui_controller.display_worktree_details(worktree)
        
        # Verify console.print was called with a Panel
        self.mock_console.print.assert_called_once()
        call_args = self.mock_console.print.call_args[0]
        panel = call_args[0]
        
        # Verify it's a Panel
        assert hasattr(panel, 'renderable')
        assert hasattr(panel, 'title')
    
    def test_display_worktree_details_bare_repo(self):
        """Test displaying details for bare repository."""
        worktree = self.sample_worktrees[2]  # Bare repository
        
        self.ui_controller.display_worktree_details(worktree)
        
        # Verify console.print was called
        self.mock_console.print.assert_called_once()
        call_args = self.mock_console.print.call_args[0]
        panel = call_args[0]
        assert hasattr(panel, 'renderable')
    
    def test_display_worktree_summary(self):
        """Test displaying worktree summary statistics."""
        self.ui_controller.display_worktree_summary(self.sample_worktrees)
        
        # Verify console.print was called with a Panel
        self.mock_console.print.assert_called_once()
        call_args = self.mock_console.print.call_args[0]
        panel = call_args[0]
        
        # Verify it's a Panel
        assert hasattr(panel, 'renderable')
        assert hasattr(panel, 'title')
    
    def test_display_worktree_summary_empty(self):
        """Test displaying summary for empty worktree list."""
        self.ui_controller.display_worktree_summary([])
        
        # Should not print anything for empty list
        self.mock_console.print.assert_not_called()
    
    @patch('os.path.expanduser')
    def test_display_worktree_list_path_formatting(self, mock_expanduser):
        """Test that paths are formatted relative to home directory."""
        mock_expanduser.return_value = "/home/user"
        
        # Create worktree with path under home directory
        worktree = WorktreeInfo(
            path="/home/user/projects/test",
            branch="test",
            commit_hash="abc123",
            commit_message="Test commit",
            has_uncommitted_changes=False
        )
        
        self.ui_controller.display_worktree_list([worktree])
        
        # Verify console.print was called
        self.mock_console.print.assert_called_once()
        mock_expanduser.assert_called()
    
    def test_display_worktree_details_long_commit_message(self):
        """Test that long commit messages are truncated."""
        long_message = "This is a very long commit message that should be truncated because it exceeds the maximum length"
        worktree = WorktreeInfo(
            path="/test/path",
            branch="test",
            commit_hash="abc123def456",
            commit_message=long_message,
            has_uncommitted_changes=False
        )
        
        self.ui_controller.display_worktree_details(worktree)
        
        # Verify console.print was called
        self.mock_console.print.assert_called_once()
    
    def test_display_worktree_summary_statistics(self):
        """Test that summary calculates statistics correctly."""
        # Test with known data: 3 total, 1 modified, 2 clean, 1 bare
        self.ui_controller.display_worktree_summary(self.sample_worktrees)
        
        # Verify console.print was called
        self.mock_console.print.assert_called_once()
        call_args = self.mock_console.print.call_args[0]
        panel = call_args[0]
        assert hasattr(panel, 'renderable')


class TestUIControllerDiffVisualization:
    """Test cases for diff summary visualization methods."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_console = Mock(spec=Console)
        self.mock_console.size.width = 80
        self.mock_console.size.height = 24
        self.ui_controller = UIController(console=self.mock_console)
        
        # Create sample diff summary data for testing
        self.sample_diff = DiffSummary(
            files_modified=3,
            files_added=2,
            files_deleted=1,
            total_insertions=150,
            total_deletions=75,
            summary_text="Modified core functionality and added tests"
        )
        
        self.empty_diff = DiffSummary(
            files_modified=0,
            files_added=0,
            files_deleted=0,
            total_insertions=0,
            total_deletions=0,
            summary_text=""
        )
    
    def test_display_diff_summary_with_changes(self):
        """Test displaying diff summary with changes."""
        self.ui_controller.display_diff_summary(
            self.sample_diff, 
            worktree_branch="feature/test", 
            base_branch="main"
        )
        
        # Verify console.print was called with a Panel
        self.mock_console.print.assert_called_once()
        call_args = self.mock_console.print.call_args[0]
        panel = call_args[0]
        assert hasattr(panel, 'renderable')
        assert hasattr(panel, 'title')
    
    def test_display_diff_summary_no_changes(self):
        """Test displaying diff summary with no changes."""
        self.ui_controller.display_diff_summary(self.empty_diff)
        
        # Verify console.print was called
        self.mock_console.print.assert_called_once()
        call_args = self.mock_console.print.call_args[0]
        panel = call_args[0]
        assert hasattr(panel, 'renderable')
    
    def test_display_diff_summary_none(self):
        """Test displaying None diff summary."""
        self.ui_controller.display_diff_summary(None)
        
        # Should display info message
        self.mock_console.print.assert_called_once()
        call_args = self.mock_console.print.call_args[0]
        panel = call_args[0]
        assert hasattr(panel, 'renderable')
    
    def test_display_diff_summary_compact_with_changes(self):
        """Test compact diff summary with changes."""
        result = self.ui_controller.display_diff_summary_compact(self.sample_diff)
        
        # Should contain formatted change indicators
        assert "[added]" in result
        assert "[modified]" in result
        assert "[deleted]" in result
        assert "+2" in result  # 2 files added
        assert "~3" in result  # 3 files modified
        assert "-1" in result  # 1 file deleted
    
    def test_display_diff_summary_compact_no_changes(self):
        """Test compact diff summary with no changes."""
        result = self.ui_controller.display_diff_summary_compact(self.empty_diff)
        
        assert result == "[unchanged]no changes[/unchanged]"
    
    def test_display_diff_summary_compact_none(self):
        """Test compact diff summary with None input."""
        result = self.ui_controller.display_diff_summary_compact(None)
        
        assert result == "[dim]no diff[/dim]"
    
    def test_display_diff_visualization_with_changes(self):
        """Test diff visualization with changes."""
        self.ui_controller.display_diff_visualization(self.sample_diff, max_width=20)
        
        # Verify console.print was called with visualization
        self.mock_console.print.assert_called_once()
        call_args = self.mock_console.print.call_args[0]
        panel = call_args[0]
        assert hasattr(panel, 'renderable')
    
    def test_display_diff_visualization_no_changes(self):
        """Test diff visualization with no changes."""
        self.ui_controller.display_diff_visualization(self.empty_diff)
        
        # Should print message about no changes
        self.mock_console.print.assert_called_once()
    
    def test_display_diff_visualization_none(self):
        """Test diff visualization with None input."""
        self.ui_controller.display_diff_visualization(None)
        
        # Should not print anything
        self.mock_console.print.assert_not_called()
    
    def test_display_diff_visualization_scaling(self):
        """Test diff visualization with scaling for large numbers."""
        large_diff = DiffSummary(
            files_modified=0,
            files_added=0,
            files_deleted=0,
            total_insertions=1000,
            total_deletions=500,
            summary_text=""
        )
        
        self.ui_controller.display_diff_visualization(large_diff, max_width=10)
        
        # Should scale down and still display
        self.mock_console.print.assert_called_once()
    
    def test_display_file_change_indicators_all_types(self):
        """Test file change indicators with all change types."""
        result = self.ui_controller.display_file_change_indicators(
            files_added=3,
            files_modified=2,
            files_deleted=1
        )
        
        # Should contain all indicator types
        assert "[added]" in result
        assert "[modified]" in result
        assert "[deleted]" in result
        assert "●●●" in result  # 3 added files
        assert "◐◐" in result   # 2 modified files
        assert "○" in result     # 1 deleted file
    
    def test_display_file_change_indicators_many_files(self):
        """Test file change indicators with many files (should show overflow)."""
        result = self.ui_controller.display_file_change_indicators(
            files_added=10,
            files_modified=0,
            files_deleted=0
        )
        
        # Should show 5 symbols plus overflow indicator
        assert "●●●●●" in result
        assert "(+5)" in result
    
    def test_display_file_change_indicators_no_changes(self):
        """Test file change indicators with no changes."""
        result = self.ui_controller.display_file_change_indicators(
            files_added=0,
            files_modified=0,
            files_deleted=0
        )
        
        assert result == "[unchanged]no changes[/unchanged]"
    
    def test_display_file_change_indicators_partial_changes(self):
        """Test file change indicators with only some change types."""
        result = self.ui_controller.display_file_change_indicators(
            files_added=2,
            files_modified=0,
            files_deleted=3
        )
        
        # Should only show added and deleted, not modified
        assert "[added]" in result
        assert "[deleted]" in result
        assert "[modified]" not in result
        assert "●●" in result
        assert "○○○" in result
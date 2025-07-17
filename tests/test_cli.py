"""Unit tests for CLI module."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from click.testing import CliRunner

from git_worktree_manager.cli import cli, GitWorktreeCLI, main
from git_worktree_manager.git_ops import GitRepositoryError


class TestGitWorktreeCLI:
    """Test cases for GitWorktreeCLI class."""
    
    def test_init(self):
        """Test CLI initialization."""
        cli_instance = GitWorktreeCLI()
        assert cli_instance.git_ops is not None
    
    @patch('git_worktree_manager.cli.GitOperations')
    def test_validate_git_repository_success(self, mock_git_ops):
        """Test successful Git repository validation."""
        # Setup mock
        mock_git_instance = Mock()
        mock_git_instance.is_git_repository.return_value = True
        mock_git_ops.return_value = mock_git_instance
        
        cli_instance = GitWorktreeCLI()
        result = cli_instance.validate_git_repository()
        
        assert result is True
        mock_git_instance.is_git_repository.assert_called_once()
    
    @patch('git_worktree_manager.cli.GitOperations')
    @patch('git_worktree_manager.cli.console')
    def test_validate_git_repository_failure(self, mock_console, mock_git_ops):
        """Test Git repository validation failure."""
        # Setup mock
        mock_git_instance = Mock()
        mock_git_instance.is_git_repository.side_effect = GitRepositoryError("Not a git repository")
        mock_git_ops.return_value = mock_git_instance
        
        cli_instance = GitWorktreeCLI()
        result = cli_instance.validate_git_repository()
        
        assert result is False
        mock_git_instance.is_git_repository.assert_called_once()
        mock_console.print.assert_called_once_with("[red]Error:[/red] Not a git repository")
    
    @patch('git_worktree_manager.cli.GitOperations')
    def test_validate_git_repository_not_git_repo(self, mock_git_ops):
        """Test validation when not in a Git repository."""
        # Setup mock
        mock_git_instance = Mock()
        mock_git_instance.is_git_repository.return_value = False
        mock_git_ops.return_value = mock_git_instance
        
        cli_instance = GitWorktreeCLI()
        result = cli_instance.validate_git_repository()
        
        assert result is False
        mock_git_instance.is_git_repository.assert_called_once()


class TestCLICommands:
    """Test cases for CLI commands."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()
    
    @patch('git_worktree_manager.cli.GitWorktreeCLI.validate_git_repository')
    def test_cli_no_command_shows_help(self, mock_validate):
        """Test that CLI shows help when no command is provided."""
        mock_validate.return_value = True
        
        result = self.runner.invoke(cli, [])
        
        assert result.exit_code == 0
        assert "Git Worktree Manager" in result.output
        assert "Available commands:" in result.output
        assert "create" in result.output
        assert "list" in result.output
        assert "configure" in result.output
    
    @patch('git_worktree_manager.cli.GitWorktreeCLI.validate_git_repository')
    def test_cli_help_command(self, mock_validate):
        """Test CLI help command."""
        mock_validate.return_value = True
        
        result = self.runner.invoke(cli, ['--help'])
        
        assert result.exit_code == 0
        assert "Git Worktree Manager" in result.output
        assert "Interactive CLI tool" in result.output
    
    @patch('git_worktree_manager.worktree_manager.WorktreeManager')
    @patch('git_worktree_manager.cli.GitWorktreeCLI.validate_git_repository')
    def test_create_command_basic_functionality(self, mock_validate, mock_worktree_manager):
        """Test create command basic functionality."""
        from git_worktree_manager.models import WorktreeInfo
        
        mock_validate.return_value = True
        mock_manager_instance = Mock()
        mock_worktree_info = WorktreeInfo(
            path="/test/path",
            branch="test-branch",
            commit_hash="abc123",
            commit_message="Test commit",
            base_branch="main"
        )
        mock_manager_instance.create_worktree.return_value = mock_worktree_info
        mock_worktree_manager.return_value = mock_manager_instance
        
        result = self.runner.invoke(cli, ['create'])
        
        assert result.exit_code == 0
        assert "Creating New Worktree" in result.output
    
    @patch('git_worktree_manager.worktree_manager.WorktreeManager')
    @patch('git_worktree_manager.cli.GitWorktreeCLI.validate_git_repository')
    def test_list_command_basic_functionality(self, mock_validate, mock_worktree_manager):
        """Test list command basic functionality."""
        from git_worktree_manager.models import WorktreeInfo
        
        mock_validate.return_value = True
        mock_manager_instance = Mock()
        mock_worktrees = [
            WorktreeInfo(
                path="/test/path",
                branch="main",
                commit_hash="abc123",
                commit_message="Test commit",
                base_branch=None
            )
        ]
        mock_manager_instance.list_worktrees.return_value = mock_worktrees
        mock_manager_instance.ui_controller = Mock()
        mock_worktree_manager.return_value = mock_manager_instance
        
        result = self.runner.invoke(cli, ['list'])
        
        assert result.exit_code == 0
        assert "Git Worktrees" in result.output
    
    @patch('git_worktree_manager.config.ConfigManager')
    @patch('git_worktree_manager.cli.GitWorktreeCLI.validate_git_repository')
    def test_configure_command_basic_functionality(self, mock_validate, mock_config_manager):
        """Test configure command basic functionality."""
        mock_validate.return_value = True
        mock_config_instance = Mock()
        mock_config_instance.get_default_worktree_location.return_value = '/test/path'
        mock_config_instance.load_user_preferences.return_value = {}
        mock_config_manager.return_value = mock_config_instance
        
        result = self.runner.invoke(cli, ['configure'], input='n\n')
        
        assert result.exit_code == 0
        assert "Worktree Configuration" in result.output
    
    @patch('git_worktree_manager.cli.GitWorktreeCLI.validate_git_repository')
    def test_git_repository_validation_failure(self, mock_validate):
        """Test command execution when not in Git repository."""
        mock_validate.return_value = False
        
        result = self.runner.invoke(cli, ['create'])
        
        assert result.exit_code == 1
        assert "Not in a Git repository" in result.output
        assert "git init" in result.output
    
    @patch('git_worktree_manager.cli.GitWorktreeCLI.validate_git_repository')
    def test_create_command_help(self, mock_validate):
        """Test create command help."""
        mock_validate.return_value = True
        
        result = self.runner.invoke(cli, ['create', '--help'])
        
        assert result.exit_code == 0
        assert "Create a new worktree interactively" in result.output
        assert "branch name" in result.output
    
    @patch('git_worktree_manager.cli.GitWorktreeCLI.validate_git_repository')
    def test_list_command_help(self, mock_validate):
        """Test list command help."""
        mock_validate.return_value = True
        
        result = self.runner.invoke(cli, ['list', '--help'])
        
        assert result.exit_code == 0
        assert "List all worktrees" in result.output
        assert "status information" in result.output
    
    @patch('git_worktree_manager.cli.GitWorktreeCLI.validate_git_repository')
    def test_configure_command_help(self, mock_validate):
        """Test configure command help."""
        mock_validate.return_value = True
        
        result = self.runner.invoke(cli, ['configure', '--help'])
        
        assert result.exit_code == 0
        assert "Configure worktree preferences" in result.output
        assert "storage locations" in result.output


class TestMainFunction:
    """Test cases for main function."""
    
    @patch('git_worktree_manager.cli.cli')
    def test_main_no_args(self, mock_cli):
        """Test main function with no arguments."""
        mock_cli.return_value = None
        
        result = main()
        
        assert result == 0
        mock_cli.assert_called_once_with()
    
    @patch('git_worktree_manager.cli.cli')
    def test_main_with_args(self, mock_cli):
        """Test main function with arguments."""
        mock_cli.return_value = None
        test_args = ['create']
        
        result = main(test_args)
        
        assert result == 0
        mock_cli.assert_called_once_with(test_args)
    
    @patch('git_worktree_manager.cli.cli')
    def test_main_click_exception(self, mock_cli):
        """Test main function handling Click exceptions."""
        from click import ClickException
        
        mock_exception = ClickException("Test error")
        mock_exception.exit_code = 2
        mock_exception.show = Mock()
        mock_cli.side_effect = mock_exception
        
        result = main()
        
        assert result == 2
        mock_exception.show.assert_called_once()
    
    @patch('git_worktree_manager.cli.cli')
    @patch('git_worktree_manager.cli.console')
    def test_main_keyboard_interrupt(self, mock_console, mock_cli):
        """Test main function handling keyboard interrupt."""
        mock_cli.side_effect = KeyboardInterrupt()
        
        result = main()
        
        assert result == 1
        mock_console.print.assert_called_once_with("\n[yellow]Operation cancelled by user.[/yellow]")
    
    @patch('git_worktree_manager.cli.cli')
    @patch('git_worktree_manager.cli.console')
    def test_main_unexpected_exception(self, mock_console, mock_cli):
        """Test main function handling unexpected exceptions."""
        mock_cli.side_effect = Exception("Unexpected error")
        
        result = main()
        
        assert result == 1
        mock_console.print.assert_called_once_with("[red]Unexpected error:[/red] Unexpected error")


class TestCLIIntegration:
    """Integration tests for CLI functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()
    
    @patch('git_worktree_manager.worktree_manager.WorktreeManager')
    @patch('git_worktree_manager.cli.GitOperations')
    def test_full_cli_workflow_valid_repo(self, mock_git_ops, mock_worktree_manager):
        """Test full CLI workflow in a valid Git repository."""
        from git_worktree_manager.models import WorktreeInfo
        
        # Setup mocks
        mock_git_instance = Mock()
        mock_git_instance.is_git_repository.return_value = True
        mock_git_ops.return_value = mock_git_instance
        
        mock_manager_instance = Mock()
        mock_worktrees = [
            WorktreeInfo(
                path="/test/path",
                branch="main",
                commit_hash="abc123",
                commit_message="Test commit",
                base_branch=None
            )
        ]
        mock_manager_instance.list_worktrees.return_value = mock_worktrees
        mock_manager_instance.ui_controller = Mock()
        mock_worktree_manager.return_value = mock_manager_instance
        
        # Test help display
        result = self.runner.invoke(cli, [])
        assert result.exit_code == 0
        assert "Git Worktree Manager" in result.output
        
        # Test list command
        result = self.runner.invoke(cli, ['list'])
        assert result.exit_code == 0
        assert "Git Worktrees" in result.output
        
        # Test configure command (with mock to avoid interactive input)
        with patch('git_worktree_manager.config.ConfigManager') as mock_config_manager:
            mock_config_instance = Mock()
            mock_config_instance.get_default_worktree_location.return_value = '/test/path'
            mock_config_instance.load_user_preferences.return_value = {}
            mock_config_manager.return_value = mock_config_instance
            
            result = self.runner.invoke(cli, ['configure'], input='n\n')
            assert result.exit_code == 0
            assert "Worktree Configuration" in result.output
    
    @patch('git_worktree_manager.cli.GitOperations')
    def test_full_cli_workflow_invalid_repo(self, mock_git_ops):
        """Test full CLI workflow in an invalid Git repository."""
        # Setup mock
        mock_git_instance = Mock()
        mock_git_instance.is_git_repository.return_value = False
        mock_git_ops.return_value = mock_git_instance
        
        # Test that commands fail with proper error message
        for command in ['create', 'list', 'configure']:
            result = self.runner.invoke(cli, [command])
            assert result.exit_code == 1
            assert "Not in a Git repository" in result.output
    
    @patch('git_worktree_manager.cli.GitOperations')
    def test_cli_with_git_error(self, mock_git_ops):
        """Test CLI behavior when Git operations raise errors."""
        # Setup mock
        mock_git_instance = Mock()
        mock_git_instance.is_git_repository.side_effect = GitRepositoryError("Git not found")
        mock_git_ops.return_value = mock_git_instance
        
        # Test that commands fail gracefully
        result = self.runner.invoke(cli, ['create'])
        assert result.exit_code == 1
        # The error should be handled by validate_git_repository method


class TestCreateCommand:
    """Test cases for the create command."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()
    
    @patch('git_worktree_manager.worktree_manager.WorktreeManager')
    @patch('git_worktree_manager.cli.GitWorktreeCLI.validate_git_repository')
    def test_create_command_success(self, mock_validate, mock_worktree_manager):
        """Test successful worktree creation."""
        from git_worktree_manager.models import WorktreeInfo
        
        # Setup mocks
        mock_validate.return_value = True
        mock_manager_instance = Mock()
        mock_worktree_info = WorktreeInfo(
            path="/test/path",
            branch="feature-branch",
            commit_hash="abc123",
            commit_message="Test commit",
            base_branch="main"
        )
        mock_manager_instance.create_worktree.return_value = mock_worktree_info
        mock_worktree_manager.return_value = mock_manager_instance
        
        # Run command
        result = self.runner.invoke(cli, ['create'])
        
        # Verify results
        assert result.exit_code == 0
        assert "Creating New Worktree" in result.output
        assert "Worktree Created Successfully" in result.output
        assert "feature-branch" in result.output
        assert "/test/path" in result.output
        mock_manager_instance.create_worktree.assert_called_once()
    
    @patch('git_worktree_manager.worktree_manager.WorktreeManager')
    @patch('git_worktree_manager.cli.GitWorktreeCLI.validate_git_repository')
    def test_create_command_worktree_creation_error(self, mock_validate, mock_worktree_manager):
        """Test worktree creation error handling."""
        from git_worktree_manager.worktree_manager import WorktreeCreationError
        
        # Setup mocks
        mock_validate.return_value = True
        mock_manager_instance = Mock()
        mock_manager_instance.create_worktree.side_effect = WorktreeCreationError("Creation failed")
        mock_worktree_manager.return_value = mock_manager_instance
        
        # Run command
        result = self.runner.invoke(cli, ['create'])
        
        # Verify results
        assert result.exit_code == 1
        assert "Failed to create worktree" in result.output
        assert "Creation failed" in result.output
    
    @patch('git_worktree_manager.worktree_manager.WorktreeManager')
    @patch('git_worktree_manager.cli.GitWorktreeCLI.validate_git_repository')
    def test_create_command_keyboard_interrupt(self, mock_validate, mock_worktree_manager):
        """Test keyboard interrupt handling during creation."""
        # Setup mocks
        mock_validate.return_value = True
        mock_manager_instance = Mock()
        mock_manager_instance.create_worktree.side_effect = KeyboardInterrupt()
        mock_worktree_manager.return_value = mock_manager_instance
        
        # Run command
        result = self.runner.invoke(cli, ['create'])
        
        # Verify results
        assert result.exit_code == 1
        assert "cancelled by user" in result.output
    
    @patch('git_worktree_manager.worktree_manager.WorktreeManager')
    @patch('git_worktree_manager.cli.GitWorktreeCLI.validate_git_repository')
    def test_create_command_unexpected_error(self, mock_validate, mock_worktree_manager):
        """Test unexpected error handling during creation."""
        # Setup mocks
        mock_validate.return_value = True
        mock_manager_instance = Mock()
        mock_manager_instance.create_worktree.side_effect = Exception("Unexpected error")
        mock_worktree_manager.return_value = mock_manager_instance
        
        # Run command
        result = self.runner.invoke(cli, ['create'])
        
        # Verify results
        assert result.exit_code == 1
        assert "Unexpected error" in result.output
    
    @patch('git_worktree_manager.cli.GitWorktreeCLI.validate_git_repository')
    def test_create_command_invalid_repo(self, mock_validate):
        """Test create command in invalid Git repository."""
        mock_validate.return_value = False
        
        result = self.runner.invoke(cli, ['create'])
        
        assert result.exit_code == 1
        assert "Not in a Git repository" in result.output


class TestListCommand:
    """Test cases for the list command."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()
    
    @patch('git_worktree_manager.worktree_manager.WorktreeManager')
    @patch('git_worktree_manager.cli.GitWorktreeCLI.validate_git_repository')
    def test_list_command_success(self, mock_validate, mock_worktree_manager):
        """Test successful worktree listing."""
        from git_worktree_manager.models import WorktreeInfo
        
        # Setup mocks
        mock_validate.return_value = True
        mock_manager_instance = Mock()
        mock_worktrees = [
            WorktreeInfo(
                path="/test/path1",
                branch="main",
                commit_hash="abc123",
                commit_message="Main commit",
                base_branch=None
            ),
            WorktreeInfo(
                path="/test/path2",
                branch="feature-branch",
                commit_hash="def456",
                commit_message="Feature commit",
                base_branch="main"
            )
        ]
        mock_manager_instance.list_worktrees.return_value = mock_worktrees
        mock_manager_instance.ui_controller = Mock()
        mock_worktree_manager.return_value = mock_manager_instance
        
        # Run command
        result = self.runner.invoke(cli, ['list'])
        
        # Verify results
        assert result.exit_code == 0
        assert "Git Worktrees" in result.output
        assert "Loading worktree information" in result.output
        mock_manager_instance.list_worktrees.assert_called_once()
        mock_manager_instance.ui_controller.display_worktree_summary.assert_called_once()
        mock_manager_instance.ui_controller.display_worktree_list.assert_called_once()
    
    @patch('git_worktree_manager.worktree_manager.WorktreeManager')
    @patch('git_worktree_manager.cli.GitWorktreeCLI.validate_git_repository')
    def test_list_command_no_worktrees(self, mock_validate, mock_worktree_manager):
        """Test list command when no worktrees exist."""
        # Setup mocks
        mock_validate.return_value = True
        mock_manager_instance = Mock()
        mock_manager_instance.list_worktrees.return_value = []
        mock_worktree_manager.return_value = mock_manager_instance
        
        # Run command
        result = self.runner.invoke(cli, ['list'])
        
        # Verify results
        assert result.exit_code == 0
        assert "No worktrees found" in result.output
        assert "create" in result.output
    
    @patch('git_worktree_manager.worktree_manager.WorktreeManager')
    @patch('git_worktree_manager.cli.GitWorktreeCLI.validate_git_repository')
    def test_list_command_with_details(self, mock_validate, mock_worktree_manager):
        """Test list command with details flag."""
        from git_worktree_manager.models import WorktreeInfo
        
        # Setup mocks
        mock_validate.return_value = True
        mock_manager_instance = Mock()
        mock_worktrees = [
            WorktreeInfo(
                path="/test/path1",
                branch="main",
                commit_hash="abc123",
                commit_message="Main commit",
                base_branch=None
            )
        ]
        mock_manager_instance.list_worktrees.return_value = mock_worktrees
        mock_manager_instance.ui_controller = Mock()
        mock_worktree_manager.return_value = mock_manager_instance
        
        # Run command
        result = self.runner.invoke(cli, ['list', '--details'])
        
        # Verify results
        assert result.exit_code == 0
        assert "Detailed Information" in result.output
        mock_manager_instance.ui_controller.display_worktree_details.assert_called()
    
    @patch('git_worktree_manager.worktree_manager.WorktreeManager')
    @patch('git_worktree_manager.cli.GitWorktreeCLI.validate_git_repository')
    def test_list_command_with_diff(self, mock_validate, mock_worktree_manager):
        """Test list command with diff flag."""
        from git_worktree_manager.models import WorktreeInfo, DiffSummary
        
        # Setup mocks
        mock_validate.return_value = True
        mock_manager_instance = Mock()
        mock_worktrees = [
            WorktreeInfo(
                path="/test/path1",
                branch="feature-branch",
                commit_hash="abc123",
                commit_message="Feature commit",
                base_branch="main"
            )
        ]
        mock_diff_summary = DiffSummary(
            files_modified=2,
            files_added=1,
            files_deleted=0,
            total_insertions=10,
            total_deletions=5,
            summary_text="+10 -5"
        )
        mock_manager_instance.list_worktrees.return_value = mock_worktrees
        mock_manager_instance.calculate_diff_summary.return_value = mock_diff_summary
        mock_manager_instance.ui_controller = Mock()
        mock_worktree_manager.return_value = mock_manager_instance
        
        # Run command
        result = self.runner.invoke(cli, ['list', '--diff'])
        
        # Verify results
        assert result.exit_code == 0
        assert "Diff Summaries" in result.output
        mock_manager_instance.calculate_diff_summary.assert_called()
        mock_manager_instance.ui_controller.display_diff_summary.assert_called()
    
    @patch('git_worktree_manager.worktree_manager.WorktreeManager')
    @patch('git_worktree_manager.cli.GitWorktreeCLI.validate_git_repository')
    def test_list_command_git_error(self, mock_validate, mock_worktree_manager):
        """Test list command with Git error."""
        from git_worktree_manager.git_ops import GitRepositoryError
        
        # Setup mocks
        mock_validate.return_value = True
        mock_manager_instance = Mock()
        mock_manager_instance.list_worktrees.side_effect = GitRepositoryError("Git error")
        mock_worktree_manager.return_value = mock_manager_instance
        
        # Run command
        result = self.runner.invoke(cli, ['list'])
        
        # Verify results
        assert result.exit_code == 1
        assert "Git operation failed" in result.output
        assert "Git error" in result.output
    
    @patch('git_worktree_manager.worktree_manager.WorktreeManager')
    @patch('git_worktree_manager.cli.GitWorktreeCLI.validate_git_repository')
    def test_list_command_keyboard_interrupt(self, mock_validate, mock_worktree_manager):
        """Test list command with keyboard interrupt."""
        # Setup mocks
        mock_validate.return_value = True
        mock_manager_instance = Mock()
        mock_manager_instance.list_worktrees.side_effect = KeyboardInterrupt()
        mock_worktree_manager.return_value = mock_manager_instance
        
        # Run command
        result = self.runner.invoke(cli, ['list'])
        
        # Verify results
        assert result.exit_code == 1
        assert "cancelled by user" in result.output
    
    @patch('git_worktree_manager.worktree_manager.WorktreeManager')
    @patch('git_worktree_manager.cli.GitWorktreeCLI.validate_git_repository')
    def test_list_command_unexpected_error(self, mock_validate, mock_worktree_manager):
        """Test list command with unexpected error."""
        # Setup mocks
        mock_validate.return_value = True
        mock_manager_instance = Mock()
        mock_manager_instance.list_worktrees.side_effect = Exception("Unexpected error")
        mock_worktree_manager.return_value = mock_manager_instance
        
        # Run command
        result = self.runner.invoke(cli, ['list'])
        
        # Verify results
        assert result.exit_code == 1
        assert "Unexpected error" in result.output
    
    @patch('git_worktree_manager.cli.GitWorktreeCLI.validate_git_repository')
    def test_list_command_invalid_repo(self, mock_validate):
        """Test list command in invalid Git repository."""
        mock_validate.return_value = False
        
        result = self.runner.invoke(cli, ['list'])
        
        assert result.exit_code == 1
        assert "Not in a Git repository" in result.output


class TestConfigureCommand:
    """Test cases for the configure command."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()
    
    @patch('git_worktree_manager.config.ConfigManager')
    @patch('git_worktree_manager.cli.GitWorktreeCLI.validate_git_repository')
    def test_configure_command_show(self, mock_validate, mock_config_manager):
        """Test configure command with show flag."""
        # Setup mocks
        mock_validate.return_value = True
        mock_config_instance = Mock()
        mock_config_instance.load_user_preferences.return_value = {
            'default_worktree_location': '/test/path'
        }
        mock_config_instance.get_default_worktree_location.return_value = '/test/path'
        mock_config_manager.return_value = mock_config_instance
        
        # Run command
        result = self.runner.invoke(cli, ['configure', '--show'])
        
        # Verify results
        assert result.exit_code == 0
        assert "Current Configuration" in result.output
        assert "/test/path" in result.output
        mock_config_instance.load_user_preferences.assert_called_once()
        mock_config_instance.get_default_worktree_location.assert_called_once()
    
    @patch('git_worktree_manager.config.ConfigManager')
    @patch('git_worktree_manager.cli.GitWorktreeCLI.validate_git_repository')
    def test_configure_command_reset_confirmed(self, mock_validate, mock_config_manager):
        """Test configure command with reset flag (confirmed)."""
        # Setup mocks
        mock_validate.return_value = True
        mock_config_instance = Mock()
        mock_config_manager.return_value = mock_config_instance
        
        # Run command with 'y' input for confirmation
        result = self.runner.invoke(cli, ['configure', '--reset'], input='y\n')
        
        # Verify results
        assert result.exit_code == 0
        assert "Configuration reset to defaults successfully" in result.output
        mock_config_instance.save_user_preferences.assert_called_once_with({})
    
    @patch('git_worktree_manager.config.ConfigManager')
    @patch('git_worktree_manager.cli.GitWorktreeCLI.validate_git_repository')
    def test_configure_command_reset_cancelled(self, mock_validate, mock_config_manager):
        """Test configure command with reset flag (cancelled)."""
        # Setup mocks
        mock_validate.return_value = True
        mock_config_instance = Mock()
        mock_config_manager.return_value = mock_config_instance
        
        # Run command with 'n' input for confirmation
        result = self.runner.invoke(cli, ['configure', '--reset'], input='n\n')
        
        # Verify results
        assert result.exit_code == 0
        assert "Configuration reset cancelled" in result.output
        mock_config_instance.save_user_preferences.assert_not_called()
    
    @patch('git_worktree_manager.config.ConfigManager')
    @patch('git_worktree_manager.cli.GitWorktreeCLI.validate_git_repository')
    def test_configure_command_interactive_no_change(self, mock_validate, mock_config_manager):
        """Test interactive configure command with no changes."""
        # Setup mocks
        mock_validate.return_value = True
        mock_config_instance = Mock()
        mock_config_instance.get_default_worktree_location.return_value = '/current/path'
        mock_config_instance.load_user_preferences.return_value = {}
        mock_config_manager.return_value = mock_config_instance
        
        # Run command with 'n' input (don't change location)
        result = self.runner.invoke(cli, ['configure'], input='n\n')
        
        # Verify results
        assert result.exit_code == 0
        assert "Current default worktree location" in result.output
        assert "/current/path" in result.output
        assert "Configuration updated successfully" in result.output
    
    @patch('os.path.exists')
    @patch('pathlib.Path.mkdir')
    @patch('git_worktree_manager.config.ConfigManager')
    @patch('git_worktree_manager.cli.GitWorktreeCLI.validate_git_repository')
    def test_configure_command_interactive_change_location(self, mock_validate, mock_config_manager, mock_mkdir, mock_exists):
        """Test interactive configure command with location change."""
        # Setup mocks
        mock_validate.return_value = True
        mock_config_instance = Mock()
        mock_config_instance.get_default_worktree_location.return_value = '/current/path'
        mock_config_instance.load_user_preferences.return_value = {}
        mock_config_manager.return_value = mock_config_instance
        mock_exists.return_value = True  # Parent directory exists
        
        # Run command with 'y' to change location and provide new path
        result = self.runner.invoke(cli, ['configure'], input='y\n/new/path\n')
        
        # Verify results
        assert result.exit_code == 0
        assert "Would you like to change" in result.output
        mock_config_instance.save_user_preferences.assert_called()
    
    @patch('git_worktree_manager.config.ConfigManager')
    @patch('git_worktree_manager.cli.GitWorktreeCLI.validate_git_repository')
    def test_configure_command_config_error(self, mock_validate, mock_config_manager):
        """Test configure command with configuration error."""
        from git_worktree_manager.config import ConfigError
        
        # Setup mocks
        mock_validate.return_value = True
        mock_config_instance = Mock()
        mock_config_instance.load_user_preferences.side_effect = ConfigError("Config error")
        mock_config_manager.return_value = mock_config_instance
        
        # Run command
        result = self.runner.invoke(cli, ['configure', '--show'])
        
        # Verify results
        assert result.exit_code == 1
        assert "Error loading configuration" in result.output
        assert "Config error" in result.output
    
    @patch('git_worktree_manager.config.ConfigManager')
    @patch('git_worktree_manager.cli.GitWorktreeCLI.validate_git_repository')
    def test_configure_command_keyboard_interrupt(self, mock_validate, mock_config_manager):
        """Test configure command with keyboard interrupt."""
        # Setup mocks
        mock_validate.return_value = True
        mock_config_instance = Mock()
        mock_config_instance.get_default_worktree_location.return_value = '/current/path'
        mock_config_instance.load_user_preferences.return_value = {}
        mock_config_manager.return_value = mock_config_instance
        
        # Simulate keyboard interrupt during input
        with patch('rich.prompt.Confirm.ask', side_effect=KeyboardInterrupt()):
            result = self.runner.invoke(cli, ['configure'])
        
        # Verify results
        assert result.exit_code == 1
        assert "cancelled by user" in result.output
    
    @patch('git_worktree_manager.config.ConfigManager')
    @patch('git_worktree_manager.cli.GitWorktreeCLI.validate_git_repository')
    def test_configure_command_unexpected_error(self, mock_validate, mock_config_manager):
        """Test configure command with unexpected error."""
        # Setup mocks
        mock_validate.return_value = True
        mock_config_instance = Mock()
        mock_config_instance.get_default_worktree_location.side_effect = Exception("Unexpected error")
        mock_config_manager.return_value = mock_config_instance
        
        # Run command
        result = self.runner.invoke(cli, ['configure'])
        
        # Verify results
        assert result.exit_code == 1
        assert "Unexpected error" in result.output
    
    @patch('git_worktree_manager.cli.GitWorktreeCLI.validate_git_repository')
    def test_configure_command_invalid_repo(self, mock_validate):
        """Test configure command in invalid Git repository."""
        mock_validate.return_value = False
        
        result = self.runner.invoke(cli, ['configure'])
        
        assert result.exit_code == 1
        assert "Not in a Git repository" in result.output
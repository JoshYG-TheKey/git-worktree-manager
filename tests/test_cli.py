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
    
    @patch('git_worktree_manager.cli.GitWorktreeCLI.validate_git_repository')
    def test_create_command_placeholder(self, mock_validate):
        """Test create command placeholder."""
        mock_validate.return_value = True
        
        result = self.runner.invoke(cli, ['create'])
        
        assert result.exit_code == 0
        assert "Coming in next task" in result.output
    
    @patch('git_worktree_manager.cli.GitWorktreeCLI.validate_git_repository')
    def test_list_command_placeholder(self, mock_validate):
        """Test list command placeholder."""
        mock_validate.return_value = True
        
        result = self.runner.invoke(cli, ['list'])
        
        assert result.exit_code == 0
        assert "Coming in next task" in result.output
    
    @patch('git_worktree_manager.cli.GitWorktreeCLI.validate_git_repository')
    def test_configure_command_placeholder(self, mock_validate):
        """Test configure command placeholder."""
        mock_validate.return_value = True
        
        result = self.runner.invoke(cli, ['configure'])
        
        assert result.exit_code == 0
        assert "Coming in next task" in result.output
    
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
    
    @patch('git_worktree_manager.cli.GitOperations')
    def test_full_cli_workflow_valid_repo(self, mock_git_ops):
        """Test full CLI workflow in a valid Git repository."""
        # Setup mock
        mock_git_instance = Mock()
        mock_git_instance.is_git_repository.return_value = True
        mock_git_ops.return_value = mock_git_instance
        
        # Test help display
        result = self.runner.invoke(cli, [])
        assert result.exit_code == 0
        assert "Git Worktree Manager" in result.output
        
        # Test create command
        result = self.runner.invoke(cli, ['create'])
        assert result.exit_code == 0
        assert "Coming in next task" in result.output
        
        # Test list command
        result = self.runner.invoke(cli, ['list'])
        assert result.exit_code == 0
        assert "Coming in next task" in result.output
        
        # Test configure command
        result = self.runner.invoke(cli, ['configure'])
        assert result.exit_code == 0
        assert "Coming in next task" in result.output
    
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
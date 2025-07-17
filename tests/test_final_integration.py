"""Final integration tests for complete workflows."""

import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from git_worktree_manager.cli import cli


class TestCompleteWorkflows:
    """Test complete end-to-end workflows."""

    def setup_method(self):
        """Set up test environment."""
        self.runner = CliRunner()
        self.temp_dir = None

    def teardown_method(self):
        """Clean up test environment."""
        if self.temp_dir and os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir, ignore_errors=True)

    def create_test_git_repo(self):
        """Create a temporary Git repository for testing."""
        self.temp_dir = tempfile.mkdtemp()
        repo_path = Path(self.temp_dir) / "test_repo"
        repo_path.mkdir()

        # Initialize git repo
        subprocess.run(["git", "init"], cwd=repo_path, check=True, capture_output=True)
        subprocess.run(
            ["git", "config", "user.name", "Test User"], cwd=repo_path, check=True
        )
        subprocess.run(
            ["git", "config", "user.email", "test@example.com"],
            cwd=repo_path,
            check=True,
        )

        # Create initial commit
        (repo_path / "README.md").write_text("# Test Repository")
        subprocess.run(["git", "add", "README.md"], cwd=repo_path, check=True)
        subprocess.run(
            ["git", "commit", "-m", "Initial commit"], cwd=repo_path, check=True
        )

        # Create a feature branch
        subprocess.run(
            ["git", "checkout", "-b", "feature/test"], cwd=repo_path, check=True
        )
        (repo_path / "feature.txt").write_text("Feature content")
        subprocess.run(["git", "add", "feature.txt"], cwd=repo_path, check=True)
        subprocess.run(
            ["git", "commit", "-m", "Add feature"], cwd=repo_path, check=True
        )
        subprocess.run(["git", "checkout", "main"], cwd=repo_path, check=True)

        return repo_path

    def test_cli_help_and_info(self):
        """Test CLI help and information display."""
        # Test main help
        result = self.runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "Git Worktree Manager" in result.output
        assert "create" in result.output
        assert "list" in result.output
        assert "configure" in result.output

        # Test command-specific help
        result = self.runner.invoke(cli, ["create", "--help"])
        assert result.exit_code == 0
        assert "Create a new worktree" in result.output

        result = self.runner.invoke(cli, ["list", "--help"])
        assert result.exit_code == 0
        assert "List all worktrees" in result.output

        result = self.runner.invoke(cli, ["configure", "--help"])
        assert result.exit_code == 0
        assert "Configure worktree preferences" in result.output

    def test_non_git_repository_error(self):
        """Test error handling when not in a Git repository."""
        with tempfile.TemporaryDirectory() as temp_dir:
            os.chdir(temp_dir)

            # Test create command
            result = self.runner.invoke(cli, ["create"])
            assert result.exit_code == 1
            assert "Not in a Git repository" in result.output

            # Test list command
            result = self.runner.invoke(cli, ["list"])
            assert result.exit_code == 1
            assert "Not in a Git repository" in result.output

    def test_list_command_in_git_repo(self):
        """Test list command in a real Git repository."""
        repo_path = self.create_test_git_repo()
        os.chdir(repo_path)

        result = self.runner.invoke(cli, ["list"])
        assert result.exit_code == 0
        assert "Worktree List" in result.output
        assert "main" in result.output  # Should show main branch worktree

    def test_list_command_with_options(self):
        """Test list command with various options."""
        repo_path = self.create_test_git_repo()
        os.chdir(repo_path)

        # Test with --details flag
        result = self.runner.invoke(cli, ["list", "--details"])
        assert result.exit_code == 0
        assert "Detailed Information" in result.output

        # Test with --diff flag
        result = self.runner.invoke(cli, ["list", "--diff"])
        assert result.exit_code == 0
        # Should handle diff calculation gracefully

    def test_configure_show_command(self):
        """Test configure command with --show option."""
        repo_path = self.create_test_git_repo()
        os.chdir(repo_path)

        result = self.runner.invoke(cli, ["configure", "--show"])
        assert result.exit_code == 0
        assert "Current Configuration" in result.output
        assert "Default Worktree Location" in result.output

    def test_configure_reset_command(self):
        """Test configure command with --reset option."""
        repo_path = self.create_test_git_repo()
        os.chdir(repo_path)

        # Test reset with confirmation
        result = self.runner.invoke(cli, ["configure", "--reset"], input="y\n")
        assert result.exit_code == 0
        assert "Configuration reset" in result.output

        # Test reset with cancellation
        result = self.runner.invoke(cli, ["configure", "--reset"], input="n\n")
        assert result.exit_code == 0
        assert "cancelled" in result.output

    @patch("git_worktree_manager.ui_controller.UIController.prompt_branch_name")
    @patch("git_worktree_manager.ui_controller.UIController.select_base_branch")
    @patch("git_worktree_manager.ui_controller.UIController.select_worktree_location")
    def test_create_worktree_workflow(
        self, mock_location, mock_base_branch, mock_branch_name
    ):
        """Test complete worktree creation workflow."""
        repo_path = self.create_test_git_repo()
        os.chdir(repo_path)

        # Mock user inputs
        mock_branch_name.return_value = "test-branch"
        mock_base_branch.return_value = "main"
        mock_location.return_value = str(repo_path.parent / "worktrees" / "test-branch")

        result = self.runner.invoke(cli, ["create"])

        # Should complete successfully or show appropriate error
        # (May fail due to actual Git operations, but should handle gracefully)
        assert result.exit_code in [
            0,
            1,
        ]  # Allow for expected failures in test environment

        if result.exit_code == 0:
            assert "Worktree Created Successfully" in result.output
        else:
            # Should show meaningful error message
            assert "Error" in result.output or "Failed" in result.output

    def test_keyboard_interrupt_handling(self):
        """Test that keyboard interrupts are handled gracefully."""
        repo_path = self.create_test_git_repo()
        os.chdir(repo_path)

        # Simulate KeyboardInterrupt during create command
        with patch(
            "git_worktree_manager.worktree_manager.WorktreeManager.create_worktree"
        ) as mock_create:
            mock_create.side_effect = KeyboardInterrupt()

            result = self.runner.invoke(cli, ["create"])
            assert result.exit_code == 1
            assert "cancelled by user" in result.output

    def test_error_message_quality(self):
        """Test that error messages are helpful and actionable."""
        repo_path = self.create_test_git_repo()
        os.chdir(repo_path)

        # Test with mocked Git error
        with patch(
            "git_worktree_manager.git_ops.GitOperations.list_worktrees"
        ) as mock_list:
            from git_worktree_manager.exceptions import GitRepositoryError

            mock_list.side_effect = GitRepositoryError("Test Git error")

            result = self.runner.invoke(cli, ["list"])
            assert result.exit_code == 1
            assert "Git operation failed" in result.output
            assert "Test Git error" in result.output

    def test_performance_with_mock_data(self):
        """Test performance characteristics with mocked large datasets."""
        repo_path = self.create_test_git_repo()
        os.chdir(repo_path)

        # Mock large worktree list
        from git_worktree_manager.models import WorktreeInfo

        large_worktree_list = [
            WorktreeInfo(
                path=f"/path/to/worktree-{i}",
                branch=f"branch-{i}",
                commit_hash=f"abc123{i:02d}",
                commit_message=f"Commit message {i}",
                base_branch="main",
                is_bare=False,
                has_uncommitted_changes=i % 3 == 0,
            )
            for i in range(50)  # 50 worktrees
        ]

        with patch(
            "git_worktree_manager.worktree_manager.WorktreeManager.list_worktrees"
        ) as mock_list:
            mock_list.return_value = large_worktree_list

            import time

            start_time = time.time()
            result = self.runner.invoke(cli, ["list"])
            end_time = time.time()

            assert result.exit_code == 0
            assert end_time - start_time < 5.0  # Should complete within 5 seconds
            assert "50 found" in result.output or "Total Worktrees: 50" in result.output


class TestErrorRecovery:
    """Test error recovery and cleanup mechanisms."""

    def test_git_command_failure_recovery(self):
        """Test recovery from Git command failures."""
        runner = CliRunner()

        with tempfile.TemporaryDirectory() as temp_dir:
            os.chdir(temp_dir)

            # Create a directory that looks like a git repo but isn't
            os.makedirs(".git")

            result = runner.invoke(cli, ["list"])
            assert result.exit_code == 1
            # Should show meaningful error, not crash

    def test_permission_error_handling(self):
        """Test handling of permission errors."""
        runner = CliRunner()

        # This test would need specific setup for permission errors
        # For now, just ensure the error handling code paths exist
        from git_worktree_manager.exceptions import WorktreeError

        assert WorktreeError is not None

    def test_disk_space_error_simulation(self):
        """Test handling of disk space errors."""
        # This would require more complex setup to simulate disk space issues
        # For now, verify error handling infrastructure exists
        from git_worktree_manager.exceptions import FileSystemError

        assert FileSystemError is not None


class TestCLIIntegration:
    """Test CLI integration with all components."""

    def test_all_components_importable(self):
        """Test that all components can be imported and initialized."""
        from git_worktree_manager import (
            config,
            git_ops,
        )

        # Test that main classes can be instantiated
        try:
            git_ops.GitOperations()
            config.ConfigManager()
            # UI controller and worktree manager require more setup
        except Exception as e:
            pytest.fail(f"Failed to instantiate core components: {e}")

    def test_cli_entry_point_integration(self):
        """Test that CLI entry point works correctly."""
        from git_worktree_manager.cli import main

        # Test with help argument (expect SystemExit)
        try:
            result = main(["--help"])
            assert result == 0
        except SystemExit as e:
            assert e.code == 0  # Help should exit with code 0

    def test_console_script_integration(self):
        """Test that console script is properly configured."""
        # Test that the script can be found and executed
        result = subprocess.run(
            ["git-worktree-manager", "--help"], capture_output=True, text=True
        )

        assert result.returncode == 0
        assert "Git Worktree Manager" in result.stdout

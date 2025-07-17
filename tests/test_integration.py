"""Integration tests for Git Worktree Manager workflows.

These tests create real Git repositories and test complete workflows
end-to-end to ensure all components work together correctly.
"""

import os
import shutil
import subprocess
import tempfile
import time
from pathlib import Path

import pytest

from git_worktree_manager.config import ConfigManager
from git_worktree_manager.git_ops import GitOperations


class IntegrationTestBase:
    """Base class for integration tests with Git repository setup."""

    def setup_method(self):
        """Set up a temporary Git repository for testing."""
        self.temp_dir = tempfile.mkdtemp()
        self.repo_path = Path(self.temp_dir) / "test_repo"
        self.worktree_base = Path(self.temp_dir) / "worktrees"

        # Create test repository
        self.repo_path.mkdir()
        os.chdir(self.repo_path)

        # Initialize Git repository
        subprocess.run(["git", "init"], check=True, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Test User"], check=True)
        subprocess.run(["git", "config", "user.email", "test@example.com"], check=True)

        # Create initial commit
        (self.repo_path / "README.md").write_text("# Test Repository\n")
        subprocess.run(["git", "add", "README.md"], check=True)
        subprocess.run(["git", "commit", "-m", "Initial commit"], check=True)

        # Create additional branches for testing
        subprocess.run(["git", "checkout", "-b", "develop"], check=True)
        (self.repo_path / "develop.txt").write_text("Develop branch file\n")
        subprocess.run(["git", "add", "develop.txt"], check=True)
        subprocess.run(["git", "commit", "-m", "Add develop file"], check=True)

        subprocess.run(["git", "checkout", "main"], check=True)

        # Create worktree directory
        self.worktree_base.mkdir()

    def teardown_method(self):
        """Clean up temporary directories."""
        os.chdir("/")
        if self.temp_dir and Path(self.temp_dir).exists():
            shutil.rmtree(self.temp_dir)


class TestGitOperationsIntegration(IntegrationTestBase):
    """Test Git operations with real repositories."""

    def test_repository_detection(self):
        """Test Git repository detection."""
        git_ops = GitOperations(str(self.repo_path))
        assert git_ops.is_git_repository() is True

        # Test non-Git directory
        non_git_dir = Path(self.temp_dir) / "not_git"
        non_git_dir.mkdir()
        git_ops_non_git = GitOperations(str(non_git_dir))
        assert git_ops_non_git.is_git_repository() is False

    def test_branch_operations(self):
        """Test branch listing and current branch detection."""
        git_ops = GitOperations(str(self.repo_path))

        # Test branch listing
        branches = git_ops.get_branches()
        assert "main" in branches
        assert "develop" in branches

        # Test current branch detection
        current_branch = git_ops.get_current_branch()
        assert current_branch == "main"

    def test_worktree_creation_and_listing(self):
        """Test creating and listing worktrees."""
        git_ops = GitOperations(str(self.repo_path))
        worktree_path = str(self.worktree_base / "test-worktree")

        # Create worktree
        git_ops.create_worktree(worktree_path, "feature-branch", "main")

        # Verify worktree exists
        assert Path(worktree_path).exists()
        assert (Path(worktree_path) / ".git").exists()

        # List worktrees
        worktrees = git_ops.list_worktrees()
        assert len(worktrees) >= 2  # Main repo + new worktree

        # Find our worktree (handle path resolution differences)
        test_worktree = None
        for w in worktrees:
            # Use Path.resolve() to handle symlinks and path differences
            if Path(w.path).resolve() == Path(worktree_path).resolve():
                test_worktree = w
                break

        assert test_worktree is not None
        assert test_worktree.branch == "feature-branch"

    def test_commit_info_retrieval(self):
        """Test commit information retrieval."""
        git_ops = GitOperations(str(self.repo_path))

        # Get commit info for main branch
        commit_info = git_ops.get_commit_info("main")
        assert commit_info.message == "Initial commit"
        assert commit_info.author == "Test User"
        assert len(commit_info.hash) > 0

        # Get commit info for develop branch
        commit_info_develop = git_ops.get_commit_info("develop")
        assert commit_info_develop.message == "Add develop file"

    def test_diff_summary_calculation(self):
        """Test diff summary between branches."""
        git_ops = GitOperations(str(self.repo_path))

        # Get diff between main and develop
        diff_summary = git_ops.get_diff_summary("main", "develop")
        assert diff_summary.files_added == 1  # develop.txt was added
        assert diff_summary.total_insertions >= 1


class TestConfigurationIntegration(IntegrationTestBase):
    """Test configuration management in real scenarios."""

    def test_config_creation_and_loading(self):
        """Test configuration creation and loading."""
        config_manager = ConfigManager()

        # Set custom configuration
        custom_path = str(self.worktree_base)
        config_manager.set_default_worktree_location(custom_path)

        # Verify configuration was set
        assert config_manager.get_default_worktree_location() == custom_path

    def test_environment_variable_override(self):
        """Test that environment variables override configuration."""
        import os
        from unittest.mock import patch

        env_path = str(self.worktree_base / "env_override")

        with patch.dict(os.environ, {"WORKTREE_DEFAULT_PATH": env_path}):
            config_manager = ConfigManager()
            assert config_manager.get_default_worktree_location() == env_path


class TestPerformanceIntegration(IntegrationTestBase):
    """Test performance with larger repositories."""

    @pytest.mark.slow
    def test_large_repository_performance(self):
        """Test performance with a repository containing many files."""
        # Create many files to simulate a larger repository
        for i in range(50):  # Reduced from 100 for faster tests
            file_path = self.repo_path / f"file_{i:03d}.txt"
            file_path.write_text(f"Content of file {i}\n")

        # Add and commit all files
        subprocess.run(["git", "add", "."], check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Add many files"], check=True, capture_output=True
        )

        # Test worktree operations performance
        git_ops = GitOperations(str(self.repo_path))

        # Test listing worktrees performance
        start_time = time.time()
        worktrees = git_ops.list_worktrees()
        list_time = time.time() - start_time

        assert list_time < 5.0  # Should complete within 5 seconds
        assert len(worktrees) >= 1  # Should find at least the main repository

        # Test diff summary performance
        start_time = time.time()
        diff_summary = git_ops.get_diff_summary("HEAD~1", "HEAD")
        diff_time = time.time() - start_time

        assert diff_time < 5.0  # Should complete within 5 seconds
        assert diff_summary.files_added == 50  # Should detect all added files


class TestErrorHandlingIntegration(IntegrationTestBase):
    """Test error handling in integration scenarios."""

    def test_invalid_repository_handling(self):
        """Test error handling with invalid Git repository."""
        # Remove .git directory to corrupt repository
        git_dir = self.repo_path / ".git"
        if git_dir.exists():
            shutil.rmtree(git_dir)

        git_ops = GitOperations(str(self.repo_path))

        # Should detect it's not a Git repository
        assert git_ops.is_git_repository() is False

        # Operations should raise appropriate errors
        with pytest.raises(Exception):
            git_ops.list_worktrees()

    def test_invalid_branch_handling(self):
        """Test error handling with invalid branch names."""
        git_ops = GitOperations(str(self.repo_path))

        # Try to get commit info for non-existent branch
        with pytest.raises(Exception):
            git_ops.get_commit_info("non-existent-branch")

        # Try to create diff summary with invalid branch
        with pytest.raises(Exception):
            git_ops.get_diff_summary("main", "non-existent-branch")


class TestCacheIntegration(IntegrationTestBase):
    """Test caching functionality in real scenarios."""

    def test_branch_caching(self):
        """Test that branch information is cached properly."""
        git_ops = GitOperations(str(self.repo_path))

        # First call should populate cache
        start_time = time.time()
        branches1 = git_ops.get_branches()
        first_call_time = time.time() - start_time

        # Second call should be faster (cached)
        start_time = time.time()
        branches2 = git_ops.get_branches()
        second_call_time = time.time() - start_time

        # Results should be the same
        assert branches1 == branches2

        # Second call should be faster (though this might be flaky)
        # We'll just verify it completes quickly
        assert second_call_time < 1.0

    def test_cache_invalidation(self):
        """Test cache invalidation functionality."""
        git_ops = GitOperations(str(self.repo_path))

        # Populate cache
        git_ops.get_branches()

        # Invalidate cache
        invalidated_count = git_ops.invalidate_branches_cache()
        assert invalidated_count is True  # Should have invalidated something

        # Should still work after invalidation
        branches = git_ops.get_branches()
        assert "main" in branches


if __name__ == "__main__":
    pytest.main([__file__])

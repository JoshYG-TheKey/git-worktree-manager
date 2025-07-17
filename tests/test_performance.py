"""Performance tests for Git operations."""

import os
import subprocess
import tempfile
import time
from unittest.mock import MagicMock, patch

import pytest

from git_worktree_manager.git_ops import GitOperations


class TestGitOperationsPerformance:
    """Performance tests for GitOperations class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.git_ops = GitOperations(enable_cache=True)

    @pytest.mark.performance
    def test_diff_calculation_performance_with_caching(self):
        """Test diff calculation performance with caching enabled."""
        # Mock a large diff output
        large_diff_output = self._create_mock_large_diff_output(1000)

        with patch("subprocess.run") as mock_run:
            mock_result = MagicMock()
            mock_result.stdout = large_diff_output
            mock_result.returncode = 0
            mock_run.return_value = mock_result

            # First call - should be slower (cache miss)
            start_time = time.time()
            diff1 = self.git_ops.get_diff_summary("main", "dev")
            first_call_time = time.time() - start_time

            # Second call - should be faster (cache hit)
            start_time = time.time()
            diff2 = self.git_ops.get_diff_summary("main", "dev")
            second_call_time = time.time() - start_time

            # Verify results are the same
            assert diff1.files_modified == diff2.files_modified
            assert diff1.total_insertions == diff2.total_insertions

            # Cache hit should be significantly faster
            assert second_call_time < first_call_time / 10  # At least 10x faster

            # Verify cache was used (only one subprocess call)
            assert mock_run.call_count == 1

    @pytest.mark.performance
    def test_diff_calculation_performance_without_caching(self):
        """Test diff calculation performance without caching."""
        git_ops_uncached = GitOperations(enable_cache=False)
        large_diff_output = self._create_mock_large_diff_output(500)

        with patch("subprocess.run") as mock_run:
            mock_result = MagicMock()
            mock_result.stdout = large_diff_output
            mock_result.returncode = 0
            mock_run.return_value = mock_result

            # Multiple calls should all take similar time
            times = []
            for _ in range(3):
                start_time = time.time()
                git_ops_uncached.get_diff_summary("main", "dev")
                times.append(time.time() - start_time)

            # All calls should execute subprocess (no caching)
            assert mock_run.call_count == 3

            # Times should be relatively consistent (no significant speedup)
            avg_time = sum(times) / len(times)
            for t in times:
                assert abs(t - avg_time) / avg_time < 0.5  # Within 50% of average

    @pytest.mark.performance
    def test_numstat_parsing_performance(self):
        """Test performance of numstat parsing vs stat parsing."""
        # Create large diff outputs
        numstat_output = self._create_mock_numstat_output(2000)
        stat_output = self._create_mock_stat_output(2000)

        # Test numstat parsing performance
        start_time = time.time()
        result_numstat = self.git_ops._parse_diff_numstat(numstat_output)
        numstat_time = time.time() - start_time

        # Test stat parsing performance
        start_time = time.time()
        result_stat = self.git_ops._parse_diff_summary(stat_output)
        stat_time = time.time() - start_time

        # Both parsing methods should complete quickly (under 1 second)
        assert numstat_time < 1.0
        assert stat_time < 1.0

        # Results should be comparable
        assert (
            result_numstat.files_modified
            + result_numstat.files_added
            + result_numstat.files_deleted
            > 0
        )
        assert (
            result_stat.files_modified
            + result_stat.files_added
            + result_stat.files_deleted
            > 0
        )

    @pytest.mark.performance
    def test_progressive_loading_performance(self):
        """Test progressive loading performance."""
        large_diff_output = self._create_mock_numstat_output(5000)

        with patch("subprocess.run") as mock_run:
            mock_result = MagicMock()
            mock_result.stdout = large_diff_output
            mock_result.returncode = 0
            mock_run.return_value = mock_result

            # Test with file limit
            start_time = time.time()
            diff_limited = self.git_ops.get_diff_summary_progressive(
                "main", "dev", max_files=100
            )
            limited_time = time.time() - start_time

            # Reset mock for unlimited test
            mock_run.reset_mock()
            mock_run.return_value = mock_result

            # Test without file limit
            start_time = time.time()
            diff_unlimited = self.git_ops.get_diff_summary_progressive(
                "main", "dev", max_files=None
            )
            unlimited_time = time.time() - start_time

            # Limited processing should be faster
            assert limited_time <= unlimited_time

            # Limited result should have fewer or equal files
            limited_total = (
                diff_limited.files_modified
                + diff_limited.files_added
                + diff_limited.files_deleted
            )
            unlimited_total = (
                diff_unlimited.files_modified
                + diff_unlimited.files_added
                + diff_unlimited.files_deleted
            )
            assert limited_total <= unlimited_total

    @pytest.mark.performance
    def test_performance_metrics_collection(self):
        """Test performance metrics collection."""
        with patch("subprocess.run") as mock_run:
            mock_result = MagicMock()
            mock_result.stdout = self._create_mock_numstat_output(100)
            mock_result.returncode = 0
            mock_run.return_value = mock_result

            # Perform several operations
            for i in range(5):
                self.git_ops.get_diff_summary(f"branch{i}", "main")

            # Check performance metrics
            metrics = self.git_ops.get_performance_metrics()
            assert "diff_summary" in metrics

            diff_metrics = metrics["diff_summary"]
            assert diff_metrics["total_calls"] == 5
            assert diff_metrics["total_time"] > 0
            assert diff_metrics["average_time"] > 0
            assert diff_metrics["max_time"] >= diff_metrics["min_time"]

    @pytest.mark.performance
    def test_cache_performance_with_large_dataset(self):
        """Test cache performance with large datasets."""
        # Create a large number of different cache entries
        with patch("subprocess.run") as mock_run:
            mock_result = MagicMock()
            mock_result.stdout = "main\ndev\nfeature"
            mock_result.returncode = 0
            mock_run.return_value = mock_result

            # Fill cache with many entries
            start_time = time.time()
            for i in range(100):
                # This will create different cache keys
                self.git_ops._cache.set(f"test_key_{i}", f"test_value_{i}")
            cache_fill_time = time.time() - start_time

            # Test cache retrieval performance
            start_time = time.time()
            for i in range(100):
                value = self.git_ops._cache.get(f"test_key_{i}")
                assert value == f"test_value_{i}"
            cache_retrieval_time = time.time() - start_time

            # Cache operations should be fast
            assert cache_fill_time < 1.0  # Should take less than 1 second
            assert cache_retrieval_time < 0.1  # Should take less than 100ms

            # Check cache stats
            stats = self.git_ops.get_cache_stats()
            assert stats["cache_size"] == 100
            assert stats["hits"] == 100

    @pytest.mark.performance
    def test_memory_usage_with_large_cache(self):
        """Test memory usage with large cache entries."""

        # Get initial memory usage (approximate)
        initial_cache_size = len(str(self.git_ops._cache._cache))

        # Add large cache entries
        large_data = "x" * 10000  # 10KB string
        for i in range(100):
            self.git_ops._cache.set(f"large_key_{i}", large_data)

        # Check cache size growth
        final_cache_size = len(str(self.git_ops._cache._cache))

        # Cache should have grown significantly
        assert final_cache_size > initial_cache_size * 10

        # Clear cache and verify cleanup
        self.git_ops._cache.clear()
        cleared_cache_size = len(str(self.git_ops._cache._cache))

        # Cache should be much smaller after clearing
        assert cleared_cache_size < initial_cache_size * 2

    @pytest.mark.performance
    def test_timeout_handling_performance(self):
        """Test timeout handling doesn't significantly impact performance."""
        with patch("subprocess.run") as mock_run:
            # Mock a quick response
            mock_result = MagicMock()
            mock_result.stdout = "1\t2\tfile.txt"
            mock_result.returncode = 0
            mock_run.return_value = mock_result

            # Time multiple operations with timeout
            start_time = time.time()
            for _ in range(10):
                self.git_ops.get_diff_summary("main", "dev")
            total_time = time.time() - start_time

            # Operations should complete quickly despite timeout parameter
            assert total_time < 1.0  # Should take less than 1 second for 10 operations

    def _create_mock_large_diff_output(self, num_files: int) -> str:
        """Create mock diff --stat output for testing."""
        lines = []
        for i in range(num_files):
            filename = f"file_{i}.py"
            changes = f" {filename} | {i + 1} {'+'*(i % 10)}{'−'*(i % 5)}"
            lines.append(changes)

        # Add summary line
        total_files = num_files
        total_insertions = sum(range(1, num_files + 1))
        total_deletions = sum(i % 5 for i in range(num_files))

        summary = f" {total_files} files changed, {total_insertions} insertions(+), {total_deletions} deletions(-)"
        lines.append(summary)

        return "\n".join(lines)

    def _create_mock_numstat_output(self, num_files: int) -> str:
        """Create mock diff --numstat output for testing."""
        lines = []
        for i in range(num_files):
            insertions = i + 1
            deletions = i % 5
            filename = f"file_{i}.py"
            lines.append(f"{insertions}\t{deletions}\t{filename}")

        return "\n".join(lines)

    def _create_mock_stat_output(self, num_files: int) -> str:
        """Create mock diff --stat output for testing."""
        lines = []
        for i in range(num_files):
            filename = f"file_{i}.py"
            insertions = i + 1
            deletions = i % 5
            changes = f" {filename} | {insertions + deletions} {'+'*min(insertions, 10)}{'−'*min(deletions, 10)}"
            lines.append(changes)

        # Add summary line
        total_files = num_files
        total_insertions = sum(range(1, num_files + 1))
        total_deletions = sum(i % 5 for i in range(num_files))

        summary = f" {total_files} files changed, {total_insertions} insertions(+), {total_deletions} deletions(-)"
        lines.append(summary)

        return "\n".join(lines)


class TestRealRepositoryPerformance:
    """Performance tests with real Git repositories (integration tests)."""

    @pytest.mark.slow
    @pytest.mark.integration
    def test_real_repository_performance(self):
        """Test performance with a real Git repository."""
        # This test requires a real Git repository
        # Skip if not in a Git repository
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--git-dir"],
                capture_output=True,
                text=True,
                check=True,
            )
        except (subprocess.CalledProcessError, FileNotFoundError):
            pytest.skip("Not in a Git repository or Git not available")

        git_ops = GitOperations(enable_cache=True)

        # Test branch listing performance
        start_time = time.time()
        branches = git_ops.get_branches()
        branch_time = time.time() - start_time

        assert len(branches) > 0
        assert branch_time < 5.0  # Should complete within 5 seconds

        # Test current branch performance
        start_time = time.time()
        current_branch = git_ops.get_current_branch()
        current_branch_time = time.time() - start_time

        assert current_branch is not None
        assert current_branch_time < 1.0  # Should complete within 1 second

        # Test caching performance (second call should be faster)
        start_time = time.time()
        branches2 = git_ops.get_branches()
        cached_branch_time = time.time() - start_time

        assert branches == branches2
        assert cached_branch_time < branch_time / 5  # Should be at least 5x faster

    @pytest.mark.slow
    @pytest.mark.integration
    def test_large_repository_simulation(self):
        """Simulate performance with a large repository."""
        # Create a temporary Git repository for testing
        with tempfile.TemporaryDirectory() as temp_dir:
            # Initialize Git repository
            subprocess.run(
                ["git", "init"], cwd=temp_dir, check=True, capture_output=True
            )
            subprocess.run(
                ["git", "config", "user.email", "test@example.com"],
                cwd=temp_dir,
                check=True,
            )
            subprocess.run(
                ["git", "config", "user.name", "Test User"], cwd=temp_dir, check=True
            )

            # Create many files to simulate a large repository
            for i in range(50):  # Create 50 files (reasonable for test)
                file_path = os.path.join(temp_dir, f"file_{i}.txt")
                with open(file_path, "w") as f:
                    f.write(f"Content of file {i}\n" * (i + 1))

            # Add and commit files
            subprocess.run(
                ["git", "add", "."], cwd=temp_dir, check=True, capture_output=True
            )
            subprocess.run(
                ["git", "commit", "-m", "Initial commit"],
                cwd=temp_dir,
                check=True,
                capture_output=True,
            )

            # Create a branch and modify files
            subprocess.run(
                ["git", "checkout", "-b", "feature"],
                cwd=temp_dir,
                check=True,
                capture_output=True,
            )

            # Modify files
            for i in range(25):  # Modify half the files
                file_path = os.path.join(temp_dir, f"file_{i}.txt")
                with open(file_path, "a") as f:
                    f.write(f"Modified content {i}\n")

            subprocess.run(
                ["git", "add", "."], cwd=temp_dir, check=True, capture_output=True
            )
            subprocess.run(
                ["git", "commit", "-m", "Feature changes"],
                cwd=temp_dir,
                check=True,
                capture_output=True,
            )

            # Test performance with this repository
            git_ops = GitOperations(repo_path=temp_dir, enable_cache=True)

            # Test diff calculation performance
            start_time = time.time()
            diff_summary = git_ops.get_diff_summary("main", "feature")
            diff_time = time.time() - start_time

            # Verify results - files should be detected as added since they're new
            total_files_changed = (
                diff_summary.files_modified
                + diff_summary.files_added
                + diff_summary.files_deleted
            )
            assert total_files_changed > 0
            assert diff_time < 2.0  # Should complete within 2 seconds

            # Test progressive loading
            start_time = time.time()
            diff_progressive = git_ops.get_diff_summary_progressive(
                "main", "feature", max_files=10
            )
            progressive_time = time.time() - start_time

            # Progressive loading should be reasonably fast (within 50% margin for small datasets)
            # In larger datasets, progressive loading would show more significant benefits
            # For small test datasets, timing can vary significantly due to overhead
            assert progressive_time <= max(
                diff_time * 1.5, 0.1
            )  # Allow 50% margin or 100ms max

            # Check performance metrics
            metrics = git_ops.get_performance_metrics()
            assert len(metrics) > 0

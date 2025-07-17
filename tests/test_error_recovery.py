"""Unit tests for the error recovery module."""

import pytest
import subprocess
import time
import os
import tempfile
import shutil
from unittest.mock import patch, MagicMock, call
from pathlib import Path

from git_worktree_manager.error_recovery import (
    RetryConfig,
    with_retry,
    WorktreeCleanupManager,
    GracefulDegradationManager,
    ErrorRecoveryManager,
    get_error_recovery_manager,
    with_git_retry,
    with_worktree_cleanup
)
from git_worktree_manager.exceptions import (
    GitRepositoryError,
    WorktreeCreationError,
    FileSystemError
)


class TestRetryConfig:
    """Test cases for RetryConfig class."""
    
    def test_default_config(self):
        """Test RetryConfig with default values."""
        config = RetryConfig()
        
        assert config.max_attempts == 3
        assert config.base_delay == 1.0
        assert config.max_delay == 10.0
        assert config.backoff_multiplier == 2.0
        assert subprocess.TimeoutExpired in config.retryable_exceptions
        assert subprocess.CalledProcessError in config.retryable_exceptions
        assert OSError in config.retryable_exceptions
        assert IOError in config.retryable_exceptions
    
    def test_custom_config(self):
        """Test RetryConfig with custom values."""
        custom_exceptions = [ValueError, TypeError]
        config = RetryConfig(
            max_attempts=5,
            base_delay=0.5,
            max_delay=5.0,
            backoff_multiplier=1.5,
            retryable_exceptions=custom_exceptions
        )
        
        assert config.max_attempts == 5
        assert config.base_delay == 0.5
        assert config.max_delay == 5.0
        assert config.backoff_multiplier == 1.5
        assert config.retryable_exceptions == custom_exceptions


class TestWithRetryDecorator:
    """Test cases for the with_retry decorator."""
    
    def test_successful_operation_no_retry(self):
        """Test that successful operations don't trigger retries."""
        call_count = 0
        
        @with_retry(RetryConfig(max_attempts=3))
        def successful_operation():
            nonlocal call_count
            call_count += 1
            return "success"
        
        result = successful_operation()
        
        assert result == "success"
        assert call_count == 1
    
    def test_retry_on_retryable_exception(self):
        """Test retry behavior with retryable exceptions."""
        call_count = 0
        
        @with_retry(RetryConfig(max_attempts=3, base_delay=0.1))
        def failing_operation():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise subprocess.CalledProcessError(1, ["test"])
            return "success"
        
        result = failing_operation()
        
        assert result == "success"
        assert call_count == 3
    
    def test_no_retry_on_non_retryable_exception(self):
        """Test that non-retryable exceptions don't trigger retries."""
        call_count = 0
        
        @with_retry(RetryConfig(max_attempts=3, retryable_exceptions=[OSError]))
        def failing_operation():
            nonlocal call_count
            call_count += 1
            raise ValueError("Not retryable")
        
        with pytest.raises(ValueError, match="Not retryable"):
            failing_operation()
        
        assert call_count == 1
    
    def test_max_attempts_exhausted(self):
        """Test behavior when max attempts are exhausted."""
        call_count = 0
        
        @with_retry(RetryConfig(max_attempts=2, base_delay=0.1))
        def always_failing_operation():
            nonlocal call_count
            call_count += 1
            raise subprocess.CalledProcessError(1, ["test"])
        
        with pytest.raises(subprocess.CalledProcessError):
            always_failing_operation()
        
        assert call_count == 2
    
    @patch('time.sleep')
    def test_exponential_backoff(self, mock_sleep):
        """Test exponential backoff delay calculation."""
        call_count = 0
        
        @with_retry(RetryConfig(max_attempts=4, base_delay=1.0, backoff_multiplier=2.0))
        def failing_operation():
            nonlocal call_count
            call_count += 1
            if call_count < 4:
                raise subprocess.CalledProcessError(1, ["test"])
            return "success"
        
        result = failing_operation()
        
        assert result == "success"
        assert call_count == 4
        
        # Check that sleep was called with exponential backoff delays
        expected_delays = [1.0, 2.0, 4.0]  # base_delay * (multiplier ^ attempt)
        actual_delays = [call.args[0] for call in mock_sleep.call_args_list]
        assert actual_delays == expected_delays
    
    @patch('time.sleep')
    def test_max_delay_cap(self, mock_sleep):
        """Test that delays are capped at max_delay."""
        call_count = 0
        
        @with_retry(RetryConfig(
            max_attempts=4, 
            base_delay=1.0, 
            max_delay=2.5, 
            backoff_multiplier=2.0
        ))
        def failing_operation():
            nonlocal call_count
            call_count += 1
            if call_count < 4:
                raise subprocess.CalledProcessError(1, ["test"])
            return "success"
        
        result = failing_operation()
        
        assert result == "success"
        
        # Check that delays are capped at max_delay
        expected_delays = [1.0, 2.0, 2.5]  # Third delay capped at max_delay
        actual_delays = [call.args[0] for call in mock_sleep.call_args_list]
        assert actual_delays == expected_delays


class TestWorktreeCleanupManager:
    """Test cases for WorktreeCleanupManager."""
    
    def test_init(self):
        """Test WorktreeCleanupManager initialization."""
        manager = WorktreeCleanupManager("/test/repo")
        
        assert manager.repo_path == "/test/repo"
        assert manager.cleanup_registry == {}
    
    def test_register_cleanup(self):
        """Test registering cleanup functions."""
        manager = WorktreeCleanupManager()
        
        def cleanup_func1():
            pass
        
        def cleanup_func2():
            pass
        
        manager.register_cleanup("op1", cleanup_func1)
        manager.register_cleanup("op1", cleanup_func2)
        manager.register_cleanup("op2", cleanup_func1)
        
        assert len(manager.cleanup_registry["op1"]) == 2
        assert len(manager.cleanup_registry["op2"]) == 1
        assert cleanup_func1 in manager.cleanup_registry["op1"]
        assert cleanup_func2 in manager.cleanup_registry["op1"]
        assert cleanup_func1 in manager.cleanup_registry["op2"]
    
    def test_execute_cleanup_success(self):
        """Test successful cleanup execution."""
        manager = WorktreeCleanupManager()
        
        cleanup_calls = []
        
        def cleanup_func1():
            cleanup_calls.append("func1")
        
        def cleanup_func2():
            cleanup_calls.append("func2")
        
        manager.register_cleanup("test_op", cleanup_func1)
        manager.register_cleanup("test_op", cleanup_func2)
        
        manager.execute_cleanup("test_op")
        
        # Should execute in reverse order
        assert cleanup_calls == ["func2", "func1"]
        assert "test_op" not in manager.cleanup_registry
    
    def test_execute_cleanup_with_failures(self):
        """Test cleanup execution with some failures."""
        manager = WorktreeCleanupManager()
        
        cleanup_calls = []
        
        def cleanup_func1():
            cleanup_calls.append("func1")
        
        def failing_cleanup():
            raise Exception("Cleanup failed")
        
        def cleanup_func2():
            cleanup_calls.append("func2")
        
        manager.register_cleanup("test_op", cleanup_func1)
        manager.register_cleanup("test_op", failing_cleanup)
        manager.register_cleanup("test_op", cleanup_func2)
        
        # Should not raise exception even if some cleanups fail
        manager.execute_cleanup("test_op")
        
        # Should still execute other cleanup functions
        assert "func1" in cleanup_calls
        assert "func2" in cleanup_calls
        assert "test_op" not in manager.cleanup_registry
    
    def test_execute_cleanup_nonexistent_operation(self):
        """Test cleanup execution for non-existent operation."""
        manager = WorktreeCleanupManager()
        
        # Should not raise exception
        manager.execute_cleanup("nonexistent")
    
    @patch('subprocess.run')
    @patch('shutil.rmtree')
    @patch('os.path.exists')
    def test_cleanup_failed_worktree(self, mock_exists, mock_rmtree, mock_run):
        """Test comprehensive worktree cleanup."""
        manager = WorktreeCleanupManager("/test/repo")
        
        mock_exists.return_value = True
        mock_run.return_value = MagicMock(returncode=0)
        
        manager.cleanup_failed_worktree("/test/worktree", "test-branch")
        
        # Should remove directory
        mock_rmtree.assert_called_once_with("/test/worktree")
        
        # Should make multiple subprocess calls for cleanup
        assert mock_run.call_count >= 1
        
        # Check that worktree remove was called
        worktree_remove_calls = [
            call for call in mock_run.call_args_list
            if call[0][0][:3] == ["git", "worktree", "remove"]
        ]
        assert len(worktree_remove_calls) == 1
        
        # Verify the worktree remove call
        worktree_remove_call = worktree_remove_calls[0]
        assert worktree_remove_call[0][0] == ["git", "worktree", "remove", "--force", "/test/worktree"]
        assert worktree_remove_call[1]["cwd"] == "/test/repo"
        assert worktree_remove_call[1]["timeout"] == 30
    
    @patch('subprocess.run')
    @patch('shutil.rmtree')
    @patch('os.path.exists')
    def test_cleanup_failed_worktree_with_errors(self, mock_exists, mock_rmtree, mock_run):
        """Test worktree cleanup handles errors gracefully."""
        manager = WorktreeCleanupManager("/test/repo")
        
        mock_exists.return_value = True
        mock_rmtree.side_effect = Exception("Permission denied")
        mock_run.side_effect = subprocess.TimeoutExpired(["git"], 30)
        
        # Should not raise exception
        manager.cleanup_failed_worktree("/test/worktree", "test-branch")
    
    def test_cleanup_partial_operations(self):
        """Test cleanup of all partial operations."""
        manager = WorktreeCleanupManager()
        
        cleanup_calls = []
        
        def cleanup1():
            cleanup_calls.append("op1")
        
        def cleanup2():
            cleanup_calls.append("op2")
        
        manager.register_cleanup("op1", cleanup1)
        manager.register_cleanup("op2", cleanup2)
        
        manager.cleanup_partial_operations()
        
        assert "op1" in cleanup_calls
        assert "op2" in cleanup_calls
        assert manager.cleanup_registry == {}


class TestGracefulDegradationManager:
    """Test cases for GracefulDegradationManager."""
    
    def test_init(self):
        """Test GracefulDegradationManager initialization."""
        manager = GracefulDegradationManager()
        
        assert manager.feature_availability == {}
        assert manager.fallback_strategies == {}
    
    def test_check_feature_availability_success(self):
        """Test feature availability check with successful check."""
        manager = GracefulDegradationManager()
        
        def check_feature():
            return True
        
        result = manager.check_feature_availability("test_feature", check_feature)
        
        assert result is True
        assert manager.feature_availability["test_feature"] is True
    
    def test_check_feature_availability_failure(self):
        """Test feature availability check with failed check."""
        manager = GracefulDegradationManager()
        
        def check_feature():
            raise Exception("Feature not available")
        
        result = manager.check_feature_availability("test_feature", check_feature)
        
        assert result is False
        assert manager.feature_availability["test_feature"] is False
    
    def test_check_feature_availability_cached(self):
        """Test that feature availability is cached."""
        manager = GracefulDegradationManager()
        
        call_count = 0
        
        def check_feature():
            nonlocal call_count
            call_count += 1
            return True
        
        # First call
        result1 = manager.check_feature_availability("test_feature", check_feature)
        # Second call should use cache
        result2 = manager.check_feature_availability("test_feature", check_feature)
        
        assert result1 is True
        assert result2 is True
        assert call_count == 1  # Should only be called once
    
    def test_register_fallback(self):
        """Test registering fallback strategies."""
        manager = GracefulDegradationManager()
        
        def fallback_func():
            return "fallback"
        
        manager.register_fallback("test_feature", fallback_func)
        
        assert manager.fallback_strategies["test_feature"] == fallback_func
    
    def test_execute_with_fallback_success(self):
        """Test execution with successful primary function."""
        manager = GracefulDegradationManager()
        
        def primary_func(arg):
            return f"primary: {arg}"
        
        def fallback_func(arg):
            return f"fallback: {arg}"
        
        manager.register_fallback("test_feature", fallback_func)
        
        result = manager.execute_with_fallback("test_feature", primary_func, "test")
        
        assert result == "primary: test"
    
    def test_execute_with_fallback_failure(self):
        """Test execution with failed primary function using fallback."""
        manager = GracefulDegradationManager()
        
        def primary_func(arg):
            raise Exception("Primary failed")
        
        def fallback_func(arg):
            return f"fallback: {arg}"
        
        manager.register_fallback("test_feature", fallback_func)
        
        result = manager.execute_with_fallback("test_feature", primary_func, "test")
        
        assert result == "fallback: test"
    
    def test_execute_with_fallback_no_fallback(self):
        """Test execution with failed primary function and no fallback."""
        manager = GracefulDegradationManager()
        
        def primary_func(arg):
            raise ValueError("Primary failed")
        
        with pytest.raises(ValueError, match="Primary failed"):
            manager.execute_with_fallback("test_feature", primary_func, "test")


class TestErrorRecoveryManager:
    """Test cases for ErrorRecoveryManager."""
    
    def test_init(self):
        """Test ErrorRecoveryManager initialization."""
        manager = ErrorRecoveryManager("/test/repo")
        
        assert manager.repo_path == "/test/repo"
        assert isinstance(manager.cleanup_manager, WorktreeCleanupManager)
        assert isinstance(manager.degradation_manager, GracefulDegradationManager)
    
    @patch('subprocess.run')
    def test_check_git_availability_success(self, mock_run):
        """Test Git availability check with Git installed."""
        mock_run.return_value = MagicMock(returncode=0)
        
        manager = ErrorRecoveryManager()
        result = manager.check_git_availability()
        
        assert result is True
        mock_run.assert_called_with(
            ["git", "--version"],
            capture_output=True,
            text=True,
            timeout=5
        )
    
    @patch('subprocess.run')
    def test_check_git_availability_failure(self, mock_run):
        """Test Git availability check with Git not installed."""
        mock_run.return_value = MagicMock(returncode=1)
        
        manager = ErrorRecoveryManager()
        result = manager.check_git_availability()
        
        assert result is False
    
    @patch('subprocess.run')
    def test_check_git_availability_exception(self, mock_run):
        """Test Git availability check with exception."""
        mock_run.side_effect = FileNotFoundError()
        
        manager = ErrorRecoveryManager()
        result = manager.check_git_availability()
        
        assert result is False
    
    def test_safe_worktree_creation_success(self):
        """Test successful worktree creation."""
        manager = ErrorRecoveryManager()
        
        def creation_func():
            return "worktree created"
        
        result = manager.safe_worktree_creation(
            creation_func,
            "/test/worktree",
            "test-branch"
        )
        
        assert result == "worktree created"
    
    @patch.object(WorktreeCleanupManager, 'cleanup_failed_worktree')
    def test_safe_worktree_creation_failure_with_cleanup(self, mock_cleanup):
        """Test worktree creation failure with cleanup."""
        manager = ErrorRecoveryManager()
        
        def failing_creation_func():
            raise Exception("Creation failed")
        
        with pytest.raises(WorktreeCreationError):
            manager.safe_worktree_creation(
                failing_creation_func,
                "/test/worktree",
                "test-branch",
                cleanup_on_failure=True
            )
        
        # Cleanup should be called
        mock_cleanup.assert_called_once_with("/test/worktree", "test-branch")
    
    def test_safe_worktree_creation_failure_no_cleanup(self):
        """Test worktree creation failure without cleanup."""
        manager = ErrorRecoveryManager()
        
        def failing_creation_func():
            raise WorktreeCreationError("Creation failed")
        
        with pytest.raises(WorktreeCreationError, match="Creation failed"):
            manager.safe_worktree_creation(
                failing_creation_func,
                "/test/worktree",
                "test-branch",
                cleanup_on_failure=False
            )
    
    @patch.object(ErrorRecoveryManager, 'check_git_availability')
    def test_safe_git_operation_git_not_available(self, mock_check_git):
        """Test Git operation when Git is not available."""
        mock_check_git.return_value = False
        
        manager = ErrorRecoveryManager()
        
        def git_operation():
            return "success"
        
        with pytest.raises(GitRepositoryError, match="Git is not installed"):
            manager.safe_git_operation(git_operation, "test_operation")
    
    @patch.object(ErrorRecoveryManager, 'check_git_availability')
    def test_safe_git_operation_success(self, mock_check_git):
        """Test successful Git operation."""
        mock_check_git.return_value = True
        
        manager = ErrorRecoveryManager()
        
        def git_operation():
            return "git success"
        
        result = manager.safe_git_operation(git_operation, "test_operation")
        
        assert result == "git success"
    
    @patch.object(ErrorRecoveryManager, 'check_git_availability')
    @patch('time.sleep')
    def test_safe_git_operation_with_retry(self, mock_sleep, mock_check_git):
        """Test Git operation with retry on transient errors."""
        mock_check_git.return_value = True
        
        manager = ErrorRecoveryManager()
        
        call_count = 0
        
        def git_operation():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                # Simulate transient Git error
                raise subprocess.CalledProcessError(128, ["git", "test"])
            return "success after retry"
        
        result = manager.safe_git_operation(git_operation, "test_operation")
        
        assert result == "success after retry"
        assert call_count == 3
    
    @patch.object(ErrorRecoveryManager, 'check_git_availability')
    def test_safe_git_operation_non_transient_error(self, mock_check_git):
        """Test Git operation with non-transient error."""
        mock_check_git.return_value = True
        
        manager = ErrorRecoveryManager()
        
        def git_operation():
            # Non-transient Git error
            raise subprocess.CalledProcessError(1, ["git", "test"], stderr=b"fatal error")
        
        with pytest.raises(GitRepositoryError, match="Git operation 'test_operation' failed"):
            manager.safe_git_operation(git_operation, "test_operation")
    
    @patch.object(WorktreeCleanupManager, 'cleanup_partial_operations')
    def test_cleanup_all_partial_operations(self, mock_cleanup):
        """Test cleanup of all partial operations."""
        manager = ErrorRecoveryManager()
        
        manager.cleanup_all_partial_operations()
        
        mock_cleanup.assert_called_once()


class TestGlobalErrorRecoveryManager:
    """Test cases for global error recovery manager functions."""
    
    def test_get_error_recovery_manager_singleton(self):
        """Test that get_error_recovery_manager returns singleton."""
        manager1 = get_error_recovery_manager("/test/repo")
        manager2 = get_error_recovery_manager("/test/repo")
        
        assert manager1 is manager2
        assert manager1.repo_path == "/test/repo"
    
    def test_get_error_recovery_manager_different_paths(self):
        """Test that different repo paths create different managers."""
        manager1 = get_error_recovery_manager("/test/repo1")
        manager2 = get_error_recovery_manager("/test/repo2")
        
        assert manager1 is not manager2
        assert manager1.repo_path == "/test/repo1"
        assert manager2.repo_path == "/test/repo2"


class TestConvenienceDecorators:
    """Test cases for convenience decorators."""
    
    @patch('time.sleep')
    def test_with_git_retry_decorator(self, mock_sleep):
        """Test with_git_retry decorator."""
        call_count = 0
        
        @with_git_retry()
        def git_operation():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise subprocess.CalledProcessError(128, ["git"])
            return "success"
        
        result = git_operation()
        
        assert result == "success"
        assert call_count == 3
    
    @patch.object(ErrorRecoveryManager, 'safe_worktree_creation')
    def test_with_worktree_cleanup_decorator(self, mock_safe_creation):
        """Test with_worktree_cleanup decorator."""
        mock_safe_creation.return_value = "success"
        
        @with_worktree_cleanup("/test/worktree", "test-branch")
        def worktree_operation(arg):
            return f"operation: {arg}"
        
        result = worktree_operation("test")
        
        # Should call safe_worktree_creation with the wrapped function
        mock_safe_creation.assert_called_once()
        call_args = mock_safe_creation.call_args
        assert call_args[0][1] == "/test/worktree"
        assert call_args[0][2] == "test-branch"


class TestIntegrationScenarios:
    """Integration test scenarios for error recovery."""
    
    @patch('subprocess.run')
    @patch('shutil.rmtree')
    @patch('os.path.exists')
    def test_complete_worktree_creation_failure_recovery(self, mock_exists, mock_rmtree, mock_run):
        """Test complete worktree creation failure and recovery scenario."""
        mock_exists.return_value = True
        
        manager = ErrorRecoveryManager("/test/repo")
        
        def failing_creation():
            # This will trigger a subprocess.CalledProcessError
            raise subprocess.CalledProcessError(128, ["git", "worktree", "add"], stderr=b"worktree creation failed")
        
        with pytest.raises(WorktreeCreationError):
            manager.safe_worktree_creation(
                failing_creation,
                "/test/worktree",
                "test-branch"
            )
        
        # Verify cleanup was attempted
        mock_rmtree.assert_called_once_with("/test/worktree")
    
    @patch('subprocess.run')
    @patch('time.sleep')
    def test_git_operation_retry_and_recovery(self, mock_sleep, mock_run):
        """Test Git operation retry and eventual success."""
        # First two calls fail with transient error, third succeeds
        mock_run.side_effect = [
            # Git availability check
            MagicMock(returncode=0),
            # First attempt - transient failure
            subprocess.CalledProcessError(128, ["git", "branch"]),
            # Second attempt - transient failure
            subprocess.CalledProcessError(128, ["git", "branch"]),
            # Third attempt - success
            MagicMock(returncode=0, stdout="main\nfeature\n")
        ]
        
        manager = ErrorRecoveryManager("/test/repo")
        
        def git_branch_operation():
            result = subprocess.run(
                ["git", "branch"],
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout
        
        result = manager.safe_git_operation(git_branch_operation, "list_branches")
        
        assert result == "main\nfeature\n"
        # Should have slept twice (between retries)
        assert mock_sleep.call_count == 2
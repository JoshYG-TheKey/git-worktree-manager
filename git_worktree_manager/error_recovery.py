"""
Error recovery and cleanup mechanisms for Git Worktree Manager.

This module provides comprehensive error recovery functionality including:
- Retry logic for transient failures
- Enhanced cleanup for failed operations
- Graceful degradation for missing features
- Recovery strategies for various error scenarios
"""

import time
import logging
import subprocess
import shutil
import os
from pathlib import Path
from typing import Callable, Any, Optional, List, Dict, Union
from functools import wraps

from .exceptions import (
    WorktreeError,
    GitRepositoryError,
    FileSystemError,
    WorktreeCreationError,
    git_not_installed_error
)

logger = logging.getLogger(__name__)


class RetryConfig:
    """Configuration for retry behavior."""
    
    def __init__(
        self,
        max_attempts: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 10.0,
        backoff_multiplier: float = 2.0,
        retryable_exceptions: Optional[List[type]] = None
    ):
        """
        Initialize retry configuration.
        
        Args:
            max_attempts: Maximum number of retry attempts
            base_delay: Base delay between retries in seconds
            max_delay: Maximum delay between retries in seconds
            backoff_multiplier: Multiplier for exponential backoff
            retryable_exceptions: List of exception types that should trigger retries
        """
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.backoff_multiplier = backoff_multiplier
        self.retryable_exceptions = retryable_exceptions or [
            subprocess.TimeoutExpired,
            subprocess.CalledProcessError,
            OSError,
            IOError
        ]


def with_retry(config: Optional[RetryConfig] = None):
    """
    Decorator to add retry logic to functions.
    
    Args:
        config: RetryConfig instance, uses default if None
    """
    if config is None:
        config = RetryConfig()
    
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            last_exception = None
            
            for attempt in range(config.max_attempts):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    
                    # Check if this exception type should trigger a retry
                    if not any(isinstance(e, exc_type) for exc_type in config.retryable_exceptions):
                        # Not a retryable exception, re-raise immediately
                        raise
                    
                    # Don't retry on the last attempt
                    if attempt == config.max_attempts - 1:
                        break
                    
                    # Calculate delay with exponential backoff
                    delay = min(
                        config.base_delay * (config.backoff_multiplier ** attempt),
                        config.max_delay
                    )
                    
                    logger.warning(
                        f"Attempt {attempt + 1}/{config.max_attempts} failed for {func.__name__}: {e}. "
                        f"Retrying in {delay:.1f} seconds..."
                    )
                    
                    time.sleep(delay)
            
            # All retries exhausted, raise the last exception
            if last_exception:
                raise last_exception
        
        return wrapper
    return decorator


class WorktreeCleanupManager:
    """Manages cleanup operations for failed worktree operations."""
    
    def __init__(self, repo_path: str = "."):
        """
        Initialize cleanup manager.
        
        Args:
            repo_path: Path to the Git repository
        """
        self.repo_path = repo_path
        self.cleanup_registry: Dict[str, List[Callable]] = {}
    
    def register_cleanup(self, operation_id: str, cleanup_func: Callable) -> None:
        """
        Register a cleanup function for an operation.
        
        Args:
            operation_id: Unique identifier for the operation
            cleanup_func: Function to call for cleanup
        """
        if operation_id not in self.cleanup_registry:
            self.cleanup_registry[operation_id] = []
        self.cleanup_registry[operation_id].append(cleanup_func)
    
    def execute_cleanup(self, operation_id: str) -> None:
        """
        Execute all cleanup functions for an operation.
        
        Args:
            operation_id: Unique identifier for the operation
        """
        if operation_id not in self.cleanup_registry:
            return
        
        cleanup_functions = self.cleanup_registry[operation_id]
        
        for cleanup_func in reversed(cleanup_functions):  # Execute in reverse order
            try:
                cleanup_func()
                logger.debug(f"Successfully executed cleanup function for {operation_id}")
            except Exception as e:
                logger.warning(f"Cleanup function failed for {operation_id}: {e}")
        
        # Clear the registry for this operation
        del self.cleanup_registry[operation_id]
    
    def cleanup_failed_worktree(self, worktree_path: str, branch_name: Optional[str] = None) -> None:
        """
        Comprehensive cleanup for a failed worktree creation.
        
        Args:
            worktree_path: Path where the worktree was being created
            branch_name: Name of the branch (for additional cleanup)
        """
        cleanup_steps = []
        
        try:
            # Step 1: Remove the directory if it exists
            if os.path.exists(worktree_path):
                cleanup_steps.append(f"Removing directory: {worktree_path}")
                shutil.rmtree(worktree_path)
                logger.info(f"Removed failed worktree directory: {worktree_path}")
        except Exception as e:
            logger.warning(f"Failed to remove worktree directory {worktree_path}: {e}")
        
        try:
            # Step 2: Remove worktree from Git's tracking (force removal)
            cleanup_steps.append(f"Removing Git worktree tracking for: {worktree_path}")
            result = subprocess.run(
                ["git", "worktree", "remove", "--force", worktree_path],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=30
            )
            if result.returncode == 0:
                logger.info(f"Removed Git worktree tracking for: {worktree_path}")
        except subprocess.TimeoutExpired:
            logger.warning(f"Timeout while removing Git worktree tracking for: {worktree_path}")
        except Exception as e:
            logger.warning(f"Failed to remove Git worktree tracking for {worktree_path}: {e}")
        
        try:
            # Step 3: Clean up any orphaned branch if it was created
            if branch_name:
                cleanup_steps.append(f"Checking for orphaned branch: {branch_name}")
                # Check if branch exists and has no worktree
                result = subprocess.run(
                    ["git", "branch", "--list", branch_name],
                    cwd=self.repo_path,
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                
                if result.returncode == 0 and result.stdout.strip():
                    # Branch exists, check if it has any commits or is referenced
                    result = subprocess.run(
                        ["git", "log", "-1", "--oneline", branch_name],
                        cwd=self.repo_path,
                        capture_output=True,
                        text=True,
                        timeout=10
                    )
                    
                    # If the branch has no commits or only the initial commit from base branch,
                    # it might be safe to remove (but be conservative)
                    logger.info(f"Branch {branch_name} exists but cleanup is conservative - manual review recommended")
        except Exception as e:
            logger.warning(f"Failed to check/cleanup branch {branch_name}: {e}")
        
        logger.info(f"Completed worktree cleanup for {worktree_path}. Steps attempted: {cleanup_steps}")
    
    def cleanup_partial_operations(self) -> None:
        """Clean up any remaining partial operations."""
        for operation_id in list(self.cleanup_registry.keys()):
            logger.info(f"Cleaning up partial operation: {operation_id}")
            self.execute_cleanup(operation_id)


class GracefulDegradationManager:
    """Manages graceful degradation when features are unavailable."""
    
    def __init__(self):
        """Initialize graceful degradation manager."""
        self.feature_availability: Dict[str, bool] = {}
        self.fallback_strategies: Dict[str, Callable] = {}
    
    def check_feature_availability(self, feature_name: str, check_func: Callable) -> bool:
        """
        Check if a feature is available and cache the result.
        
        Args:
            feature_name: Name of the feature to check
            check_func: Function that returns True if feature is available
            
        Returns:
            True if feature is available, False otherwise
        """
        if feature_name not in self.feature_availability:
            try:
                self.feature_availability[feature_name] = check_func()
            except Exception:
                self.feature_availability[feature_name] = False
        
        return self.feature_availability[feature_name]
    
    def register_fallback(self, feature_name: str, fallback_func: Callable) -> None:
        """
        Register a fallback strategy for a feature.
        
        Args:
            feature_name: Name of the feature
            fallback_func: Function to call when feature is unavailable
        """
        self.fallback_strategies[feature_name] = fallback_func
    
    def execute_with_fallback(self, feature_name: str, primary_func: Callable, *args, **kwargs) -> Any:
        """
        Execute a function with fallback if the feature is unavailable.
        
        Args:
            feature_name: Name of the feature
            primary_func: Primary function to execute
            *args: Arguments for the function
            **kwargs: Keyword arguments for the function
            
        Returns:
            Result from primary function or fallback
        """
        try:
            return primary_func(*args, **kwargs)
        except Exception as e:
            if feature_name in self.fallback_strategies:
                logger.warning(f"Primary function failed for {feature_name}: {e}. Using fallback.")
                return self.fallback_strategies[feature_name](*args, **kwargs)
            else:
                raise


class ErrorRecoveryManager:
    """Main error recovery manager that coordinates all recovery mechanisms."""
    
    def __init__(self, repo_path: str = "."):
        """
        Initialize error recovery manager.
        
        Args:
            repo_path: Path to the Git repository
        """
        self.repo_path = repo_path
        self.cleanup_manager = WorktreeCleanupManager(repo_path)
        self.degradation_manager = GracefulDegradationManager()
        self._setup_fallback_strategies()
    
    def _setup_fallback_strategies(self) -> None:
        """Set up default fallback strategies."""
        # Git availability fallback
        def git_not_available_fallback(*args, **kwargs):
            raise git_not_installed_error()
        
        self.degradation_manager.register_fallback("git", git_not_available_fallback)
        
        # Rich UI fallback (use plain text)
        def plain_text_fallback(message: str, *args, **kwargs):
            print(message)
        
        self.degradation_manager.register_fallback("rich_ui", plain_text_fallback)
    
    def check_git_availability(self) -> bool:
        """Check if Git is available."""
        def check_git():
            result = subprocess.run(
                ["git", "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0
        
        return self.degradation_manager.check_feature_availability("git", check_git)
    
    def safe_worktree_creation(
        self,
        creation_func: Callable,
        worktree_path: str,
        branch_name: Optional[str] = None,
        cleanup_on_failure: bool = True
    ) -> Any:
        """
        Safely execute worktree creation with comprehensive error handling.
        
        Args:
            creation_func: Function that creates the worktree
            worktree_path: Path where worktree will be created
            branch_name: Name of the branch being created
            cleanup_on_failure: Whether to cleanup on failure
            
        Returns:
            Result from creation function
        """
        operation_id = f"worktree_creation_{int(time.time())}"
        
        try:
            # Register cleanup functions
            if cleanup_on_failure:
                self.cleanup_manager.register_cleanup(
                    operation_id,
                    lambda: self.cleanup_manager.cleanup_failed_worktree(worktree_path, branch_name)
                )
            
            # Execute the creation function with retry logic
            retry_config = RetryConfig(
                max_attempts=2,  # Conservative retry for worktree creation
                base_delay=1.0,
                retryable_exceptions=[subprocess.TimeoutExpired, OSError]
            )
            
            @with_retry(retry_config)
            def execute_creation():
                return creation_func()
            
            result = execute_creation()
            
            # Success - clear cleanup registry
            if operation_id in self.cleanup_manager.cleanup_registry:
                del self.cleanup_manager.cleanup_registry[operation_id]
            
            return result
            
        except Exception as e:
            # Failure - execute cleanup
            if cleanup_on_failure:
                logger.error(f"Worktree creation failed: {e}. Executing cleanup...")
                self.cleanup_manager.execute_cleanup(operation_id)
            
            # Re-raise with enhanced error information
            if isinstance(e, WorktreeError):
                raise
            else:
                raise WorktreeCreationError(
                    f"Failed to create worktree at '{worktree_path}': {e}",
                    worktree_path=worktree_path,
                    branch_name=branch_name,
                    user_guidance="Check permissions and disk space, then try again"
                )
    
    def safe_git_operation(
        self,
        operation_func: Callable,
        operation_name: str,
        retry_config: Optional[RetryConfig] = None
    ) -> Any:
        """
        Safely execute a Git operation with retry logic.
        
        Args:
            operation_func: Function that performs the Git operation
            operation_name: Name of the operation for logging
            retry_config: Custom retry configuration
            
        Returns:
            Result from operation function
        """
        if not self.check_git_availability():
            raise git_not_installed_error()
        
        if retry_config is None:
            retry_config = RetryConfig(
                max_attempts=3,
                base_delay=0.5,
                retryable_exceptions=[
                    subprocess.TimeoutExpired,
                    subprocess.CalledProcessError
                ]
            )
        
        @with_retry(retry_config)
        def execute_operation():
            try:
                return operation_func()
            except subprocess.CalledProcessError as e:
                # Check if this is a transient error that should be retried
                if e.returncode in [128, 129]:  # Common Git transient error codes
                    logger.warning(f"Transient Git error in {operation_name}: {e}")
                    raise  # Will be caught by retry logic
                else:
                    # Non-transient error, don't retry
                    raise GitRepositoryError(
                        f"Git operation '{operation_name}' failed: {e}",
                        git_command=str(e.cmd) if hasattr(e, 'cmd') else None,
                        exit_code=e.returncode,
                        stderr=e.stderr.decode() if e.stderr else None
                    )
        
        return execute_operation()
    
    def cleanup_all_partial_operations(self) -> None:
        """Clean up all partial operations."""
        self.cleanup_manager.cleanup_partial_operations()


# Global error recovery manager instance
_error_recovery_manager: Optional[ErrorRecoveryManager] = None


def get_error_recovery_manager(repo_path: str = ".") -> ErrorRecoveryManager:
    """
    Get the global error recovery manager instance.
    
    Args:
        repo_path: Path to the Git repository
        
    Returns:
        ErrorRecoveryManager instance
    """
    global _error_recovery_manager
    if _error_recovery_manager is None or _error_recovery_manager.repo_path != repo_path:
        _error_recovery_manager = ErrorRecoveryManager(repo_path)
    return _error_recovery_manager


# Convenience decorators
def with_git_retry(retry_config: Optional[RetryConfig] = None):
    """Decorator for Git operations with retry logic."""
    return with_retry(retry_config or RetryConfig(
        max_attempts=3,
        base_delay=0.5,
        retryable_exceptions=[subprocess.TimeoutExpired, subprocess.CalledProcessError]
    ))


def with_worktree_cleanup(worktree_path: str, branch_name: Optional[str] = None):
    """Decorator that adds automatic cleanup for worktree operations."""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            recovery_manager = get_error_recovery_manager()
            return recovery_manager.safe_worktree_creation(
                lambda: func(*args, **kwargs),
                worktree_path,
                branch_name
            )
        return wrapper
    return decorator
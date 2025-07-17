"""
Custom exception hierarchy for Git Worktree Manager.

This module defines a comprehensive exception hierarchy that provides
clear error messages, user guidance, and proper error categorization
for all worktree operations.
"""

import logging
from typing import Any, Dict, Optional

# Configure logging for error handling
logger = logging.getLogger(__name__)


class WorktreeError(Exception):
    """
    Base exception for all worktree operations.

    This is the root exception class that all other worktree-related
    exceptions inherit from. It provides common functionality for
    error message formatting and user guidance.
    """

    def __init__(
        self,
        message: str,
        user_guidance: Optional[str] = None,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize WorktreeError with enhanced error information.

        Args:
            message: The error message describing what went wrong
            user_guidance: Optional guidance for the user on how to resolve the issue
            error_code: Optional error code for programmatic error handling
            details: Optional dictionary with additional error context
        """
        super().__init__(message)
        self.message = message
        self.user_guidance = user_guidance
        self.error_code = error_code
        self.details = details or {}

        # Log the error for debugging
        logger.error(
            f"WorktreeError: {message}",
            extra={
                "error_code": error_code,
                "user_guidance": user_guidance,
                "details": self.details,
            },
        )

    def __str__(self) -> str:
        """Return formatted error message with user guidance."""
        result = self.message
        if self.user_guidance:
            result += f"\n\nSuggestion: {self.user_guidance}"
        return result

    def get_formatted_message(self) -> str:
        """Get a formatted error message suitable for CLI display."""
        lines = [f"Error: {self.message}"]

        if self.error_code:
            lines.append(f"Code: {self.error_code}")

        if self.user_guidance:
            lines.append(f"Suggestion: {self.user_guidance}")

        if self.details:
            lines.append("Details:")
            for key, value in self.details.items():
                lines.append(f"  {key}: {value}")

        return "\n".join(lines)


class GitRepositoryError(WorktreeError):
    """
    Exception raised for Git repository related errors.

    This includes errors like:
    - Not being in a Git repository
    - Git command failures
    - Repository corruption
    - Git not being installed
    """

    def __init__(
        self,
        message: str,
        git_command: Optional[str] = None,
        exit_code: Optional[int] = None,
        stderr: Optional[str] = None,
        **kwargs,
    ):
        """
        Initialize GitRepositoryError with Git-specific context.

        Args:
            message: The error message
            git_command: The Git command that failed
            exit_code: The exit code from the Git command
            stderr: The stderr output from the Git command
            **kwargs: Additional arguments passed to WorktreeError
        """
        details = kwargs.get("details", {})
        if git_command:
            details["git_command"] = git_command
        if exit_code is not None:
            details["exit_code"] = exit_code
        if stderr:
            details["stderr"] = stderr

        kwargs["details"] = details
        super().__init__(message, **kwargs)


class FileSystemError(WorktreeError):
    """
    Exception raised for file system related errors.

    This includes errors like:
    - Permission denied
    - Disk space issues
    - Invalid paths
    - Directory creation failures
    """

    def __init__(
        self,
        message: str,
        path: Optional[str] = None,
        operation: Optional[str] = None,
        **kwargs,
    ):
        """
        Initialize FileSystemError with file system context.

        Args:
            message: The error message
            path: The file system path involved in the error
            operation: The operation that was being performed
            **kwargs: Additional arguments passed to WorktreeError
        """
        details = kwargs.get("details", {})
        if path:
            details["path"] = path
        if operation:
            details["operation"] = operation

        kwargs["details"] = details
        super().__init__(message, **kwargs)


class UserInputError(WorktreeError):
    """
    Exception raised for user input validation errors.

    This includes errors like:
    - Invalid branch names
    - Conflicting worktree names
    - Invalid configuration values
    - Invalid command-line arguments
    """

    def __init__(
        self,
        message: str,
        input_value: Optional[str] = None,
        valid_options: Optional[list] = None,
        **kwargs,
    ):
        """
        Initialize UserInputError with input validation context.

        Args:
            message: The error message
            input_value: The invalid input value
            valid_options: List of valid options (if applicable)
            **kwargs: Additional arguments passed to WorktreeError
        """
        details = kwargs.get("details", {})
        if input_value is not None:
            details["input_value"] = input_value
        if valid_options:
            details["valid_options"] = valid_options

        kwargs["details"] = details
        super().__init__(message, **kwargs)


class ConfigError(WorktreeError):
    """
    Exception raised for configuration-related errors.

    This includes errors like:
    - Configuration file parsing errors
    - Invalid configuration values
    - Configuration file access issues
    """

    def __init__(
        self,
        message: str,
        config_file: Optional[str] = None,
        config_key: Optional[str] = None,
        **kwargs,
    ):
        """
        Initialize ConfigError with configuration context.

        Args:
            message: The error message
            config_file: The configuration file involved
            config_key: The configuration key that caused the error
            **kwargs: Additional arguments passed to WorktreeError
        """
        details = kwargs.get("details", {})
        if config_file:
            details["config_file"] = config_file
        if config_key:
            details["config_key"] = config_key

        kwargs["details"] = details
        super().__init__(message, **kwargs)


class ConfigValidationError(ConfigError):
    """
    Exception raised for configuration validation errors.

    This is a specialized ConfigError for validation-specific issues.
    """

    pass


class WorktreeManagerError(WorktreeError):
    """
    Exception raised for WorktreeManager operations.

    This is the base exception for high-level worktree management
    operations that may involve multiple subsystems.
    """

    pass


class WorktreeCreationError(WorktreeManagerError):
    """
    Exception raised when worktree creation fails.

    This includes errors during the complete worktree creation workflow,
    including validation, Git operations, and file system operations.
    """

    def __init__(
        self,
        message: str,
        worktree_path: Optional[str] = None,
        branch_name: Optional[str] = None,
        base_branch: Optional[str] = None,
        **kwargs,
    ):
        """
        Initialize WorktreeCreationError with creation context.

        Args:
            message: The error message
            worktree_path: The path where the worktree was being created
            branch_name: The branch name for the worktree
            base_branch: The base branch for the worktree
            **kwargs: Additional arguments passed to WorktreeManagerError
        """
        details = kwargs.get("details", {})
        if worktree_path:
            details["worktree_path"] = worktree_path
        if branch_name:
            details["branch_name"] = branch_name
        if base_branch:
            details["base_branch"] = base_branch

        kwargs["details"] = details
        super().__init__(message, **kwargs)


class WorktreeListingError(WorktreeManagerError):
    """
    Exception raised when worktree listing operations fail.

    This includes errors during worktree discovery, status calculation,
    and diff summary generation.
    """

    pass


class UIError(WorktreeError):
    """
    Exception raised for user interface related errors.

    This includes errors in Rich UI components, interactive prompts,
    and display formatting.
    """

    def __init__(self, message: str, component: Optional[str] = None, **kwargs):
        """
        Initialize UIError with UI component context.

        Args:
            message: The error message
            component: The UI component that caused the error
            **kwargs: Additional arguments passed to WorktreeError
        """
        details = kwargs.get("details", {})
        if component:
            details["component"] = component

        kwargs["details"] = details
        super().__init__(message, **kwargs)


# Convenience functions for common error scenarios
def git_not_installed_error() -> GitRepositoryError:
    """Create a standardized error for when Git is not installed."""
    return GitRepositoryError(
        "Git is not installed or not available in PATH",
        user_guidance="Please install Git and ensure it's available in your PATH",
        error_code="GIT_NOT_INSTALLED",
    )


def not_git_repository_error(path: str = ".") -> GitRepositoryError:
    """Create a standardized error for when not in a Git repository."""
    return GitRepositoryError(
        f"'{path}' is not a Git repository",
        user_guidance="Please run this command from within a Git repository",
        error_code="NOT_GIT_REPOSITORY",
        details={"path": path},
    )


def invalid_branch_name_error(branch_name: str) -> UserInputError:
    """Create a standardized error for invalid branch names."""
    return UserInputError(
        f"Invalid branch name: '{branch_name}'",
        user_guidance="Branch names cannot contain spaces or special characters like ~, ^, :, ?, *, [",
        error_code="INVALID_BRANCH_NAME",
        input_value=branch_name,
    )


def worktree_already_exists_error(path: str) -> WorktreeCreationError:
    """Create a standardized error for when a worktree already exists."""
    return WorktreeCreationError(
        f"A worktree already exists at '{path}'",
        user_guidance="Choose a different location or remove the existing worktree",
        error_code="WORKTREE_EXISTS",
        worktree_path=path,
    )


def permission_denied_error(path: str, operation: str) -> FileSystemError:
    """Create a standardized error for permission denied."""
    return FileSystemError(
        f"Permission denied: cannot {operation} '{path}'",
        user_guidance="Check file permissions or run with appropriate privileges",
        error_code="PERMISSION_DENIED",
        path=path,
        operation=operation,
    )

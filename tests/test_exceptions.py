"""Unit tests for the exceptions module."""

from unittest.mock import patch

from git_worktree_manager.exceptions import (
    ConfigError,
    ConfigValidationError,
    FileSystemError,
    GitRepositoryError,
    UIError,
    UserInputError,
    WorktreeCreationError,
    WorktreeError,
    WorktreeListingError,
    WorktreeManagerError,
    git_not_installed_error,
    invalid_branch_name_error,
    not_git_repository_error,
    permission_denied_error,
    worktree_already_exists_error,
)


class TestWorktreeError:
    """Test cases for the base WorktreeError class."""

    def test_basic_error_creation(self):
        """Test basic WorktreeError creation."""
        error = WorktreeError("Test error message")
        assert str(error) == "Test error message"
        assert error.message == "Test error message"
        assert error.user_guidance is None
        assert error.error_code is None
        assert error.details == {}

    def test_error_with_user_guidance(self):
        """Test WorktreeError with user guidance."""
        error = WorktreeError("Test error message", user_guidance="Try this solution")
        expected_str = "Test error message\n\nSuggestion: Try this solution"
        assert str(error) == expected_str
        assert error.user_guidance == "Try this solution"

    def test_error_with_all_parameters(self):
        """Test WorktreeError with all parameters."""
        details = {"key1": "value1", "key2": "value2"}
        error = WorktreeError(
            "Test error message",
            user_guidance="Try this solution",
            error_code="TEST_ERROR",
            details=details,
        )

        assert error.message == "Test error message"
        assert error.user_guidance == "Try this solution"
        assert error.error_code == "TEST_ERROR"
        assert error.details == details

    def test_formatted_message(self):
        """Test get_formatted_message method."""
        details = {"path": "/test/path", "operation": "create"}
        error = WorktreeError(
            "Test error message",
            user_guidance="Try this solution",
            error_code="TEST_ERROR",
            details=details,
        )

        formatted = error.get_formatted_message()
        expected_lines = [
            "Error: Test error message",
            "Code: TEST_ERROR",
            "Suggestion: Try this solution",
            "Details:",
            "  path: /test/path",
            "  operation: create",
        ]
        assert formatted == "\n".join(expected_lines)

    @patch("git_worktree_manager.exceptions.logger")
    def test_error_logging(self, mock_logger):
        """Test that errors are logged when created."""
        details = {"test": "data"}
        error = WorktreeError(
            "Test error message",
            user_guidance="Try this solution",
            error_code="TEST_ERROR",
            details=details,
        )

        mock_logger.error.assert_called_once_with(
            "WorktreeError: Test error message",
            extra={
                "error_code": "TEST_ERROR",
                "user_guidance": "Try this solution",
                "details": details,
            },
        )


class TestGitRepositoryError:
    """Test cases for GitRepositoryError."""

    def test_basic_git_error(self):
        """Test basic GitRepositoryError creation."""
        error = GitRepositoryError("Git command failed")
        assert isinstance(error, WorktreeError)
        assert error.message == "Git command failed"

    def test_git_error_with_command_details(self):
        """Test GitRepositoryError with Git command details."""
        error = GitRepositoryError(
            "Git command failed",
            git_command="git branch",
            exit_code=128,
            stderr="fatal: not a git repository",
        )

        assert error.details["git_command"] == "git branch"
        assert error.details["exit_code"] == 128
        assert error.details["stderr"] == "fatal: not a git repository"

    def test_git_error_inheritance(self):
        """Test GitRepositoryError inheritance."""
        error = GitRepositoryError("Test error")
        assert isinstance(error, WorktreeError)
        assert isinstance(error, Exception)


class TestFileSystemError:
    """Test cases for FileSystemError."""

    def test_basic_filesystem_error(self):
        """Test basic FileSystemError creation."""
        error = FileSystemError("File operation failed")
        assert isinstance(error, WorktreeError)
        assert error.message == "File operation failed"

    def test_filesystem_error_with_path_details(self):
        """Test FileSystemError with path and operation details."""
        error = FileSystemError(
            "Permission denied", path="/test/path", operation="create_directory"
        )

        assert error.details["path"] == "/test/path"
        assert error.details["operation"] == "create_directory"

    def test_filesystem_error_inheritance(self):
        """Test FileSystemError inheritance."""
        error = FileSystemError("Test error")
        assert isinstance(error, WorktreeError)
        assert isinstance(error, Exception)


class TestUserInputError:
    """Test cases for UserInputError."""

    def test_basic_user_input_error(self):
        """Test basic UserInputError creation."""
        error = UserInputError("Invalid input")
        assert isinstance(error, WorktreeError)
        assert error.message == "Invalid input"

    def test_user_input_error_with_validation_details(self):
        """Test UserInputError with validation details."""
        valid_options = ["option1", "option2", "option3"]
        error = UserInputError(
            "Invalid choice", input_value="invalid_option", valid_options=valid_options
        )

        assert error.details["input_value"] == "invalid_option"
        assert error.details["valid_options"] == valid_options

    def test_user_input_error_inheritance(self):
        """Test UserInputError inheritance."""
        error = UserInputError("Test error")
        assert isinstance(error, WorktreeError)
        assert isinstance(error, Exception)


class TestConfigError:
    """Test cases for ConfigError."""

    def test_basic_config_error(self):
        """Test basic ConfigError creation."""
        error = ConfigError("Configuration error")
        assert isinstance(error, WorktreeError)
        assert error.message == "Configuration error"

    def test_config_error_with_file_details(self):
        """Test ConfigError with configuration file details."""
        error = ConfigError(
            "Invalid configuration",
            config_file="/path/to/config.toml",
            config_key="worktree.default_path",
        )

        assert error.details["config_file"] == "/path/to/config.toml"
        assert error.details["config_key"] == "worktree.default_path"

    def test_config_error_inheritance(self):
        """Test ConfigError inheritance."""
        error = ConfigError("Test error")
        assert isinstance(error, WorktreeError)
        assert isinstance(error, Exception)


class TestConfigValidationError:
    """Test cases for ConfigValidationError."""

    def test_config_validation_error_inheritance(self):
        """Test ConfigValidationError inherits from ConfigError."""
        error = ConfigValidationError("Validation error")
        assert isinstance(error, ConfigError)
        assert isinstance(error, WorktreeError)
        assert isinstance(error, Exception)


class TestWorktreeManagerError:
    """Test cases for WorktreeManagerError."""

    def test_worktree_manager_error_inheritance(self):
        """Test WorktreeManagerError inheritance."""
        error = WorktreeManagerError("Manager error")
        assert isinstance(error, WorktreeError)
        assert isinstance(error, Exception)


class TestWorktreeCreationError:
    """Test cases for WorktreeCreationError."""

    def test_basic_worktree_creation_error(self):
        """Test basic WorktreeCreationError creation."""
        error = WorktreeCreationError("Creation failed")
        assert isinstance(error, WorktreeManagerError)
        assert error.message == "Creation failed"

    def test_worktree_creation_error_with_details(self):
        """Test WorktreeCreationError with creation details."""
        error = WorktreeCreationError(
            "Failed to create worktree",
            worktree_path="/path/to/worktree",
            branch_name="feature-branch",
            base_branch="main",
        )

        assert error.details["worktree_path"] == "/path/to/worktree"
        assert error.details["branch_name"] == "feature-branch"
        assert error.details["base_branch"] == "main"

    def test_worktree_creation_error_inheritance(self):
        """Test WorktreeCreationError inheritance."""
        error = WorktreeCreationError("Test error")
        assert isinstance(error, WorktreeManagerError)
        assert isinstance(error, WorktreeError)
        assert isinstance(error, Exception)


class TestWorktreeListingError:
    """Test cases for WorktreeListingError."""

    def test_worktree_listing_error_inheritance(self):
        """Test WorktreeListingError inheritance."""
        error = WorktreeListingError("Listing error")
        assert isinstance(error, WorktreeManagerError)
        assert isinstance(error, WorktreeError)
        assert isinstance(error, Exception)


class TestUIError:
    """Test cases for UIError."""

    def test_basic_ui_error(self):
        """Test basic UIError creation."""
        error = UIError("UI component failed")
        assert isinstance(error, WorktreeError)
        assert error.message == "UI component failed"

    def test_ui_error_with_component_details(self):
        """Test UIError with component details."""
        error = UIError("Rich table rendering failed", component="worktree_table")

        assert error.details["component"] == "worktree_table"

    def test_ui_error_inheritance(self):
        """Test UIError inheritance."""
        error = UIError("Test error")
        assert isinstance(error, WorktreeError)
        assert isinstance(error, Exception)


class TestConvenienceFunctions:
    """Test cases for convenience error creation functions."""

    def test_git_not_installed_error(self):
        """Test git_not_installed_error convenience function."""
        error = git_not_installed_error()

        assert isinstance(error, GitRepositoryError)
        assert "Git is not installed" in error.message
        assert "install Git" in error.user_guidance
        assert error.error_code == "GIT_NOT_INSTALLED"

    def test_not_git_repository_error(self):
        """Test not_git_repository_error convenience function."""
        error = not_git_repository_error("/test/path")

        assert isinstance(error, GitRepositoryError)
        assert "'/test/path' is not a Git repository" in error.message
        assert "run this command from within a Git repository" in error.user_guidance
        assert error.error_code == "NOT_GIT_REPOSITORY"
        assert error.details["path"] == "/test/path"

    def test_not_git_repository_error_default_path(self):
        """Test not_git_repository_error with default path."""
        error = not_git_repository_error()

        assert "'.' is not a Git repository" in error.message
        assert error.details["path"] == "."

    def test_invalid_branch_name_error(self):
        """Test invalid_branch_name_error convenience function."""
        error = invalid_branch_name_error("invalid~branch")

        assert isinstance(error, UserInputError)
        assert "Invalid branch name: 'invalid~branch'" in error.message
        assert "cannot contain spaces or special characters" in error.user_guidance
        assert error.error_code == "INVALID_BRANCH_NAME"
        assert error.details["input_value"] == "invalid~branch"

    def test_worktree_already_exists_error(self):
        """Test worktree_already_exists_error convenience function."""
        error = worktree_already_exists_error("/path/to/worktree")

        assert isinstance(error, WorktreeCreationError)
        assert "A worktree already exists at '/path/to/worktree'" in error.message
        assert "Choose a different location" in error.user_guidance
        assert error.error_code == "WORKTREE_EXISTS"
        assert error.details["worktree_path"] == "/path/to/worktree"

    def test_permission_denied_error(self):
        """Test permission_denied_error convenience function."""
        error = permission_denied_error("/test/path", "create")

        assert isinstance(error, FileSystemError)
        assert "Permission denied: cannot create '/test/path'" in error.message
        assert "Check file permissions" in error.user_guidance
        assert error.error_code == "PERMISSION_DENIED"
        assert error.details["path"] == "/test/path"
        assert error.details["operation"] == "create"


class TestErrorMessageFormatting:
    """Test cases for error message formatting."""

    def test_error_str_without_guidance(self):
        """Test __str__ method without user guidance."""
        error = WorktreeError("Simple error message")
        assert str(error) == "Simple error message"

    def test_error_str_with_guidance(self):
        """Test __str__ method with user guidance."""
        error = WorktreeError("Error occurred", user_guidance="Try this fix")
        expected = "Error occurred\n\nSuggestion: Try this fix"
        assert str(error) == expected

    def test_formatted_message_minimal(self):
        """Test get_formatted_message with minimal information."""
        error = WorktreeError("Simple error")
        formatted = error.get_formatted_message()
        assert formatted == "Error: Simple error"

    def test_formatted_message_complete(self):
        """Test get_formatted_message with complete information."""
        error = WorktreeError(
            "Complex error",
            user_guidance="Try this solution",
            error_code="COMPLEX_ERROR",
            details={"detail1": "value1", "detail2": "value2"},
        )

        formatted = error.get_formatted_message()
        lines = formatted.split("\n")

        assert "Error: Complex error" in lines
        assert "Code: COMPLEX_ERROR" in lines
        assert "Suggestion: Try this solution" in lines
        assert "Details:" in lines
        assert "  detail1: value1" in lines
        assert "  detail2: value2" in lines


class TestErrorLogging:
    """Test cases for error logging functionality."""

    @patch("git_worktree_manager.exceptions.logger")
    def test_error_logging_with_all_details(self, mock_logger):
        """Test that all error details are logged."""
        details = {"key": "value"}
        error = WorktreeError(
            "Test message",
            user_guidance="Test guidance",
            error_code="TEST_CODE",
            details=details,
        )

        mock_logger.error.assert_called_once_with(
            "WorktreeError: Test message",
            extra={
                "error_code": "TEST_CODE",
                "user_guidance": "Test guidance",
                "details": details,
            },
        )

    @patch("git_worktree_manager.exceptions.logger")
    def test_error_logging_minimal(self, mock_logger):
        """Test logging with minimal error information."""
        error = WorktreeError("Simple message")

        mock_logger.error.assert_called_once_with(
            "WorktreeError: Simple message",
            extra={"error_code": None, "user_guidance": None, "details": {}},
        )

    @patch("git_worktree_manager.exceptions.logger")
    def test_derived_error_logging(self, mock_logger):
        """Test that derived errors also trigger logging."""
        error = GitRepositoryError("Git error")

        # Should still log as WorktreeError since that's the base class
        mock_logger.error.assert_called_once()
        call_args = mock_logger.error.call_args
        assert "WorktreeError: Git error" in call_args[0][0]

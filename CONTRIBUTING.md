# Contributing to Git Worktree Manager

Thank you for your interest in contributing to Git Worktree Manager! This guide will help you get started with development, testing, and contributing to the project.

## Quick Start

1. **Clone and setup**:
   ```bash
   git clone <repository-url>
   cd git-worktree-manager
   make install-dev
   make setup-alias
   ```

2. **Test your setup**:
   ```bash
   gitwm --help
   make test
   ```

## Development Environment

### Prerequisites

- Python 3.8 or higher
- Git 2.15 or higher
- A terminal that supports Rich formatting

### Installation

```bash
# Install in development mode with all dependencies
make install-dev

# Or manually:
pip install -e ".[dev]"
```

### Shell Alias

Create the convenient `gitwm` alias:

```bash
make setup-alias
```

This adds `alias gitwm='git-worktree-manager'` to your shell configuration.

## Project Structure

```
git-worktree-manager/
├── git_worktree_manager/          # Main package
│   ├── __init__.py
│   ├── cli.py                     # CLI entry point
│   ├── worktree_manager.py        # Core business logic
│   ├── git_ops.py                 # Git operations
│   ├── ui_controller.py           # Rich UI components
│   ├── config.py                  # Configuration management
│   ├── models.py                  # Data models
│   ├── cache.py                   # Caching layer
│   ├── exceptions.py              # Custom exceptions
│   └── error_recovery.py          # Error handling
├── tests/                         # Test suite
│   ├── test_*.py                  # Unit tests
│   └── test_integration.py        # Integration tests
├── .kiro/specs/                   # Feature specifications
├── README.md                      # User documentation
├── CONTRIBUTING.md                # This file
├── Makefile                       # Development commands
└── pyproject.toml                 # Package configuration
```

## Development Workflow

### 1. Making Changes

1. **Create a feature branch**:
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes** following the coding standards below

3. **Test your changes**:
   ```bash
   make test
   make lint
   ```

4. **Format your code**:
   ```bash
   make format
   ```

### 2. Testing

#### Running Tests

```bash
# Run all tests
make test

# Run with coverage
make test-coverage

# Run specific test file
pytest tests/test_git_ops.py -v

# Run specific test
pytest tests/test_git_ops.py::test_get_branches -v
```

#### Test Structure

- **Unit Tests**: Test individual components in isolation
- **Integration Tests**: Test component interactions
- **Performance Tests**: Validate performance requirements

#### Writing Tests

```python
# Example unit test
def test_git_operations_branch_listing(mock_subprocess):
    """Test that branch listing parses Git output correctly."""
    mock_subprocess.return_value.stdout = "main\nfeature/test\n"
    
    git_ops = GitOperations()
    branches = git_ops.get_branches()
    
    assert "main" in branches
    assert "feature/test" in branches
```

### 3. Code Quality

#### Linting and Formatting

```bash
# Check code quality
make lint

# Auto-format code
make format

# Manual commands
black .                    # Format with Black
ruff check .              # Lint with Ruff
mypy git_worktree_manager/ # Type checking
```

#### Code Standards

- **Python Style**: Follow PEP 8, enforced by Black
- **Type Hints**: Use type hints for all public functions
- **Docstrings**: Document all public classes and methods
- **Error Handling**: Use custom exceptions with clear messages
- **Testing**: Maintain >90% test coverage

#### Example Code Style

```python
from typing import List, Optional
from dataclasses import dataclass

@dataclass
class WorktreeInfo:
    """Information about a Git worktree.
    
    Attributes:
        path: Filesystem path to the worktree
        branch: Git branch name
        commit_hash: Latest commit hash
    """
    path: str
    branch: str
    commit_hash: str
    
    def is_clean(self) -> bool:
        """Check if worktree has no uncommitted changes."""
        # Implementation here
        pass
```

## Architecture Overview

### Core Components

1. **CLI Layer** (`cli.py`): Command-line interface using Click
2. **Business Logic** (`worktree_manager.py`): Core worktree operations
3. **Git Interface** (`git_ops.py`): Git command execution and parsing
4. **UI Layer** (`ui_controller.py`): Rich-based user interface
5. **Configuration** (`config.py`): Settings and preferences
6. **Data Models** (`models.py`): Type-safe data structures

### Design Principles

- **Separation of Concerns**: Each module has a single responsibility
- **Dependency Injection**: Components receive dependencies explicitly
- **Error Handling**: Graceful failure with helpful error messages
- **Performance**: Efficient Git operations with caching
- **User Experience**: Rich, interactive interface

## Common Development Tasks

### Adding a New Feature

1. **Update Requirements**: Add to `.kiro/specs/git-worktree-manager/requirements.md`
2. **Design**: Update design document if needed
3. **Implement**: Write code following existing patterns
4. **Test**: Add comprehensive tests
5. **Document**: Update README and docstrings

### Adding a New Git Operation

```python
# In git_ops.py
def new_git_operation(self, param: str) -> ResultType:
    """Description of what this operation does.
    
    Args:
        param: Description of parameter
        
    Returns:
        Description of return value
        
    Raises:
        GitRepositoryError: When Git operation fails
    """
    try:
        result = self._run_git_command(['git', 'command', param])
        return self._parse_result(result)
    except subprocess.CalledProcessError as e:
        raise GitRepositoryError(f"Git operation failed: {e}")
```

### Adding a New UI Component

```python
# In ui_controller.py
def display_new_component(self, data: DataType) -> None:
    """Display a new UI component.
    
    Args:
        data: Data to display
    """
    table = Table(title="Component Title")
    table.add_column("Column 1")
    table.add_column("Column 2")
    
    for item in data:
        table.add_row(item.field1, item.field2)
    
    self.console.print(table)
```

## Debugging

### Common Issues

1. **Git Command Failures**: Check Git version and repository state
2. **Rich Display Issues**: Verify terminal compatibility
3. **Path Issues**: Test with various filesystem layouts
4. **Performance**: Profile with large repositories

### Debug Mode

```bash
# Enable verbose logging
export WORKTREE_DEBUG=1
gitwm

# Run with Python debugger
python -m pdb -m git_worktree_manager.cli
```

### Testing with Different Git Setups

```bash
# Create test repository
mkdir test-repo && cd test-repo
git init
git commit --allow-empty -m "Initial commit"

# Test the tool
gitwm
```

## Performance Considerations

### Git Operations

- Use `--porcelain` flags for consistent output
- Batch operations when possible
- Cache expensive operations
- Use `git rev-parse` for validation

### UI Performance

- Lazy load large datasets
- Use Rich's live display for progress
- Minimize expensive operations during interaction

### Memory Usage

- Stream large command outputs
- Clean up temporary resources
- Limit cache sizes

## Release Process

1. **Update Version**: Bump version in `pyproject.toml`
2. **Update Changelog**: Document changes
3. **Test**: Run full test suite
4. **Tag Release**: Create Git tag
5. **Build**: `python -m build`
6. **Publish**: Upload to PyPI

## Getting Help

- **Issues**: Open GitHub issues for bugs or feature requests
- **Discussions**: Use GitHub discussions for questions
- **Code Review**: All changes require review before merging

## Code of Conduct

- Be respectful and inclusive
- Focus on constructive feedback
- Help others learn and grow
- Follow project guidelines

Thank you for contributing to Git Worktree Manager! 🚀
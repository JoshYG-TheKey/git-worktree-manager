# Git Worktree Manager

An interactive CLI tool for managing Git worktrees with a beautiful Rich-based interface. Simplify worktree creation, management, and visualization with guided workflows and comprehensive status information.

![Demo](https://via.placeholder.com/800x400/1a1a1a/ffffff?text=Git+Worktree+Manager+Demo)

## ✨ Features

- **🎯 Interactive Worktree Creation**: Guided workflow for creating new worktrees with branch selection
- **📊 Comprehensive Status Display**: View all worktrees with branch info, commit details, and change status
- **🔍 Diff Summaries**: See what changes exist between worktree branches and their base branches
- **⚙️ Configurable Storage**: Set custom locations for worktree storage with persistent preferences
- **🎨 Rich UI**: Beautiful terminal interface with colors, tables, and progress indicators
- **⚡ Performance Optimized**: Efficient Git operations with caching for large repositories
- **🛠️ Developer Friendly**: Easy setup with Makefile and shell alias support

## 🚀 Quick Start

```bash
# Clone and install
git clone <repository-url>
cd git-worktree-manager
make install-dev && make setup-alias

# Use the tool (with convenient alias)
gitwm
```

## 📋 Requirements

- **Python**: 3.8 or higher
- **Git**: 2.15 or higher (for worktree support)
- **Terminal**: Must support Rich formatting (most modern terminals)
- **Context**: Must be run from within a Git repository

## 📦 Installation

### Option 1: Quick Development Setup (Recommended)

```bash
git clone <repository-url>
cd git-worktree-manager
make install-dev    # Install with dev dependencies
make setup-alias    # Create 'gitwm' alias
```

### Option 2: From PyPI (when published)

```bash
pip install git-worktree-manager
```

### Option 3: Manual Installation

```bash
git clone <repository-url>
cd git-worktree-manager
pip install -e .
```

### Shell Alias Setup

The Makefile can automatically set up a convenient `gitwm` alias:

```bash
make setup-alias    # Adds alias to ~/.zshrc and ~/.bashrc
source ~/.zshrc     # Reload shell (or restart terminal)
gitwm --help        # Test the alias
```

To remove the alias later:
```bash
make remove-alias
```

## 🎮 Usage

### Basic Usage

```bash
# Using the full command
git-worktree-manager

# Using the alias (after setup)
gitwm
```

### Interactive Menu

The tool presents an interactive menu with options:

1. **📁 Create new worktree** - Guided worktree creation
2. **📋 List worktrees** - View all existing worktrees
3. **⚙️ Configure** - Set preferences and default paths
4. **❌ Exit** - Quit the application

### Command Line Options

```bash
gitwm --help              # Show help
gitwm --version           # Show version
gitwm --config-path       # Show config file location
```

## 📖 Examples

### Example 1: Creating Your First Worktree

```bash
$ gitwm
┌─ Git Worktree Manager ─┐
│ 1. Create new worktree │
│ 2. List worktrees      │
│ 3. Configure           │
│ 4. Exit                │
└─────────────────────────┘

# Select option 1
Enter worktree name: feature-auth
Select base branch: main
Storage location: /Users/dev/worktrees ✓

✅ Created worktree 'feature-auth' at /Users/dev/worktrees/feature-auth
```

### Example 2: Viewing Worktree Status

```bash
$ gitwm
# Select option 2 - List worktrees

┌─ Active Worktrees ─────────────────────────────────────────┐
│ Name         │ Branch       │ Status    │ Changes │ Path   │
├──────────────┼──────────────┼───────────┼─────────┼────────┤
│ main         │ main         │ Clean     │ 0       │ ~/repo │
│ feature-auth │ feature-auth │ Modified  │ 3       │ ~/wt/… │
│ bugfix-123   │ bugfix-123   │ Clean     │ 0       │ ~/wt/… │
└──────────────┴──────────────┴───────────┴─────────┴────────┘

📊 Diff Summary for feature-auth:
  • 2 files modified
  • 1 file added
  • 0 files deleted
  • +45 insertions, -12 deletions
```

### Example 3: Configuration

```bash
$ gitwm
# Select option 3 - Configure

Current Settings:
  Default Path: ~/worktrees
  Theme: dark
  Show Progress: true

What would you like to configure?
1. Change default worktree path
2. UI preferences
3. Reset to defaults

# Select option 1
Enter new default path: ~/projects/worktrees
✅ Configuration saved
```

## ⚙️ Configuration

### Environment Variables

```bash
# Set default worktree storage location
export WORKTREE_DEFAULT_PATH="~/my-worktrees"

# Enable debug mode
export WORKTREE_DEBUG=1

# Custom config file location
export WORKTREE_CONFIG_PATH="~/.config/my-worktree-config.toml"
```

### Configuration File

Location: `~/.config/git-worktree-manager/config.toml`

```toml
[worktree]
default_path = "~/worktrees"
auto_cleanup = true

[ui]
theme = "dark"
show_progress = true
max_display_items = 50

[performance]
cache_timeout = 300
max_cached_items = 100
```

### Configuration Options

| Section | Option | Default | Description |
|---------|--------|---------|-------------|
| `worktree` | `default_path` | `~/worktrees` | Default storage location |
| `worktree` | `auto_cleanup` | `true` | Auto-remove stale worktrees |
| `ui` | `theme` | `dark` | UI color theme |
| `ui` | `show_progress` | `true` | Show progress indicators |
| `performance` | `cache_timeout` | `300` | Cache timeout in seconds |

## 🔧 Development

### Development Setup

```bash
# Full development setup
make install-dev    # Install with dev dependencies
make setup-alias    # Create shell alias
make test          # Run tests
make lint          # Check code quality
```

### Available Make Commands

```bash
make help           # Show all available commands
make install        # Install package
make install-dev    # Install with dev dependencies
make test           # Run tests
make test-coverage  # Run tests with coverage
make lint           # Run linting
make format         # Format code
make clean          # Clean build artifacts
make setup-alias    # Create 'gitwm' shell alias
make remove-alias   # Remove shell alias
```

### Running Tests

```bash
make test                    # Run all tests
make test-coverage          # Run with coverage report
pytest tests/test_git_ops.py -v  # Run specific test file
```

## 🐛 Troubleshooting

### Common Issues

#### "Not in a Git repository"
```bash
# Ensure you're in a Git repository
git status
# If not, initialize or navigate to a Git repo
git init  # or cd /path/to/git/repo
```

#### "Git command failed"
```bash
# Check Git version (requires 2.15+)
git --version

# Check Git worktree support
git worktree --help
```

#### "Permission denied" errors
```bash
# Check directory permissions
ls -la ~/worktrees

# Create directory with proper permissions
mkdir -p ~/worktrees
chmod 755 ~/worktrees
```

#### Rich display issues
```bash
# Test Rich compatibility
python -c "from rich.console import Console; Console().print('Test')"

# Use basic mode if needed
export TERM=xterm-256color
```

### Debug Mode

Enable verbose logging:

```bash
export WORKTREE_DEBUG=1
gitwm
```

### Performance Issues

For large repositories:

```bash
# Increase cache timeout
export WORKTREE_CACHE_TIMEOUT=600

# Limit displayed items
export WORKTREE_MAX_DISPLAY=25
```

### Getting Help

- **📖 Documentation**: See [CONTRIBUTING.md](CONTRIBUTING.md) for development
- **🐛 Bug Reports**: Open GitHub issues
- **💬 Questions**: Use GitHub discussions
- **🔧 Development**: Check the Makefile for common tasks

## 🎯 Use Cases

### For Individual Developers

- **Feature Development**: Create isolated environments for each feature
- **Bug Fixes**: Quickly switch between main and bugfix branches
- **Code Review**: Check out PR branches without affecting main work
- **Experimentation**: Try different approaches in separate worktrees

### For Teams

- **Parallel Development**: Work on multiple features simultaneously
- **Testing**: Maintain separate worktrees for different test scenarios
- **Release Management**: Keep release branches in dedicated worktrees
- **Code Archaeology**: Explore different versions without branch switching

## 🚀 Performance

Optimized for large repositories:

- ⚡ **Fast Operations**: Complete within 2 seconds for up to 100 worktrees
- 🧠 **Smart Caching**: Branch lists and commit information cached
- 📊 **Efficient Git Commands**: Uses `--porcelain` flags for consistent parsing
- 🔄 **Progressive Loading**: Large datasets loaded incrementally
- 💾 **Memory Efficient**: Streams large command outputs

## 🤝 Contributing

We welcome contributions! See [CONTRIBUTING.md](CONTRIBUTING.md) for detailed guidelines.

Quick contribution setup:
```bash
git clone <repository-url>
cd git-worktree-manager
make install-dev
make test
# Make your changes
make format && make lint && make test
```

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Built with [Rich](https://github.com/Textualize/rich) for beautiful terminal UI
- Uses [Click](https://click.palletsprojects.com/) for CLI framework
- Inspired by Git's powerful worktree functionality

---

**Made with ❤️ for developers who love Git worktrees**
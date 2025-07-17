# Git Worktree Manager - Development and Installation Makefile

.PHONY: help install install-dev test test-coverage lint format clean setup-alias remove-alias docs

# Default target
help:
	@echo "Git Worktree Manager - Available Commands:"
	@echo ""
	@echo "Installation:"
	@echo "  install          Install the package"
	@echo "  install-dev      Install in development mode with dev dependencies"
	@echo "  setup-alias      Create 'gitwm' shell alias for git-worktree-manager"
	@echo "  remove-alias     Remove 'gitwm' shell alias"
	@echo ""
	@echo "Development:"
	@echo "  test             Run all tests"
	@echo "  test-coverage    Run tests with coverage report"
	@echo "  lint             Run linting (ruff and mypy)"
	@echo "  format           Format code with black"
	@echo "  clean            Clean build artifacts and cache"
	@echo ""
	@echo "Documentation:"
	@echo "  docs             Generate documentation"
	@echo ""
	@echo "Quick Start:"
	@echo "  make install-dev && make setup-alias"

# Installation targets
install:
	@echo "Installing git-worktree-manager..."
	pip install .

install-dev:
	@echo "Installing git-worktree-manager in development mode..."
	pip install -e ".[dev]"
	@echo "Development installation complete!"
	@echo "Run 'make setup-alias' to create the 'gitwm' alias."

# Alias management
setup-alias:
	@echo "Setting up 'gitwm' alias..."
	@if [ -f ~/.zshrc ]; then \
		if ! grep -q "alias gitwm=" ~/.zshrc; then \
			echo "" >> ~/.zshrc; \
			echo "# Git Worktree Manager alias" >> ~/.zshrc; \
			echo "alias gitwm='git-worktree-manager'" >> ~/.zshrc; \
			echo "Added 'gitwm' alias to ~/.zshrc"; \
		else \
			echo "'gitwm' alias already exists in ~/.zshrc"; \
		fi; \
	fi
	@if [ -f ~/.bashrc ]; then \
		if ! grep -q "alias gitwm=" ~/.bashrc; then \
			echo "" >> ~/.bashrc; \
			echo "# Git Worktree Manager alias" >> ~/.bashrc; \
			echo "alias gitwm='git-worktree-manager'" >> ~/.bashrc; \
			echo "Added 'gitwm' alias to ~/.bashrc"; \
		else \
			echo "'gitwm' alias already exists in ~/.bashrc"; \
		fi; \
	fi
	@echo ""
	@echo "Alias setup complete! Restart your shell or run:"
	@echo "  source ~/.zshrc    (for zsh users)"
	@echo "  source ~/.bashrc   (for bash users)"
	@echo ""
	@echo "Then you can use: gitwm"

remove-alias:
	@echo "Removing 'gitwm' alias..."
	@if [ -f ~/.zshrc ]; then \
		sed -i.bak '/# Git Worktree Manager alias/d' ~/.zshrc; \
		sed -i.bak '/alias gitwm=/d' ~/.zshrc; \
		rm -f ~/.zshrc.bak; \
		echo "Removed alias from ~/.zshrc"; \
	fi
	@if [ -f ~/.bashrc ]; then \
		sed -i.bak '/# Git Worktree Manager alias/d' ~/.bashrc; \
		sed -i.bak '/alias gitwm=/d' ~/.bashrc; \
		rm -f ~/.bashrc.bak; \
		echo "Removed alias from ~/.bashrc"; \
	fi

# Development targets
test:
	@echo "Running tests..."
	pytest -v

test-coverage:
	@echo "Running tests with coverage..."
	pytest --cov=git_worktree_manager --cov-report=html --cov-report=term-missing -v
	@echo "Coverage report generated in htmlcov/"

lint:
	@echo "Running linting..."
	ruff check .
	mypy git_worktree_manager/

format:
	@echo "Formatting code..."
	black .
	ruff check --fix .

clean:
	@echo "Cleaning build artifacts..."
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	rm -rf .pytest_cache/
	rm -rf htmlcov/
	rm -rf .coverage
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

# Documentation
docs:
	@echo "Documentation is in README.md and CONTRIBUTING.md"
	@echo "For API docs, run: python -m pydoc git_worktree_manager"

# Quick development setup
dev-setup: install-dev setup-alias
	@echo ""
	@echo "🎉 Development setup complete!"
	@echo ""
	@echo "Quick test: gitwm --help"
	@echo "Run tests: make test"
	@echo "Format code: make format"
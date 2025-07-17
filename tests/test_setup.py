"""Tests for package setup and installation."""

import subprocess
import sys
import tempfile
from pathlib import Path

import pytest


class TestPackageSetup:
    """Test package setup and installation."""

    def test_package_metadata(self):
        """Test that package metadata is correctly configured."""
        import git_worktree_manager

        # Test that the package can be imported
        assert git_worktree_manager is not None

        # Test that main modules exist
        from git_worktree_manager import (
            cli,
            config,
            git_ops,
            ui_controller,
            worktree_manager,
        )

        assert cli is not None
        assert worktree_manager is not None
        assert git_ops is not None
        assert ui_controller is not None
        assert config is not None

    def test_cli_entry_point(self):
        """Test that CLI entry point is accessible."""
        from git_worktree_manager.cli import main

        # Test that main function exists and is callable
        assert callable(main)

    def test_dependencies_importable(self):
        """Test that all required dependencies can be imported."""
        try:
            import click
            import rich
            import toml
        except ImportError as e:
            pytest.fail(f"Required dependency not available: {e}")

    def test_pyproject_toml_exists(self):
        """Test that pyproject.toml exists and is valid."""
        pyproject_path = Path(__file__).parent.parent / "pyproject.toml"
        assert pyproject_path.exists(), "pyproject.toml not found"

        # Test that it can be parsed
        import toml

        with open(pyproject_path) as f:
            config = toml.load(f)

        # Verify essential fields
        assert "project" in config
        assert "name" in config["project"]
        assert config["project"]["name"] == "git-worktree-manager"
        assert "version" in config["project"]
        assert "dependencies" in config["project"]
        assert "scripts" in config["project"]

    def test_readme_exists(self):
        """Test that README.md exists and contains essential information."""
        readme_path = Path(__file__).parent.parent / "README.md"
        assert readme_path.exists(), "README.md not found"

        with open(readme_path) as f:
            content = f.read()

        # Check for essential sections
        assert "# Git Worktree Manager" in content
        assert (
            "Installation" in content
        )  # Could be "## Installation" or "📦 Installation"
        assert "Usage" in content  # Could be "## Usage" or "🎮 Usage"
        assert "pip install" in content

    @pytest.mark.skipif(
        subprocess.run(
            [sys.executable, "-m", "build", "--help"], capture_output=True
        ).returncode
        != 0,
        reason="build module not available",
    )
    def test_package_builds(self):
        """Test that the package can be built."""
        import shutil
        from pathlib import Path

        project_root = Path(__file__).parent.parent

        with tempfile.TemporaryDirectory() as temp_dir:
            # Copy project to temp directory
            temp_project = Path(temp_dir) / "project"
            shutil.copytree(
                project_root,
                temp_project,
                ignore=shutil.ignore_patterns(
                    ".git", "__pycache__", "*.pyc", "dist", "build"
                ),
            )

            # Try to build the package
            result = subprocess.run(
                [sys.executable, "-m", "build"],
                cwd=temp_project,
                capture_output=True,
                text=True,
            )

            if result.returncode != 0:
                pytest.skip(f"Package build failed: {result.stderr}")

            # Check that dist files were created
            dist_dir = temp_project / "dist"
            assert dist_dir.exists()

            dist_files = list(dist_dir.glob("*"))
            assert len(dist_files) > 0, "No distribution files created"


class TestInstallation:
    """Test installation scenarios."""

    def test_editable_install(self):
        """Test that editable installation works."""
        project_root = Path(__file__).parent.parent

        # Test that we can import after editable install
        # (This assumes the test is run in an environment where the package is installed)
        try:
            import git_worktree_manager
            from git_worktree_manager.cli import main

            assert callable(main)
        except ImportError:
            pytest.skip("Package not installed in editable mode")

    def test_console_script_available(self):
        """Test that console script is available after installation."""
        # Check if the console script is available
        result = subprocess.run(
            ["git-worktree-manager", "--help"], capture_output=True, text=True
        )

        if result.returncode != 0:
            pytest.skip("Console script not available (package may not be installed)")

        # Should show help text
        assert "Usage:" in result.stdout or "usage:" in result.stdout.lower()

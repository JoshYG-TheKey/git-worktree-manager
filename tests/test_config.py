"""Tests for configuration management."""

import os
import tempfile
import toml
from pathlib import Path
from unittest.mock import patch, mock_open
import pytest

from git_worktree_manager.config import (
    ConfigManager,
    Config,
    WorktreeConfig,
    UIConfig,
    PerformanceConfig,
    ConfigError,
    ConfigValidationError,
)


class TestConfigManager:
    """Test cases for ConfigManager class."""

    def test_init_with_default_config_dir(self):
        """Test ConfigManager initialization with default config directory."""
        config_manager = ConfigManager()
        expected_dir = Path.home() / ".config" / "git-worktree-manager"
        assert config_manager._config_dir == expected_dir

    def test_init_with_custom_config_dir(self):
        """Test ConfigManager initialization with custom config directory."""
        custom_dir = "/tmp/custom-config"
        config_manager = ConfigManager(custom_dir)
        assert config_manager._config_dir == Path(custom_dir)

    @patch.dict(os.environ, {"WORKTREE_CONFIG_PATH": "/tmp/env-config"})
    def test_init_with_env_config_path(self):
        """Test ConfigManager initialization with environment variable config path."""
        config_manager = ConfigManager()
        assert config_manager._config_dir == Path("/tmp/env-config")

    def test_get_default_worktree_location_from_env(self):
        """Test getting default worktree location from environment variable."""
        with patch.dict(os.environ, {"WORKTREE_DEFAULT_PATH": "/tmp/worktrees"}):
            config_manager = ConfigManager()
            location = config_manager.get_default_worktree_location()
            assert location == "/tmp/worktrees"

    def test_get_default_worktree_location_from_config(self):
        """Test getting default worktree location from config file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_manager = ConfigManager(temp_dir)
            
            # Create config file
            config_data = {"worktree": {"default_path": "/custom/worktrees"}}
            config_file = Path(temp_dir) / "config.toml"
            with open(config_file, 'w') as f:
                toml.dump(config_data, f)
            
            location = config_manager.get_default_worktree_location()
            assert location == "/custom/worktrees"

    def test_get_default_worktree_location_fallback(self):
        """Test getting default worktree location with fallback to default."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_manager = ConfigManager(temp_dir)
            location = config_manager.get_default_worktree_location()
            expected = str(Path("~/worktrees").expanduser())
            assert location == expected

    def test_set_default_worktree_location(self):
        """Test setting default worktree location."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_manager = ConfigManager(temp_dir)
            new_path = "/new/worktree/path"
            
            config_manager.set_default_worktree_location(new_path)
            
            # Verify it was saved
            location = config_manager.get_default_worktree_location()
            assert location == new_path

    def test_load_config_creates_default_when_not_exists(self):
        """Test loading config creates default when file doesn't exist."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_manager = ConfigManager(temp_dir)
            config = config_manager.load_config()
            
            # Should create default config
            assert isinstance(config, Config)
            assert isinstance(config.worktree, WorktreeConfig)
            assert isinstance(config.ui, UIConfig)
            assert isinstance(config.performance, PerformanceConfig)
            
            # Config file should be created
            config_file = Path(temp_dir) / "config.toml"
            assert config_file.exists()

    def test_load_config_from_existing_file(self):
        """Test loading config from existing file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_manager = ConfigManager(temp_dir)
            
            # Create config file
            config_data = {
                "worktree": {"default_path": "/test/path", "auto_cleanup": False},
                "ui": {"theme": "light", "show_progress": False},
                "performance": {"cache_timeout": 600, "max_cached_items": 200}
            }
            config_file = Path(temp_dir) / "config.toml"
            with open(config_file, 'w') as f:
                toml.dump(config_data, f)
            
            config = config_manager.load_config()
            
            assert config.worktree.default_path == "/test/path"
            assert config.worktree.auto_cleanup is False
            assert config.ui.theme == "light"
            assert config.ui.show_progress is False
            assert config.performance.cache_timeout == 600
            assert config.performance.max_cached_items == 200

    def test_load_config_handles_corrupted_file(self):
        """Test loading config handles corrupted TOML file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_manager = ConfigManager(temp_dir)
            
            # Create corrupted config file
            config_file = Path(temp_dir) / "config.toml"
            with open(config_file, 'w') as f:
                f.write("invalid toml content [[[")
            
            config = config_manager.load_config()
            
            # Should create default config
            assert isinstance(config, Config)
            # The config stores the unexpanded path, expansion happens in get_default_worktree_location
            assert config.worktree.default_path == "~/worktrees"

    def test_save_config(self):
        """Test saving configuration to file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_manager = ConfigManager(temp_dir)
            
            config = Config(
                worktree=WorktreeConfig(default_path="/test/save", auto_cleanup=False),
                ui=UIConfig(theme="light"),
                performance=PerformanceConfig(cache_timeout=900)
            )
            
            config_manager.save_config(config)
            
            # Verify file was created and contains correct data
            config_file = Path(temp_dir) / "config.toml"
            assert config_file.exists()
            
            with open(config_file, 'r') as f:
                saved_data = toml.load(f)
            
            assert saved_data["worktree"]["default_path"] == "/test/save"
            assert saved_data["worktree"]["auto_cleanup"] is False
            assert saved_data["ui"]["theme"] == "light"
            assert saved_data["performance"]["cache_timeout"] == 900

    def test_save_config_creates_directory(self):
        """Test saving config creates directory if it doesn't exist."""
        with tempfile.TemporaryDirectory() as temp_dir:
            nested_dir = Path(temp_dir) / "nested" / "config"
            config_manager = ConfigManager(str(nested_dir))
            
            config = Config(worktree=WorktreeConfig(default_path="/test"))
            config_manager.save_config(config)
            
            # Directory should be created
            assert nested_dir.exists()
            assert (nested_dir / "config.toml").exists()

    def test_load_user_preferences(self):
        """Test loading user preferences as dictionary."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_manager = ConfigManager(temp_dir)
            
            # Create config
            config = Config(
                worktree=WorktreeConfig(default_path="/test", auto_cleanup=False),
                ui=UIConfig(theme="light"),
                performance=PerformanceConfig(cache_timeout=600)
            )
            config_manager.save_config(config)
            
            prefs = config_manager.load_user_preferences()
            
            assert prefs["worktree"]["default_path"] == "/test"
            assert prefs["worktree"]["auto_cleanup"] is False
            assert prefs["ui"]["theme"] == "light"
            assert prefs["performance"]["cache_timeout"] == 600

    def test_save_user_preferences(self):
        """Test saving user preferences from dictionary."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_manager = ConfigManager(temp_dir)
            
            # Start with default config
            config_manager.load_config()
            
            # Update preferences
            prefs = {
                "worktree": {"default_path": "/updated/path", "auto_cleanup": False},
                "ui": {"theme": "light"},
                "performance": {"cache_timeout": 900}
            }
            config_manager.save_user_preferences(prefs)
            
            # Verify changes were saved
            updated_config = config_manager.load_config()
            assert updated_config.worktree.default_path == "/updated/path"
            assert updated_config.worktree.auto_cleanup is False
            assert updated_config.ui.theme == "light"
            assert updated_config.performance.cache_timeout == 900

    def test_save_user_preferences_partial_update(self):
        """Test saving user preferences with partial updates."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_manager = ConfigManager(temp_dir)
            
            # Start with default config
            original_config = config_manager.load_config()
            original_theme = original_config.ui.theme
            
            # Update only worktree preferences
            prefs = {"worktree": {"default_path": "/partial/update"}}
            config_manager.save_user_preferences(prefs)
            
            # Verify only worktree was updated, UI remained the same
            updated_config = config_manager.load_config()
            assert updated_config.worktree.default_path == "/partial/update"
            assert updated_config.ui.theme == original_theme

    @patch.dict(os.environ, {"WORKTREE_DEFAULT_PATH": "/env/worktrees"})
    def test_create_default_config_with_env_var(self):
        """Test creating default config uses environment variable."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_manager = ConfigManager(temp_dir)
            config = config_manager._create_default_config()
            
            assert config.worktree.default_path == "/env/worktrees"

    def test_create_default_config_without_env_var(self):
        """Test creating default config without environment variable."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_manager = ConfigManager(temp_dir)
            config = config_manager._create_default_config()
            
            assert config.worktree.default_path == "~/worktrees"

    def test_parse_config_data_minimal(self):
        """Test parsing minimal config data."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_manager = ConfigManager(temp_dir)
            
            # Minimal config data
            config_data = {"worktree": {"default_path": "/minimal"}}
            config = config_manager._parse_config_data(config_data)
            
            assert config.worktree.default_path == "/minimal"
            assert config.worktree.auto_cleanup is True  # default value
            assert config.ui.theme == "dark"  # default value
            assert config.performance.cache_timeout == 300  # default value

    def test_parse_config_data_missing_worktree_path(self):
        """Test parsing config data with missing worktree default_path."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_manager = ConfigManager(temp_dir)
            
            # Config without default_path
            config_data = {"worktree": {"auto_cleanup": False}}
            config = config_manager._parse_config_data(config_data)
            
            # Should use default
            assert config.worktree.default_path == "~/worktrees"
            assert config.worktree.auto_cleanup is False

    @patch.dict(os.environ, {"WORKTREE_DEFAULT_PATH": "/env/fallback"})
    def test_parse_config_data_uses_env_fallback(self):
        """Test parsing config data uses environment variable as fallback."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_manager = ConfigManager(temp_dir)
            
            # Config without default_path
            config_data = {"worktree": {"auto_cleanup": False}}
            config = config_manager._parse_config_data(config_data)
            
            # Should use environment variable
            assert config.worktree.default_path == "/env/fallback"

    def test_config_caching(self):
        """Test that config is cached after first load."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_manager = ConfigManager(temp_dir)
            
            # First load
            config1 = config_manager.load_config()
            
            # Second load should return same object
            config2 = config_manager.load_config()
            
            assert config1 is config2

    def test_config_cache_updated_after_save(self):
        """Test that config cache is updated after save."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_manager = ConfigManager(temp_dir)
            
            # Load initial config
            config1 = config_manager.load_config()
            original_path = config1.worktree.default_path
            
            # Modify and save
            config1.worktree.default_path = "/new/cached/path"
            config_manager.save_config(config1)
            
            # Load again should return updated config
            config2 = config_manager.load_config()
            assert config2.worktree.default_path == "/new/cached/path"
            assert config2.worktree.default_path != original_path


class TestConfigDataClasses:
    """Test cases for configuration data classes."""

    def test_worktree_config_defaults(self):
        """Test WorktreeConfig default values."""
        config = WorktreeConfig(default_path="/test")
        assert config.default_path == "/test"
        assert config.auto_cleanup is True

    def test_ui_config_defaults(self):
        """Test UIConfig default values."""
        config = UIConfig()
        assert config.theme == "dark"
        assert config.show_progress is True

    def test_performance_config_defaults(self):
        """Test PerformanceConfig default values."""
        config = PerformanceConfig()
        assert config.cache_timeout == 300
        assert config.max_cached_items == 100

    def test_config_post_init(self):
        """Test Config __post_init__ creates default sub-configs."""
        config = Config(worktree=WorktreeConfig(default_path="/test"))
        
        assert isinstance(config.ui, UIConfig)
        assert isinstance(config.performance, PerformanceConfig)
        assert config.ui.theme == "dark"
        assert config.performance.cache_timeout == 300


class TestConfigError:
    """Test cases for ConfigError exception."""

    def test_config_error_inheritance(self):
        """Test ConfigError inherits from Exception."""
        error = ConfigError("test error")
        assert isinstance(error, Exception)
        assert str(error) == "test error"


class TestConfigValidation:
    """Test cases for configuration validation."""

    def test_validate_config_valid(self):
        """Test validating a valid configuration."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_manager = ConfigManager(temp_dir)
            
            config = Config(
                worktree=WorktreeConfig(default_path="/valid/path", auto_cleanup=True),
                ui=UIConfig(theme="dark", show_progress=True),
                performance=PerformanceConfig(cache_timeout=300, max_cached_items=100)
            )
            
            # Should not raise any exception
            config_manager.validate_config(config)

    def test_validate_worktree_config_empty_path(self):
        """Test validation fails for empty worktree path."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_manager = ConfigManager(temp_dir)
            
            config = Config(worktree=WorktreeConfig(default_path=""))
            
            with pytest.raises(ConfigValidationError, match="default_path cannot be empty"):
                config_manager.validate_config(config)

    def test_validate_worktree_config_non_string_path(self):
        """Test validation fails for non-string worktree path."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_manager = ConfigManager(temp_dir)
            
            config = Config(worktree=WorktreeConfig(default_path=123))
            
            with pytest.raises(ConfigValidationError, match="default_path must be a string"):
                config_manager.validate_config(config)

    def test_validate_worktree_config_relative_path(self):
        """Test validation fails for relative worktree path."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_manager = ConfigManager(temp_dir)
            
            config = Config(worktree=WorktreeConfig(default_path="relative/path"))
            
            with pytest.raises(ConfigValidationError, match="must be absolute or start with ~"):
                config_manager.validate_config(config)

    def test_validate_worktree_config_home_path(self):
        """Test validation passes for home directory path."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_manager = ConfigManager(temp_dir)
            
            config = Config(worktree=WorktreeConfig(default_path="~/worktrees"))
            
            # Should not raise any exception
            config_manager.validate_config(config)

    def test_validate_worktree_config_non_bool_cleanup(self):
        """Test validation fails for non-boolean auto_cleanup."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_manager = ConfigManager(temp_dir)
            
            config = Config(worktree=WorktreeConfig(default_path="/test", auto_cleanup="yes"))
            
            with pytest.raises(ConfigValidationError, match="auto_cleanup must be a boolean"):
                config_manager.validate_config(config)

    def test_validate_ui_config_invalid_theme(self):
        """Test validation fails for invalid UI theme."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_manager = ConfigManager(temp_dir)
            
            config = Config(
                worktree=WorktreeConfig(default_path="/test"),
                ui=UIConfig(theme="invalid")
            )
            
            with pytest.raises(ConfigValidationError, match="theme must be one of"):
                config_manager.validate_config(config)

    def test_validate_ui_config_valid_themes(self):
        """Test validation passes for valid UI themes."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_manager = ConfigManager(temp_dir)
            
            for theme in ["dark", "light", "auto"]:
                config = Config(
                    worktree=WorktreeConfig(default_path="/test"),
                    ui=UIConfig(theme=theme)
                )
                # Should not raise any exception
                config_manager.validate_config(config)

    def test_validate_ui_config_non_bool_progress(self):
        """Test validation fails for non-boolean show_progress."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_manager = ConfigManager(temp_dir)
            
            config = Config(
                worktree=WorktreeConfig(default_path="/test"),
                ui=UIConfig(show_progress="true")
            )
            
            with pytest.raises(ConfigValidationError, match="show_progress must be a boolean"):
                config_manager.validate_config(config)

    def test_validate_performance_config_non_int_timeout(self):
        """Test validation fails for non-integer cache_timeout."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_manager = ConfigManager(temp_dir)
            
            config = Config(
                worktree=WorktreeConfig(default_path="/test"),
                performance=PerformanceConfig(cache_timeout="300")
            )
            
            with pytest.raises(ConfigValidationError, match="cache_timeout must be an integer"):
                config_manager.validate_config(config)

    def test_validate_performance_config_negative_timeout(self):
        """Test validation fails for negative cache_timeout."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_manager = ConfigManager(temp_dir)
            
            config = Config(
                worktree=WorktreeConfig(default_path="/test"),
                performance=PerformanceConfig(cache_timeout=-1)
            )
            
            with pytest.raises(ConfigValidationError, match="cache_timeout must be non-negative"):
                config_manager.validate_config(config)

    def test_validate_performance_config_excessive_timeout(self):
        """Test validation fails for excessive cache_timeout."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_manager = ConfigManager(temp_dir)
            
            config = Config(
                worktree=WorktreeConfig(default_path="/test"),
                performance=PerformanceConfig(cache_timeout=100000)
            )
            
            with pytest.raises(ConfigValidationError, match="cannot exceed 86400 seconds"):
                config_manager.validate_config(config)

    def test_validate_performance_config_non_int_max_items(self):
        """Test validation fails for non-integer max_cached_items."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_manager = ConfigManager(temp_dir)
            
            config = Config(
                worktree=WorktreeConfig(default_path="/test"),
                performance=PerformanceConfig(max_cached_items="100")
            )
            
            with pytest.raises(ConfigValidationError, match="max_cached_items must be an integer"):
                config_manager.validate_config(config)

    def test_validate_performance_config_zero_max_items(self):
        """Test validation fails for zero max_cached_items."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_manager = ConfigManager(temp_dir)
            
            config = Config(
                worktree=WorktreeConfig(default_path="/test"),
                performance=PerformanceConfig(max_cached_items=0)
            )
            
            with pytest.raises(ConfigValidationError, match="max_cached_items must be at least 1"):
                config_manager.validate_config(config)

    def test_validate_performance_config_excessive_max_items(self):
        """Test validation fails for excessive max_cached_items."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_manager = ConfigManager(temp_dir)
            
            config = Config(
                worktree=WorktreeConfig(default_path="/test"),
                performance=PerformanceConfig(max_cached_items=20000)
            )
            
            with pytest.raises(ConfigValidationError, match="cannot exceed 10000"):
                config_manager.validate_config(config)

    def test_validate_and_save_preferences_valid(self):
        """Test validating and saving valid preferences."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_manager = ConfigManager(temp_dir)
            
            prefs = {
                "worktree": {"default_path": "/valid/path", "auto_cleanup": False},
                "ui": {"theme": "light"},
                "performance": {"cache_timeout": 600}
            }
            
            # Should not raise any exception
            config_manager.validate_and_save_preferences(prefs)
            
            # Verify changes were saved
            config = config_manager.load_config()
            assert config.worktree.default_path == "/valid/path"
            assert config.worktree.auto_cleanup is False
            assert config.ui.theme == "light"
            assert config.performance.cache_timeout == 600

    def test_validate_and_save_preferences_invalid_setting(self):
        """Test validation fails for unknown setting."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_manager = ConfigManager(temp_dir)
            
            prefs = {
                "worktree": {"unknown_setting": "value"}
            }
            
            with pytest.raises(ConfigValidationError, match="Unknown worktree setting"):
                config_manager.validate_and_save_preferences(prefs)

    def test_validate_and_save_preferences_invalid_value(self):
        """Test validation fails for invalid preference value."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_manager = ConfigManager(temp_dir)
            
            prefs = {
                "ui": {"theme": "invalid_theme"}
            }
            
            with pytest.raises(ConfigValidationError, match="theme must be one of"):
                config_manager.validate_and_save_preferences(prefs)

    def test_reset_to_defaults(self):
        """Test resetting configuration to defaults."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_manager = ConfigManager(temp_dir)
            
            # Create custom config
            custom_config = Config(
                worktree=WorktreeConfig(default_path="/custom", auto_cleanup=False),
                ui=UIConfig(theme="light"),
                performance=PerformanceConfig(cache_timeout=900)
            )
            config_manager.save_config(custom_config)
            
            # Reset to defaults
            config_manager.reset_to_defaults()
            
            # Verify defaults were restored
            config = config_manager.load_config()
            assert config.worktree.default_path == "~/worktrees"
            assert config.worktree.auto_cleanup is True
            assert config.ui.theme == "dark"
            assert config.performance.cache_timeout == 300

    def test_backup_config(self):
        """Test creating configuration backup."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_manager = ConfigManager(temp_dir)
            
            # Create config
            config = Config(worktree=WorktreeConfig(default_path="/test"))
            config_manager.save_config(config)
            
            # Create backup
            backup_path = config_manager.backup_config()
            
            # Verify backup exists and contains correct data
            assert Path(backup_path).exists()
            with open(backup_path, 'r') as f:
                backup_data = toml.load(f)
            assert backup_data["worktree"]["default_path"] == "/test"

    def test_backup_config_custom_path(self):
        """Test creating configuration backup with custom path."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_manager = ConfigManager(temp_dir)
            
            # Create config
            config = Config(worktree=WorktreeConfig(default_path="/test"))
            config_manager.save_config(config)
            
            # Create backup with custom path
            custom_backup = str(Path(temp_dir) / "custom_backup.toml")
            backup_path = config_manager.backup_config(custom_backup)
            
            assert backup_path == custom_backup
            assert Path(custom_backup).exists()

    def test_backup_config_no_file(self):
        """Test backup fails when no config file exists."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_manager = ConfigManager(temp_dir)
            
            with pytest.raises(ConfigError, match="No configuration file exists"):
                config_manager.backup_config()

    def test_restore_config(self):
        """Test restoring configuration from backup."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_manager = ConfigManager(temp_dir)
            
            # Create original config
            original_config = Config(worktree=WorktreeConfig(default_path="/original"))
            config_manager.save_config(original_config)
            
            # Create backup
            backup_path = config_manager.backup_config()
            
            # Modify config
            modified_config = Config(worktree=WorktreeConfig(default_path="/modified"))
            config_manager.save_config(modified_config)
            
            # Restore from backup
            config_manager.restore_config(backup_path)
            
            # Verify original config was restored
            config = config_manager.load_config()
            assert config.worktree.default_path == "/original"

    def test_restore_config_nonexistent_backup(self):
        """Test restore fails for nonexistent backup file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_manager = ConfigManager(temp_dir)
            
            with pytest.raises(ConfigError, match="Backup file does not exist"):
                config_manager.restore_config("/nonexistent/backup.toml")

    def test_restore_config_invalid_backup(self):
        """Test restore fails for invalid backup file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_manager = ConfigManager(temp_dir)
            
            # Create invalid backup file
            invalid_backup = Path(temp_dir) / "invalid_backup.toml"
            with open(invalid_backup, 'w') as f:
                f.write("invalid toml content [[[")
            
            with pytest.raises(ConfigError, match="Failed to restore backup"):
                config_manager.restore_config(str(invalid_backup))

    def test_save_config_validates_before_saving(self):
        """Test that save_config validates configuration before saving."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_manager = ConfigManager(temp_dir)
            
            # Create invalid config
            invalid_config = Config(
                worktree=WorktreeConfig(default_path=""),  # Invalid empty path
            )
            
            with pytest.raises(ConfigValidationError, match="default_path cannot be empty"):
                config_manager.save_config(invalid_config)


class TestConfigValidationError:
    """Test cases for ConfigValidationError exception."""

    def test_config_validation_error_inheritance(self):
        """Test ConfigValidationError inherits from ConfigError."""
        error = ConfigValidationError("validation error")
        assert isinstance(error, ConfigError)
        assert isinstance(error, Exception)
        assert str(error) == "validation error"
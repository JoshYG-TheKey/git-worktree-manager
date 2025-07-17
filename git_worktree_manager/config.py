"""Configuration management for Git Worktree Manager."""

import os
import toml
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict


@dataclass
class WorktreeConfig:
    """Configuration data structure for worktree settings."""
    default_path: str
    auto_cleanup: bool = True


@dataclass
class UIConfig:
    """Configuration data structure for UI settings."""
    theme: str = "dark"
    show_progress: bool = True


@dataclass
class PerformanceConfig:
    """Configuration data structure for performance settings."""
    cache_timeout: int = 300
    max_cached_items: int = 100


@dataclass
class Config:
    """Main configuration data structure."""
    worktree: WorktreeConfig
    ui: UIConfig = None
    performance: PerformanceConfig = None

    def __post_init__(self):
        if self.ui is None:
            self.ui = UIConfig()
        if self.performance is None:
            self.performance = PerformanceConfig()


class ConfigManager:
    """Manages configuration loading, saving, and environment variable integration."""

    DEFAULT_CONFIG_FILENAME = "config.toml"
    DEFAULT_WORKTREE_PATH = "~/worktrees"
    ENV_WORKTREE_DEFAULT_PATH = "WORKTREE_DEFAULT_PATH"
    ENV_CONFIG_PATH = "WORKTREE_CONFIG_PATH"

    def __init__(self, config_dir: Optional[str] = None):
        """Initialize ConfigManager with optional custom config directory."""
        self._config_dir = self._get_config_directory(config_dir)
        self._config_file = self._config_dir / self.DEFAULT_CONFIG_FILENAME
        self._config: Optional[Config] = None

    def _get_config_directory(self, custom_dir: Optional[str] = None) -> Path:
        """Get the configuration directory path."""
        if custom_dir:
            return Path(custom_dir).expanduser()
        
        # Check environment variable for custom config path
        env_config_path = os.getenv(self.ENV_CONFIG_PATH)
        if env_config_path:
            return Path(env_config_path).expanduser()
        
        # Default to ~/.config/git-worktree-manager
        return Path.home() / ".config" / "git-worktree-manager"

    def get_default_worktree_location(self) -> str:
        """Get the default worktree location with environment variable override."""
        # Check environment variable first
        env_path = os.getenv(self.ENV_WORKTREE_DEFAULT_PATH)
        if env_path:
            return str(Path(env_path).expanduser())
        
        # Load from config file
        config = self.load_config()
        return str(Path(config.worktree.default_path).expanduser())

    def set_default_worktree_location(self, path: str) -> None:
        """Set the default worktree location and save to config."""
        config = self.load_config()
        config.worktree.default_path = path
        self.save_config(config)

    def load_config(self) -> Config:
        """Load configuration from file or create default if not exists."""
        if self._config is not None:
            return self._config

        if not self._config_file.exists():
            self._config = self._create_default_config()
            self.save_config(self._config)
            return self._config

        try:
            with open(self._config_file, 'r', encoding='utf-8') as f:
                config_data = toml.load(f)
            
            self._config = self._parse_config_data(config_data)
            return self._config
        
        except (toml.TomlDecodeError, OSError, KeyError) as e:
            # If config is corrupted, create default and save
            self._config = self._create_default_config()
            self.save_config(self._config)
            return self._config

    def save_config(self, config: Config) -> None:
        """Save configuration to file."""
        # Validate configuration before saving
        self.validate_config(config)
        
        # Ensure config directory exists
        self._config_dir.mkdir(parents=True, exist_ok=True)
        
        # Convert config to dictionary
        config_dict = {
            "worktree": asdict(config.worktree),
            "ui": asdict(config.ui),
            "performance": asdict(config.performance)
        }
        
        try:
            with open(self._config_file, 'w', encoding='utf-8') as f:
                toml.dump(config_dict, f)
            
            # Update cached config
            self._config = config
            
        except OSError as e:
            raise ConfigError(f"Failed to save configuration: {e}")

    def load_user_preferences(self) -> Dict[str, Any]:
        """Load user preferences as a dictionary."""
        config = self.load_config()
        return {
            "worktree": asdict(config.worktree),
            "ui": asdict(config.ui),
            "performance": asdict(config.performance)
        }

    def save_user_preferences(self, prefs: Dict[str, Any]) -> None:
        """Save user preferences from a dictionary."""
        config = self.load_config()
        
        # Update worktree settings
        if "worktree" in prefs:
            for key, value in prefs["worktree"].items():
                if hasattr(config.worktree, key):
                    setattr(config.worktree, key, value)
        
        # Update UI settings
        if "ui" in prefs:
            for key, value in prefs["ui"].items():
                if hasattr(config.ui, key):
                    setattr(config.ui, key, value)
        
        # Update performance settings
        if "performance" in prefs:
            for key, value in prefs["performance"].items():
                if hasattr(config.performance, key):
                    setattr(config.performance, key, value)
        
        self.save_config(config)

    def validate_config(self, config: Config) -> None:
        """Validate configuration values."""
        self._validate_worktree_config(config.worktree)
        self._validate_ui_config(config.ui)
        self._validate_performance_config(config.performance)

    def _validate_worktree_config(self, worktree_config: WorktreeConfig) -> None:
        """Validate worktree configuration."""
        if not worktree_config.default_path:
            raise ConfigValidationError("Worktree default_path cannot be empty")
        
        if not isinstance(worktree_config.default_path, str):
            raise ConfigValidationError("Worktree default_path must be a string")
        
        # Validate path format (basic check)
        try:
            path = Path(worktree_config.default_path).expanduser()
            # Check if path is absolute or starts with ~ (home directory)
            if not (path.is_absolute() or str(worktree_config.default_path).startswith('~')):
                raise ConfigValidationError(
                    f"Worktree default_path must be absolute or start with ~: {worktree_config.default_path}"
                )
        except (ValueError, OSError) as e:
            raise ConfigValidationError(f"Invalid worktree default_path: {e}")
        
        if not isinstance(worktree_config.auto_cleanup, bool):
            raise ConfigValidationError("Worktree auto_cleanup must be a boolean")

    def _validate_ui_config(self, ui_config: UIConfig) -> None:
        """Validate UI configuration."""
        valid_themes = {"dark", "light", "auto"}
        if ui_config.theme not in valid_themes:
            raise ConfigValidationError(
                f"UI theme must be one of {valid_themes}, got: {ui_config.theme}"
            )
        
        if not isinstance(ui_config.show_progress, bool):
            raise ConfigValidationError("UI show_progress must be a boolean")

    def _validate_performance_config(self, performance_config: PerformanceConfig) -> None:
        """Validate performance configuration."""
        if not isinstance(performance_config.cache_timeout, int):
            raise ConfigValidationError("Performance cache_timeout must be an integer")
        
        if performance_config.cache_timeout < 0:
            raise ConfigValidationError("Performance cache_timeout must be non-negative")
        
        if performance_config.cache_timeout > 86400:  # 24 hours
            raise ConfigValidationError("Performance cache_timeout cannot exceed 86400 seconds (24 hours)")
        
        if not isinstance(performance_config.max_cached_items, int):
            raise ConfigValidationError("Performance max_cached_items must be an integer")
        
        if performance_config.max_cached_items < 1:
            raise ConfigValidationError("Performance max_cached_items must be at least 1")
        
        if performance_config.max_cached_items > 10000:
            raise ConfigValidationError("Performance max_cached_items cannot exceed 10000")

    def validate_and_save_preferences(self, prefs: Dict[str, Any]) -> None:
        """Validate and save user preferences with enhanced error handling."""
        try:
            # Create a temporary config to validate
            config = self.load_config()
            temp_config = Config(
                worktree=WorktreeConfig(**asdict(config.worktree)),
                ui=UIConfig(**asdict(config.ui)),
                performance=PerformanceConfig(**asdict(config.performance))
            )
            
            # Apply preferences to temporary config
            if "worktree" in prefs:
                for key, value in prefs["worktree"].items():
                    if hasattr(temp_config.worktree, key):
                        setattr(temp_config.worktree, key, value)
                    else:
                        raise ConfigValidationError(f"Unknown worktree setting: {key}")
            
            if "ui" in prefs:
                for key, value in prefs["ui"].items():
                    if hasattr(temp_config.ui, key):
                        setattr(temp_config.ui, key, value)
                    else:
                        raise ConfigValidationError(f"Unknown UI setting: {key}")
            
            if "performance" in prefs:
                for key, value in prefs["performance"].items():
                    if hasattr(temp_config.performance, key):
                        setattr(temp_config.performance, key, value)
                    else:
                        raise ConfigValidationError(f"Unknown performance setting: {key}")
            
            # Validate the temporary config
            self.validate_config(temp_config)
            
            # If validation passes, save the config
            self.save_config(temp_config)
            
        except (TypeError, ValueError) as e:
            raise ConfigValidationError(f"Invalid preference value: {e}")

    def reset_to_defaults(self) -> None:
        """Reset configuration to default values."""
        default_config = self._create_default_config()
        self.save_config(default_config)

    def backup_config(self, backup_path: Optional[str] = None) -> str:
        """Create a backup of the current configuration."""
        if backup_path is None:
            backup_path = str(self._config_file.with_suffix('.toml.backup'))
        
        backup_file = Path(backup_path)
        
        if not self._config_file.exists():
            raise ConfigError("No configuration file exists to backup")
        
        try:
            import shutil
            shutil.copy2(self._config_file, backup_file)
            return str(backup_file)
        except OSError as e:
            raise ConfigError(f"Failed to create backup: {e}")

    def restore_config(self, backup_path: str) -> None:
        """Restore configuration from a backup file."""
        backup_file = Path(backup_path)
        
        if not backup_file.exists():
            raise ConfigError(f"Backup file does not exist: {backup_path}")
        
        try:
            # Validate the backup file first
            with open(backup_file, 'r', encoding='utf-8') as f:
                config_data = toml.load(f)
            
            temp_config = self._parse_config_data(config_data)
            self.validate_config(temp_config)
            
            # If validation passes, restore the backup
            import shutil
            shutil.copy2(backup_file, self._config_file)
            
            # Clear cached config to force reload
            self._config = None
            
        except (toml.TomlDecodeError, OSError, ConfigValidationError) as e:
            raise ConfigError(f"Failed to restore backup: {e}")

    def _create_default_config(self) -> Config:
        """Create default configuration."""
        # Use environment variable if available, otherwise use default
        default_path = os.getenv(self.ENV_WORKTREE_DEFAULT_PATH, self.DEFAULT_WORKTREE_PATH)
        
        return Config(
            worktree=WorktreeConfig(default_path=default_path),
            ui=UIConfig(),
            performance=PerformanceConfig()
        )

    def _parse_config_data(self, config_data: Dict[str, Any]) -> Config:
        """Parse configuration data from TOML into Config object."""
        # Parse worktree config (required)
        worktree_data = config_data.get("worktree", {})
        if "default_path" not in worktree_data:
            # Use environment variable or default if not in config
            worktree_data["default_path"] = os.getenv(
                self.ENV_WORKTREE_DEFAULT_PATH, 
                self.DEFAULT_WORKTREE_PATH
            )
        
        worktree_config = WorktreeConfig(**worktree_data)
        
        # Parse UI config (optional)
        ui_data = config_data.get("ui", {})
        ui_config = UIConfig(**ui_data)
        
        # Parse performance config (optional)
        performance_data = config_data.get("performance", {})
        performance_config = PerformanceConfig(**performance_data)
        
        return Config(
            worktree=worktree_config,
            ui=ui_config,
            performance=performance_config
        )


class ConfigError(Exception):
    """Exception raised for configuration-related errors."""
    pass


class ConfigValidationError(ConfigError):
    """Exception raised for configuration validation errors."""
    pass
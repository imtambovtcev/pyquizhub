"""
Configuration Manager for PyQuizHub using Pydantic Settings.

This module provides a robust, type-safe configuration system with:
- Automatic config file discovery
- Environment variable override support with proper type conversion
- Configuration validation with clear error messages
- No circular dependencies with logging

Key features:
1. Config path search strategy (multiple fallback locations)
2. Pydantic-based validation
3. Proper environment variable handling
4. Clear error messages
5. Backward-compatible API
"""

import os
import yaml
import logging
from typing import Optional, Dict, Any, Literal, Tuple
from pydantic import BaseModel, Field, ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict, PydanticBaseSettingsSource


# Use basic logging during config initialization (before custom logger is set up)
_basic_logger = logging.getLogger(__name__)


class FileStorageSettings(BaseModel):
    """Settings for file-based storage."""
    base_dir: str = Field(default=".pyquizhub", description="Base directory for file storage")


class SQLStorageSettings(BaseModel):
    """Settings for SQL-based storage."""
    connection_string: str = Field(
        default="sqlite:///pyquizhub.db",
        description="SQLAlchemy connection string"
    )


class StorageSettings(BaseModel):
    """Storage configuration."""
    type: Literal["file", "sql"] = Field(default="file", description="Storage type")
    file: FileStorageSettings = Field(default_factory=FileStorageSettings)
    sql: SQLStorageSettings = Field(default_factory=SQLStorageSettings)


class APISettings(BaseModel):
    """API configuration."""
    base_url: str = Field(default="http://127.0.0.1:8000", description="API base URL")
    host: str = Field(default="0.0.0.0", description="Host for uvicorn")
    port: int = Field(default=8000, ge=1, le=65535, description="Port for uvicorn")


class SecuritySettings(BaseModel):
    """Security configuration."""
    use_tokens: bool = Field(default=True, description="Enable token-based authentication")
    admin_token_env: str = Field(default="PYQUIZHUB_ADMIN_TOKEN")
    creator_token_env: str = Field(default="PYQUIZHUB_CREATOR_TOKEN")
    user_token_env: str = Field(default="PYQUIZHUB_USER_TOKEN")


class LoggingSettings(BaseModel):
    """Logging configuration (raw dict for logging.config.dictConfig)."""
    version: int = Field(default=1)
    disable_existing_loggers: bool = Field(default=False)
    formatters: Dict[str, Any] = Field(default_factory=dict)
    handlers: Dict[str, Any] = Field(default_factory=dict)
    root: Dict[str, Any] = Field(default_factory=dict)
    loggers: Dict[str, Any] = Field(default_factory=dict)

    model_config = {'extra': 'allow'}  # Allow extra fields for logging config flexibility


class AppSettings(BaseSettings):
    """
    Main application settings using Pydantic Settings.
    
    This class automatically:
    - Loads configuration from YAML files
    - Overrides values from environment variables
    - Validates all settings
    - Provides type-safe access to configuration
    
    Environment variables use the format: PYQUIZHUB_SECTION__KEY
    Example: PYQUIZHUB_STORAGE__TYPE=sql
    """
    
    storage: StorageSettings = Field(default_factory=StorageSettings)
    api: APISettings = Field(default_factory=APISettings)
    security: SecuritySettings = Field(default_factory=SecuritySettings)
    logging: LoggingSettings = Field(default_factory=LoggingSettings)
    
    model_config = SettingsConfigDict(
        env_prefix="PYQUIZHUB_",
        env_nested_delimiter="__",
        case_sensitive=False,
        # Allow extra fields for forward compatibility
        extra="ignore",
    )
    
    # Class variable to temporarily store YAML data
    _temp_config_data: Optional[Dict[str, Any]] = None
    _temp_config_path: Optional[str] = None

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> Tuple[PydanticBaseSettingsSource, ...]:
        """
        Customize the sources and their priority for loading settings.
        
        Priority (highest to lowest):
        1. Environment variables (highest priority)
        2. YAML file data (if loaded via from_yaml)
        3. Default values
        """
        # Create a custom source for YAML data
        class YamlSettingsSource(PydanticBaseSettingsSource):
            def get_field_value(self, field: Any, field_name: str) -> Tuple[Any, str, bool]:
                # Return YAML data if available
                if cls._temp_config_data and field_name in cls._temp_config_data:
                    return cls._temp_config_data[field_name], field_name, False
                return None, field_name, False
            
            def __call__(self) -> Dict[str, Any]:
                return cls._temp_config_data or {}
        
        # Return sources in priority order (first = highest priority)
        return (
            env_settings,  # Environment variables have highest priority
            YamlSettingsSource(settings_cls),  # Then YAML file
            init_settings,  # Then init arguments
        )

    @classmethod
    def from_yaml(cls, config_path: Optional[str] = None) -> 'AppSettings':
        """
        Load configuration from YAML file with fallback search strategy.
        
        Search order:
        1. PYQUIZHUB_CONFIG_PATH environment variable (if set)
        2. ./config.yaml (project root)
        3. pyquizhub/config/config.yaml (package location)
        
        Note: Environment variables (PYQUIZHUB_*) always override YAML values.
        
        Args:
            config_path: Explicit path to config file (skips search if provided)
            
        Returns:
            AppSettings instance
            
        Raises:
            FileNotFoundError: If no config file is found in any location
            ValidationError: If config file has invalid structure or values
        """
        if config_path is None:
            config_path = cls._find_config_file()
        
        _basic_logger.info(f"Loading configuration from: {config_path}")
        
        try:
            with open(config_path, "r") as f:
                config_data = yaml.safe_load(f) or {}
        except FileNotFoundError:
            _basic_logger.error(f"Configuration file not found: {config_path}")
            raise FileNotFoundError(
                f"Configuration file not found: {config_path}\n"
                f"Tried search paths: {cls._get_search_paths()}"
            )
        except yaml.YAMLError as e:
            _basic_logger.error(f"Invalid YAML in config file: {e}")
            raise ValueError(f"Invalid YAML in configuration file {config_path}: {e}")
        
        # Store config file path temporarily for merging
        cls._temp_config_data = config_data
        cls._temp_config_path = config_path
        
        try:
            # Create instance - this will use our custom settings source
            # which merges file data with env vars (env vars take precedence)
            settings = cls()
            _basic_logger.info("Configuration loaded and validated successfully")
            return settings
        except ValidationError as e:
            _basic_logger.error(f"Configuration validation failed: {e}")
            raise ValueError(f"Configuration validation failed:\n{e}")
        finally:
            # Clean up temp data
            cls._temp_config_data = None
            cls._temp_config_path = None
    
    @staticmethod
    def _get_search_paths() -> list[str]:
        """Get list of paths to search for config file."""
        return [
            os.getenv("PYQUIZHUB_CONFIG_PATH", ""),
            "./config.yaml",            # Project root
            os.path.join(os.path.dirname(__file__), "config.yaml"),  # Package location
        ]
    
    @classmethod
    def _find_config_file(cls) -> str:
        """
        Search for config file in multiple locations.
        
        Returns:
            Path to first found config file
            
        Raises:
            FileNotFoundError: If no config file is found
        """
        search_paths = cls._get_search_paths()
        
        for path in search_paths:
            if path and os.path.isfile(path):
                _basic_logger.debug(f"Found config file at: {path}")
                return path
        
        # If we get here, no config file was found
        error_msg = (
            "No configuration file found. Searched in:\n" +
            "\n".join(f"  - {p}" for p in search_paths if p) +
            "\n\nPlease either:\n"
            "  1. Set PYQUIZHUB_CONFIG_PATH environment variable\n"
            "  2. Place config.yaml in project root\n"
            "  3. Use environment variables to configure (see .env.example)"
        )
        _basic_logger.error(error_msg)
        raise FileNotFoundError(error_msg)


class ConfigManager:
    """
    Thread-safe singleton wrapper for AppSettings.
    
    This maintains backward compatibility with the old ConfigManager API
    while using the new Pydantic-based settings internally.
    """
    
    _instance: Optional['ConfigManager'] = None
    _settings: Optional[AppSettings] = None
    _config_path: Optional[str] = None
    
    def __init__(self):
        """Initialize ConfigManager. Use get_instance() instead."""
        pass
    
    @classmethod
    def get_instance(cls) -> 'ConfigManager':
        """Get singleton instance of ConfigManager."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    @classmethod
    def reset_instance(cls):
        """Reset singleton instance (for testing)."""
        cls._instance = None
        cls._settings = None
        cls._config_path = None
    
    def load(self, config_path: Optional[str] = None) -> Dict[str, Any]:
        """
        Load configuration from file.
        
        Args:
            config_path: Optional path to config file
            
        Returns:
            Configuration as dictionary
        """
        if self._settings is not None and config_path is None:
            # Already loaded, return cached config
            return self._settings.model_dump()
        
        self._config_path = config_path
        self._settings = AppSettings.from_yaml(config_path)
        
        return self._settings.model_dump()
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value using dot notation.
        
        Args:
            key: Config key in dot notation (e.g., "storage.type")
            default: Default value if key not found
            
        Returns:
            Configuration value or default
        """
        if self._settings is None:
            self.load()
        
        # Navigate through nested structure
        keys = key.split(".")
        value = self._settings.model_dump()
        
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k, default)
                if value is default:
                    break
            else:
                return default
        
        return value
    
    def get_config(self) -> Dict[str, Any]:
        """Get entire configuration as dictionary."""
        if self._settings is None:
            self.load()
        return self._settings.model_dump()
    
    def get_config_path(self) -> Optional[str]:
        """Get path to loaded configuration file."""
        return self._config_path
    
    # Convenience properties for backward compatibility
    
    @property
    def storage_type(self) -> str:
        """Get storage type."""
        if self._settings is None:
            self.load()
        return self._settings.storage.type
    
    @property
    def storage_file_base_dir(self) -> str:
        """Get file storage base directory."""
        if self._settings is None:
            self.load()
        return self._settings.storage.file.base_dir
    
    @property
    def storage_sql_connection_string(self) -> str:
        """Get SQL connection string."""
        if self._settings is None:
            self.load()
        return self._settings.storage.sql.connection_string
    
    @property
    def api_base_url(self) -> str:
        """Get API base URL."""
        if self._settings is None:
            self.load()
        return self._settings.api.base_url
    
    @property
    def api_host(self) -> str:
        """Get API host."""
        if self._settings is None:
            self.load()
        return self._settings.api.host
    
    @property
    def api_port(self) -> int:
        """Get API port."""
        if self._settings is None:
            self.load()
        return self._settings.api.port
    
    @property
    def security_use_tokens(self) -> bool:
        """Check if token security is enabled."""
        if self._settings is None:
            self.load()
        return self._settings.security.use_tokens
    
    @property
    def logging_config(self) -> Dict[str, Any]:
        """Get logging configuration."""
        if self._settings is None:
            self.load()
        return self._settings.logging.model_dump()
    
    def get_token_env_var(self, token_type: str) -> Optional[str]:
        """
        Get environment variable name for a token type.
        
        Args:
            token_type: Type of token (admin, creator, user)
            
        Returns:
            Environment variable name
        """
        if self._settings is None:
            self.load()
        
        token_map = {
            "admin": self._settings.security.admin_token_env,
            "creator": self._settings.security.creator_token_env,
            "user": self._settings.security.user_token_env,
        }
        return token_map.get(token_type)
    
    def get_token(self, token_type: str) -> Optional[str]:
        """
        Get token value from environment variable.
        
        Args:
            token_type: Type of token (admin, creator, user)
            
        Returns:
            Token value or None
        """
        if self._settings is None:
            self.load()
        
        if not self._settings.security.use_tokens:
            return None
        
        env_var = self.get_token_env_var(token_type)
        if env_var:
            return os.getenv(env_var)
        return None


def get_config_manager() -> ConfigManager:
    """
    Get the ConfigManager singleton instance.
    
    Returns:
        ConfigManager instance
    """
    return ConfigManager.get_instance()


def get_logger(name: str) -> logging.Logger:
    """
    Get a configured logger instance.
    
    DEPRECATED: Use pyquizhub.logging.setup.get_logger instead.
    This function is kept for backward compatibility but will issue a warning.
    
    Args:
        name: Name for the logger
        
    Returns:
        Logger instance
    """
    # Import here to avoid circular dependency
    from pyquizhub.logging.setup import get_logger as new_get_logger
    
    # Issue deprecation warning (only once per module)
    if not hasattr(get_logger, '_warned'):
        logging.warning(
            "get_logger from pyquizhub.config.settings is deprecated. "
            "Please use pyquizhub.logging.setup.get_logger instead."
        )
        get_logger._warned = True
    
    return new_get_logger(name)


__all__ = [
    'ConfigManager',
    'AppSettings',
    'get_config_manager',
    'get_logger',  # Deprecated
    'StorageSettings',
    'APISettings',
    'SecuritySettings',
    'LoggingSettings',
    'FileStorageSettings',
    'SQLStorageSettings',
]

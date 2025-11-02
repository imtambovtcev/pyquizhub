"""
Configuration Manager for PyQuizHub.

This module provides a thread-safe singleton ConfigManager class that loads
and manages application configuration with support for environment variable
overrides and validation.
"""

import os
import yaml
import logging
import threading
from typing import Optional, Any, Dict


class ConfigManager:
    """
    Thread-safe singleton class to manage application configuration.
    
    This class ensures that configuration is loaded only once and provides
    a centralized interface for accessing configuration values throughout
    the application.
    
    Attributes:
        _instance: Singleton instance of ConfigManager
        _lock: Thread lock for singleton instantiation
        _config: Cached configuration dictionary
        _config_path: Path to the configuration file
    """
    
    _instance: Optional['ConfigManager'] = None
    _lock = threading.Lock()
    
    def __init__(self):
        """Initialize ConfigManager. Should not be called directly."""
        if ConfigManager._instance is not None:
            raise RuntimeError("Use ConfigManager.get_instance() instead")
        
        self._config: Optional[Dict[str, Any]] = None
        self._config_path: Optional[str] = None
        self._initialized = False
    
    @classmethod
    def get_instance(cls) -> 'ConfigManager':
        """
        Get the singleton instance of ConfigManager.
        
        Returns:
            ConfigManager: Singleton instance
        """
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls.__new__(cls)
                    cls._instance.__init__()
        return cls._instance
    
    @classmethod
    def reset_instance(cls):
        """
        Reset the singleton instance. Useful for testing.
        
        Warning: This should only be used in test environments.
        """
        with cls._lock:
            cls._instance = None
    
    def load(self, config_path: Optional[str] = None) -> Dict[str, Any]:
        """
        Load configuration from file.
        
        Args:
            config_path: Path to configuration file. If None, uses default path.
        
        Returns:
            Dict containing configuration data
        
        Raises:
            FileNotFoundError: If configuration file is not found
        """
        if self._initialized and config_path is None:
            # Return cached config if already loaded and no new path specified
            return self._config
        
        if config_path is None:
            config_path = os.getenv(
                "PYQUIZHUB_CONFIG_PATH",
                os.path.join(os.path.dirname(__file__), "config.yaml")
            )
        
        self._config_path = config_path
        
        try:
            with open(config_path, "r") as f:
                self._config = yaml.safe_load(f)
            self._initialized = True
            logging.debug(f"Configuration loaded from {config_path}")
            return self._config
        except FileNotFoundError:
            logging.error(f"Configuration file not found at {config_path}")
            raise
        except Exception as e:
            logging.error(f"Error loading configuration: {e}")
            raise
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value by key using dot notation.
        
        Args:
            key: Configuration key in dot notation (e.g., "storage.type")
            default: Default value if key is not found
        
        Returns:
            Configuration value or default
        """
        if not self._initialized:
            self.load()
        
        keys = key.split(".")
        value = self._config
        
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k, default)
                if value is default:
                    break
            else:
                return default
        
        # Check for environment variable override
        env_key = f"PYQUIZHUB_{key.upper().replace('.', '__')}"
        env_value = os.getenv(env_key)
        
        if env_value is not None:
            # Try to convert to appropriate type
            if isinstance(value, bool):
                return env_value.lower() in ('true', '1', 'yes')
            elif isinstance(value, int):
                try:
                    return int(env_value)
                except ValueError:
                    pass
            return env_value
        
        return value
    
    def get_config(self) -> Dict[str, Any]:
        """
        Get the entire configuration dictionary.
        
        Returns:
            Complete configuration dictionary
        """
        if not self._initialized:
            self.load()
        return self._config
    
    def get_config_path(self) -> str:
        """
        Get the path to the loaded configuration file.
        
        Returns:
            Path to configuration file
        """
        if not self._initialized:
            self.load()
        return self._config_path
    
    # Convenience properties for common config access patterns
    
    @property
    def storage_type(self) -> str:
        """Get storage type (file or sql)."""
        return self.get("storage.type", "file")
    
    @property
    def storage_file_base_dir(self) -> str:
        """Get file storage base directory."""
        return self.get("storage.file.base_dir", ".pyquizhub")
    
    @property
    def storage_sql_connection_string(self) -> str:
        """Get SQL storage connection string."""
        return self.get("storage.sql.connection_string", "sqlite:///pyquizhub.db")
    
    @property
    def api_base_url(self) -> str:
        """Get API base URL."""
        return self.get("api.base_url", "http://127.0.0.1:8000")
    
    @property
    def api_host(self) -> str:
        """Get API host."""
        return self.get("api.host", "0.0.0.0")
    
    @property
    def api_port(self) -> int:
        """Get API port."""
        return self.get("api.port", 8000)
    
    @property
    def security_use_tokens(self) -> bool:
        """Check if token security is enabled."""
        return self.get("security.use_tokens", True)
    
    def get_token_env_var(self, token_type: str) -> Optional[str]:
        """
        Get the environment variable name for a token type.
        
        Args:
            token_type: Type of token (admin, creator, user)
        
        Returns:
            Environment variable name or None
        """
        return self.get(f"security.{token_type}_token_env")
    
    def get_token(self, token_type: str) -> Optional[str]:
        """
        Get token value from environment variable.
        
        Args:
            token_type: Type of token (admin, creator, user)
        
        Returns:
            Token value or None
        """
        if not self.security_use_tokens:
            return None
        
        token_env_key = self.get_token_env_var(token_type)
        if token_env_key:
            return os.getenv(token_env_key)
        return None
    
    @property
    def logging_config(self) -> Dict[str, Any]:
        """Get logging configuration."""
        return self.get("logging", {})


def get_config_manager() -> ConfigManager:
    """
    Get the ConfigManager singleton instance.
    
    Returns:
        ConfigManager instance
    """
    return ConfigManager.get_instance()
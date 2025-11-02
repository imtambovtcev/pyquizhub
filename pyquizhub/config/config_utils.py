import os
import logging
from typing import Optional
from pyquizhub.config.settings import get_config_manager


def load_config(config_path: str = None) -> dict:
    """
    Load configuration using ConfigManager singleton.
    
    DEPRECATED: Use get_config_manager() directly instead.
    This function is kept for backward compatibility.
    
    Args:
        config_path: Path to configuration file. If None, uses default path.
    
    Returns:
        Dict containing configuration data
    """
    config_manager = get_config_manager()
    if config_path is not None:
        config_manager.load(config_path)
    return config_manager.get_config()


def get_config_value(config: dict, key: str, default=None):
    """
    Get configuration value by key using dot notation.
    
    DEPRECATED: Use get_config_manager().get(key, default) directly instead.
    This function is kept for backward compatibility.
    
    Args:
        config: Configuration dictionary (ignored, kept for compatibility)
        key: Configuration key in dot notation (e.g., "storage.type")
        default: Default value if key is not found
    
    Returns:
        Configuration value or default
    """
    config_manager = get_config_manager()
    return config_manager.get(key, default)


def get_token_from_config(token_type: str) -> Optional[str]:
    """
    Get token value from environment variable via ConfigManager.
    
    Args:
        token_type: Type of token (admin, creator, user)
    
    Returns:
        Token value or None
    """
    config_manager = get_config_manager()
    return config_manager.get_token(token_type)


def get_logger(name: str) -> logging.Logger:
    """
    Get a configured logger instance.
    
    Args:
        name: Name for the logger
    
    Returns:
        Configured logger instance
    """
    config_manager = get_config_manager()
    from pyquizhub.logging.log_manager import LogManager
    return LogManager.get_instance(config_manager.logging_config).get_logger(name)


def get_uvicorn_config():
    """
    Get uvicorn configuration (host and port).
    
    Returns:
        Tuple of (host, port)
    """
    config_manager = get_config_manager()
    return config_manager.api_host, config_manager.api_port

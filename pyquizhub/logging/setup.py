"""
Logging setup for PyQuizHub.

This module provides delayed logging initialization to avoid circular
dependencies with the configuration system.

Usage:
    # In main.py or initialization code:
    from pyquizhub.logging.setup import setup_logging, get_logger
    from pyquizhub.config.settings import get_config_manager
    
    # Load config first
    config_manager = get_config_manager()
    config_manager.load()
    
    # Then setup logging
    setup_logging(config_manager.logging_config)
    
    # Now get loggers
    logger = get_logger(__name__)
"""

import logging
import logging.config
import os
from typing import Dict, Any, Optional
from pyquizhub.logging.log_manager import LogManager


_logging_configured = False
_log_manager: Optional[LogManager] = None


def setup_logging(logging_config: Dict[str, Any]) -> None:
    """
    Initialize logging system with configuration.
    
    This should be called AFTER configuration is loaded, not during
    config loading (to avoid circular dependencies).
    
    Args:
        logging_config: Dictionary with logging configuration
    """
    global _logging_configured, _log_manager
    
    if _logging_configured:
        logging.warning("Logging already configured, skipping re-initialization")
        return
    
    # Initialize LogManager singleton
    _log_manager = LogManager.get_instance(logging_config)
    _logging_configured = True
    
    logging.info("Logging system initialized successfully")


def get_logger(name: str) -> logging.Logger:
    """
    Get a configured logger instance.
    
    If logging hasn't been set up yet, this returns a basic logger
    that will work but won't have custom configuration.
    
    Args:
        name: Name for the logger (typically __name__)
        
    Returns:
        Logger instance
    """
    if _logging_configured and _log_manager is not None:
        return _log_manager.get_logger(name)
    else:
        # Return basic logger if logging not yet configured
        # This allows early modules to log without breaking
        logger = logging.getLogger(name)
        if not logger.handlers:
            # Add basic console handler if none exists
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)
        return logger


def is_logging_configured() -> bool:
    """
    Check if logging has been configured.
    
    Returns:
        True if setup_logging() has been called
    """
    return _logging_configured


def reset_logging():
    """
    Reset logging configuration.
    
    This is mainly useful for testing.
    """
    global _logging_configured, _log_manager
    _logging_configured = False
    _log_manager = None

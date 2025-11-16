"""
Log manager for PyQuizHub.

This module provides a singleton LogManager class to configure and manage logging
for the application. It supports configuration via a dictionary and ensures
log directories are created if they do not exist.
"""

import logging
import logging.config
import os


class LogManager:
    """
    Singleton class to manage logging configuration and provide logger instances.

    This class ensures that logging is configured only once and provides a method
    to retrieve logger instances by name.

    Attributes:
        _instance (LogManager | None): Singleton instance of LogManager
        logger_settings (dict): Logging configuration settings
    """

    _instance: 'LogManager' | None = None

    def __init__(self, logger_settings: dict):
        """
        Initialize the LogManager with logging settings.

        Args:
            logger_settings (dict): Dictionary containing logging configuration
        """
        self.logger_settings = logger_settings or {}
        if self.logger_settings:
            # Ensure version is set in config
            if 'version' not in self.logger_settings:
                self.logger_settings['version'] = 1

            # Ensure log directory exists
            log_path = self.logger_settings.get(
                'handlers', {}).get('file', {}).get('filename')
            if log_path:
                os.makedirs(os.path.dirname(log_path), exist_ok=True)

            # Configure logging using dictConfig
            try:
                logging.config.dictConfig(self.logger_settings)
            except ValueError as e:
                # Fallback to basic configuration if dictionary config fails
                logging.basicConfig(level=logging.INFO)
                logging.warning(
                    f"Failed to configure logging with provided settings: {e}")

    @classmethod
    def get_instance(cls, logger_settings: dict = None) -> 'LogManager':
        """
        Get the singleton instance of LogManager.

        Args:
            logger_settings (dict, optional): Dictionary containing logging configuration

        Returns:
            LogManager: Singleton instance of LogManager
        """
        if cls._instance is None:
            cls._instance = cls(logger_settings)
        return cls._instance

    def get_logger(self, name: str) -> logging.Logger:
        """
        Get a logger instance by name.

        Args:
            name (str): Name of the logger

        Returns:
            logging.Logger: Logger instance
        """
        return logging.getLogger(name)

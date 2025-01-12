import logging
import logging.config
import os
from typing import Optional


class LogManager:
    _instance: Optional['LogManager'] = None

    def __init__(self, logger_settings: dict):
        self.logger_settings = logger_settings or {}
        if self.logger_settings:
            # Ensure log directory exists
            log_path = self.logger_settings.get(
                'handlers', {}).get('file', {}).get('filename')
            if log_path:
                os.makedirs(os.path.dirname(log_path), exist_ok=True)
            # Configure logging using dictConfig
            logging.config.dictConfig(self.logger_settings)

    @classmethod
    def get_instance(cls, logger_settings: dict = None) -> 'LogManager':
        if cls._instance is None:
            cls._instance = cls(logger_settings)
        return cls._instance

    def get_logger(self, name: str) -> logging.Logger:
        return logging.getLogger(name)

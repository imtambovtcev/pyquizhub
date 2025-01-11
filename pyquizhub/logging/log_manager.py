import logging
import os
from logging.handlers import RotatingFileHandler
from typing import Optional


class LogManager:
    _instance: Optional['LogManager'] = None

    def __init__(self, logger_settings: dict):
        self.logger_settings = logger_settings or {}
        self.log_format = logger_settings.get(
            "format", "%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        self.date_format = logger_settings.get(
            "date_format", "%Y-%m-%d %H:%M:%S")
        self.default_level = self._get_level(
            logger_settings.get("level", "INFO"))

    @classmethod
    def get_instance(cls, logger_settings: dict = None) -> 'LogManager':
        if cls._instance is None:
            cls._instance = cls(logger_settings)
        return cls._instance

    def _get_level(self, level_name: str) -> int:
        return getattr(logging, level_name.upper(), logging.INFO)

    def get_logger(self, name: str) -> logging.Logger:
        logger = logging.getLogger(name)
        # if logger.hasHandlers():
        #     return logger

        logger.setLevel(self.default_level)
        formatter = logging.Formatter(
            self.log_format, datefmt=self.date_format)

        # Console handler
        if self.logger_settings.get("console", {}).get("enabled", True):
            console_level = self._get_level(self.logger_settings.get(
                "console", {}).get("level", "INFO"))
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(formatter)
            console_handler.setLevel(console_level)
            logger.addHandler(console_handler)

        # File handler
        if self.logger_settings.get("file", {}).get("enabled", True):
            file_path = self.logger_settings.get(
                "file", {}).get("path", "logs/pyquizhub.log")
            os.makedirs(os.path.dirname(file_path), exist_ok=True)

            file_level = self._get_level(self.logger_settings.get(
                "file", {}).get("level", "DEBUG"))
            max_size = self.logger_settings.get(
                "file", {}).get("max_size", 1048576)
            backup_count = self.logger_settings.get(
                "file", {}).get("backup_count", 5)

            file_handler = RotatingFileHandler(
                file_path, maxBytes=max_size, backupCount=backup_count)
            file_handler.setFormatter(formatter)
            file_handler.setLevel(file_level)
            logger.addHandler(file_handler)

        return logger

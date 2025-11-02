# Updated config_utils.py

from settings import ConfigManager


def load_config():
    config = ConfigManager.get_instance().config
    return config


def get_config_value(key):
    config = ConfigManager.get_instance().config
    return config.get(key)


def get_token_from_config():
    config = ConfigManager.get_instance().config
    return config.get('token')


def get_logger():
    config = ConfigManager.get_instance().config
    logger = create_logger(config)
    return logger


def get_uvicorn_config():
    config = ConfigManager.get_instance().config
    return config.get('uvicorn')

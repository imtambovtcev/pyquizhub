import os
import yaml
from fastapi import HTTPException


def load_config(config_path: str = None) -> dict:
    if config_path is None:
        config_path = os.getenv("PYQUIZHUB_CONFIG_PATH", os.path.join(
            os.path.dirname(__file__), "config.yaml"))
    with open(config_path, "r") as f:
        return yaml.safe_load(f)


def get_config_value(config: dict, key: str, default=None):
    keys = key.split(".")
    value = config
    for k in keys:
        value = value.get(k, default)
        if value is default:
            break
    return value


def get_token_from_config(token_type: str) -> str:
    config = load_config()
    use_tokens = get_config_value(config, "security.use_tokens", False)
    if use_tokens:
        token_env_key = get_config_value(
            config, f"security.{token_type}_token_env", "")
        return os.getenv(token_env_key, None)
    return None

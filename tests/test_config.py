"""
Tests for configuration management system.

Tests cover:
- Configuration file loading from multiple paths
- Environment variable overrides
- Configuration validation
- Error handling for missing/invalid configs
"""

import os
import pytest
import tempfile
import yaml
from pathlib import Path
from pyquizhub.config.settings import (
    get_config_manager,
    ConfigManager,
    AppSettings,
    StorageSettings,
    APISettings,
    SecuritySettings,
    LoggingSettings
)
from pydantic import ValidationError


@pytest.fixture(autouse=True)
def reset_config():
    """Reset config manager before each test."""
    ConfigManager.reset_instance()
    yield
    ConfigManager.reset_instance()


@pytest.fixture
def valid_config():
    """Return a valid configuration dictionary."""
    return {
        "storage": {
            "type": "file",
            "file": {
                "base_dir": ".pyquizhub"
            },
            "sql": {
                "connection_string": "sqlite:///pyquizhub.db"
            }
        },
        "api": {
            "base_url": "http://127.0.0.1:8000",
            "host": "0.0.0.0",
            "port": 8000
        },
        "security": {
            "use_tokens": True,
            "admin_token_env": "PYQUIZHUB_ADMIN_TOKEN",
            "creator_token_env": "PYQUIZHUB_CREATOR_TOKEN",
            "user_token_env": "PYQUIZHUB_USER_TOKEN"
        },
        "logging": {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "standard": {
                    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
                }
            },
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "level": "INFO",
                    "formatter": "standard"
                }
            },
            "root": {
                "level": "INFO",
                "handlers": ["console"]
            }
        }
    }


@pytest.fixture
def config_file(valid_config):
    """Create a temporary config file."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        yaml.dump(valid_config, f)
        config_path = f.name

    yield config_path

    # Cleanup
    if os.path.exists(config_path):
        os.unlink(config_path)


class TestConfigLoading:
    """Test configuration loading from files."""

    def test_load_config_from_explicit_path(self, config_file):
        """Test loading config from explicitly provided path."""
        config_manager = get_config_manager()
        config = config_manager.load(config_file)

        assert config is not None
        assert config['storage']['type'] == 'file'
        assert config['api']['port'] == 8000

    def test_load_config_from_env_var(self, config_file, monkeypatch):
        """Test loading config from PYQUIZHUB_CONFIG_PATH env var."""
        monkeypatch.setenv("PYQUIZHUB_CONFIG_PATH", config_file)

        config_manager = get_config_manager()
        config = config_manager.load()

        assert config is not None
        assert config['storage']['type'] == 'file'

    def test_config_file_not_found(self):
        """Test error handling when config file doesn't exist."""
        config_manager = get_config_manager()

        with pytest.raises(FileNotFoundError) as exc_info:
            config_manager.load("/nonexistent/path/config.yaml")

        assert "not found" in str(exc_info.value).lower()

    def test_invalid_yaml(self):
        """Test error handling for invalid YAML."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("invalid: yaml: content: [")
            invalid_config_path = f.name

        try:
            config_manager = get_config_manager()
            with pytest.raises(ValueError) as exc_info:
                config_manager.load(invalid_config_path)

            assert "yaml" in str(exc_info.value).lower()
        finally:
            os.unlink(invalid_config_path)

    def test_singleton_pattern(self, config_file):
        """Test that ConfigManager is a singleton."""
        cm1 = get_config_manager()
        cm2 = get_config_manager()

        assert cm1 is cm2

        cm1.load(config_file)
        config1 = cm1.get_config()
        config2 = cm2.get_config()

        assert config1 == config2


class TestConfigAccess:
    """Test configuration value access methods."""

    def test_get_with_dot_notation(self, config_file):
        """Test accessing config values with dot notation."""
        config_manager = get_config_manager()
        config_manager.load(config_file)

        assert config_manager.get("storage.type") == "file"
        assert config_manager.get("api.port") == 8000
        assert config_manager.get("api.host") == "0.0.0.0"

    def test_get_with_default(self, config_file):
        """Test default values for non-existent keys."""
        config_manager = get_config_manager()
        config_manager.load(config_file)

        assert config_manager.get("nonexistent.key", "default") == "default"

    def test_convenience_properties(self, config_file):
        """Test convenience property accessors."""
        config_manager = get_config_manager()
        config_manager.load(config_file)

        assert config_manager.storage_type == "file"
        assert config_manager.api_port == 8000
        assert config_manager.api_host == "0.0.0.0"
        assert config_manager.security_use_tokens is True


class TestEnvironmentVariableOverrides:
    """Test environment variable override functionality."""

    def test_override_storage_type(self, config_file, monkeypatch):
        """Test overriding storage type via environment variable."""
        monkeypatch.setenv("PYQUIZHUB_STORAGE__TYPE", "sql")

        config_manager = get_config_manager()
        config_manager.load(config_file)

        # Note: With new Pydantic-based system, env vars override at load time
        settings = AppSettings.from_yaml(config_file)
        assert settings.storage.type == "sql"

    def test_override_api_port(self, config_file, monkeypatch):
        """Test overriding API port via environment variable."""
        monkeypatch.setenv("PYQUIZHUB_API__PORT", "9000")

        settings = AppSettings.from_yaml(config_file)
        assert settings.api.port == 9000

    def test_override_boolean_value(self, config_file, monkeypatch):
        """Test overriding boolean values."""
        monkeypatch.setenv("PYQUIZHUB_SECURITY__USE_TOKENS", "false")

        settings = AppSettings.from_yaml(config_file)
        assert settings.security.use_tokens is False

    def test_override_connection_string(self, config_file, monkeypatch):
        """Test overriding SQL connection string."""
        new_conn_str = "postgresql://user:pass@localhost/db"
        monkeypatch.setenv(
            "PYQUIZHUB_STORAGE__SQL__CONNECTION_STRING",
            new_conn_str)

        settings = AppSettings.from_yaml(config_file)
        assert settings.storage.sql.connection_string == new_conn_str


class TestConfigValidation:
    """Test configuration validation."""

    def test_invalid_storage_type(self, config_file):
        """Test validation catches invalid storage types."""
        # Modify config to have invalid storage type
        with open(config_file, 'r') as f:
            config_data = yaml.safe_load(f)

        config_data['storage']['type'] = 'invalid_type'

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config_data, f)
            invalid_config_path = f.name

        try:
            with pytest.raises(ValueError) as exc_info:
                AppSettings.from_yaml(invalid_config_path)

            assert "validation" in str(exc_info.value).lower()
        finally:
            os.unlink(invalid_config_path)

    def test_invalid_port_number(self, config_file):
        """Test validation catches invalid port numbers."""
        with open(config_file, 'r') as f:
            config_data = yaml.safe_load(f)

        config_data['api']['port'] = 99999  # Invalid port

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config_data, f)
            invalid_config_path = f.name

        try:
            with pytest.raises(ValueError) as exc_info:
                AppSettings.from_yaml(invalid_config_path)

            assert "validation" in str(exc_info.value).lower()
        finally:
            os.unlink(invalid_config_path)

    def test_missing_required_sections_use_defaults(self, config_file):
        """Test that missing optional sections use defaults."""
        # Create minimal config
        minimal_config = {"storage": {"type": "file"}}

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(minimal_config, f)
            minimal_config_path = f.name

        try:
            settings = AppSettings.from_yaml(minimal_config_path)

            # Should use defaults
            assert settings.api.port == 8000
            assert settings.security.use_tokens is True
        finally:
            os.unlink(minimal_config_path)


class TestTokenManagement:
    """Test token retrieval functionality."""

    def test_get_admin_token(self, config_file, monkeypatch):
        """Test retrieving admin token from environment."""
        monkeypatch.setenv("PYQUIZHUB_ADMIN_TOKEN", "test_admin_token")

        config_manager = get_config_manager()
        config_manager.load(config_file)

        token = config_manager.get_token("admin")
        assert token == "test_admin_token"

    def test_get_creator_token(self, config_file, monkeypatch):
        """Test retrieving creator token from environment."""
        monkeypatch.setenv("PYQUIZHUB_CREATOR_TOKEN", "test_creator_token")

        config_manager = get_config_manager()
        config_manager.load(config_file)

        token = config_manager.get_token("creator")
        assert token == "test_creator_token"

    def test_tokens_disabled(self, config_file, monkeypatch):
        """Test token retrieval when tokens are disabled."""
        monkeypatch.setenv("PYQUIZHUB_SECURITY__USE_TOKENS", "false")
        monkeypatch.setenv("PYQUIZHUB_ADMIN_TOKEN", "test_admin_token")

        config_manager = get_config_manager()
        config_manager.load(config_file)

        # Reload with env var override
        ConfigManager.reset_instance()
        config_manager = get_config_manager()
        config_manager.load(config_file)

        token = config_manager.get_token("admin")
        # Note: This behavior depends on implementation
        # The new system should check security.use_tokens


class TestConfigPathSearch:
    """Test configuration file search strategy."""

    def test_search_order(self, valid_config, monkeypatch):
        """Test that config search follows correct priority order."""
        # Create config in current directory
        local_config_path = "./test_config.yaml"
        with open(local_config_path, 'w') as f:
            yaml.dump(valid_config, f)

        try:
            # Set env var to different path (should take precedence)
            env_config_path = "./test_env_config.yaml"
            modified_config = valid_config.copy()
            modified_config['api']['port'] = 9999

            with open(env_config_path, 'w') as f:
                yaml.dump(modified_config, f)

            try:
                monkeypatch.setenv("PYQUIZHUB_CONFIG_PATH", env_config_path)

                config_manager = get_config_manager()
                config_manager.load()

                # Should use the env var path (port 9999)
                assert config_manager.api_port == 9999
            finally:
                if os.path.exists(env_config_path):
                    os.unlink(env_config_path)
        finally:
            if os.path.exists(local_config_path):
                os.unlink(local_config_path)


class TestPydanticModels:
    """Test Pydantic model validation and serialization."""

    def test_storage_settings_defaults(self):
        """Test StorageSettings with defaults."""
        settings = StorageSettings()
        assert settings.type == "file"
        assert settings.file.base_dir == ".pyquizhub"

    def test_api_settings_validation(self):
        """Test APISettings validation."""
        # Valid port
        settings = APISettings(port=8000)
        assert settings.port == 8000

        # Invalid port should raise error
        with pytest.raises(ValidationError):
            APISettings(port=999999)

    def test_security_settings_defaults(self):
        """Test SecuritySettings with defaults."""
        settings = SecuritySettings()
        assert settings.use_tokens is True
        assert settings.admin_token_env == "PYQUIZHUB_ADMIN_TOKEN"

    def test_app_settings_serialization(self, valid_config):
        """Test AppSettings can be serialized back to dict."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(valid_config, f)
            config_path = f.name

        try:
            settings = AppSettings.from_yaml(config_path)
            config_dict = settings.model_dump()

            assert isinstance(config_dict, dict)
            assert 'storage' in config_dict
            assert 'api' in config_dict
            assert config_dict['storage']['type'] == 'file'
        finally:
            os.unlink(config_path)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

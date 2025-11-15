"""
PyQuizHub test configuration.

This module provides pytest fixtures for setting up test environments, including:
- Temporary project directories
- Configuration files
- Storage directories
- Logger setup
- API client setup
"""

import pytest
import os
from fastapi.testclient import TestClient
from pyquizhub.config.settings import ConfigManager, get_config_manager


# Session-level fixture to clear environment variables before any tests run
@pytest.fixture(scope="session", autouse=True)
def clear_env_vars():
    """
    Clear PYQUIZHUB environment variables at session start.

    This ensures that environment variables from .env files don't interfere
    with test isolation, especially when running tests from VSCode which
    automatically loads .env files.
    """
    env_vars_to_clear = [
        "PYQUIZHUB_STORAGE__TYPE",
        "PYQUIZHUB_STORAGE__SQL__CONNECTION_STRING",
        "PYQUIZHUB_STORAGE__FILE__BASE_DIR",
        "PYQUIZHUB_API__BASE_URL",
        "PYQUIZHUB_API__HOST",
        "PYQUIZHUB_API__PORT",
        "PYQUIZHUB_ADMIN_TOKEN",
        "PYQUIZHUB_CREATOR_TOKEN",
        "PYQUIZHUB_USER_TOKEN",
    ]

    # Store original values
    original_values = {}
    for var in env_vars_to_clear:
        if var in os.environ:
            original_values[var] = os.environ[var]
            del os.environ[var]

    yield

    # Restore original values after all tests complete
    for var, value in original_values.items():
        os.environ[var] = value


@pytest.fixture(scope="module")
def test_project_dir(tmp_path_factory, request):
    """Creates a unique test project directory for each test module."""
    dirname = f"test_project_{request.module.__name__}"
    tmpdir = tmp_path_factory.mktemp(dirname)
    return tmpdir


@pytest.fixture(scope="module")
def config_path(test_project_dir):
    """Creates a config file in the test project directory."""
    config_dir = test_project_dir / "test_config"
    config_dir.mkdir()
    config_path = config_dir / "test_config.yaml"
    return config_path


@pytest.fixture(scope="module", autouse=True)
def setup_config(config_path):
    """
    Setup the config file and environment variable.

    This fixture sets up the configuration file and the PYQUIZHUB_CONFIG_PATH
    environment variable for the duration of the test module.
    """
    original_config_path = os.environ.get("PYQUIZHUB_CONFIG_PATH")
    os.environ["PYQUIZHUB_CONFIG_PATH"] = str(config_path)

    # Create an empty config file
    config_path.write_text(f"""
fixture:
    config_path: {str(config_path)}
""")

    # Reset ConfigManager to ensure clean state for tests
    ConfigManager.reset_instance()

    yield

    # Reset ConfigManager after tests
    ConfigManager.reset_instance()

    if original_config_path:
        os.environ["PYQUIZHUB_CONFIG_PATH"] = original_config_path
    else:
        os.environ.pop("PYQUIZHUB_CONFIG_PATH", None)


@pytest.fixture(scope="module")
def storage_base_dir(test_project_dir):
    """Creates a storage directory in the test project directory."""
    storage_dir = test_project_dir / "storage"
    storage_dir.mkdir()
    return storage_dir


@pytest.fixture(scope="module", autouse=True)
def setup_logger(config_path, test_project_dir):
    """
    Setup logger to log to the pytest temp directory.

    This fixture configures the logger to write logs to the test project directory.
    """
    from pyquizhub.logging.log_manager import LogManager
    log_dir = test_project_dir / "logs"
    log_dir.mkdir()

    config_content = f"""
logging:
    format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    date_format: "%Y-%m-%d %H:%M:%S"
    level: "DEBUG"
    console:
        enabled: True
        level: "INFO"
    file:
        enabled: True
        path: "{log_dir}/pyquizhub.log"
        level: "DEBUG"
        max_size: 1048576
        backup_count: 5
"""
    with open(config_path, "a") as f:
        f.write(config_content)

    config_manager = get_config_manager()
    config_manager.load(str(config_path))
    LogManager.get_instance(config_manager.logging_config)


@pytest.fixture(scope="module")
def api_client(config_path, storage_base_dir, test_project_dir):
    """
    Creates a unique API client for each test module with its own storage.

    This fixture sets up an API client with a unique storage directory for each test module.
    """
    config_content = f"""
storage:
    type: "file"
    file:
        base_dir: "{storage_base_dir}"
    sql:
        connection_string: "sqlite:///{test_project_dir}/test.db"
api:
    base_url: "http://testserver"
security:
    use_tokens: true
"""
    with open(config_path, "a") as f:
        f.write(config_content)

    # Set token environment variables for tests
    os.environ["PYQUIZHUB_ADMIN_TOKEN"] = "test_admin_token_12345"
    os.environ["PYQUIZHUB_CREATOR_TOKEN"] = "test_admin_token_12345"
    os.environ["PYQUIZHUB_USER_TOKEN"] = "test_user_token_67890"

    # Force config manager to reload after writing security config
    from pyquizhub.config.settings import ConfigManager
    ConfigManager.reset_instance()
    config_manager = ConfigManager.get_instance()
    config_manager.load(str(config_path))

    # Now import app after config is properly set up
    from pyquizhub.main import app

    with TestClient(app, base_url="http://testserver") as client:
        yield client

    # Clean up environment variables after test
    os.environ.pop("PYQUIZHUB_ADMIN_TOKEN", None)
    os.environ.pop("PYQUIZHUB_CREATOR_TOKEN", None)
    os.environ.pop("PYQUIZHUB_USER_TOKEN", None)

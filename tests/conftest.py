
import pytest
import os
from fastapi.testclient import TestClient
from pyquizhub.config.config_utils import load_config


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
    """Setup the config file and environment variable."""

    original_config_path = os.environ.get("PYQUIZHUB_CONFIG_PATH")
    os.environ["PYQUIZHUB_CONFIG_PATH"] = str(config_path)

    # Create an empty config file
    config_path.write_text(f"""
fixture:
    config_path: {str(config_path)}
""")

    yield

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
    """Setup logger to log to the pytest temp directory."""
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

    config = load_config(str(config_path))
    LogManager.get_instance(config.get('logging', {}))


@pytest.fixture(scope="module")
def api_client(config_path, storage_base_dir, test_project_dir):
    """Creates a unique API client for each test module with its own storage."""
    from pyquizhub.main import app
    config_content = f"""
storage:
    type: "file"
    file:
        base_dir: "{storage_base_dir}"
    sql:
        connection_string: "sqlite:///{test_project_dir}/test.db"
api:
    base_url: "http://testserver"
"""
    with open(config_path, "a") as f:
        f.write(config_content)

    with TestClient(app, base_url="http://testserver") as client:
        yield client

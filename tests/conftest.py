import pytest
import os
from fastapi.testclient import TestClient
from pyquizhub.main import app
from pyquizhub.core.storage.file_storage import FileStorageManager


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


@pytest.fixture(scope="module")
def storage_base_dir(test_project_dir):
    """Creates a storage directory in the test project directory."""
    storage_dir = test_project_dir / "storage"
    storage_dir.mkdir()
    return storage_dir


@pytest.fixture(scope="module")
def api_client(config_path, storage_base_dir, test_project_dir):
    """Creates a unique API client for each test module with its own storage."""
    original_config_path = os.environ.get("PYQUIZHUB_CONFIG_PATH")

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
    config_path.write_text(config_content)

    os.environ["PYQUIZHUB_CONFIG_PATH"] = str(config_path)

    with TestClient(app, base_url="http://testserver") as client:
        yield client

    if original_config_path:
        os.environ["PYQUIZHUB_CONFIG_PATH"] = original_config_path
    else:
        os.environ.pop("PYQUIZHUB_CONFIG_PATH", None)

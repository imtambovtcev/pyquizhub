import pytest
import os
from fastapi.testclient import TestClient
from pyquizhub.core.engine.engine_api import app


class AdapterAPIServer:
    """
    Simulate an adapter-specific API server using TestClient in-process.
    """

    def __init__(self, config_path):
        self.config_path = config_path
        self.client = TestClient(app)

    def start(self):
        """Set CONFIG_PATH so the CLI picks up our in-memory config."""
        os.environ["CONFIG_PATH"] = self.config_path

    def stop(self):
        """Clean up environment."""
        if "CONFIG_PATH" in os.environ:
            del os.environ["CONFIG_PATH"]


@pytest.fixture(scope="module")
def adapter_api(tmpdir_factory):
    """
    Provide an AdapterAPIServer fixture that writes a config file, points
    `api.base_url` to http://testserver, and initializes TestClient in-process.
    """
    tmpdir = tmpdir_factory.mktemp("adapter_config")
    config_path = tmpdir.join("adapter_test_config.yaml")

    # The key: base_url = "http://testserver"
    # so that the CLI's requests go in-process via TestClient
    config_content = f"""
    storage:
      type: "sql"
      sql:
        connection_string: "sqlite:///{tmpdir}/adapter_test.db"
    api:
      base_url: "http://testserver"
    """
    config_path.write(config_content)

    server = AdapterAPIServer(str(config_path))
    server.start()
    yield server
    server.stop()

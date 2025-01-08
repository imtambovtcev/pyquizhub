import os
import yaml
from sqlalchemy import create_engine, MetaData


def initialize_system():
    """Initialize the pyquizhub system based on the configuration."""
    # Load configuration
    config_path = "config.yaml"
    if not os.path.exists(config_path):
        raise FileNotFoundError(
            f"Configuration file '{config_path}' not found.")

    with open(config_path, "r") as f:
        config = yaml.safe_load(f)

    # Handle storage initialization
    storage_type = config.get("storage", {}).get("type", "file")
    if storage_type == "file":
        base_dir = config["storage"]["file"]["base_dir"]
        os.makedirs(base_dir, exist_ok=True)
        os.makedirs(os.path.join(base_dir, "quizzes"), exist_ok=True)
        os.makedirs(os.path.join(base_dir, "results"), exist_ok=True)
        print(f"File-based storage initialized at {base_dir}.")
    elif storage_type == "sql":
        connection_string = config["storage"]["sql"]["connection_string"]
        engine = create_engine(connection_string)
        metadata = MetaData()

        # Create tables (example schema)
        metadata.create_all(engine)
        print(f"SQL storage initialized with connection: {connection_string}.")
    else:
        raise ValueError(f"Unsupported storage type: {storage_type}")

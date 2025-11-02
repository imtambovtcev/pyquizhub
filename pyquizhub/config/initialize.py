import os
from sqlalchemy import create_engine, MetaData
from pyquizhub.config.settings import get_config_manager


def initialize_system():
    """Initialize the pyquizhub system based on the configuration."""
    # Get configuration manager
    config_manager = get_config_manager()
    config_manager.load()  # Ensure config is loaded

    # Handle storage initialization
    storage_type = config_manager.storage_type
    if storage_type == "file":
        base_dir = config_manager.storage_file_base_dir
        os.makedirs(base_dir, exist_ok=True)
        os.makedirs(os.path.join(base_dir, "quizzes"), exist_ok=True)
        os.makedirs(os.path.join(base_dir, "results"), exist_ok=True)
        print(f"File-based storage initialized at {base_dir}.")
    elif storage_type == "sql":
        connection_string = config_manager.storage_sql_connection_string
        engine = create_engine(connection_string)
        metadata = MetaData()

        # Create tables (example schema)
        metadata.create_all(engine)
        print(f"SQL storage initialized with connection: {connection_string}.")
    else:
        raise ValueError(f"Unsupported storage type: {storage_type}")

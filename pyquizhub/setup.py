import yaml
import os


def setup():
    """CLI command to configure and initialize pyquizhub."""
    config_path = "config.yaml"

    # Prompt for storage type
    print("Welcome to PyQuizHub Setup!")
    storage_type = input("Select storage type (file/sql): ").strip().lower()

    if storage_type not in ["file", "sql"]:
        print("Invalid storage type. Exiting.")
        return

    # Configure file-based storage
    if storage_type == "file":
        base_dir = input(
            "Enter base directory for storage (default: .pyquizhub): ").strip()
        base_dir = base_dir or ".pyquizhub"
        os.makedirs(base_dir, exist_ok=True)
        print(f"File-based storage configured at {base_dir}.")

    # Configure SQL storage
    elif storage_type == "sql":
        connection_string = input(
            "Enter SQLAlchemy connection string (default: sqlite:///pyquizhub.db): ").strip()
        connection_string = connection_string or "sqlite:///pyquizhub.db"
        print(
            f"SQL storage configured with connection string: {connection_string}.")

    # Save configuration
    config = {
        "storage": {
            "type": storage_type,
            "file": {"base_dir": base_dir if storage_type == "file" else None},
            "sql": {"connection_string": connection_string if storage_type == "sql" else None}
        }
    }
    with open(config_path, "w") as f:
        yaml.safe_dump(config, f)

    print("Configuration saved. Run 'python pyquizhub/initialize.py' to complete setup.")


if __name__ == "__main__":
    setup()

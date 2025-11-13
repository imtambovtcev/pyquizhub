#!/usr/bin/env python3
"""
Migration script to add api_data column to sessions table.
This is needed for API integration features in quizzes.
"""

from sqlalchemy import create_engine, MetaData, Table, Column, JSON, inspect, text
import sys

def migrate_database(connection_string: str):
    """Add api_data column to sessions table if it doesn't exist."""
    print(f"Connecting to database: {connection_string}")
    engine = create_engine(connection_string)

    # Check if api_data column exists
    inspector = inspect(engine)
    columns = [c["name"] for c in inspector.get_columns("sessions")]

    print(f"Current sessions table columns: {columns}")

    if "api_data" in columns:
        print("✓ api_data column already exists. No migration needed.")
        return

    print("Adding api_data column to sessions table...")

    # Add the column
    with engine.connect() as conn:
        conn.execute(text("ALTER TABLE sessions ADD COLUMN api_data JSON"))
        conn.commit()

    print("✓ Successfully added api_data column to sessions table")

    # Verify the column was added
    inspector = inspect(engine)
    columns_after = [c["name"] for c in inspector.get_columns("sessions")]
    print(f"Sessions table columns after migration: {columns_after}")

if __name__ == "__main__":
    # Default connection string for the Docker setup (PostgreSQL)
    import os
    db_host = os.getenv("POSTGRES_HOST", "db")
    db_name = os.getenv("POSTGRES_DB", "pyquizhub")
    db_user = os.getenv("POSTGRES_USER", "pyquizhub")
    db_password = os.getenv("POSTGRES_PASSWORD", "pyquizhub")
    connection_string = f"postgresql://{db_user}:{db_password}@{db_host}:5432/{db_name}"

    if len(sys.argv) > 1:
        connection_string = sys.argv[1]

    try:
        migrate_database(connection_string)
        print("\n✓ Migration completed successfully!")
    except Exception as e:
        print(f"\n✗ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

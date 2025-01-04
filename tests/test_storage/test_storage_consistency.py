import pytest
from pyquizhub.storage.file_storage import FileStorageManager
from pyquizhub.storage.sql_storage import SQLStorageManager
import os


@pytest.fixture
def file_storage(tmpdir):
    """Provide a FileStorageManager instance using pytest's temporary directory."""
    return FileStorageManager(tmpdir)


@pytest.fixture
def sql_storage(tmpdir):
    """Provide a SQLStorageManager instance using an in-memory SQLite database."""
    connection_string = f"sqlite:///{tmpdir}/test.db"
    return SQLStorageManager(connection_string)


def test_storage_consistency_users(file_storage: FileStorageManager, sql_storage: SQLStorageManager):
    """Test consistency of user data between file and SQL storage."""
    users = {
        "user1": {"permissions": ["create"]},
        "user2": {"permissions": ["participate"]}
    }
    file_storage.add_users(users)
    sql_storage.add_users(users)

    file_users = file_storage.get_users()
    sql_users = sql_storage.get_users()

    assert file_users == sql_users


def test_storage_consistency_quiz(file_storage: FileStorageManager, sql_storage: SQLStorageManager):
    """Test consistency of quiz data between file and SQL storage."""
    quiz_data = {
        "title": "Sample Quiz",
        "questions": [{"id": 1, "text": "Q1"}]
    }
    creator_id = "user1"
    file_storage.add_quiz("quiz_001", quiz_data, creator_id)
    sql_storage.add_quiz("quiz_001", quiz_data, creator_id)

    file_quiz = file_storage.get_quiz("quiz_001")
    sql_quiz = sql_storage.get_quiz("quiz_001")

    assert file_quiz == sql_quiz


def test_storage_consistency_results(file_storage: FileStorageManager, sql_storage: SQLStorageManager):
    """Test consistency of user results between file and SQL storage."""
    results = {
        "scores": {"math": 10},
        "answers": {"1": "A"}
    }
    file_storage.add_results("user1", "quiz_001", results)
    sql_storage.add_results("user1", "quiz_001", results)

    file_results = file_storage.get_results("user1", "quiz_001")
    sql_results = sql_storage.get_results("user1", "quiz_001")

    assert file_results == sql_results


def test_storage_consistency_tokens(file_storage: FileStorageManager, sql_storage: SQLStorageManager):
    """Test consistency of tokens between file and SQL storage."""
    tokens = [{"token": "abc123", "quiz_id": "quiz_001", "type": "single-use"}]
    file_storage.add_tokens(tokens)
    sql_storage.add_tokens(tokens)

    file_tokens = file_storage.get_tokens()
    sql_tokens = sql_storage.get_tokens()

    assert file_tokens == sql_tokens

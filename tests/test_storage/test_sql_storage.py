import pytest
from sqlalchemy import create_engine
from pyquizhub.storage.sql_storage import SQLStorageManager


@pytest.fixture
def sql_storage(tmpdir):
    """Provide a SQLStorageManager instance using an in-memory SQLite database."""
    connection_string = f"sqlite:///{tmpdir}/test.db"
    return SQLStorageManager(connection_string)


def test_add_and_get_users(sql_storage: SQLStorageManager):
    """Test adding and getting user data."""
    users = {
        "user1": {"permissions": ["create"]},
        "user2": {"permissions": ["participate"]}
    }
    sql_storage.add_users(users)
    loaded_users = sql_storage.get_users()
    assert loaded_users == users


def test_add_and_get_quiz(sql_storage: SQLStorageManager):
    """Test adding and getting quiz data."""
    quiz_data = {
        "title": "Sample Quiz",
        "questions": [{"id": 1, "text": "Q1"}]
    }
    creator_id = "user1"
    sql_storage.add_quiz("quiz_001", quiz_data, creator_id)
    loaded_quiz = sql_storage.get_quiz("quiz_001")
    assert loaded_quiz == quiz_data


def test_add_and_get_results(sql_storage: SQLStorageManager):
    """Test adding and getting user results."""
    results = {
        "scores": {"math": 10},
        "answers": {"1": "A"}
    }
    sql_storage.add_results("user1", "quiz_001", results)
    loaded_results = sql_storage.get_results("user1", "quiz_001")
    expected_results = {
        "user_id": "user1",
        "quiz_id": "quiz_001",
        "scores": {"math": 10},
        "answers": {"1": "A"}
    }
    assert loaded_results == expected_results


def test_add_and_get_tokens(sql_storage: SQLStorageManager):
    """Test adding and getting tokens."""
    tokens = [{"token": "abc123", "quiz_id": "quiz_001", "type": "single-use"}]
    sql_storage.add_tokens(tokens)
    loaded_tokens = sql_storage.get_tokens()
    assert loaded_tokens == tokens


def test_get_participated_users(sql_storage: SQLStorageManager):
    """Test getting participated users."""
    results = {
        "scores": {"math": 10},
        "answers": {"1": "A"}
    }
    sql_storage.add_results("user1", "quiz_001", results)
    sql_storage.add_results("user2", "quiz_001", results)
    user_ids = sql_storage.get_participated_users("quiz_001")
    assert set(user_ids) == {"user1", "user2"}

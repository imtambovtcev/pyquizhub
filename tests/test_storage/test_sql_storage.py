import pytest
from sqlalchemy import create_engine
from pyquizhub.storage.sql_storage import SQLStorageManager


@pytest.fixture
def sql_storage():
    """Provide an SQLStorageManager instance using an in-memory SQLite database."""
    connection_string = "sqlite:///:memory:"
    return SQLStorageManager(connection_string)


def test_load_and_save_users(sql_storage):
    """Test saving and loading user data."""
    users = {"user1": {"permissions": ["create"]}, "user2": {
        "permissions": ["participate"]}}
    sql_storage.save_users(users)
    loaded_users = sql_storage.load_users()
    assert loaded_users == users


def test_load_and_save_quiz(sql_storage):
    """Test saving and loading quiz data."""
    quiz_data = {
        "title": "Sample Quiz",
        "questions": [{"id": 1, "text": "Q1"}]
    }
    sql_storage.save_quiz("quiz_001", quiz_data)
    loaded_quiz = sql_storage.load_quiz("quiz_001")
    assert loaded_quiz == quiz_data


def test_load_and_save_results(sql_storage):
    """Test saving and loading user results."""
    results = {"scores": {"math": 10}, "answers": {"1": "A"}}
    sql_storage.save_results("user1", "quiz_001", results)
    loaded_results = sql_storage.load_results("user1", "quiz_001")
    assert loaded_results is not None
    assert loaded_results["scores"] == results["scores"]
    assert loaded_results["answers"] == results["answers"]


def test_load_and_save_tokens(sql_storage):
    """Test saving and loading tokens."""
    tokens = [{"token": "abc123", "quiz_id": "quiz_001", "type": "single-use"}]
    sql_storage.save_tokens(tokens)
    loaded_tokens = sql_storage.load_tokens()
    assert len(loaded_tokens) == 1
    assert loaded_tokens[0]["token"] == "abc123"
    assert loaded_tokens[0]["quiz_id"] == "quiz_001"
    assert loaded_tokens[0]["type"] == "single-use"

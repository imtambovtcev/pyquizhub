import pytest
from pyquizhub.storage.file_storage import FileStorageManager


@pytest.fixture
def file_storage(tmpdir):
    """Provide a FileStorageManager instance using pytest's temporary directory."""
    return FileStorageManager(tmpdir)


def test_load_and_save_users(file_storage):
    """Test saving and loading user data."""
    users = {
        "user1": {"permissions": ["create"]},
        "user2": {"permissions": ["participate"]}
    }
    file_storage.save_users(users)
    loaded_users = file_storage.load_users()
    assert loaded_users == users


def test_load_and_save_quiz(file_storage):
    """Test saving and loading quiz data."""
    quiz_data = {
        "title": "Sample Quiz",
        "questions": [{"id": 1, "text": "Q1"}]
    }
    file_storage.save_quiz("quiz_001", quiz_data)
    loaded_quiz = file_storage.load_quiz("quiz_001")
    assert loaded_quiz == quiz_data


def test_load_and_save_results(file_storage):
    """Test saving and loading user results."""
    results = {
        "scores": {"math": 10},
        "answers": {"1": "A"}
    }
    file_storage.save_results("user1", "quiz_001", results)
    loaded_results = file_storage.load_results("user1", "quiz_001")
    assert loaded_results == results


def test_load_and_save_tokens(file_storage):
    """Test saving and loading tokens."""
    tokens = [{"token": "abc123", "quiz_id": "quiz_001", "type": "single-use"}]
    file_storage.save_tokens(tokens)
    loaded_tokens = file_storage.load_tokens()
    assert loaded_tokens == tokens

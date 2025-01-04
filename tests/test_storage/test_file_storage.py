import pytest
from pyquizhub.storage.file_storage import FileStorageManager


@pytest.fixture
def file_storage(tmpdir):
    """Provide a FileStorageManager instance using pytest's temporary directory."""
    return FileStorageManager(tmpdir)


def test_add_and_get_users(file_storage: FileStorageManager):
    """Test adding and getting user data."""
    users = {
        "user1": {"permissions": ["create"]},
        "user2": {"permissions": ["participate"]}
    }
    file_storage.add_users(users)
    loaded_users = file_storage.get_users()
    assert loaded_users == users


def test_add_and_get_quiz(file_storage: FileStorageManager):
    """Test adding and getting quiz data."""
    quiz_data = {
        "title": "Sample Quiz",
        "questions": [{"id": 1, "text": "Q1"}]
    }
    creator_id = "user1"
    file_storage.add_quiz("quiz_001", quiz_data, creator_id)
    loaded_quiz = file_storage.get_quiz("quiz_001")
    assert loaded_quiz == quiz_data


def test_add_and_get_results(file_storage: FileStorageManager):
    """Test adding and getting user results."""
    results = {
        "scores": {"math": 10},
        "answers": {"1": "A"}
    }
    file_storage.add_results("user1", "quiz_001", results)
    loaded_results = file_storage.get_results("user1", "quiz_001")
    expected_results = {
        "user_id": "user1",
        "quiz_id": "quiz_001",
        "scores": {"math": 10},
        "answers": {"1": "A"}
    }
    assert loaded_results == expected_results


def test_add_and_get_tokens(file_storage: FileStorageManager):
    """Test adding and getting tokens."""
    tokens = [{"token": "abc123", "quiz_id": "quiz_001", "type": "single-use"}]
    file_storage.add_tokens(tokens)
    loaded_tokens = file_storage.get_tokens()
    assert loaded_tokens == tokens

import pytest
from pyquizhub.storage.file_storage import FileStorageManager
import uuid


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
        "questions": [
            {
                "id": 1,
                "data": {
                    "text": "Q1",
                    "type": "multiple_choice",
                    "options": [{"value": "A", "label": "Option A"}]
                }
            }
        ]
    }
    creator_id = "user1"
    file_storage.add_quiz("quiz-001", quiz_data, creator_id)
    loaded_quiz = file_storage.get_quiz("quiz-001")
    assert loaded_quiz == quiz_data


def test_add_and_get_results(file_storage: FileStorageManager):
    """Test adding and getting user results."""
    results = {
        "scores": {"math": 10},
        "answers": {"1": "A"}
    }
    session_id = str(uuid.uuid4())
    file_storage.add_results("user1", "quiz-001", session_id, results)
    loaded_results = file_storage.get_results("user1", "quiz-001", session_id)
    expected_results = {
        "user_id": "user1",
        "quiz_id": "quiz-001",
        "session_id": session_id,
        "scores": {"math": 10},
        "answers": {"1": "A"}
    }
    assert loaded_results == expected_results


def test_add_and_get_tokens(file_storage: FileStorageManager):
    """Test adding and getting tokens."""
    tokens = [{"token": "abc123", "quiz_id": "quiz-001", "type": "single-use"}]
    file_storage.add_tokens(tokens)
    loaded_tokens = file_storage.get_tokens()
    assert loaded_tokens == tokens


def test_get_participated_users(file_storage: FileStorageManager):
    """Test getting participated users."""
    results = {
        "scores": {"math": 10},
        "answers": {"1": "A"}
    }
    session_id = "session-001"
    file_storage.add_results("user1", "quiz-001", session_id, results)
    file_storage.add_results("user2", "quiz-001", session_id, results)
    user_ids = file_storage.get_participated_users("quiz-001")
    assert set(user_ids) == {"user1", "user2"}

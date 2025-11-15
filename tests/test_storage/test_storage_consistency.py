import pytest
from pyquizhub.core.storage.file_storage import FileStorageManager
from pyquizhub.core.storage.sql_storage import SQLStorageManager
import os
from datetime import datetime


@pytest.fixture
def file_storage(tmpdir):
    """Provide a FileStorageManager instance using pytest's temporary directory."""
    return FileStorageManager(tmpdir)


@pytest.fixture
def sql_storage(tmpdir):
    """Provide a SQLStorageManager instance using an in-memory SQLite database."""
    connection_string = f"sqlite:///{tmpdir}/test.db"
    return SQLStorageManager(connection_string)


def test_storage_consistency_users(
        file_storage: FileStorageManager,
        sql_storage: SQLStorageManager):
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


def test_storage_consistency_quiz(
        file_storage: FileStorageManager,
        sql_storage: SQLStorageManager):
    """Test consistency of quiz data between file and SQL storage."""
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
    sql_storage.add_quiz("quiz-001", quiz_data, creator_id)

    file_quiz = file_storage.get_quiz("quiz-001")
    sql_quiz = sql_storage.get_quiz("quiz-001")

    assert file_quiz == sql_quiz


def test_storage_consistency_results(
        file_storage: FileStorageManager,
        sql_storage: SQLStorageManager):
    """Test consistency of user results between file and SQL storage."""
    results = {
        "scores": {"math": 10},
        "answers": {"1": "A"},
        "timestamp": datetime.now().isoformat()
    }
    session_id = "session-001"
    file_storage.add_results("user1", "quiz-001", session_id, results)
    sql_storage.add_results("user1", "quiz-001", session_id, results)

    file_results = file_storage.get_results("user1", "quiz-001", session_id)
    sql_results = sql_storage.get_results("user1", "quiz-001", session_id)

    assert file_results == sql_results

    file_sessions = file_storage.get_session_ids_by_user_and_quiz(
        "user1", "quiz-001")
    sql_sessions = sql_storage.get_session_ids_by_user_and_quiz(
        "user1", "quiz-001")

    assert set(file_sessions) == set(sql_sessions)


def test_storage_consistency_tokens(
        file_storage: FileStorageManager,
        sql_storage: SQLStorageManager):
    """Test consistency of tokens between file and SQL storage."""
    tokens = [{"token": "abc123", "quiz_id": "quiz-001", "type": "single-use"}]
    file_storage.add_tokens(tokens)
    sql_storage.add_tokens(tokens)

    file_tokens = file_storage.get_tokens()
    sql_tokens = sql_storage.get_tokens()

    assert file_tokens == sql_tokens


def test_storage_consistency_participated_users(
        file_storage: FileStorageManager,
        sql_storage: SQLStorageManager):
    """Test consistency of participated users between file and SQL storage."""
    results = {
        "scores": {"math": 10},
        "answers": {"1": "A"}
    }
    session_id = "session-001"
    file_storage.add_results("user1", "quiz-001", session_id, results)
    file_storage.add_results("user2", "quiz-001", session_id, results)
    sql_storage.add_results("user1", "quiz-001", session_id, results)
    sql_storage.add_results("user2", "quiz-001", session_id, results)

    file_users = file_storage.get_participated_users("quiz-001")
    sql_users = sql_storage.get_participated_users("quiz-001")

    assert set(file_users) == set(sql_users)


def test_storage_consistency_get_users_with_stats(
        file_storage: FileStorageManager,
        sql_storage: SQLStorageManager):
    """Test consistency of get_users with statistics between file and SQL storage."""
    # Add some users with permissions
    users = {
        "user1": {"permissions": ["create"]},
        "user2": {"permissions": []}
    }
    file_storage.add_users(users)
    sql_storage.add_users(users)

    # Add results to generate statistics
    results = {
        "scores": {"math": 10},
        "answers": {"1": "A"},
        "timestamp": datetime.now().isoformat()
    }
    file_storage.add_results("user1", "quiz-001", "session-001", results)
    file_storage.add_results("user1", "quiz-002", "session-002", results)
    file_storage.add_results("user2", "quiz-001", "session-003", results)

    sql_storage.add_results("user1", "quiz-001", "session-001", results)
    sql_storage.add_results("user1", "quiz-002", "session-002", results)
    sql_storage.add_results("user2", "quiz-001", "session-003", results)

    # Get users with stats
    file_users = file_storage.get_users()
    sql_users = sql_storage.get_users()

    # Both should return users with permissions and quizzes_taken
    assert "user1" in file_users
    assert "user2" in file_users
    assert "user1" in sql_users
    assert "user2" in sql_users

    # Check structure
    for user_id in ["user1", "user2"]:
        assert "permissions" in file_users[user_id]
        assert "quizzes_taken" in file_users[user_id]
        assert "permissions" in sql_users[user_id]
        assert "quizzes_taken" in sql_users[user_id]

        # Check permissions match
        assert set(file_users[user_id]["permissions"]) == set(
            sql_users[user_id]["permissions"])

        # Check quizzes_taken match
        assert file_users[user_id]["quizzes_taken"] == sql_users[user_id]["quizzes_taken"]

    # Verify specific counts
    assert file_users["user1"]["quizzes_taken"] == 2
    assert sql_users["user1"]["quizzes_taken"] == 2
    assert file_users["user2"]["quizzes_taken"] == 1
    assert sql_users["user2"]["quizzes_taken"] == 1


def test_storage_consistency_get_all_sessions(
        file_storage: FileStorageManager,
        sql_storage: SQLStorageManager):
    """Test consistency of get_all_sessions between file and SQL storage."""
    # Create session data
    session_data_1 = {
        "session_id": "session-001",
        "user_id": "user1",
        "quiz_id": "quiz-001",
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
        "current_question_id": 0,
        "completed": False,
        "engine_state": {}
    }

    session_data_2 = {
        "session_id": "session-002",
        "user_id": "user1",
        "quiz_id": "quiz-002",
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
        "current_question_id": 5,
        "completed": False,
        "engine_state": {}
    }

    session_data_3 = {
        "session_id": "session-003",
        "user_id": "user2",
        "quiz_id": "quiz-001",
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
        "current_question_id": 2,
        "completed": True,
        "engine_state": {}
    }

    # Save sessions to both storages
    file_storage.save_session_state(session_data_1)
    file_storage.save_session_state(session_data_2)
    file_storage.save_session_state(session_data_3)

    sql_storage.save_session_state(session_data_1)
    sql_storage.save_session_state(session_data_2)
    sql_storage.save_session_state(session_data_3)

    # Get all sessions from both storages
    file_sessions = file_storage.get_all_sessions()
    sql_sessions = sql_storage.get_all_sessions()

    # Both should return dict with user_id -> list of session_ids
    assert isinstance(file_sessions, dict)
    assert isinstance(sql_sessions, dict)

    # Check that both have the same users
    assert set(file_sessions.keys()) == set(sql_sessions.keys())

    # Check that session IDs match for each user
    for user_id in file_sessions.keys():
        assert set(file_sessions[user_id]) == set(sql_sessions[user_id])

    # Verify specific data
    assert "user1" in file_sessions
    assert "user2" in file_sessions
    assert len(file_sessions["user1"]) == 2
    assert len(file_sessions["user2"]) == 1
    assert "session-001" in file_sessions["user1"]
    assert "session-002" in file_sessions["user1"]
    assert "session-003" in file_sessions["user2"]


def test_storage_consistency_load_session_state(
        file_storage: FileStorageManager,
        sql_storage: SQLStorageManager):
    """Test consistency of load_session_state between file and SQL storage."""
    session_data = {
        "session_id": "session-999",
        "user_id": "user_test",
        "quiz_id": "quiz-999",
        "created_at": "2025-11-14T12:00:00",
        "updated_at": "2025-11-14T12:30:00",
        "current_question_id": 3,
        "completed": False,
        "engine_state": {"some": "data"}
    }

    # Save to both storages
    file_storage.save_session_state(session_data)
    sql_storage.save_session_state(session_data)

    # Load from both storages
    file_loaded = file_storage.load_session_state("session-999")
    sql_loaded = sql_storage.load_session_state("session-999")

    # Both should return the same data
    assert file_loaded is not None
    assert sql_loaded is not None

    # Compare key fields (engine_state might be serialized differently)
    for key in ["session_id", "user_id", "quiz_id", "created_at",
                "updated_at", "current_question_id", "completed"]:
        assert file_loaded[key] == sql_loaded[key]

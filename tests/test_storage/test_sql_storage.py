import pytest
from sqlalchemy import create_engine
from pyquizhub.core.storage.sql_storage import SQLStorageManager


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
    sql_storage.add_quiz("quiz-001", quiz_data, creator_id)
    loaded_quiz = sql_storage.get_quiz("quiz-001")
    assert loaded_quiz == quiz_data


def test_add_and_get_results(sql_storage: SQLStorageManager):
    """Test adding and getting user results."""
    results = {
        "scores": {"math": 10},
        "answers": {"1": "A"}
    }
    quiz_id = "quiz-001"
    session_id = "session-001"
    user_id = "user1"
    sql_storage.add_results(user_id, quiz_id, session_id, results)
    loaded_results = sql_storage.get_results(user_id, quiz_id, session_id)
    expected_results = {
        "user_id": user_id,
        "quiz_id": quiz_id,
        "session_id": session_id,
        "scores": {"math": 10},
        "answers": {"1": "A"},
        "timestamp": loaded_results["timestamp"]
    }
    assert loaded_results == expected_results

    # Test get_results_by_quiz
    results_by_quiz = sql_storage.get_results_by_quiz(quiz_id)
    assert user_id in results_by_quiz
    assert session_id in results_by_quiz[user_id]
    assert results_by_quiz[user_id][session_id] == expected_results

    # Test get_results_by_user
    results_by_user = sql_storage.get_results_by_user(user_id)
    assert quiz_id in results_by_user
    assert session_id in results_by_user[quiz_id]
    assert results_by_user[quiz_id][session_id] == expected_results

    # Test get_results_by_quiz_and_user
    results_by_quiz_and_user = sql_storage.get_results_by_quiz_and_user(
        quiz_id, user_id)
    assert session_id in results_by_quiz_and_user
    assert results_by_quiz_and_user[session_id] == expected_results

    # Test get_all_results
    all_results = sql_storage.get_all_results()
    assert user_id in all_results
    assert quiz_id in all_results[user_id]
    assert session_id in all_results[user_id][quiz_id]
    assert all_results[user_id][quiz_id][session_id] == expected_results

    # Test get_session_ids_by_user_and_quiz
    session_ids = sql_storage.get_session_ids_by_user_and_quiz(
        user_id, quiz_id)
    assert session_id in session_ids

    # Test get_all_sessions
    all_sessions = sql_storage.get_all_sessions()
    assert user_id in all_sessions
    assert session_id in all_sessions[user_id]

    # Test get_sessions_by_user
    sessions_by_user = sql_storage.get_sessions_by_user(user_id)
    assert session_id in sessions_by_user

    # Test get_sessions_by_quiz
    sessions_by_quiz = sql_storage.get_sessions_by_quiz(quiz_id)
    assert session_id in sessions_by_quiz

    # Test get_sessions_by_quiz_and_user
    sessions_by_quiz_and_user = sql_storage.get_sessions_by_quiz_and_user(
        quiz_id, user_id)
    assert session_id in sessions_by_quiz_and_user


def test_add_and_get_tokens(sql_storage: SQLStorageManager):
    """Test adding and getting tokens."""
    tokens = [{"token": "abc123", "quiz_id": "quiz-001", "type": "single-use"}]
    sql_storage.add_tokens(tokens)
    loaded_tokens = sql_storage.get_tokens()
    assert loaded_tokens == tokens


def test_get_participated_users(sql_storage: SQLStorageManager):
    """Test getting participated users."""
    results = {
        "scores": {"math": 10},
        "answers": {"1": "A"}
    }
    session_id = "session-001"
    sql_storage.add_results("user1", "quiz-001", session_id, results)
    sql_storage.add_results("user2", "quiz-001", session_id, results)
    user_ids = sql_storage.get_participated_users("quiz-001")
    assert set(user_ids) == {"user1", "user2"}

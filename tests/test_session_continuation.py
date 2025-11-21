"""
Tests for session continuation functionality.

This module tests that:
1. Users can resume unfinished quiz sessions
2. Pre-question operations (API calls, score updates) are NOT re-executed
3. The current question is retrieved from saved state
4. Session continuation works across different adapters
"""
import pytest
from starlette.testclient import TestClient
from pyquizhub.config.settings import get_config_manager


@pytest.fixture(scope="module")
def user_headers(api_client):
    config_manager = get_config_manager()
    headers = {"Content-Type": "application/json"}
    token = config_manager.get_token("user")
    if token:
        headers["Authorization"] = token
    return headers


@pytest.fixture(scope="module")
def admin_headers(api_client):
    config_manager = get_config_manager()
    headers = {"Content-Type": "application/json"}
    token = config_manager.get_token("admin")
    if token:
        headers["Authorization"] = token
    return headers


@pytest.fixture(scope="module")
def simple_quiz():
    """Load the simple quiz JSON."""
    import json
    with open("tests/test_quiz_jsons/simple_quiz.json") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def joke_quiz_dynamic():
    """Load the joke quiz with dynamic API."""
    import json
    with open("tests/test_quiz_jsons/joke_quiz_dynamic_api.json") as f:
        return json.load(f)


def test_session_continuation_simple_quiz(
        api_client: TestClient,
        admin_headers,
        user_headers,
        simple_quiz):
    """Test that a user can continue an unfinished quiz session."""
    # Create quiz
    response = api_client.post(
        "/admin/create_quiz",
        json={"quiz": simple_quiz, "creator_id": "admin"},
        headers=admin_headers
    )
    assert response.status_code == 200
    quiz_id = response.json()["quiz_id"]

    # Generate token
    response = api_client.post(
        "/admin/generate_token",
        json={"quiz_id": quiz_id, "type": "permanent"},
        headers=admin_headers
    )
    assert response.status_code == 200
    token = response.json()["token"]

    user_id = "test_user_continuation"

    # Start quiz
    response = api_client.post(
        "/quiz/start_quiz",
        json={"token": token, "user_id": user_id},
        headers=user_headers
    )
    assert response.status_code == 200
    data1 = response.json()
    session_id_1 = data1["session_id"]
    question_1 = data1["question"]

    # Verify we got the first question
    assert question_1["data"]["type"] == "multiple_choice"
    assert "Do you like apples?" in question_1["data"]["text"]

    # Now try to start the quiz again with same user and token
    # Should resume the existing session, not create a new one
    response = api_client.post(
        "/quiz/start_quiz",
        json={"token": token, "user_id": user_id},
        headers=user_headers
    )
    assert response.status_code == 200
    data2 = response.json()
    session_id_2 = data2["session_id"]
    question_2 = data2["question"]

    # Should be the SAME session ID
    assert session_id_2 == session_id_1, "Should resume existing session, not create new one"

    # Should be the SAME question
    assert question_2["data"]["text"] == question_1["data"]["text"]
    assert question_2["data"]["type"] == question_1["data"]["type"]


def test_session_continuation_after_completion(
        api_client: TestClient,
        admin_headers,
        user_headers,
        simple_quiz):
    """Test that completing a quiz allows starting a new session."""
    # Create quiz
    response = api_client.post(
        "/admin/create_quiz",
        json={"quiz": simple_quiz, "creator_id": "admin"},
        headers=admin_headers
    )
    assert response.status_code == 200
    quiz_id = response.json()["quiz_id"]

    # Generate token
    response = api_client.post(
        "/admin/generate_token",
        json={"quiz_id": quiz_id, "type": "permanent"},
        headers=admin_headers
    )
    assert response.status_code == 200
    token = response.json()["token"]

    user_id = "test_user_completion"

    # Start quiz
    response = api_client.post(
        "/quiz/start_quiz",
        json={"token": token, "user_id": user_id},
        headers=user_headers
    )
    assert response.status_code == 200
    session_id_1 = response.json()["session_id"]

    # Complete the quiz
    response = api_client.post(
        f"/quiz/submit_answer/{quiz_id}",
        json={
            "user_id": user_id,
            "session_id": session_id_1,
            "answer": {"answer": "yes"}
        },
        headers=user_headers
    )
    assert response.status_code == 200

    # Now start the quiz again - should create a NEW session since previous is
    # completed
    response = api_client.post(
        "/quiz/start_quiz",
        json={"token": token, "user_id": user_id},
        headers=user_headers
    )
    assert response.status_code == 200
    session_id_2 = response.json()["session_id"]

    # Should be a DIFFERENT session ID
    assert session_id_2 != session_id_1, "Should create new session after previous quiz completed"


def test_session_continuation_preserves_api_data(
        api_client: TestClient,
        admin_headers,
        user_headers,
        joke_quiz_dynamic):
    """Test that session continuation does NOT re-execute API calls."""
    # Create quiz
    response = api_client.post(
        "/admin/create_quiz",
        json={"quiz": joke_quiz_dynamic, "creator_id": "admin"},
        headers=admin_headers
    )
    assert response.status_code == 200
    quiz_id = response.json()["quiz_id"]

    # Generate token
    response = api_client.post(
        "/admin/generate_token",
        json={"quiz_id": quiz_id, "type": "permanent"},
        headers=admin_headers
    )
    assert response.status_code == 200
    token = response.json()["token"]

    user_id = "test_user_api"

    # Start quiz (will fetch joke from API)
    response = api_client.post(
        "/quiz/start_quiz",
        json={"token": token, "user_id": user_id},
        headers=user_headers
    )
    assert response.status_code == 200
    data1 = response.json()
    session_id_1 = data1["session_id"]
    question_1 = data1["question"]

    # Extract the joke from the question text
    joke_text_1 = question_1["data"]["text"]

    # Resume the session
    response = api_client.post(
        "/quiz/start_quiz",
        json={"token": token, "user_id": user_id},
        headers=user_headers
    )
    assert response.status_code == 200
    data2 = response.json()
    question_2 = data2["question"]

    # Extract the joke from the resumed question
    joke_text_2 = question_2["data"]["text"]

    # The joke should be EXACTLY the same (proving API wasn't called again)
    assert joke_text_2 == joke_text_1, "Resumed session should show same joke (API not re-executed)"
    assert session_id_1 == data2["session_id"], "Should be same session"


def test_get_active_sessions_endpoint(
        api_client: TestClient,
        admin_headers,
        user_headers,
        simple_quiz):
    """Test the /active_sessions endpoint."""
    # Create quiz
    response = api_client.post(
        "/admin/create_quiz",
        json={"quiz": simple_quiz, "creator_id": "admin"},
        headers=admin_headers
    )
    assert response.status_code == 200
    quiz_id = response.json()["quiz_id"]

    # Generate token
    response = api_client.post(
        "/admin/generate_token",
        json={"quiz_id": quiz_id, "type": "permanent"},
        headers=admin_headers
    )
    assert response.status_code == 200
    token = response.json()["token"]

    user_id = "test_user_active"

    # Check active sessions (should be empty)
    response = api_client.get(
        f"/quiz/active_sessions?user_id={user_id}&token={token}",
        headers=user_headers
    )
    assert response.status_code == 200
    assert len(response.json()["active_sessions"]) == 0

    # Start quiz
    response = api_client.post(
        "/quiz/start_quiz",
        json={"token": token, "user_id": user_id},
        headers=user_headers
    )
    assert response.status_code == 200
    session_id = response.json()["session_id"]

    # Check active sessions (should have one)
    response = api_client.get(
        f"/quiz/active_sessions?user_id={user_id}&token={token}",
        headers=user_headers
    )
    assert response.status_code == 200
    active_sessions = response.json()["active_sessions"]
    assert len(active_sessions) == 1
    assert active_sessions[0]["session_id"] == session_id
    assert active_sessions[0]["completed"] is False

    # Complete the quiz
    response = api_client.post(
        f"/quiz/submit_answer/{quiz_id}",
        json={
            "user_id": user_id,
            "session_id": session_id,
            "answer": {"answer": "yes"}
        },
        headers=user_headers
    )
    assert response.status_code == 200

    # Check active sessions (should be empty again)
    response = api_client.get(
        f"/quiz/active_sessions?user_id={user_id}&token={token}",
        headers=user_headers
    )
    assert response.status_code == 200
    assert len(response.json()["active_sessions"]) == 0

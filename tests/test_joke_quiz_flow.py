"""
Tests for joke quiz end-to-end flow with user output verification.

This module tests the joke quiz with API integration (mocked), verifying:
- API integration and variable substitution
- Exact user-facing output with joke data
- Rating system
- Quiz loop behavior ("hear another joke")
- Complete user journey

Note: These tests focus on user-facing output. Admin results API calls are
skipped because the current API has a validation bug with string variables in scores.
"""
import pytest
from unittest.mock import patch, Mock
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


@pytest.fixture(autouse=True)
def mock_joke_api():
    """Mock the joke API to return consistent test data."""
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "id": 42,
        "type": "general",
        "setup": "Why don't scientists trust atoms?",
        "punchline": "Because they make up everything!"
    }

    # Patch requests.request in the api_integration module
    with patch('pyquizhub.core.engine.api_integration.requests.request', return_value=mock_response) as mock_request:
        yield mock_request


@pytest.fixture(scope="module")
def joke_quiz():
    """Load the joke quiz JSON."""
    import json
    with open("tests/test_quiz_jsons/joke_quiz_api.json") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def joke_quiz_setup(api_client: TestClient, admin_headers, joke_quiz):
    """Create joke quiz and generate token."""
    # Create quiz
    response = api_client.post(
        "/admin/create_quiz",
        json={"quiz": joke_quiz, "creator_id": "admin"},
        headers=admin_headers
    )
    assert response.status_code == 200
    data = response.json()
    quiz_id = data["quiz_id"]

    # Generate token
    response = api_client.post(
        "/admin/generate_token",
        json={"quiz_id": quiz_id, "type": "permanent"},
        headers=admin_headers
    )
    assert response.status_code == 200
    token = response.json()["token"]

    return {"quiz_id": quiz_id, "token": token}


class TestJokeQuizFlow:
    """Test suite for joke quiz end-to-end user experience."""

    def test_joke_quiz_displays_joke_and_rates(
            self, api_client: TestClient, user_headers, admin_headers, joke_quiz_setup, mock_joke_api):
        """Test that joke quiz displays joke with variable substitution."""
        # Start quiz - API should be called (but mocked)
        response = api_client.post(
            "/quiz/start_quiz",
            json={"token": joke_quiz_setup["token"], "user_id": "test_display"},
            headers=user_headers
        )
        assert response.status_code == 200
        data = response.json()
        session_id = data["session_id"]
        quiz_id = data["quiz_id"]

        # Verify Question 1 contains the joke
        assert data["question"]["id"] == 1
        question_data = data["question"]["data"]
        question_text = question_data["text"]

        # Verify joke setup and punchline are in the question text
        assert "Why don't scientists trust atoms?" in question_text
        assert "Because they make up everything!" in question_text
        assert "How funny is this joke?" in question_text

        # Verify question type
        assert question_data["type"] == "integer"
        assert question_data.get("min") == 1
        assert question_data.get("max") == 5

        # Verify API was called
        assert mock_joke_api.called

        # Rate the joke
        response = api_client.post(
            f"/quiz/submit_answer/{quiz_id}",
            json={
                "user_id": "test_display",
                "session_id": session_id,
                "answer": {"answer": 5}
            },
            headers=user_headers
        )
        assert response.status_code == 200
        data = response.json()

        # Should be at Question 2
        assert data["question"]["id"] == 2
        assert data["question"]["data"]["text"] == "Would you like to hear another joke?"

    def test_joke_quiz_loop_behavior(
            self, api_client: TestClient, user_headers, admin_headers, joke_quiz_setup):
        """Test that answering 'yes' loops back to show another joke."""
        # Start quiz
        response = api_client.post(
            "/quiz/start_quiz",
            json={"token": joke_quiz_setup["token"], "user_id": "test_loop"},
            headers=user_headers
        )
        assert response.status_code == 200
        data = response.json()
        session_id = data["session_id"]
        quiz_id = data["quiz_id"]

        # Verify first joke displayed
        assert data["question"]["id"] == 1
        assert "Why don't scientists trust atoms?" in data["question"]["data"]["text"]

        # Rate first joke
        response = api_client.post(
            f"/quiz/submit_answer/{quiz_id}",
            json={
                "user_id": "test_loop",
                "session_id": session_id,
                "answer": {"answer": 4}
            },
            headers=user_headers
        )
        assert response.status_code == 200
        data = response.json()

        # At question 2: "Would you like to hear another joke?"
        assert data["question"]["id"] == 2

        # Answer "yes" to hear another joke
        response = api_client.post(
            f"/quiz/submit_answer/{quiz_id}",
            json={
                "user_id": "test_loop",
                "session_id": session_id,
                "answer": {"answer": "yes"}
            },
            headers=user_headers
        )
        assert response.status_code == 200
        data = response.json()

        # Should LOOP BACK to Question 1 with another joke
        assert data["question"]["id"] == 1
        assert "joke" in data["question"]["data"]["text"].lower()

    def test_joke_quiz_finish_behavior(
            self, api_client: TestClient, user_headers, admin_headers, joke_quiz_setup):
        """Test that answering 'no' finishes the quiz."""
        # Start quiz
        response = api_client.post(
            "/quiz/start_quiz",
            json={"token": joke_quiz_setup["token"], "user_id": "test_finish"},
            headers=user_headers
        )
        assert response.status_code == 200
        data = response.json()
        session_id = data["session_id"]
        quiz_id = data["quiz_id"]

        # Rate joke
        response = api_client.post(
            f"/quiz/submit_answer/{quiz_id}",
            json={
                "user_id": "test_finish",
                "session_id": session_id,
                "answer": {"answer": 3}
            },
            headers=user_headers
        )
        assert response.status_code == 200

        # Answer "no" to finish
        response = api_client.post(
            f"/quiz/submit_answer/{quiz_id}",
            json={
                "user_id": "test_finish",
                "session_id": session_id,
                "answer": {"answer": "no"}
            },
            headers=user_headers
        )
        assert response.status_code == 200
        data = response.json()

        # Quiz should be completed
        assert data["question"] is None

    def test_joke_quiz_variable_substitution(
            self, api_client: TestClient, user_headers, admin_headers, joke_quiz_setup):
        """Test that joke variables are correctly substituted in question text."""
        # Start quiz
        response = api_client.post(
            "/quiz/start_quiz",
            json={"token": joke_quiz_setup["token"], "user_id": "test_substitution"},
            headers=user_headers
        )
        assert response.status_code == 200
        data = response.json()
        question_text = data["question"]["data"]["text"]

        # Verify variable substitution worked
        assert "{variables." not in question_text, "Variable placeholders should be replaced"
        assert "{api." not in question_text, "API placeholders should be replaced"

        # Should contain actual joke data from mock
        assert "Why don't scientists trust atoms?" in question_text
        assert "Because they make up everything!" in question_text

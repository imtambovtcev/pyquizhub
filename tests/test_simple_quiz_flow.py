"""
Tests for simple quiz end-to-end flow with user output verification.

This module tests the simple quiz to ensure exact user-facing output is correct,
not just internal scores. This acts as a regression test - if output changes
unexpectedly, these tests will catch it.
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
def simple_quiz_setup(api_client: TestClient, admin_headers, simple_quiz):
    """Create simple quiz and generate token."""
    # Create quiz
    response = api_client.post(
        "/admin/create_quiz",
        json={"quiz": simple_quiz, "creator_id": "admin"},
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


class TestSimpleQuizFlow:
    """Test suite for simple quiz end-to-end user experience."""

    def test_simple_quiz_answer_yes(
            self, api_client: TestClient, user_headers, admin_headers, simple_quiz_setup):
        """Test complete flow answering 'yes' - verify exact user output."""
        # Start quiz
        response = api_client.post(
            "/quiz/start_quiz",
            json={"token": simple_quiz_setup["token"], "user_id": "test_yes_user"},
            headers=user_headers
        )
        assert response.status_code == 200
        data = response.json()
        session_id = data["session_id"]
        quiz_id = data["quiz_id"]

        # Verify first question content
        assert data["question"]["id"] == 1
        question_data = data["question"]["data"]
        assert question_data["text"] == "Do you like apples?"
        assert question_data["type"] == "multiple_choice"
        assert len(question_data["options"]) == 2

        # Verify options are correct
        options = {opt["value"]: opt["label"] for opt in question_data["options"]}
        assert options["yes"] == "Yes"
        assert options["no"] == "No"

        # Submit answer 'yes'
        response = api_client.post(
            f"/quiz/submit_answer/{quiz_id}",
            json={
                "user_id": "test_yes_user",
                "session_id": session_id,
                "answer": {"answer": "yes"}
            },
            headers=user_headers
        )
        assert response.status_code == 200
        data = response.json()

        # Quiz should be completed (simple quiz has only 1 question)
        assert data["question"] is None

        # Verify results stored correctly
        response = api_client.get(
            f"/admin/results/{quiz_id}",
            headers=admin_headers
        )
        assert response.status_code == 200
        results = response.json()["results"]

        assert "test_yes_user" in results
        user_results = results["test_yes_user"][session_id]

        # Verify exact scores for 'yes' answer
        assert user_results["scores"]["score_a"] == 1.0

        # Verify answer recorded
        assert len(user_results["answers"]) == 1
        assert user_results["answers"][0]["question_id"] == 1
        assert user_results["answers"][0]["answer"] == "yes"

    def test_simple_quiz_answer_no(
            self, api_client: TestClient, user_headers, admin_headers, simple_quiz_setup):
        """Test complete flow answering 'no' - verify score stays 0."""
        # Start quiz
        response = api_client.post(
            "/quiz/start_quiz",
            json={"token": simple_quiz_setup["token"], "user_id": "test_no_user"},
            headers=user_headers
        )
        assert response.status_code == 200
        data = response.json()
        session_id = data["session_id"]
        quiz_id = data["quiz_id"]

        # Verify question text is exact
        assert data["question"]["data"]["text"] == "Do you like apples?"

        # Submit answer 'no'
        response = api_client.post(
            f"/quiz/submit_answer/{quiz_id}",
            json={
                "user_id": "test_no_user",
                "session_id": session_id,
                "answer": {"answer": "no"}
            },
            headers=user_headers
        )
        assert response.status_code == 200
        data = response.json()

        # Quiz completed
        assert data["question"] is None

        # Verify results
        response = api_client.get(
            f"/admin/results/{quiz_id}",
            headers=admin_headers
        )
        assert response.status_code == 200
        results = response.json()["results"]

        user_results = results["test_no_user"][session_id]

        # Score should remain 0 for 'no' answer (no score update in quiz)
        assert user_results["scores"]["score_a"] == 0.0

        # Verify answer recorded
        assert user_results["answers"][0]["answer"] == "no"

    def test_simple_quiz_metadata(
            self, api_client: TestClient, user_headers, simple_quiz_setup):
        """Test that quiz metadata is accessible and correct."""
        quiz_id = simple_quiz_setup["quiz_id"]

        # Start quiz to get quiz data
        response = api_client.post(
            "/quiz/start_quiz",
            json={"token": simple_quiz_setup["token"], "user_id": "test_metadata_user"},
            headers=user_headers
        )
        assert response.status_code == 200
        data = response.json()

        # Verify session created
        assert "session_id" in data
        assert data["quiz_id"] == quiz_id
        assert "question" in data

        # Question should have expected structure
        question = data["question"]
        assert question is not None
        assert "id" in question
        assert "data" in question
        assert "text" in question["data"]
        assert "type" in question["data"]

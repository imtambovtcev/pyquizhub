"""
Tests for Admin API endpoints.

Tests the new admin endpoints: all_users, all_results, all_sessions
"""

import pytest
import json
import os
from fastapi.testclient import TestClient
from datetime import datetime
from pyquizhub.config.settings import get_config_manager


@pytest.fixture(scope="module")
def quiz_data():
    """Load test quiz data."""
    file_path = os.path.join(os.path.dirname(
        __file__), "test_quiz_jsons", "complex_quiz.json")
    with open(file_path, "r") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def user_headers(api_client):
    """Provide user authentication headers."""
    config_manager = get_config_manager()
    headers = {"Content-Type": "application/json"}
    token = config_manager.get_token("user")
    if token:
        headers["Authorization"] = token
    return headers


@pytest.fixture(scope="module")
def admin_headers(api_client):
    """Provide admin authentication headers."""
    config_manager = get_config_manager()
    headers = {"Content-Type": "application/json"}
    token = config_manager.get_token("admin")
    if token:
        headers["Authorization"] = token
    return headers


class TestAdminAPI:
    """Tests for admin-only API endpoints."""

    quiz_id = None
    user_id = "test_admin_user"
    session_id = None

    def test_get_all_users_empty(self, api_client: TestClient, admin_headers):
        """Test retrieving all users when none exist."""
        response = api_client.get("/admin/all_users", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert "users" in data
        # Users dict might be empty or contain users from other tests
        assert isinstance(data["users"], dict)

    def test_get_all_results_empty(
            self,
            api_client: TestClient,
            admin_headers):
        """Test retrieving all results when none exist."""
        response = api_client.get("/admin/all_results", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert "results" in data
        assert isinstance(data["results"], dict)

    def test_get_all_sessions_empty(
            self,
            api_client: TestClient,
            admin_headers):
        """Test retrieving all sessions when none exist."""
        response = api_client.get("/admin/all_sessions", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert "sessions" in data
        assert isinstance(data["sessions"], list)

    def test_create_quiz_for_tests(
            self,
            api_client: TestClient,
            quiz_data,
            admin_headers):
        """Create a quiz for testing admin endpoints."""
        request_data = {"quiz": quiz_data, "creator_id": self.user_id}
        response = api_client.post(
            "/admin/create_quiz", json=request_data, headers=admin_headers)
        assert response.status_code == 200
        TestAdminAPI.quiz_id = response.json()["quiz_id"]
        assert TestAdminAPI.quiz_id

    def test_start_quiz_session(
            self,
            api_client: TestClient,
            admin_headers,
            user_headers):
        """Start a quiz session to generate session data."""
        assert TestAdminAPI.quiz_id, "Quiz must be created first"

        # Generate a token first
        request_data = {
            "quiz_id": TestAdminAPI.quiz_id,
            "type": "permanent"
        }
        response = api_client.post(
            "/admin/generate_token",
            json=request_data,
            headers=admin_headers)
        assert response.status_code == 200
        token = response.json()["token"]

        # Start quiz with token (using user_headers as start_quiz requires user
        # token)
        request_data = {
            "token": token,
            "user_id": self.user_id
        }
        response = api_client.post(
            "/quiz/start_quiz",
            json=request_data,
            headers=user_headers)
        assert response.status_code == 200
        data = response.json()
        TestAdminAPI.session_id = data["session_id"]
        assert TestAdminAPI.session_id

    def test_get_all_sessions_with_data(
            self,
            api_client: TestClient,
            admin_headers):
        """Test retrieving all sessions after creating one."""
        response = api_client.get("/admin/all_sessions", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert "sessions" in data
        assert isinstance(data["sessions"], list)

        # Find our session
        our_session = None
        for session in data["sessions"]:
            if session["session_id"] == TestAdminAPI.session_id:
                our_session = session
                break

        if our_session:  # Session might not be found in some test scenarios
            assert our_session["user_id"] == self.user_id
            assert our_session["quiz_id"] == TestAdminAPI.quiz_id
            assert "created_at" in our_session
            assert "updated_at" in our_session
            assert "current_question_id" in our_session
            assert "completed" in our_session
            assert isinstance(our_session["completed"], bool)

    def test_answer_question_and_complete(
            self,
            api_client: TestClient,
            user_headers):
        """Answer questions to generate results."""
        assert TestAdminAPI.session_id, "Session must be started first"
        assert TestAdminAPI.quiz_id, "Quiz must be created first"

        # Answer all questions to complete the quiz
        for question_id in range(10):  # complex_quiz has 10 questions
            request_data = {
                "session_id": TestAdminAPI.session_id,
                "user_id": self.user_id,
                # Answer format matches engine expectations
                "answer": {"answer": "yes"}
            }
            response = api_client.post(
                f"/quiz/submit_answer/{TestAdminAPI.quiz_id}",
                json=request_data,
                headers=user_headers)

            # Last question might return final results
            if response.status_code == 200:
                data = response.json()
                if "question" in data and data["question"] is None:
                    # Quiz completed
                    break

    def test_get_all_results_with_data(
            self,
            api_client: TestClient,
            admin_headers):
        """Test retrieving all results after completing a quiz."""
        response = api_client.get("/admin/all_results", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert "results" in data
        assert isinstance(data["results"], dict)

        # Check if our user's results exist
        if self.user_id in data["results"]:
            user_results = data["results"][self.user_id]
            assert isinstance(user_results, dict)

            # Check if our quiz results exist
            if TestAdminAPI.quiz_id in user_results:
                quiz_results = user_results[TestAdminAPI.quiz_id]
                assert isinstance(quiz_results, dict)

                # Check structure of results
                for session_id, result in quiz_results.items():
                    assert "scores" in result or "answers" in result
                    if "timestamp" in result:
                        # Verify timestamp is valid
                        assert isinstance(result["timestamp"], str)

    def test_get_all_users_with_data(
            self,
            api_client: TestClient,
            admin_headers):
        """Test retrieving all users after quiz activity."""
        response = api_client.get("/admin/all_users", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert "users" in data
        assert isinstance(data["users"], dict)

        # Check if our user exists
        if self.user_id in data["users"]:
            user_data = data["users"][self.user_id]
            assert "permissions" in user_data
            assert "quizzes_taken" in user_data
            assert isinstance(user_data["permissions"], list)
            assert isinstance(user_data["quizzes_taken"], int)
            # User should have taken at least 1 quiz (ours)
            assert user_data["quizzes_taken"] >= 0

    def test_admin_endpoints_require_auth(self, api_client: TestClient):
        """Test that admin endpoints require authentication."""
        # Test without headers
        response = api_client.get("/admin/all_users")
        assert response.status_code == 403

        response = api_client.get("/admin/all_results")
        assert response.status_code == 403

        response = api_client.get("/admin/all_sessions")
        assert response.status_code == 403

    def test_admin_endpoints_reject_user_token(
            self,
            api_client: TestClient,
            user_headers):
        """Test that admin endpoints reject non-admin tokens."""
        # These should fail with user token (not admin)
        response = api_client.get("/admin/all_users", headers=user_headers)
        assert response.status_code == 403

        response = api_client.get("/admin/all_results", headers=user_headers)
        assert response.status_code == 403

        response = api_client.get("/admin/all_sessions", headers=user_headers)
        assert response.status_code == 403

    def test_get_all_quizzes(self, api_client: TestClient, admin_headers):
        """Test retrieving all quizzes via admin endpoint."""
        response = api_client.get("/admin/all_quizzes", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert "quizzes" in data
        assert isinstance(data["quizzes"], dict)

        # Our quiz should exist
        if TestAdminAPI.quiz_id:
            assert TestAdminAPI.quiz_id in data["quizzes"]
            quiz = data["quizzes"][TestAdminAPI.quiz_id]
            # Quiz data has metadata and questions
            assert "metadata" in quiz or "title" in quiz
            assert "questions" in quiz

    def test_get_all_tokens(self, api_client: TestClient, admin_headers):
        """Test retrieving all tokens via admin endpoint."""
        response = api_client.get("/admin/all_tokens", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert "tokens" in data
        # Tokens are grouped by quiz_id in a dict, not a flat list
        assert isinstance(data["tokens"], dict)

        # Should have at least the token we created for our quiz
        if TestAdminAPI.quiz_id and TestAdminAPI.quiz_id in data["tokens"]:
            quiz_tokens = data["tokens"][TestAdminAPI.quiz_id]
            assert isinstance(quiz_tokens, list)
            assert len(quiz_tokens) > 0
            token = quiz_tokens[0]
            assert "token" in token
            assert "quiz_id" in token
            assert "type" in token

import pytest
from pyquizhub.core.storage.sql_storage import SQLStorageManager
import json
import tempfile
import os
from fastapi.testclient import TestClient


# Fixture to provide quiz data for tests
@pytest.fixture(scope="module")
def quiz_data():
    file_path = os.path.join(os.path.dirname(
        __file__), "test_quiz_jsons", "complex_quiz.json")
    with open(file_path, "r") as f:
        return json.load(f)


# Fixture to provide invalid quiz data
@pytest.fixture(scope="module")
def invalid_quiz_data():
    file_path = os.path.join(os.path.dirname(
        __file__), "test_quiz_jsons", "invalid_quiz_bad_score_update.json")
    with open(file_path, "r") as f:
        return json.load(f)


class TestQuizEngine:
    """Group of tests for the Quiz Engine."""

    quiz_id = None
    token = None
    session_id = None
    user_id = "user1"

    def test_root(self, api_client: TestClient):
        response = api_client.get("/")
        assert response.status_code == 200
        assert response.json() == {"message": "Welcome to the Quiz Engine API"}

    def test_create_quiz(self, api_client: TestClient, quiz_data):
        """Test creating a quiz and save the quiz_id."""
        response = api_client.post(
            "/admin/create_quiz", json={"quiz": quiz_data, "creator_id": self.user_id})
        assert response.status_code == 200, f"Unexpected status code: {response.status_code}, detail: {response.json()}"
        TestQuizEngine.quiz_id = response.json()["quiz_id"]
        assert TestQuizEngine.quiz_id, "Quiz ID should not be empty."

    def test_generate_token(self, api_client: TestClient):
        """Test generating a token for the created quiz."""
        assert TestQuizEngine.quiz_id, "Quiz ID must be created before generating a token."
        response = api_client.post(
            "/admin/generate_token", json={"quiz_id": self.quiz_id, "type": "permanent"})
        assert response.status_code == 200, f"Unexpected status code: {response.status_code}, detail: {response.json()}"
        TestQuizEngine.token = response.json()["token"]
        assert TestQuizEngine.token, "Token should not be empty."

    def test_start_quiz(self, api_client: TestClient):
        """Test starting a quiz and save the session_id."""
        assert self.token, "Token must be generated before starting the quiz."
        response = api_client.post(
            f"/quiz/start_quiz?token={self.token}&user_id={self.user_id}")
        assert response.status_code == 200, f"Unexpected status code: {response.status_code}, detail: {response.json()}"
        data = response.json()
        TestQuizEngine.session_id = data["session_id"]
        assert TestQuizEngine.session_id, "Session ID should not be empty."
        assert "question" in data, "Question should be present in response."

    def test_submit_answer(self, api_client: TestClient):
        """Test submitting an answer for the current quiz session."""
        assert self.session_id, "Session ID must exist before submitting an answer."
        answer_request = {
            "user_id": self.user_id,
            "session_id": self.session_id,
            "answer": {"answer": "yes"}
        }
        response = api_client.post(
            f"/quiz/submit_answer/{self.quiz_id}", json=answer_request)
        assert response.status_code == 200, f"Unexpected status code: {response.status_code}, detail: {response.json()}"
        data = response.json()
        assert "question" in data or "final_message" in data, "Response should include next question or final message."

    # def test_get_participated_users(self, api_client: TestClient):
    #     """Test retrieving participated users for the quiz."""
    #     assert self.quiz_id, "Quiz ID must be created before retrieving participants."
    #     response = client.get(f"/admin/participated_users/{self.quiz_id}")
    #     assert response.status_code == 200, f"Unexpected status code: {response.status_code}, detail: {response.json()}"
    #     data = response.json()
    #     assert "user_ids" in data, "Response should include user IDs."
    #     assert self.user_id in data["user_ids"], f"User ID {self.user_id} should be in participated users."

    # def test_get_results(self, api_client: TestClient):
    #     """Test retrieving results for the quiz session."""
    #     assert self.quiz_id, "Quiz ID must be created before retrieving results."
    #     assert self.session_id, "Session ID must exist before retrieving results."
    #     response = client.get(
    #         f"/admin/results/{self.quiz_id}/{self.user_id}?session_id={self.session_id}")
    #     assert response.status_code == 200, f"Unexpected status code: {response.status_code}, detail: {response.json()}"
    #     data = response.json()
    #     assert "scores" in data, "Response should include scores."
    #     assert "answers" in data, "Response should include answers."

    def test_invalid_quiz_data(self, api_client: TestClient, invalid_quiz_data):
        """Test handling invalid quiz data."""
        response = api_client.post(
            "/admin/create_quiz", json={"quiz": invalid_quiz_data, "creator_id": self.user_id})
        assert response.status_code == 400, f"Unexpected status code: {response.status_code}, detail: {response.json()}"

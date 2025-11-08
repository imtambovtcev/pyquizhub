import pytest
import json
import tempfile
import os
from fastapi.testclient import TestClient
from pyquizhub.config.settings import get_config_manager


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


@pytest.fixture(scope="module")
def user_headers(config_path):
    config_manager = get_config_manager()
    config_manager.load(str(config_path))
    headers = {"Content-Type": "application/json"}
    token = config_manager.get_token("user")
    if token:
        headers["Authorization"] = token
    return headers


@pytest.fixture(scope="module")
def admin_headers(config_path):
    config_manager = get_config_manager()
    config_manager.load(str(config_path))
    headers = {"Content-Type": "application/json"}
    token = config_manager.get_token("admin")
    if token:
        headers["Authorization"] = token
    return headers


class TestQuizEngine:
    """Group of tests for the Quiz Engine."""

    quiz_id = None
    token = None
    session_id = None
    user_id = "user1"

    def test_root(self, api_client: TestClient):
        from pyquizhub.models import StartQuizRequestModel, StartQuizResponseModel, TokenRequestModel, AnswerRequestModel
        response = api_client.get("/")
        assert response.status_code == 200
        assert response.json() == {"message": "Welcome to the Quiz Engine API"}

    def test_create_quiz(
            self,
            api_client: TestClient,
            quiz_data,
            admin_headers):
        """Test creating a quiz and save the quiz_id."""
        from pyquizhub.models import StartQuizRequestModel, StartQuizResponseModel, TokenRequestModel, AnswerRequestModel
        request_data = {"quiz": quiz_data, "creator_id": self.user_id}
        response = api_client.post(
            "/admin/create_quiz", json=request_data, headers=admin_headers)
        assert response.status_code == 200, f"Unexpected status code: {
            response.status_code}, detail: {
            response.json()}"
        TestQuizEngine.quiz_id = response.json()["quiz_id"]
        assert TestQuizEngine.quiz_id, "Quiz ID should not be empty."

    def test_get_all_quizzes(self, api_client: TestClient, admin_headers):
        """Test retrieving all quizzes."""
        from pyquizhub.models import StartQuizRequestModel, StartQuizResponseModel, TokenRequestModel, AnswerRequestModel
        response = api_client.get(
            "/admin/all_quizzes", headers=admin_headers)
        assert response.status_code == 200, f"Unexpected status code: {
            response.status_code}, detail: {
            response.json()}"
        data = response.json()
        assert "quizzes" in data, "Response should include quizzes."
        assert TestQuizEngine.quiz_id in data["quizzes"], f"Quiz ID {
            TestQuizEngine.quiz_id} should be in the list of quizzes."

    def test_generate_token(self, api_client: TestClient, admin_headers):
        """Test generating a token for the created quiz."""
        from pyquizhub.models import StartQuizRequestModel, StartQuizResponseModel, TokenRequestModel, AnswerRequestModel
        assert TestQuizEngine.quiz_id, "Quiz ID must be created before generating a token."
        request_data = TokenRequestModel(
            quiz_id=self.quiz_id, type="permanent")
        response = api_client.post(
            "/admin/generate_token",
            json=request_data.dict(),
            headers=admin_headers)
        assert response.status_code == 200, f"Unexpected status code: {
            response.status_code}, detail: {
            response.json()}"
        TestQuizEngine.token = response.json()["token"]
        assert TestQuizEngine.token, "Token should not be empty."

    def test_get_all_tokens(self, api_client: TestClient, admin_headers):
        """Test retrieving all tokens."""
        from pyquizhub.models import StartQuizRequestModel, StartQuizResponseModel, TokenRequestModel, AnswerRequestModel
        response = api_client.get(
            "/admin/all_tokens", headers=admin_headers)
        assert response.status_code == 200, f"Unexpected status code: {
            response.status_code}, detail: {
            response.json()}"
        data = response.json()
        assert "tokens" in data, "Response should include tokens."
        assert TestQuizEngine.quiz_id in data["tokens"], f"Quiz ID {
            TestQuizEngine.quiz_id} should be in the list of tokens."

    def test_start_quiz(self, api_client: TestClient, user_headers):
        """Test starting a quiz and save the session_id."""
        from pyquizhub.models import StartQuizRequestModel, StartQuizResponseModel, TokenRequestModel, AnswerRequestModel
        assert self.token, "Token must be generated before starting the quiz."
        request_data = StartQuizRequestModel(
            token=self.token, user_id=self.user_id)
        response = api_client.post(
            f"/quiz/start_quiz",
            json=request_data.dict(),
            headers=user_headers)
        assert response.status_code == 200, f"Unexpected status code: {
            response.status_code}, detail: {
            response.json()}"
        data = response.json()
        TestQuizEngine.session_id = data["session_id"]
        assert TestQuizEngine.session_id, "Session ID should not be empty."
        assert "question" in data, "Question should be present in response."

    def test_submit_answer(self, api_client: TestClient, user_headers):
        """Test submitting an answer for the current quiz session."""
        from pyquizhub.models import StartQuizRequestModel, StartQuizResponseModel, TokenRequestModel, AnswerRequestModel
        assert self.session_id, "Session ID must exist before submitting an answer."
        # apple question
        answer_request = AnswerRequestModel(
            user_id=self.user_id,
            session_id=self.session_id,
            answer={"answer": "yes"}
        )
        response = api_client.post(
            f"/quiz/submit_answer/{self.quiz_id}", json=answer_request.dict(), headers=user_headers)
        assert response.status_code == 200, f"Unexpected status code: {
            response.status_code}, detail: {
            response.json()}"
        data = response.json()
        assert "question" in data, "Response should include next question"
        assert data["question"]['id'] == 2
        # pear question
        response = api_client.post(
            f"/quiz/submit_answer/{self.quiz_id}", json=answer_request.dict(), headers=user_headers)
        assert response.status_code == 200, f"Unexpected status code: {
            response.status_code}, detail: {
            response.json()}"
        data = response.json()

        assert "question" in data, "Response should include question field"
        # When quiz is completed, question is None
        assert data["question"] is None, "Question should be None when quiz is completed"

    def test_get_participated_users(self, api_client: TestClient):
        """Test retrieving participated users for the quiz."""
        from pyquizhub.models import StartQuizRequestModel, StartQuizResponseModel, TokenRequestModel, AnswerRequestModel
        assert self.quiz_id, "Quiz ID must be created before retrieving participants."
        response = api_client.get(f"/admin/participated_users/{self.quiz_id}")
        assert response.status_code == 200, f"Unexpected status code: {
            response.status_code}, detail: {
            response.json()}"
        data = response.json()
        assert "user_ids" in data, "Response should include user IDs."
        assert self.user_id in data["user_ids"], f"User ID {
            self.user_id} should be in participated users."

    def test_get_results(self, api_client: TestClient):
        """Test retrieving results for the quiz session."""
        from pyquizhub.models import StartQuizRequestModel, StartQuizResponseModel, TokenRequestModel, AnswerRequestModel
        assert self.quiz_id, "Quiz ID must be created before retrieving results."
        assert self.session_id, "Session ID must exist before retrieving results."
        response = api_client.get(
            f"/admin/results/{self.quiz_id}")
        assert response.status_code == 200, f"Unexpected status code: {
            response.status_code}, detail: {
            response.json()}"
        data = response.json()

        assert "results" in data, "Response should include results."
        assert "results" in data
        assert self.user_id in data[
            "results"], f"Results should contain user {self.user_id}"
        assert self.session_id in data["results"][self.user_id], "Results should contain the session"

    def test_invalid_quiz_data(
            self,
            api_client: TestClient,
            invalid_quiz_data):
        """Test handling invalid quiz data."""
        from pyquizhub.models import StartQuizRequestModel, StartQuizResponseModel, TokenRequestModel, AnswerRequestModel
        response = api_client.post(
            "/admin/create_quiz",
            json={
                "quiz": invalid_quiz_data,
                "creator_id": self.user_id})
        assert response.status_code == 400, f"Unexpected status code: {
            response.status_code}, detail: {
            response.json()}"

import pytest
from fastapi.testclient import TestClient
from pyquizhub.engine.engine_api import app
import json
import uuid

client = TestClient(app)


def load_quiz_data(file_path):
    with open(file_path, "r") as f:
        return json.load(f)


@pytest.fixture
def quiz_data():
    return load_quiz_data("tests/test_quiz_jsons/complex_quiz.json")


def test_root():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": 'Welcome to the Quiz Engine API'}


def test_start_quiz(quiz_data):
    # Create the quiz first
    creator_id = "user1"
    create_response = client.post("/admin/create_quiz",
                                  json={"quiz": quiz_data, "creator_id": creator_id})
    assert create_response.status_code == 200, f"Unexpected status code: {create_response.status_code}, detail: {create_response.json()}"
    quiz_id = create_response.json()["quiz_id"]

    # Generate a token for the quiz
    token_response = client.post("/admin/generate_token",
                                 json={"quiz_id": quiz_id, "type": "single-use"})
    assert token_response.status_code == 200, f"Unexpected status code: {token_response.status_code}, detail: {token_response.json()}"
    token = token_response.json()["token"]

    # Start the quiz using the generated token
    user_id = "user1"
    response = client.post(
        f"/start_quiz?token={token}&user_id={user_id}")
    assert response.status_code == 200, f"Unexpected status code: {response.status_code}, detail: {response.json()}"
    data = response.json()
    assert "session_id" in data
    assert "question" in data


def test_submit_answer(quiz_data):
    # Create the quiz first
    creator_id = "user1"
    create_response = client.post("/admin/create_quiz",
                                  json={"quiz": quiz_data, "creator_id": creator_id})
    assert create_response.status_code == 200, f"Unexpected status code: {create_response.status_code}, detail: {create_response.json()}"
    quiz_id = create_response.json()["quiz_id"]

    # Generate a token for the quiz
    token_response = client.post("/admin/generate_token",
                                 json={"quiz_id": quiz_id, "type": "single-use"})
    assert token_response.status_code == 200, f"Unexpected status code: {token_response.status_code}, detail: {token_response.json()}"
    token = token_response.json()["token"]

    # Start the quiz using the generated token
    user_id = "user1"
    start_response = client.post(
        f"/start_quiz?token={token}&user_id={user_id}")
    assert start_response.status_code == 200, f"Unexpected status code: {start_response.status_code}, detail: {start_response.json()}"
    session_id = start_response.json()["session_id"]

    answer_request = {
        "user_id": user_id,
        "session_id": session_id,
        "answer": {"answer": "yes"}
    }
    response = client.post(
        f"/submit_answer/{quiz_id}", json=answer_request)
    assert response.status_code == 200, f"Unexpected status code: {response.status_code}, detail: {response.json()}"
    data = response.json()
    assert "question" in data or "final_message" in data


def test_invalid_quiz_data():
    invalid_quiz_data = load_quiz_data(
        "tests/test_quiz_jsons/invalid_quiz_bad_score_update.json")
    response = client.post(
        f"/start_quiz?token=invalid_token&user_id=user1")
    assert response.status_code == 404, f"Unexpected status code: {response.status_code}, detail: {response.json()}"


def test_create_quiz(quiz_data):
    creator_id = "user1"
    response = client.post("/admin/create_quiz",
                           json={"quiz": quiz_data, "creator_id": creator_id})
    assert response.status_code == 200, f"Unexpected status code: {response.status_code}, detail: {response.json()}"
    data = response.json()
    assert "quiz_id" in data
    assert "title" in data


def test_generate_token():
    quiz_id = "quiz-001"
    response = client.post("/admin/generate_token",
                           json={"quiz_id": quiz_id, "type": "single-use"})
    assert response.status_code == 200, f"Unexpected status code: {response.status_code}, detail: {response.json()}"
    data = response.json()
    assert "token" in data


def test_get_participated_users():
    quiz_id = "quiz-001"
    response = client.get(f"/admin/participated_users/{quiz_id}")
    assert response.status_code == 200, f"Unexpected status code: {response.status_code}, detail: {response.json()}"
    data = response.json()
    assert "user_ids" in data

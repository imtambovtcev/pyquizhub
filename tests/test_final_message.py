"""
Tests for final_message question type functionality.

This module tests the auto-completion behavior when a quiz contains
a final_message question type, which should display to the user but
not require any answer submission.
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


@pytest.fixture
def final_message_quiz():
    """Quiz with a final_message question at the end."""
    return {
        "metadata": {
            "title": "Final Message Test Quiz",
            "description": "Tests final_message auto-completion",
            "version": "2.0"
        },
        "variables": {
            "score": {
                "type": "integer",
                "mutable_by": ["engine"],
                "tags": ["score"]
            },
            "attempts": {
                "type": "integer",
                "mutable_by": ["engine"],
                "tags": ["public"]
            }
        },
        "questions": [
            {
                "id": 1,
                "data": {
                    "text": "What is 2 + 2?",
                    "type": "integer"
                },
                "score_updates": [
                    {
                        "condition": "answer == 4",
                        "update": {
                            "score": "score + 10",
                            "attempts": "attempts + 1"
                        }
                    },
                    {
                        "condition": "answer != 4",
                        "update": {
                            "attempts": "attempts + 1"
                        }
                    }
                ]
            },
            {
                "id": 2,
                "data": {
                    "text": "What is 5 * 3?",
                    "type": "integer"
                },
                "score_updates": [
                    {
                        "condition": "answer == 15",
                        "update": {
                            "score": "score + 10",
                            "attempts": "attempts + 1"
                        }
                    },
                    {
                        "condition": "answer != 15",
                        "update": {
                            "attempts": "attempts + 1"
                        }
                    }
                ]
            },
            {
                "id": 3,
                "data": {
                    "text": "Quiz Complete! Your score: {variables.score} points from {variables.attempts} attempts.",
                    "type": "final_message"
                },
                "score_updates": []
            }
        ],
        "transitions": {
            "1": [{"expression": "true", "next_question_id": 2}],
            "2": [{"expression": "true", "next_question_id": 3}],
            "3": [{"expression": "true", "next_question_id": None}]
        }
    }


class TestFinalMessage:
    """Test suite for final_message question type."""

    def test_final_message_auto_completes_quiz(
            self, api_client: TestClient, admin_headers, user_headers, final_message_quiz):
        """Test that quiz auto-completes when final_message is reached."""
        # Create quiz
        response = api_client.post(
            "/admin/create_quiz",
            json={"quiz": final_message_quiz, "creator_id": "test_creator"},
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

        # Start quiz
        response = api_client.post(
            "/quiz/start_quiz",
            json={"token": token, "user_id": "test_user"},
            headers=user_headers
        )
        assert response.status_code == 200
        data = response.json()
        session_id = data["session_id"]
        assert data["question"]["id"] == 1

        # Answer question 1 correctly
        response = api_client.post(
            f"/quiz/submit_answer/{quiz_id}",
            json={
                "user_id": "test_user",
                "session_id": session_id,
                "answer": {"answer": 4}
            },
            headers=user_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["question"]["id"] == 2

        # Answer question 2 correctly
        response = api_client.post(
            f"/quiz/submit_answer/{quiz_id}",
            json={
                "user_id": "test_user",
                "session_id": session_id,
                "answer": {"answer": 15}
            },
            headers=user_headers
        )
        assert response.status_code == 200
        data = response.json()

        # Verify final_message is returned
        assert data["question"]["id"] == 3
        assert data["question"]["data"]["type"] == "final_message"

        # Verify variable substitution worked
        assert "20 points" in data["question"]["data"]["text"]
        assert "2 attempts" in data["question"]["data"]["text"]

        # Try to submit another answer (should fail - session deleted)
        response = api_client.post(
            f"/quiz/submit_answer/{quiz_id}",
            json={
                "user_id": "test_user",
                "session_id": session_id,
                "answer": {"answer": "done"}
            },
            headers=user_headers
        )
        assert response.status_code == 404
        assert "Session not found" in response.json()["detail"]

        # Verify results were saved
        response = api_client.get(
            f"/admin/results/{quiz_id}",
            headers=admin_headers
        )
        assert response.status_code == 200
        results = response.json()["results"]
        assert "test_user" in results

        user_results = results["test_user"][session_id]
        assert user_results["scores"]["score"] == 20.0
        assert user_results["scores"]["attempts"] == 2.0

        # Verify answers were recorded
        answers = user_results["answers"]
        assert len(answers) == 3  # 2 answered + 1 final_message (null)
        assert answers[0]["question_id"] == 1
        assert answers[0]["answer"] == 4
        assert answers[1]["question_id"] == 2
        assert answers[1]["answer"] == 15
        assert answers[2]["question_id"] == 3
        assert answers[2]["answer"] is None  # final_message has no answer

    def test_final_message_with_incorrect_answers(
            self, api_client: TestClient, admin_headers, user_headers, final_message_quiz):
        """Test final_message with incorrect answers (score should be 0)."""
        # Create quiz
        response = api_client.post(
            "/admin/create_quiz",
            json={"quiz": final_message_quiz, "creator_id": "test_creator"},
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

        # Start quiz
        response = api_client.post(
            "/quiz/start_quiz",
            json={"token": token, "user_id": "test_user2"},
            headers=user_headers
        )
        assert response.status_code == 200
        session_id = response.json()["session_id"]

        # Answer question 1 incorrectly
        response = api_client.post(
            f"/quiz/submit_answer/{quiz_id}",
            json={
                "user_id": "test_user2",
                "session_id": session_id,
                "answer": {"answer": 5}
            },
            headers=user_headers
        )
        assert response.status_code == 200

        # Answer question 2 incorrectly
        response = api_client.post(
            f"/quiz/submit_answer/{quiz_id}",
            json={
                "user_id": "test_user2",
                "session_id": session_id,
                "answer": {"answer": 10}
            },
            headers=user_headers
        )
        assert response.status_code == 200
        data = response.json()

        # Verify final_message shows correct score (0)
        assert data["question"]["data"]["type"] == "final_message"
        assert "0 points" in data["question"]["data"]["text"]
        assert "2 attempts" in data["question"]["data"]["text"]

        # Verify results
        response = api_client.get(
            f"/admin/results/{quiz_id}",
            headers=admin_headers
        )
        results = response.json()["results"]["test_user2"][session_id]
        assert results["scores"]["score"] == 0.0
        assert results["scores"]["attempts"] == 2.0


    def test_final_message_validation(
            self, api_client: TestClient, admin_headers):
        """Test that final_message questions are validated correctly."""
        quiz = {
            "metadata": {"title": "Test", "version": "2.0"},
            "variables": {"score": {"type": "integer", "mutable_by": ["engine"], "tags": ["score"]}},
            "questions": [
                {
                    "id": 1,
                    "data": {
                        "text": "Final message with options (invalid)",
                        "type": "final_message",
                        "options": [{"value": "a", "label": "A"}]  # Should not have options
                    },
                    "score_updates": []
                }
            ],
            "transitions": {
                "1": [{"expression": "true", "next_question_id": None}]
            }
        }

        response = api_client.post(
            "/admin/create_quiz",
            json={"quiz": quiz, "creator_id": "test_creator"},
            headers=admin_headers
        )

        # Should fail validation
        assert response.status_code == 400
        assert "should not have options" in str(response.json()["detail"])

"""
Tests for complex quiz end-to-end flow with user output verification.

This module tests the complex quiz with branching logic and loops,
verifying exact user-facing output at each step. Tests:
- Question text content
- Multiple choice options
- Score updates
- Transition logic (loops)
- Complete user journey
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
def complex_quiz():
    """Load the complex quiz JSON."""
    import json
    with open("tests/test_quiz_jsons/complex_quiz.json") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def complex_quiz_setup(api_client: TestClient, admin_headers, complex_quiz):
    """Create complex quiz and generate token."""
    # Create quiz
    response = api_client.post(
        "/admin/create_quiz",
        json={"quiz": complex_quiz, "creator_id": "admin"},
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


class TestComplexQuizFlow:
    """Test suite for complex quiz end-to-end user experience."""

    def test_complex_quiz_straight_path_yes_yes(
            self,
            api_client: TestClient,
            user_headers,
            admin_headers,
            complex_quiz_setup):
        """Test answering yes->yes - straight path through quiz."""
        # Start quiz
        response = api_client.post(
            "/quiz/start_quiz",
            json={
                "token": complex_quiz_setup["token"],
                "user_id": "test_yes_yes"},
            headers=user_headers)
        assert response.status_code == 200
        data = response.json()
        session_id = data["session_id"]
        quiz_id = data["quiz_id"]

        # Verify Question 1: "Do you like apples?"
        assert data["question"]["id"] == 1
        question_data = data["question"]["data"]
        assert question_data["text"] == "Do you like apples?"
        assert question_data["type"] == "multiple_choice"

        # Verify options
        options = {opt["value"]: opt["label"]
                   for opt in question_data["options"]}
        assert options["yes"] == "Yes"
        assert options["no"] == "No"

        # Answer YES to apples
        response = api_client.post(
            f"/quiz/submit_answer/{quiz_id}",
            json={
                "user_id": "test_yes_yes",
                "session_id": session_id,
                "answer": {"answer": "yes"}
            },
            headers=user_headers
        )
        assert response.status_code == 200
        data = response.json()

        # Should progress to Question 2 (fruits >= 1 after answering yes)
        assert data["question"]["id"] == 2
        question_data = data["question"]["data"]
        assert question_data["text"] == "Do you like pears?"
        assert question_data["type"] == "multiple_choice"

        # Answer YES to pears
        response = api_client.post(
            f"/quiz/submit_answer/{quiz_id}",
            json={
                "user_id": "test_yes_yes",
                "session_id": session_id,
                "answer": {"answer": "yes"}
            },
            headers=user_headers
        )
        assert response.status_code == 200
        data = response.json()

        # Quiz should be completed
        assert data["question"] is None

        # Verify final scores
        response = api_client.get(
            f"/admin/results/{quiz_id}",
            headers=admin_headers
        )
        assert response.status_code == 200
        results = response.json()["results"]

        user_results = results["test_yes_yes"][session_id]

        # Expected scores: fruits=2, apples=2, pears=2
        assert user_results["scores"]["fruits"] == 2.0
        assert user_results["scores"]["apples"] == 2.0
        assert user_results["scores"]["pears"] == 2.0

        # Verify answers recorded
        answers = user_results["answers"]
        assert len(answers) == 2
        assert answers[0]["question_id"] == 1
        assert answers[0]["answer"] == "yes"
        assert answers[1]["question_id"] == 2
        assert answers[1]["answer"] == "yes"

    def test_complex_quiz_loop_path_no_then_yes(
            self,
            api_client: TestClient,
            user_headers,
            admin_headers,
            complex_quiz_setup):
        """Test loop behavior - answering no then yes causes loop back to Q1."""
        # Start quiz
        response = api_client.post(
            "/quiz/start_quiz",
            json={
                "token": complex_quiz_setup["token"],
                "user_id": "test_no_yes"},
            headers=user_headers)
        assert response.status_code == 200
        data = response.json()
        session_id = data["session_id"]
        quiz_id = data["quiz_id"]

        # Verify Question 1
        assert data["question"]["id"] == 1
        assert data["question"]["data"]["text"] == "Do you like apples?"

        # Answer NO to apples
        response = api_client.post(
            f"/quiz/submit_answer/{quiz_id}",
            json={
                "user_id": "test_no_yes",
                "session_id": session_id,
                "answer": {"answer": "no"}
            },
            headers=user_headers
        )
        assert response.status_code == 200
        data = response.json()

        # Should LOOP BACK to Question 1 (fruits < 1, so transition goes to Q1)
        assert data["question"]["id"] == 1
        assert data["question"]["data"]["text"] == "Do you like apples?"

        # Now answer YES to apples
        response = api_client.post(
            f"/quiz/submit_answer/{quiz_id}",
            json={
                "user_id": "test_no_yes",
                "session_id": session_id,
                "answer": {"answer": "yes"}
            },
            headers=user_headers
        )
        assert response.status_code == 200
        data = response.json()

        # Should progress to Question 2
        assert data["question"]["id"] == 2
        assert data["question"]["data"]["text"] == "Do you like pears?"

        # Answer YES to pears
        response = api_client.post(
            f"/quiz/submit_answer/{quiz_id}",
            json={
                "user_id": "test_no_yes",
                "session_id": session_id,
                "answer": {"answer": "yes"}
            },
            headers=user_headers
        )
        assert response.status_code == 200
        data = response.json()

        # Quiz completed
        assert data["question"] is None

        # Verify final scores
        response = api_client.get(
            f"/admin/results/{quiz_id}",
            headers=admin_headers
        )
        results = response.json()["results"]
        user_results = results["test_no_yes"][session_id]

        # Expected scores:
        # After 'no': fruits=0, apples=-1, pears=0
        # After 'yes': fruits=1, apples=1, pears=0
        # After 'yes' to pears: fruits=2, apples=1, pears=2
        assert user_results["scores"]["fruits"] == 2.0
        assert user_results["scores"]["apples"] == 1.0
        assert user_results["scores"]["pears"] == 2.0

        # Verify 3 answers recorded (no, yes, yes)
        answers = user_results["answers"]
        assert len(answers) == 3
        assert answers[0]["question_id"] == 1
        assert answers[0]["answer"] == "no"
        assert answers[1]["question_id"] == 1
        assert answers[1]["answer"] == "yes"
        assert answers[2]["question_id"] == 2
        assert answers[2]["answer"] == "yes"

    def test_complex_quiz_yes_no_path(
            self,
            api_client: TestClient,
            user_headers,
            admin_headers,
            complex_quiz_setup):
        """Test answering yes->no to verify question 2 behavior."""
        # Start quiz
        response = api_client.post(
            "/quiz/start_quiz",
            json={
                "token": complex_quiz_setup["token"],
                "user_id": "test_yes_no"},
            headers=user_headers)
        assert response.status_code == 200
        data = response.json()
        session_id = data["session_id"]
        quiz_id = data["quiz_id"]

        # Answer YES to apples
        response = api_client.post(
            f"/quiz/submit_answer/{quiz_id}",
            json={
                "user_id": "test_yes_no",
                "session_id": session_id,
                "answer": {"answer": "yes"}
            },
            headers=user_headers
        )
        assert response.status_code == 200
        data = response.json()

        # Should be at Question 2
        assert data["question"]["id"] == 2
        assert data["question"]["data"]["text"] == "Do you like pears?"

        # Answer NO to pears
        response = api_client.post(
            f"/quiz/submit_answer/{quiz_id}",
            json={
                "user_id": "test_yes_no",
                "session_id": session_id,
                "answer": {"answer": "no"}
            },
            headers=user_headers
        )
        assert response.status_code == 200
        data = response.json()

        # Quiz completed
        assert data["question"] is None

        # Verify final scores
        response = api_client.get(
            f"/admin/results/{quiz_id}",
            headers=admin_headers
        )
        results = response.json()["results"]
        user_results = results["test_yes_no"][session_id]

        # Expected scores: fruits=1, apples=2, pears=0 (no update for 'no' to
        # pears)
        assert user_results["scores"]["fruits"] == 1.0
        assert user_results["scores"]["apples"] == 2.0
        assert user_results["scores"]["pears"] == 0.0

    def test_complex_quiz_multiple_loops(
            self,
            api_client: TestClient,
            user_headers,
            admin_headers,
            complex_quiz_setup):
        """Test multiple loops before progressing."""
        # Start quiz
        response = api_client.post(
            "/quiz/start_quiz",
            json={
                "token": complex_quiz_setup["token"],
                "user_id": "test_multi_loop"},
            headers=user_headers)
        assert response.status_code == 200
        data = response.json()
        session_id = data["session_id"]
        quiz_id = data["quiz_id"]

        # Answer NO three times (should loop 3 times)
        for i in range(3):
            assert data["question"]["id"] == 1
            assert data["question"]["data"]["text"] == "Do you like apples?"

            response = api_client.post(
                f"/quiz/submit_answer/{quiz_id}",
                json={
                    "user_id": "test_multi_loop",
                    "session_id": session_id,
                    "answer": {"answer": "no"}
                },
                headers=user_headers
            )
            assert response.status_code == 200
            data = response.json()

        # Still at question 1 after 3 loops
        assert data["question"]["id"] == 1

        # Now answer YES to break the loop
        response = api_client.post(
            f"/quiz/submit_answer/{quiz_id}",
            json={
                "user_id": "test_multi_loop",
                "session_id": session_id,
                "answer": {"answer": "yes"}
            },
            headers=user_headers
        )
        assert response.status_code == 200
        data = response.json()

        # Should progress to question 2
        assert data["question"]["id"] == 2

        # Complete the quiz
        response = api_client.post(
            f"/quiz/submit_answer/{quiz_id}",
            json={
                "user_id": "test_multi_loop",
                "session_id": session_id,
                "answer": {"answer": "yes"}
            },
            headers=user_headers
        )
        assert response.status_code == 200

        # Verify 5 answers recorded (3 no's, 1 yes, 1 yes)
        response = api_client.get(
            f"/admin/results/{quiz_id}",
            headers=admin_headers
        )
        results = response.json()["results"]
        user_results = results["test_multi_loop"][session_id]

        answers = user_results["answers"]
        assert len(answers) == 5

        # Verify the sequence
        assert answers[0]["answer"] == "no"
        assert answers[1]["answer"] == "no"
        assert answers[2]["answer"] == "no"
        assert answers[3]["answer"] == "yes"
        assert answers[4]["answer"] == "yes"

        # Final scores: apples should be -3 + 2 = -1
        # fruits should be 1
        # pears should be 2
        assert user_results["scores"]["apples"] == -1.0
        assert user_results["scores"]["fruits"] == 2.0
        assert user_results["scores"]["pears"] == 2.0

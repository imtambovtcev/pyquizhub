"""
Tests for complex weather quiz scoring system.

This module tests the weather quiz with API integration and all scoring ranges:
- 100 points: within ±1°C
- 80 points: 1-3°C away
- 60 points: 3-5°C away
- 40 points: 5-10°C away
- 20 points: more than 10°C away
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
def mock_weather_api():
    """Mock the weather API to return consistent test data."""
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "current": {
            "temperature_2m": 10.0,
            "wind_speed_10m": 15.5
        }
    }

    # Patch requests.request (not requests.get) in the api_integration module
    with patch('pyquizhub.core.engine.api_integration.requests.request', return_value=mock_response) as mock_request:
        yield mock_request


@pytest.fixture(scope="module")
def weather_quiz():
    """Load the complex weather quiz JSON."""
    import json
    with open("tests/test_quiz_jsons/complex_weather_quiz.json") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def weather_quiz_setup(api_client: TestClient, admin_headers, weather_quiz):
    """Create weather quiz and generate token (with auto-mocked API)."""
    # Create quiz
    response = api_client.post(
        "/admin/create_quiz",
        json={"quiz": weather_quiz, "creator_id": "admin"},
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


class TestWeatherQuizScoring:
    """Test suite for weather quiz scoring system."""

    def test_perfect_score_exact_match(
            self, api_client: TestClient, user_headers, weather_quiz_setup):
        """Test that exact temperature match awards 100 points."""
        # Mocked API returns 10.0°C, so predict exactly 10.0°C
        actual_temp = 10.0

        # Start quiz
        response = api_client.post(
            "/quiz/start_quiz",
            json={"token": weather_quiz_setup["token"], "user_id": "test_perfect"},
            headers=user_headers
        )
        assert response.status_code == 200
        data = response.json()
        session_id = data["session_id"]
        quiz_id = data["quiz_id"]

        # Submit answer with exact temperature
        response = api_client.post(
            f"/quiz/submit_answer/{quiz_id}",
            json={
                "user_id": "test_perfect",
                "session_id": session_id,
                "answer": {"answer": actual_temp}
            },
            headers=user_headers
        )
        assert response.status_code == 200
        data = response.json()

        # Check the question text contains the score
        # The response should be question 2 (results)
        assert data["question"]["id"] == 2
        question_text = data["question"]["data"]["text"]

        # Should show 100/100 for exact match
        assert "100/100" in question_text, f"Expected 100/100 in: {question_text}"
        # Verify the mocked temperature is shown
        assert "10.0" in question_text or "10" in question_text

    def test_score_80_within_1_3_degrees(
            self, api_client: TestClient, user_headers, weather_quiz_setup):
        """Test that 1-3°C difference awards 80 points."""
        # Mocked API returns 10.0°C
        actual_temp = 10.0
        quiz_id = weather_quiz_setup["quiz_id"]

        # Test prediction 2°C higher (12.0°C)
        response = api_client.post(
            "/quiz/start_quiz",
            json={"token": weather_quiz_setup["token"], "user_id": "test_80_higher"},
            headers=user_headers
        )
        data = response.json()
        session_id = data["session_id"]

        response = api_client.post(
            f"/quiz/submit_answer/{quiz_id}",
            json={
                "user_id": "test_80_higher",
                "session_id": session_id,
                "answer": {"answer": actual_temp + 2.0}
            },
            headers=user_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "80/100" in data["question"]["data"]["text"]

        # Test prediction 2°C lower (8.0°C)
        response = api_client.post(
            "/quiz/start_quiz",
            json={"token": weather_quiz_setup["token"], "user_id": "test_80_lower"},
            headers=user_headers
        )
        data = response.json()
        session_id = data["session_id"]

        response = api_client.post(
            f"/quiz/submit_answer/{quiz_id}",
            json={
                "user_id": "test_80_lower",
                "session_id": session_id,
                "answer": {"answer": actual_temp - 2.0}
            },
            headers=user_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "80/100" in data["question"]["data"]["text"]

    def test_score_60_within_3_5_degrees(
            self, api_client: TestClient, user_headers, weather_quiz_setup):
        """Test that 3-5°C difference awards 60 points."""
        # Mocked API returns 10.0°C, test 4°C difference (14.0°C)
        actual_temp = 10.0
        quiz_id = weather_quiz_setup["quiz_id"]

        response = api_client.post(
            "/quiz/start_quiz",
            json={"token": weather_quiz_setup["token"], "user_id": "test_60_points"},
            headers=user_headers
        )
        data = response.json()
        session_id = data["session_id"]

        response = api_client.post(
            f"/quiz/submit_answer/{quiz_id}",
            json={
                "user_id": "test_60_points",
                "session_id": session_id,
                "answer": {"answer": actual_temp + 4.0}
            },
            headers=user_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "60/100" in data["question"]["data"]["text"]

    def test_score_40_within_5_10_degrees(
            self, api_client: TestClient, user_headers, weather_quiz_setup):
        """Test that 5-10°C difference awards 40 points."""
        # Mocked API returns 10.0°C, test 7°C difference (17.0°C)
        actual_temp = 10.0
        quiz_id = weather_quiz_setup["quiz_id"]

        response = api_client.post(
            "/quiz/start_quiz",
            json={"token": weather_quiz_setup["token"], "user_id": "test_40_points"},
            headers=user_headers
        )
        data = response.json()
        session_id = data["session_id"]

        response = api_client.post(
            f"/quiz/submit_answer/{quiz_id}",
            json={
                "user_id": "test_40_points",
                "session_id": session_id,
                "answer": {"answer": actual_temp + 7.0}
            },
            headers=user_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "40/100" in data["question"]["data"]["text"]

    def test_score_20_more_than_10_degrees(
            self, api_client: TestClient, user_headers, weather_quiz_setup):
        """Test that >10°C difference awards 20 points."""
        # Mocked API returns 10.0°C, test 15°C difference (25.0°C)
        actual_temp = 10.0
        quiz_id = weather_quiz_setup["quiz_id"]

        response = api_client.post(
            "/quiz/start_quiz",
            json={"token": weather_quiz_setup["token"], "user_id": "test_20_points"},
            headers=user_headers
        )
        data = response.json()
        session_id = data["session_id"]

        response = api_client.post(
            f"/quiz/submit_answer/{quiz_id}",
            json={
                "user_id": "test_20_points",
                "session_id": session_id,
                "answer": {"answer": actual_temp + 15.0}
            },
            headers=user_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "20/100" in data["question"]["data"]["text"]

    def test_api_integration_fetches_weather_data(
            self, api_client: TestClient, user_headers, weather_quiz_setup, mock_weather_api):
        """Test that the weather API is called and data is populated."""
        quiz_id = weather_quiz_setup["quiz_id"]

        # Start quiz
        response = api_client.post(
            "/quiz/start_quiz",
            json={"token": weather_quiz_setup["token"], "user_id": "test_api_integration"},
            headers=user_headers
        )
        assert response.status_code == 200
        data = response.json()
        session_id = data["session_id"]

        # Submit any answer to see the results
        response = api_client.post(
            f"/quiz/submit_answer/{quiz_id}",
            json={
                "user_id": "test_api_integration",
                "session_id": session_id,
                "answer": {"answer": 10.0}
            },
            headers=user_headers
        )
        assert response.status_code == 200
        data = response.json()
        question_text = data["question"]["data"]["text"]

        # Verify mocked API data appears in results
        assert "Actual temperature:" in question_text
        assert "Wind speed:" in question_text
        assert "10.0" in question_text or "10" in question_text  # Mocked temperature
        assert "15.5" in question_text  # Mocked wind speed

        # Verify the mock was called
        assert mock_weather_api.called, "Weather API should have been called"

    def test_variable_substitution_in_results(
            self, api_client: TestClient, user_headers, weather_quiz_setup):
        """Test that variables are correctly substituted in question text."""
        # Start quiz
        response = api_client.post(
            "/quiz/start_quiz",
            json={"token": weather_quiz_setup["token"], "user_id": "test_substitution"},
            headers=user_headers
        )
        assert response.status_code == 200
        data = response.json()
        session_id = data["session_id"]
        quiz_id = data["quiz_id"]

        # Submit answer
        prediction = 5.5
        response = api_client.post(
            f"/quiz/submit_answer/{quiz_id}",
            json={
                "user_id": "test_substitution",
                "session_id": session_id,
                "answer": {"answer": prediction}
            },
            headers=user_headers
        )
        assert response.status_code == 200
        data = response.json()
        question_text = data["question"]["data"]["text"]

        # Check that user prediction appears
        assert f"{prediction}" in question_text or f"{int(prediction)}" in question_text

        # Check that no unreplaced placeholders remain
        assert "{variables." not in question_text, "All variable placeholders should be replaced"
        assert "{api." not in question_text, "All API placeholders should be replaced"

    def test_quiz_loop_try_again(
            self, api_client: TestClient, user_headers, weather_quiz_setup):
        """Test that users can try again and loop back to question 1."""
        # Start quiz
        response = api_client.post(
            "/quiz/start_quiz",
            json={"token": weather_quiz_setup["token"], "user_id": "test_loop"},
            headers=user_headers
        )
        assert response.status_code == 200
        data = response.json()
        session_id = data["session_id"]
        quiz_id = data["quiz_id"]

        # Answer question 1
        response = api_client.post(
            f"/quiz/submit_answer/{quiz_id}",
            json={
                "user_id": "test_loop",
                "session_id": session_id,
                "answer": {"answer": 10.0}
            },
            headers=user_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["question"]["id"] == 2  # Should be at results screen

        # Choose "yes" to try again
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
        assert data["question"]["id"] == 1  # Should loop back to question 1

    def test_final_message_auto_completion(
            self, api_client: TestClient, user_headers, weather_quiz_setup):
        """Test that choosing 'no' leads to final message and auto-completes."""
        # Start quiz
        response = api_client.post(
            "/quiz/start_quiz",
            json={"token": weather_quiz_setup["token"], "user_id": "test_final"},
            headers=user_headers
        )
        assert response.status_code == 200
        data = response.json()
        session_id = data["session_id"]
        quiz_id = data["quiz_id"]

        # Answer question 1
        response = api_client.post(
            f"/quiz/submit_answer/{quiz_id}",
            json={
                "user_id": "test_final",
                "session_id": session_id,
                "answer": {"answer": 10.0}
            },
            headers=user_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["question"]["id"] == 2

        # Choose "no" to finish
        response = api_client.post(
            f"/quiz/submit_answer/{quiz_id}",
            json={
                "user_id": "test_final",
                "session_id": session_id,
                "answer": {"answer": "no"}
            },
            headers=user_headers
        )
        assert response.status_code == 200
        data = response.json()

        # Should get final message (question 3)
        assert data["question"]["id"] == 3
        assert data["question"]["data"]["type"] == "final_message"
        assert "Thank you for playing!" in data["question"]["data"]["text"]

        # Session should be deleted (auto-completed)
        # Try to submit another answer - should fail
        response = api_client.post(
            f"/quiz/submit_answer/{quiz_id}",
            json={
                "user_id": "test_final",
                "session_id": session_id,
                "answer": {"answer": "done"}
            },
            headers=user_headers
        )
        assert response.status_code == 404
        assert "Session not found" in response.json()["detail"]

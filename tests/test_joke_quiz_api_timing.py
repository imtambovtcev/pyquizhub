"""
Tests for joke quiz API timing: static vs dynamic joke fetching.

This module tests two different API integration patterns:
1. STATIC: API called once at quiz start (same joke on loop)
2. DYNAMIC: API called before each question presentation (new joke each time)

These tests verify that the API timing configuration works correctly and that
new jokes are fetched when expected.
"""
import pytest
from unittest.mock import patch, Mock, call, AsyncMock
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


class TestStaticJokeQuiz:
    """Test quiz with API called once at start (timing: on_quiz_start)."""

    @pytest.fixture(scope="class")
    def static_joke_quiz(self):
        """Load the static joke quiz JSON."""
        import json
        with open("tests/test_quiz_jsons/joke_quiz_static_api.json") as f:
            return json.load(f)

    @pytest.fixture(scope="class")
    def static_quiz_setup(
            self,
            api_client: TestClient,
            admin_headers,
            static_joke_quiz):
        """Create static joke quiz and generate token."""
        # Create quiz
        response = api_client.post(
            "/admin/create_quiz",
            json={"quiz": static_joke_quiz, "creator_id": "admin"},
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

        return {"quiz_id": quiz_id, "token": token}

    def test_static_api_called_once_at_start(
            self,
            api_client: TestClient,
            user_headers,
            admin_headers,
            static_quiz_setup):
        """Test that API is called once at quiz start, then same joke is shown on loop."""

        # Mock the API to return a specific joke
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": 1,
            "type": "general",
            "setup": "First joke setup",
            "punchline": "First joke punchline"
        }

        # Mock httpx.AsyncClient context manager
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client.request = AsyncMock(return_value=mock_response)
        
        with patch('httpx.AsyncClient', return_value=mock_client) as mock_request:
            # Start quiz - API should be called ONCE
            response = api_client.post(
                "/quiz/start_quiz",
                json={
                    "token": static_quiz_setup["token"],
                    "user_id": "test_static"},
                headers=user_headers)
            assert response.status_code == 200
            data = response.json()
            session_id = data["session_id"]
            quiz_id = data["quiz_id"]

            # Verify first joke is shown
            question_text = data["question"]["data"]["text"]
            assert "First joke setup" in question_text
            assert "First joke punchline" in question_text

            # Verify API was called exactly ONCE
            assert mock_client.request.call_count == 1

            # Rate the joke
            response = api_client.post(
                f"/quiz/submit_answer/{quiz_id}",
                json={
                    "user_id": "test_static",
                    "session_id": session_id,
                    "answer": {"answer": 5}
                },
                headers=user_headers
            )
            assert response.status_code == 200

            # Choose "yes" to hear another joke
            response = api_client.post(
                f"/quiz/submit_answer/{quiz_id}",
                json={
                    "user_id": "test_static",
                    "session_id": session_id,
                    "answer": {"answer": "yes"}
                },
                headers=user_headers
            )
            assert response.status_code == 200
            data = response.json()

            # Should be back at question 1 with THE SAME JOKE
            assert data["question"]["id"] == 1
            question_text = data["question"]["data"]["text"]
            assert "First joke setup" in question_text
            assert "First joke punchline" in question_text

            # Verify API was still called only ONCE (not called again on loop)
            assert mock_client.request.call_count == 1


class TestDynamicJokeQuiz:
    """Test quiz with API called before each question (timing: before_question)."""

    @pytest.fixture(scope="class")
    def dynamic_joke_quiz(self):
        """Load the dynamic joke quiz JSON."""
        import json
        with open("tests/test_quiz_jsons/joke_quiz_dynamic_api.json") as f:
            return json.load(f)

    @pytest.fixture(scope="class")
    def dynamic_quiz_setup(
            self,
            api_client: TestClient,
            admin_headers,
            dynamic_joke_quiz):
        """Create dynamic joke quiz and generate token."""
        # Create quiz
        response = api_client.post(
            "/admin/create_quiz",
            json={"quiz": dynamic_joke_quiz, "creator_id": "admin"},
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

        return {"quiz_id": quiz_id, "token": token}

    def test_dynamic_api_called_before_each_question(
            self,
            api_client: TestClient,
            user_headers,
            admin_headers,
            dynamic_quiz_setup):
        """Test that API is called before EACH presentation of question 1 (new joke each loop)."""

        # Mock the API to return different jokes on each call
        joke_responses = [
            {
                "id": 1,
                "type": "general",
                "setup": "First joke setup",
                "punchline": "First joke punchline"
            },
            {
                "id": 2,
                "type": "general",
                "setup": "Second joke setup",
                "punchline": "Second joke punchline"
            },
            {
                "id": 3,
                "type": "general",
                "setup": "Third joke setup",
                "punchline": "Third joke punchline"
            }
        ]

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.side_effect = joke_responses

        # Mock httpx.AsyncClient context manager
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client.request = AsyncMock(return_value=mock_response)
        
        with patch('httpx.AsyncClient', return_value=mock_client) as mock_request:
            # Start quiz - API should be called for first joke
            response = api_client.post(
                "/quiz/start_quiz",
                json={
                    "token": dynamic_quiz_setup["token"],
                    "user_id": "test_dynamic"},
                headers=user_headers)
            assert response.status_code == 200
            data = response.json()
            session_id = data["session_id"]
            quiz_id = data["quiz_id"]

            # Verify FIRST joke is shown
            question_text = data["question"]["data"]["text"]
            assert "First joke setup" in question_text
            assert "First joke punchline" in question_text

            # API should have been called once
            assert mock_client.request.call_count == 1

            # Rate the first joke
            response = api_client.post(
                f"/quiz/submit_answer/{quiz_id}",
                json={
                    "user_id": "test_dynamic",
                    "session_id": session_id,
                    "answer": {"answer": 4}
                },
                headers=user_headers
            )
            assert response.status_code == 200

            # Choose "yes" to hear another joke
            response = api_client.post(
                f"/quiz/submit_answer/{quiz_id}",
                json={
                    "user_id": "test_dynamic",
                    "session_id": session_id,
                    "answer": {"answer": "yes"}
                },
                headers=user_headers
            )
            assert response.status_code == 200
            data = response.json()

            # Should be back at question 1 with a DIFFERENT JOKE
            assert data["question"]["id"] == 1
            question_text = data["question"]["data"]["text"]
            assert "Second joke setup" in question_text
            assert "Second joke punchline" in question_text

            # Verify the FIRST joke is NOT shown
            assert "First joke setup" not in question_text
            assert "First joke punchline" not in question_text

            # API should have been called TWICE now
            assert mock_client.request.call_count == 2

            # Rate the second joke and loop again
            response = api_client.post(
                f"/quiz/submit_answer/{quiz_id}",
                json={
                    "user_id": "test_dynamic",
                    "session_id": session_id,
                    "answer": {"answer": 5}
                },
                headers=user_headers
            )
            assert response.status_code == 200

            # Choose "yes" again
            response = api_client.post(
                f"/quiz/submit_answer/{quiz_id}",
                json={
                    "user_id": "test_dynamic",
                    "session_id": session_id,
                    "answer": {"answer": "yes"}
                },
                headers=user_headers
            )
            assert response.status_code == 200
            data = response.json()

            # Should show THIRD joke
            question_text = data["question"]["data"]["text"]
            assert "Third joke setup" in question_text
            assert "Third joke punchline" in question_text

            # Verify previous jokes are NOT shown
            assert "First joke" not in question_text
            assert "Second joke" not in question_text

            # API should have been called THREE times
            assert mock_client.request.call_count == 3

    def test_dynamic_api_only_called_for_question_1(
            self,
            api_client: TestClient,
            user_headers,
            admin_headers,
            dynamic_quiz_setup):
        """Test that API is NOT called for question 2 (only for question 1)."""

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": 1,
            "type": "general",
            "setup": "Test joke",
            "punchline": "Test punchline"
        }

        # Mock httpx.AsyncClient context manager
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client.request = AsyncMock(return_value=mock_response)
        
        with patch('httpx.AsyncClient', return_value=mock_client) as mock_request:
            # Start quiz
            response = api_client.post(
                "/quiz/start_quiz",
                json={
                    "token": dynamic_quiz_setup["token"],
                    "user_id": "test_q1_only"},
                headers=user_headers)
            data = response.json()
            session_id = data["session_id"]
            quiz_id = data["quiz_id"]

            # API called once for Q1
            assert mock_client.request.call_count == 1

            # Answer Q1
            response = api_client.post(
                f"/quiz/submit_answer/{quiz_id}",
                json={
                    "user_id": "test_q1_only",
                    "session_id": session_id,
                    "answer": {"answer": 3}
                },
                headers=user_headers
            )
            assert response.status_code == 200
            data = response.json()

            # Now at Q2 - API should still be called only once (not for Q2)
            assert data["question"]["id"] == 2
            assert mock_client.request.call_count == 1

"""
Tests for External API Integration functionality.

Tests cover:
- Successful API calls at different timings
- Various authentication methods
- Error handling (timeouts, network errors, invalid responses)
- OAuth2 token refresh
- Template variable substitution
- Response data extraction
- Session state management
- Retry logic
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import requests
from datetime import datetime, timedelta
from pyquizhub.core.engine.api_integration import (
    APIIntegrationManager,
    AuthType,
    RequestTiming
)


class TestAPIIntegrationManager:
    """Test suite for API Integration Manager."""

    @pytest.fixture
    def api_manager(self):
        """Create an API integration manager instance."""
        return APIIntegrationManager()

    @pytest.fixture
    def session_state(self):
        """Create a basic session state."""
        return {
            "current_question_id": 1,
            "scores": {"correct": 0},
            "answers": [],
            "completed": False,
            "api_data": {},
            "api_credentials": {}
        }

    def test_simple_get_request(self, api_manager, session_state):
        """Test a simple GET request with no authentication."""
        api_config = {
            "id": "test_api",
            "url": "https://api.example.com/data",
            "method": "GET",
            "auth": {"type": "none"}
        }

        with patch('requests.request') as mock_request:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"value": 42}
            mock_request.return_value = mock_response

            result_state = api_manager.execute_api_call(
                api_config,
                session_state,
                {}
            )

            # Verify API was called
            mock_request.assert_called_once()
            assert mock_request.call_args[1]['method'] == 'GET'
            assert mock_request.call_args[1]['url'] == 'https://api.example.com/data'

            # Verify state was updated
            assert "test_api" in result_state["api_data"]
            assert result_state["api_data"]["test_api"]["success"] is True
            assert result_state["api_data"]["test_api"]["response"] == {
                "value": 42}

    def test_api_key_authentication(self, api_manager, session_state):
        """Test API key authentication in headers."""
        api_config = {
            "id": "test_api",
            "url": "https://api.example.com/data",
            "method": "GET",
            "auth": {
                "type": "api_key",
                "key_name": "X-API-Key",
                "credential": "secret-key-123"
            }
        }

        with patch('requests.request') as mock_request:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"success": True}
            mock_request.return_value = mock_response

            api_manager.execute_api_call(api_config, session_state, {})

            # Verify API key was added to headers
            headers = mock_request.call_args[1]['headers']
            assert headers['X-API-Key'] == 'secret-key-123'

    def test_bearer_token_authentication(self, api_manager, session_state):
        """Test Bearer token authentication."""
        api_config = {
            "id": "test_api",
            "url": "https://api.example.com/data",
            "method": "GET",
            "auth": {
                "type": "bearer",
                "credential": "bearer-token-xyz"
            }
        }

        with patch('requests.request') as mock_request:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"success": True}
            mock_request.return_value = mock_response

            api_manager.execute_api_call(api_config, session_state, {})

            # Verify Bearer token was added
            headers = mock_request.call_args[1]['headers']
            assert headers['Authorization'] == 'Bearer bearer-token-xyz'

    def test_basic_authentication(self, api_manager, session_state):
        """Test Basic authentication."""
        api_config = {
            "id": "test_api",
            "url": "https://api.example.com/data",
            "method": "GET",
            "auth": {
                "type": "basic",
                "username": "user123",
                "credential": "pass456"
            }
        }

        with patch('requests.request') as mock_request:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"success": True}
            mock_request.return_value = mock_response

            api_manager.execute_api_call(api_config, session_state, {})

            # Verify Basic auth header
            headers = mock_request.call_args[1]['headers']
            assert 'Authorization' in headers
            assert headers['Authorization'].startswith('Basic ')

    def test_template_variable_substitution(self, api_manager, session_state):
        """Test template variable substitution in URL and body."""
        api_config = {
            "id": "test_api",
            "method": "POST",
            "prepare_request": {
                "url_template": "https://api.example.com/users/{user_id}/score",
                "body_template": {
                    "answer": "{answer}",
                    "score": "{correct}"}},
            "auth": {
                "type": "none"}}

        context = {
            "user_id": "42",
            "answer": "Paris",
            "correct": 5
        }

        with patch('requests.request') as mock_request:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"success": True}
            mock_request.return_value = mock_response

            api_manager.execute_api_call(api_config, session_state, context)

            # Verify URL was rendered
            assert mock_request.call_args[1]['url'] == 'https://api.example.com/users/42/score'

            # Verify body was rendered
            body = mock_request.call_args[1]['json']
            assert body['answer'] == 'Paris'
            assert body['score'] == '5'

    def test_response_path_extraction(self, api_manager, session_state):
        """Test JSONPath-like extraction from API response."""
        api_config = {
            "id": "weather",
            "url": "https://api.weather.com/current",
            "method": "GET",
            "auth": {"type": "none"},
            "extract_response": {
                "variables": {
                    "temperature": {
                        "path": "data.temperature",
                        "type": "float"
                    }
                }
            }
        }

        with patch('requests.request') as mock_request:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "data": {
                    "temperature": 22.5,
                    "humidity": 65
                },
                "status": "ok"
            }
            mock_request.return_value = mock_response

            result_state = api_manager.execute_api_call(
                api_config,
                session_state,
                {}
            )

            # Verify extracted value is stored in scores
            assert result_state["scores"]["temperature"] == 22.5
            # And also available in api_data
            assert result_state["api_data"]["weather"]["response"]["temperature"] == 22.5

    def test_network_error_handling(self, api_manager, session_state):
        """Test handling of network errors."""
        api_config = {
            "id": "test_api",
            "url": "https://api.example.com/data",
            "method": "GET",
            "auth": {"type": "none"}
        }

        with patch('requests.request') as mock_request:
            # Simulate network error
            mock_request.side_effect = requests.ConnectionError(
                "Network error")

            result_state = api_manager.execute_api_call(
                api_config,
                session_state,
                {}
            )

            # Verify error was recorded
            assert "test_api" in result_state["api_data"]
            assert result_state["api_data"]["test_api"]["success"] is False
            assert "error" in result_state["api_data"]["test_api"]
            assert "Network error" in result_state["api_data"]["test_api"]["error"]

    def test_timeout_error_handling(self, api_manager, session_state):
        """Test handling of timeout errors."""
        api_config = {
            "id": "test_api",
            "url": "https://api.example.com/slow",
            "method": "GET",
            "auth": {"type": "none"},
            "timeout": 1
        }

        with patch('requests.request') as mock_request:
            # Simulate timeout
            mock_request.side_effect = requests.Timeout("Request timed out")

            result_state = api_manager.execute_api_call(
                api_config,
                session_state,
                {}
            )

            # Verify timeout was recorded
            assert result_state["api_data"]["test_api"]["success"] is False
            assert "timed out" in result_state["api_data"]["test_api"]["error"].lower(
            )

    def test_http_error_handling(self, api_manager, session_state):
        """Test handling of HTTP errors (4xx, 5xx)."""
        api_config = {
            "id": "test_api",
            "url": "https://api.example.com/data",
            "method": "GET",
            "auth": {"type": "none"}
        }

        with patch('requests.request') as mock_request:
            mock_response = Mock()
            mock_response.status_code = 500
            mock_response.raise_for_status.side_effect = requests.HTTPError(
                "500 Server Error")
            mock_request.return_value = mock_response

            result_state = api_manager.execute_api_call(
                api_config,
                session_state,
                {}
            )

            # Verify error was recorded
            assert result_state["api_data"]["test_api"]["success"] is False

    def test_retry_logic_success_after_retry(self, api_manager, session_state):
        """Test retry logic succeeds after initial failures."""
        api_config = {
            "id": "test_api",
            "url": "https://api.example.com/data",
            "method": "GET",
            "auth": {"type": "none"}
        }

        with patch('requests.request') as mock_request:
            # Fail twice, then succeed
            mock_response_success = Mock()
            mock_response_success.status_code = 200
            mock_response_success.json.return_value = {"value": 42}

            mock_request.side_effect = [
                requests.ConnectionError("Error 1"),
                requests.ConnectionError("Error 2"),
                mock_response_success
            ]

            result_state = api_manager.execute_api_call(
                api_config,
                session_state,
                {}
            )

            # Verify it succeeded after retries
            assert result_state["api_data"]["test_api"]["success"] is True
            assert result_state["api_data"]["test_api"]["response"] == {
                "value": 42}
            assert mock_request.call_count == 3

    def test_retry_logic_max_retries_exceeded(
            self, api_manager, session_state):
        """Test retry logic fails after max retries."""
        api_config = {
            "id": "test_api",
            "url": "https://api.example.com/data",
            "method": "GET",
            "auth": {"type": "none"}
        }

        with patch('requests.request') as mock_request:
            # Always fail
            mock_request.side_effect = requests.ConnectionError(
                "Persistent error")

            result_state = api_manager.execute_api_call(
                api_config,
                session_state,
                {}
            )

            # Verify it failed after max retries
            assert result_state["api_data"]["test_api"]["success"] is False
            assert mock_request.call_count == 3  # max_retries

    def test_oauth2_token_refresh(self, api_manager, session_state):
        """Test OAuth2 token refresh when expired."""
        # Set up expired token in session
        session_state["api_credentials"]["oauth_api"] = {
            "token": "old_token",
            "expires_at": (datetime.now() - timedelta(minutes=10)).isoformat()
        }

        api_config = {
            "id": "test_api",
            "url": "https://api.example.com/data",
            "method": "GET",
            "auth": {
                "type": "oauth2",
                "id": "oauth_api",
                "token_url": "https://oauth.example.com/token",
                "client_id": "client123",
                "client_secret": "secret456",
                "refresh_token": "refresh789"
            }
        }

        with patch('requests.request') as mock_request, \
                patch('requests.post') as mock_post:

            # Mock token refresh
            mock_token_response = Mock()
            mock_token_response.status_code = 200
            mock_token_response.json.return_value = {
                "access_token": "new_token",
                "expires_in": 3600
            }
            mock_post.return_value = mock_token_response

            # Mock API call
            mock_api_response = Mock()
            mock_api_response.status_code = 200
            mock_api_response.json.return_value = {"success": True}
            mock_request.return_value = mock_api_response

            result_state = api_manager.execute_api_call(
                api_config,
                session_state,
                {}
            )

            # Verify token was refreshed
            mock_post.assert_called_once()
            assert "oauth_api" in result_state["api_credentials"]
            assert result_state["api_credentials"]["oauth_api"]["token"] == "new_token"

    def test_get_api_data(self, api_manager, session_state):
        """Test retrieving API data from session state."""
        session_state["api_data"]["test"] = {
            "response": {"temperature": 22.5},
            "success": True
        }

        # Test successful retrieval
        data = api_manager.get_api_data(session_state, "test")
        assert data == {"temperature": 22.5}

        # Test missing data
        data = api_manager.get_api_data(session_state, "missing", default=None)
        assert data is None

        # Test failed API call
        session_state["api_data"]["failed"] = {
            "error": "Network error",
            "success": False
        }
        data = api_manager.get_api_data(
            session_state, "failed", default="default")
        assert data == "default"

    def test_post_request_with_body(self, api_manager, session_state):
        """Test POST request with JSON body."""
        api_config = {
            "id": "test_api",
            "url": "https://api.example.com/submit",
            "method": "POST",
            "auth": {"type": "none"},
            "prepare_request": {
                "body_template": {
                    "user": "test_user",
                    "value": 42
                }
            }
        }

        with patch('requests.request') as mock_request:
            mock_response = Mock()
            mock_response.status_code = 201
            mock_response.json.return_value = {"created": True}
            mock_request.return_value = mock_response

            result_state = api_manager.execute_api_call(
                api_config,
                session_state,
                {}
            )

            # Verify POST was called with body
            assert mock_request.call_args[1]['method'] == 'POST'
            assert mock_request.call_args[1]['json'] == {
                "user": "test_user", "value": 42}
            assert result_state["api_data"]["test_api"]["status_code"] == 201

    def test_array_index_in_response_path(self, api_manager, session_state):
        """Test array indexing in response path."""
        api_config = {
            "id": "test_api",
            "url": "https://api.example.com/list",
            "method": "GET",
            "auth": {"type": "none"},
            "extract_response": {
                "variables": {
                    "first_value": {
                        "path": "results[0].value",
                        "type": "integer"
                    }
                }
            }
        }

        with patch('requests.request') as mock_request:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "results": [
                    {"value": 123, "name": "first"},
                    {"value": 456, "name": "second"}
                ]
            }
            mock_request.return_value = mock_response

            result_state = api_manager.execute_api_call(
                api_config,
                session_state,
                {}
            )

            # Verify array indexing worked and value is in scores
            assert result_state["scores"]["first_value"] == 123

    def test_malformed_json_response(self, api_manager, session_state):
        """Test handling of malformed JSON responses."""
        api_config = {
            "id": "test_api",
            "url": "https://api.example.com/data",
            "method": "GET",
            "auth": {"type": "none"}
        }

        with patch('requests.request') as mock_request:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.side_effect = ValueError("Invalid JSON")
            mock_request.return_value = mock_response

            result_state = api_manager.execute_api_call(
                api_config,
                session_state,
                {}
            )

            # Verify error was recorded
            assert result_state["api_data"]["test_api"]["success"] is False
            assert "error" in result_state["api_data"]["test_api"]

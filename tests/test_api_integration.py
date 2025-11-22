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
from unittest.mock import Mock, patch, MagicMock, AsyncMock
import httpx
from datetime import datetime, timedelta
from pyquizhub.core.engine.api_integration import (
    APIIntegrationManager,
    AuthType,
    RequestTiming
)


def create_mock_httpx_client(mock_response):
    """Helper to create a properly mocked httpx.AsyncClient."""
    mock_client = AsyncMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None
    mock_client.request = AsyncMock(return_value=mock_response)
    return mock_client


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

    async def test_simple_get_request(self, api_manager, session_state):
        """Test a simple GET request with no authentication."""
        api_config = {
            "id": "test_api",
            "url": "https://api.example.com/data",
            "method": "GET",
            "auth": {"type": "none"}
        }

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"value": 42}

        mock_client = create_mock_httpx_client(mock_response)

        with patch('httpx.AsyncClient', return_value=mock_client):
            result_state = await api_manager.execute_api_call(
                api_config,
                session_state,
                {}
            )

            # Verify API was called
            mock_client.request.assert_called_once()
            call_kwargs = mock_client.request.call_args[1]
            assert call_kwargs['method'] == 'GET'
            assert call_kwargs['url'] == 'https://api.example.com/data'

            # Verify state was updated
            assert "test_api" in result_state["api_data"]
            assert result_state["api_data"]["test_api"]["success"] is True
            assert result_state["api_data"]["test_api"]["response"] == {
                "value": 42}

    async def test_api_key_authentication(self, api_manager, session_state):
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

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"success": True}

        mock_client = create_mock_httpx_client(mock_response)

        with patch('httpx.AsyncClient', return_value=mock_client):
            await api_manager.execute_api_call(api_config, session_state, {})

            # Verify API key was added to headers
            headers = mock_client.request.call_args[1]['headers']
            assert headers['X-API-Key'] == 'secret-key-123'

    async def test_bearer_token_authentication(self, api_manager, session_state):
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

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"success": True}

        mock_client = create_mock_httpx_client(mock_response)

        with patch('httpx.AsyncClient', return_value=mock_client):
            await api_manager.execute_api_call(api_config, session_state, {})

            # Verify Bearer token was added
            headers = mock_client.request.call_args[1]['headers']
            assert headers['Authorization'] == 'Bearer bearer-token-xyz'

    async def test_basic_authentication(self, api_manager, session_state):
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

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"success": True}

        mock_client = create_mock_httpx_client(mock_response)

        with patch('httpx.AsyncClient', return_value=mock_client):
            await api_manager.execute_api_call(api_config, session_state, {})

            # Verify Basic auth header
            headers = mock_client.request.call_args[1]['headers']
            assert 'Authorization' in headers
            assert headers['Authorization'].startswith('Basic ')

    async def test_template_variable_substitution(self, api_manager, session_state):
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

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"success": True}

        mock_client = create_mock_httpx_client(mock_response)

        with patch('httpx.AsyncClient', return_value=mock_client):
            await api_manager.execute_api_call(api_config, session_state, context)

            # Verify URL was rendered
            assert mock_client.request.call_args[1]['url'] == 'https://api.example.com/users/42/score'

            # Verify body was rendered
            body = mock_client.request.call_args[1]['json']
            assert body['answer'] == 'Paris'
            assert body['score'] == '5'

    async def test_response_path_extraction(self, api_manager, session_state):
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

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": {
                "temperature": 22.5,
                "humidity": 65
            },
            "status": "ok"
        }

        mock_client = create_mock_httpx_client(mock_response)

        with patch('httpx.AsyncClient', return_value=mock_client):
            result_state = await api_manager.execute_api_call(
                api_config,
                session_state,
                {}
            )

            # Verify extracted value is stored in scores
            assert result_state["scores"]["temperature"] == 22.5

    async def test_network_error_handling(self, api_manager, session_state):
        """Test handling of network errors (connection refused, etc)."""
        api_config = {
            "id": "test_api",
            "url": "https://api.example.com/data",
            "method": "GET",
            "auth": {"type": "none"}
        }

        # Mock httpx.AsyncClient to raise ConnectError
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client.request = AsyncMock(side_effect=httpx.ConnectError(
            "Network error"))

        with patch('httpx.AsyncClient', return_value=mock_client):
            result_state = await api_manager.execute_api_call(
                api_config,
                session_state,
                {}
            )

            # Verify error was recorded
            assert result_state["api_data"]["test_api"]["success"] is False
            assert "error" in result_state["api_data"]["test_api"]

    async def test_timeout_handling(self, api_manager, session_state):
        """Test handling of request timeouts."""
        api_config = {
            "id": "test_api",
            "url": "https://api.example.com/data",
            "method": "GET",
            "auth": {"type": "none"}
        }

        # Mock httpx.AsyncClient to raise TimeoutException
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client.request = AsyncMock(side_effect=httpx.TimeoutException("Request timed out"))

        with patch('httpx.AsyncClient', return_value=mock_client):
            result_state = await api_manager.execute_api_call(
                api_config,
                session_state,
                {}
            )

            # Verify timeout was recorded
            assert result_state["api_data"]["test_api"]["success"] is False

    async def test_http_error_handling(self, api_manager, session_state):
        """Test handling of HTTP errors (4xx, 5xx)."""
        api_config = {
            "id": "test_api",
            "url": "https://api.example.com/data",
            "method": "GET",
            "auth": {"type": "none"}
        }

        mock_response = Mock()
        mock_response.status_code = 500
        # Create proper HTTPStatusError with required arguments
        mock_request = Mock()
        mock_response.raise_for_status = Mock(side_effect=httpx.HTTPStatusError(
            "500 Server Error",
            request=mock_request,
            response=mock_response
        ))

        mock_client = create_mock_httpx_client(mock_response)

        with patch('httpx.AsyncClient', return_value=mock_client):
            result_state = await api_manager.execute_api_call(
                api_config,
                session_state,
                {}
            )

            # Verify error was recorded
            assert result_state["api_data"]["test_api"]["success"] is False

    async def test_retry_logic_success_after_retry(self, api_manager, session_state):
        """Test retry logic succeeds after initial failures."""
        api_config = {
            "id": "test_api",
            "url": "https://api.example.com/data",
            "method": "GET",
            "auth": {"type": "none"}
        }

        # Fail twice, then succeed
        mock_response_success = Mock()
        mock_response_success.status_code = 200
        mock_response_success.json.return_value = {"value": 42}

        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        # Fail twice, then succeed
        mock_client.request = AsyncMock(side_effect=[
            httpx.ConnectError("Error 1"),
            httpx.ConnectError("Error 2"),
            mock_response_success
        ])

        with patch('httpx.AsyncClient', return_value=mock_client):
            result_state = await api_manager.execute_api_call(
                api_config,
                session_state,
                {}
            )

            # Verify it succeeded after retries
            assert result_state["api_data"]["test_api"]["success"] is True
            assert result_state["api_data"]["test_api"]["response"] == {
                "value": 42}
            assert mock_client.request.call_count == 3

    async def test_retry_logic_max_retries_exceeded(
            self, api_manager, session_state):
        """Test retry logic fails after max retries."""
        api_config = {
            "id": "test_api",
            "url": "https://api.example.com/data",
            "method": "GET",
            "auth": {"type": "none"}
        }

        # Always fail
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client.request = AsyncMock(side_effect=httpx.ConnectError(
            "Persistent error"))

        with patch('httpx.AsyncClient', return_value=mock_client):
            result_state = await api_manager.execute_api_call(
                api_config,
                session_state,
                {}
            )

            # Verify it failed after max retries
            assert result_state["api_data"]["test_api"]["success"] is False
            assert mock_client.request.call_count == 3  # max_retries

    async def test_oauth2_token_refresh(self, api_manager, session_state):
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

        # Mock token refresh
        mock_token_response = Mock()
        mock_token_response.status_code = 200
        mock_token_response.json.return_value = {
            "access_token": "new_token",
            "expires_in": 3600
        }

        # Mock API call
        mock_api_response = Mock()
        mock_api_response.status_code = 200
        mock_api_response.json.return_value = {"success": True}

        # Create mock clients
        mock_token_client = AsyncMock()
        mock_token_client.__aenter__.return_value = mock_token_client
        mock_token_client.__aexit__.return_value = None
        mock_token_client.post = AsyncMock(return_value=mock_token_response)

        mock_api_client = create_mock_httpx_client(mock_api_response)

        with patch('httpx.AsyncClient', side_effect=[mock_token_client, mock_api_client]):
            result_state = await api_manager.execute_api_call(
                api_config,
                session_state,
                {}
            )

            # Verify token was refreshed
            assert mock_token_client.post.called
            # Verify new token was stored
            assert result_state["api_credentials"]["oauth_api"]["token"] == "new_token"

    async def test_post_request_with_body(self, api_manager, session_state):
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

        mock_response = Mock()
        mock_response.status_code = 201
        mock_response.json.return_value = {"created": True}

        mock_client = create_mock_httpx_client(mock_response)

        with patch('httpx.AsyncClient', return_value=mock_client):
            result_state = await api_manager.execute_api_call(
                api_config,
                session_state,
                {}
            )

            # Verify POST was called with body
            assert mock_client.request.call_args[1]['method'] == 'POST'
            assert mock_client.request.call_args[1]['json'] == {
                "user": "test_user", "value": 42}
            assert result_state["api_data"]["test_api"]["status_code"] == 201

    async def test_array_index_in_response_path(self, api_manager, session_state):
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

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "results": [
                {"value": 123, "name": "first"},
                {"value": 456, "name": "second"}
            ]
        }

        mock_client = create_mock_httpx_client(mock_response)

        with patch('httpx.AsyncClient', return_value=mock_client):
            result_state = await api_manager.execute_api_call(
                api_config,
                session_state,
                {}
            )

            # Verify array indexing worked and value is in scores
            assert result_state["scores"]["first_value"] == 123

    async def test_malformed_json_response(self, api_manager, session_state):
        """Test handling of malformed JSON responses."""
        api_config = {
            "id": "test_api",
            "url": "https://api.example.com/data",
            "method": "GET",
            "auth": {"type": "none"}
        }

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.side_effect = ValueError("Invalid JSON")

        mock_client = create_mock_httpx_client(mock_response)

        with patch('httpx.AsyncClient', return_value=mock_client):
            result_state = await api_manager.execute_api_call(
                api_config,
                session_state,
                {}
            )

            # Verify error was recorded
            assert result_state["api_data"]["test_api"]["success"] is False

    async def test_file_upload_with_custom_field_name(self, api_manager, session_state):
        """Test file upload with custom field name."""
        from pyquizhub.core.engine.api_integration import FileUploadMarker

        api_config = {
            "id": "test_api",
            "url": "https://api.example.com/upload",
            "method": "POST",
            "auth": {"type": "none"},
            "prepare_request": {
                "file_field_name": "document"  # Custom field name
            }
        }

        # Create a FileUploadMarker
        file_marker = FileUploadMarker(
            filename="test.pdf",
            file_data=b"test file content",
            mime_type="application/pdf"
        )

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"uploaded": True}

        mock_client = create_mock_httpx_client(mock_response)

        # Mock _prepare_body to return the file marker
        with patch.object(api_manager, '_prepare_body', return_value=file_marker):
            with patch('httpx.AsyncClient', return_value=mock_client):
                result_state = await api_manager.execute_api_call(
                    api_config,
                    session_state,
                    {}
                )

                # Verify file was uploaded with custom field name
                assert mock_client.request.called
                call_kwargs = mock_client.request.call_args[1]
                assert 'files' in call_kwargs
                assert 'document' in call_kwargs['files']  # Custom field name
                assert call_kwargs['files']['document'][0] == 'test.pdf'
                assert call_kwargs['files']['document'][1] == b"test file content"
                assert call_kwargs['files']['document'][2] == 'application/pdf'

    async def test_file_upload_default_field_name(self, api_manager, session_state):
        """Test file upload with default field name when not specified."""
        from pyquizhub.core.engine.api_integration import FileUploadMarker

        api_config = {
            "id": "test_api",
            "url": "https://api.example.com/upload",
            "method": "POST",
            "auth": {"type": "none"}
            # No prepare_request.file_field_name specified
        }

        file_marker = FileUploadMarker(
            filename="image.png",
            file_data=b"image data",
            mime_type="image/png"
        )

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"uploaded": True}

        mock_client = create_mock_httpx_client(mock_response)

        with patch.object(api_manager, '_prepare_body', return_value=file_marker):
            with patch('httpx.AsyncClient', return_value=mock_client):
                result_state = await api_manager.execute_api_call(
                    api_config,
                    session_state,
                    {}
                )

                # Verify file was uploaded with default field name 'file'
                assert mock_client.request.called
                call_kwargs = mock_client.request.call_args[1]
                assert 'files' in call_kwargs
                assert 'file' in call_kwargs['files']  # Default field name
                assert call_kwargs['files']['file'][0] == 'image.png'

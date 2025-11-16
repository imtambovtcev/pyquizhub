"""
External API Integration for Quiz Questions.

This module provides functionality to integrate external APIs into quiz logic:
- Make HTTP requests (GET, POST, PUT, DELETE, PATCH)
- Handle authentication (API keys, Bearer tokens, Basic auth, OAuth)
- Store API state in session data (stateless architecture)
- Use API responses in questions and validations
- Support request timing (before/after questions)

Design Principles:
- Stateless: All API state stored in session data
- Secure: API credentials encrypted/protected
- Flexible: Support various REST API patterns
- Resilient: Handle timeouts, errors, retries
"""

from __future__ import annotations

import requests
import json
from typing import Any
from datetime import datetime, timedelta
from enum import Enum
from pyquizhub.logging.setup import get_logger


class AuthType(str, Enum):
    """Supported authentication types."""
    NONE = "none"
    API_KEY = "api_key"
    BEARER = "bearer"
    BASIC = "basic"
    OAUTH2 = "oauth2"


class RequestTiming(str, Enum):
    """When to execute API requests."""
    BEFORE_QUESTION = "before_question"
    AFTER_ANSWER = "after_answer"
    ON_QUIZ_START = "on_quiz_start"
    ON_QUIZ_END = "on_quiz_end"


class APIIntegrationManager:
    """
    Manages external API integrations for quizzes.

    Handles:
    - HTTP requests to external APIs
    - Authentication and token management
    - Response caching and state management
    - Error handling and retries

    All API state is stored in the session data to maintain statelessness.
    """

    def __init__(self):
        """Initialize the API integration manager."""
        self.logger = get_logger(__name__)
        self.default_timeout = 10  # seconds
        self.max_retries = 3

    def execute_api_call(
        self,
        api_config: dict[str, Any],
        session_state: dict[str, Any],
        context: dict[str, Any | None] = None
    ) -> dict[str, Any]:
        """
        Execute an API call and return updated session state.

        Args:
            api_config: API configuration containing:
                - id: API identifier
                - method: HTTP method (GET, POST, etc.)
                - url: Fixed URL OR prepare_request with url_template
                - extract_response: Variable extraction configuration
                - auth/authentication: Authentication configuration
            session_state: Current session state (contains api_data and scores)
            context: Additional context (scores, answer, question_id, etc.)

        Returns:
            Updated session state with API response data and extracted variables
        """
        # Initialize API data in session if not exists
        if "api_data" not in session_state:
            session_state["api_data"] = {}

        api_id = api_config.get("id", "default")

        try:
            # Prepare request URL (new format: url or
            # prepare_request.url_template)
            url = self._prepare_url(api_config, context or {})
            method = api_config.get("method", "GET").upper()
            headers = self._prepare_headers(api_config, session_state)
            body = self._prepare_body(api_config, context or {})

            # Check if we need to refresh auth token
            self._refresh_auth_if_needed(api_config, session_state)

            # Make request
            self.logger.info(f"Making {method} request to {url}")
            response = self._make_request(
                method=method,
                url=url,
                headers=headers,
                body=body,
                timeout=api_config.get("timeout", self.default_timeout)
            )

            # Process response and extract variables into
            # session_state["scores"]
            response_data = self._process_response(
                response, api_config, session_state)

            # Store raw response in api_data for debugging/logging
            session_state["api_data"][api_id] = {
                "response": response_data,
                "timestamp": datetime.now().isoformat(),
                "status_code": response.status_code,
                "success": True
            }

            self.logger.info(f"API call {api_id} completed successfully")

        except Exception as e:
            self.logger.error(f"API call {api_id} failed: {e}")
            session_state["api_data"][api_id] = {
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
                "success": False
            }

        return session_state

    def _prepare_url(
        self,
        api_config: dict[str, Any],
        context: dict[str, Any]
    ) -> str:
        """
        Prepare request URL from either fixed url or prepare_request.url_template.

        Args:
            api_config: API configuration
            context: Context with variables for template rendering

        Returns:
            Prepared URL string
        """
        # Check for prepare_request block (new format)
        if "prepare_request" in api_config:
            prepare_request = api_config["prepare_request"]
            if "url_template" in prepare_request:
                url_template = prepare_request["url_template"]
                return self._render_template(url_template, context)

        # Check for fixed url field (both old and new format)
        if "url" in api_config:
            return api_config["url"]

        raise ValueError(
            "API configuration must have either 'url' or 'prepare_request.url_template'")

    def _prepare_headers(
        self,
        api_config: dict[str, Any],
        session_state: dict[str, Any]
    ) -> dict[str, str]:
        """
        Prepare HTTP headers including authentication.

        Args:
            api_config: API configuration
            session_state: Current session state

        Returns:
            Headers dictionary
        """
        headers = api_config.get("headers", {}).copy()
        auth_config = api_config.get("auth", {})
        auth_type = AuthType(auth_config.get("type", "none"))

        if auth_type == AuthType.API_KEY:
            # API key in header
            key_name = auth_config.get("key_name", "X-API-Key")
            api_key = self._get_api_credential(auth_config, session_state)
            headers[key_name] = api_key

        elif auth_type == AuthType.BEARER:
            # Bearer token
            token = self._get_api_credential(auth_config, session_state)
            headers["Authorization"] = f"Bearer {token}"

        elif auth_type == AuthType.BASIC:
            # Basic auth
            import base64
            username = auth_config.get("username", "")
            password = self._get_api_credential(auth_config, session_state)
            credentials = base64.b64encode(
                f"{username}:{password}".encode()
            ).decode()
            headers["Authorization"] = f"Basic {credentials}"

        return headers

    def _get_api_credential(
        self,
        auth_config: dict[str, Any],
        session_state: dict[str, Any]
    ) -> str:
        """
        Get API credential from config or session state.

        For OAuth2, this might be a token stored in session.
        For API keys, this comes from config (should be encrypted).

        Args:
            auth_config: Authentication configuration
            session_state: Current session state

        Returns:
            API credential string
        """
        # Check if credential is in session state (for dynamic tokens)
        api_id = auth_config.get("id", "default")
        if "api_credentials" in session_state:
            if api_id in session_state["api_credentials"]:
                cred = session_state["api_credentials"][api_id]
                # Check if token is expired
                if "expires_at" in cred:
                    expires_at = datetime.fromisoformat(cred["expires_at"])
                    if datetime.now() < expires_at:
                        return cred["token"]

        # Otherwise, use credential from config
        return auth_config.get("credential", "")

    def _refresh_auth_if_needed(
        self,
        api_config: dict[str, Any],
        session_state: dict[str, Any]
    ) -> None:
        """
        Refresh OAuth2 token if needed.

        Args:
            api_config: API configuration
            session_state: Current session state (will be modified)
        """
        auth_config = api_config.get("auth", {})
        auth_type = AuthType(auth_config.get("type", "none"))

        if auth_type == AuthType.OAUTH2:
            api_id = auth_config.get("id", "default")

            # Check if token exists and is expired
            needs_refresh = True
            if "api_credentials" in session_state:
                if api_id in session_state["api_credentials"]:
                    cred = session_state["api_credentials"][api_id]
                    if "expires_at" in cred:
                        expires_at = datetime.fromisoformat(cred["expires_at"])
                        # Refresh 5 minutes before expiry
                        if datetime.now() < (expires_at - timedelta(minutes=5)):
                            needs_refresh = False

            if needs_refresh:
                self._refresh_oauth_token(auth_config, session_state)

    def _refresh_oauth_token(
        self,
        auth_config: dict[str, Any],
        session_state: dict[str, Any]
    ) -> None:
        """
        Refresh OAuth2 access token.

        Args:
            auth_config: OAuth configuration
            session_state: Session state (will be modified with new token)
        """
        token_url = auth_config.get("token_url")
        client_id = auth_config.get("client_id")
        client_secret = auth_config.get("client_secret")
        refresh_token = auth_config.get("refresh_token")

        response = requests.post(
            token_url,
            data={
                "grant_type": "refresh_token",
                "client_id": client_id,
                "client_secret": client_secret,
                "refresh_token": refresh_token
            }
        )

        if response.status_code == 200:
            token_data = response.json()
            api_id = auth_config.get("id", "default")

            if "api_credentials" not in session_state:
                session_state["api_credentials"] = {}

            expires_in = token_data.get("expires_in", 3600)
            session_state["api_credentials"][api_id] = {
                "token": token_data["access_token"],
                "expires_at": (
                    datetime.now() + timedelta(seconds=expires_in)
                ).isoformat()
            }

            self.logger.info(f"Refreshed OAuth token for {api_id}")

    def _prepare_body(
        self,
        api_config: dict[str, Any],
        context: dict[str, Any]
    ) -> dict[str, Any | None]:
        """
        Prepare request body from prepare_request.body_template.

        Args:
            api_config: API configuration containing prepare_request with body_template
            context: Context data for template rendering

        Returns:
            Request body dictionary or None
        """
        # Check for prepare_request.body_template (new format)
        if "prepare_request" in api_config:
            prepare_request = api_config["prepare_request"]
            if "body_template" in prepare_request:
                body_template = prepare_request["body_template"]
                # Render template with context
                if isinstance(body_template, dict):
                    return self._render_dict_template(body_template, context)
                elif isinstance(body_template, str):
                    rendered = self._render_template(body_template, context)
                    return json.loads(rendered)

        return None

    def _render_template(self, template: str, context: dict[str, Any]) -> str:
        """
        Render a string template with context variables.

        Supports: {variable_name} syntax

        Args:
            template: Template string
            context: Context variables

        Returns:
            Rendered string
        """
        result = template
        for key, value in context.items():
            placeholder = "{" + key + "}"
            if placeholder in result:
                result = result.replace(placeholder, str(value))
        return result

    def _render_dict_template(
        self,
        template: dict[str, Any],
        context: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Recursively render dictionary template.

        Args:
            template: Template dictionary
            context: Context variables

        Returns:
            Rendered dictionary
        """
        result = {}
        for key, value in template.items():
            if isinstance(value, str):
                result[key] = self._render_template(value, context)
            elif isinstance(value, dict):
                result[key] = self._render_dict_template(value, context)
            elif isinstance(value, list):
                result[key] = [
                    self._render_template(item, context)
                    if isinstance(item, str) else item
                    for item in value
                ]
            else:
                result[key] = value
        return result

    def _make_request(
        self,
        method: str,
        url: str,
        headers: dict[str, str],
        body: dict[str, Any | None],
        timeout: int
    ) -> requests.Response:
        """
        Make HTTP request with retry logic.

        Args:
            method: HTTP method
            url: Request URL
            headers: Request headers
            body: Request body
            timeout: Timeout in seconds

        Returns:
            Response object

        Raises:
            requests.RequestException: If request fails after retries
        """
        for attempt in range(self.max_retries):
            try:
                response = requests.request(
                    method=method,
                    url=url,
                    headers=headers,
                    json=body,
                    timeout=timeout
                )
                response.raise_for_status()
                return response
            except requests.RequestException as e:
                if attempt == self.max_retries - 1:
                    raise
                self.logger.warning(
                    f"Request attempt {attempt + 1} failed: {e}, retrying..."
                )

        raise requests.RequestException("Max retries exceeded")

    def _process_response(
        self,
        response: requests.Response,
        api_config: dict[str, Any],
        session_state: dict[str, Any]
    ) -> Any:
        """
        Process API response and extract variables into session state.

        Args:
            response: HTTP response object
            api_config: API configuration with extract_response block
            session_state: Session state to update with extracted variables

        Returns:
            Dictionary of extracted variables
        """
        data = response.json()
        extracted = {}

        # Extract variables using extract_response configuration
        if "extract_response" in api_config:
            extract_config = api_config["extract_response"]

            if "variables" in extract_config:
                for var_name, var_config in extract_config["variables"].items(
                ):
                    path = var_config["path"]
                    extracted_value = self._extract_json_path(data, path)

                    # Store extracted value directly in session scores
                    if "scores" in session_state:
                        session_state["scores"][var_name] = extracted_value
                        extracted[var_name] = extracted_value
                        self.logger.debug(
                            f"Extracted {var_name} = {extracted_value} from API response")

        return extracted if extracted else data

    def _extract_json_path(self, data: Any, path: str) -> Any:
        """
        Extract data from JSON using simple dot notation path.

        Supports: "data.temperature", "results[0].value"

        Args:
            data: JSON data
            path: Dot notation path

        Returns:
            Extracted value
        """
        parts = path.split(".")
        result = data

        for part in parts:
            # Handle array indexing
            if "[" in part and "]" in part:
                key = part[:part.index("[")]
                index = int(part[part.index("[") + 1:part.index("]")])
                result = result[key][index]
            else:
                result = result[part]

        return result

    def get_api_data(
        self,
        session_state: dict[str, Any],
        api_id: str,
        default: Any = None
    ) -> Any:
        """
        Get API response data from session state.

        Args:
            session_state: Current session state
            api_id: API identifier
            default: Default value if data not found

        Returns:
            API response data or default
        """
        if "api_data" not in session_state:
            return default

        if api_id not in session_state["api_data"]:
            return default

        api_entry = session_state["api_data"][api_id]
        if not api_entry.get("success", False):
            return default

        return api_entry.get("response", default)

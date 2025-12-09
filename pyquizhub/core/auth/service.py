"""
User Authentication Service for PyQuizHub.

This module provides an extensible authentication system that supports:
- Anonymous users (default, auto-generated IDs)
- API key authentication
- OAuth2/OIDC (extensible, not implemented)
- Custom webhook auth (extensible, not implemented)

Deployers can extend this by:
1. Subclassing UserAuthService
2. Implementing custom auth methods
3. Registering their service in the application startup

Design Philosophy:
- Default behavior: anonymous users allowed (backward compatible)
- Quiz-level overrides: individual quizzes can require auth
- Extensible: deployers can add OAuth2, LDAP, etc.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import TYPE_CHECKING
from abc import ABC, abstractmethod

from pyquizhub.logging.setup import get_logger

if TYPE_CHECKING:
    from fastapi import Request
    from pyquizhub.config.settings import UserAuthSettings

logger = get_logger(__name__)


@dataclass
class AuthResult:
    """Result of an authentication attempt."""
    authenticated: bool
    user_id: str | None
    auth_method: str  # "anonymous", "api_key", "oauth2", "custom"
    error: str | None = None

    @classmethod
    def success(cls, user_id: str, auth_method: str) -> 'AuthResult':
        """Create a successful auth result."""
        return cls(authenticated=True, user_id=user_id, auth_method=auth_method)

    @classmethod
    def failure(cls, error: str, auth_method: str = "none") -> 'AuthResult':
        """Create a failed auth result."""
        return cls(authenticated=False, user_id=None, auth_method=auth_method, error=error)


class UserAuthProvider(ABC):
    """
    Abstract base class for authentication providers.

    Deployers can implement custom providers by subclassing this.
    """

    @abstractmethod
    def authenticate(self, request: 'Request') -> AuthResult | None:
        """
        Attempt to authenticate a request.

        Args:
            request: FastAPI request object

        Returns:
            AuthResult if this provider handled the request (success or failure),
            None if this provider doesn't apply (try next provider)
        """
        pass


class AnonymousAuthProvider(UserAuthProvider):
    """
    Provider for anonymous users.

    Generates random user IDs for users without credentials.
    """

    def __init__(self, id_prefix: str = "anon_"):
        self.id_prefix = id_prefix

    def authenticate(self, request: 'Request') -> AuthResult | None:
        """Generate an anonymous user ID."""
        user_id = f"{self.id_prefix}{uuid.uuid4().hex[:12]}"
        logger.debug(f"Generated anonymous user ID: {user_id}")
        return AuthResult.success(user_id, "anonymous")


class APIKeyAuthProvider(UserAuthProvider):
    """
    Provider for API key authentication.

    Validates user-provided API keys against a store.
    """

    def __init__(self, header_name: str = "X-User-API-Key"):
        self.header_name = header_name
        # In a real implementation, this would be backed by a database
        self._api_keys: dict[str, str] = {}  # api_key -> user_id

    def register_key(self, api_key: str, user_id: str) -> None:
        """Register an API key for a user (for testing/demo)."""
        self._api_keys[api_key] = user_id

    def authenticate(self, request: 'Request') -> AuthResult | None:
        """Validate API key from request header."""
        api_key = request.headers.get(self.header_name)
        if not api_key:
            return None  # No API key provided, try next provider

        user_id = self._api_keys.get(api_key)
        if user_id:
            logger.debug(f"API key authenticated user: {user_id}")
            return AuthResult.success(user_id, "api_key")

        logger.warning(f"Invalid API key attempted")
        return AuthResult.failure("Invalid API key", "api_key")


class UserAuthService:
    """
    Main authentication service that coordinates providers.

    This service:
    1. Checks quiz-level auth requirements (allow_anonymous is per-quiz)
    2. Tries each enabled auth provider in order
    3. Falls back to anonymous if the quiz allows it

    Usage:
        auth_service = UserAuthService.from_config(config.security.user_auth)

        # In endpoint:
        result = auth_service.authenticate(request, quiz_data)
        if not result.authenticated:
            raise HTTPException(403, result.error)
        user_id = result.user_id
    """

    def __init__(self, settings: 'UserAuthSettings'):
        """
        Initialize auth service from settings.

        Args:
            settings: UserAuthSettings from config
        """
        self.settings = settings
        self._providers: list[UserAuthProvider] = []
        self._anonymous_provider = AnonymousAuthProvider(settings.anonymous_id_prefix)

        # Initialize non-anonymous providers based on settings
        if settings.api_key_enabled:
            self._providers.append(
                APIKeyAuthProvider(settings.api_key_header)
            )

        logger.info(
            f"UserAuthService initialized with {len(self._providers)} auth providers: "
            f"{[type(p).__name__ for p in self._providers]}"
        )

    @classmethod
    def from_config(cls, settings: 'UserAuthSettings') -> 'UserAuthService':
        """Create auth service from config settings."""
        return cls(settings)

    def add_provider(self, provider: UserAuthProvider, priority: int = -1) -> None:
        """
        Add a custom auth provider.

        Args:
            provider: Authentication provider to add
            priority: Position in provider list (-1 = at end)
        """
        if priority == -1:
            self._providers.append(provider)
        else:
            self._providers.insert(priority, provider)

        logger.info(f"Added auth provider: {type(provider).__name__}")

    def authenticate(
        self,
        request: 'Request',
        quiz_data: dict | None = None,
        provided_user_id: str | None = None
    ) -> AuthResult:
        """
        Authenticate a request for quiz access.

        Args:
            request: FastAPI request object
            quiz_data: Optional quiz data to check quiz-level auth settings
            provided_user_id: Optional user ID provided in request body

        Returns:
            AuthResult with authentication outcome
        """
        # Check if quiz allows anonymous access (default: True)
        quiz_allows_anonymous = self._quiz_allows_anonymous(quiz_data)

        # If user_id is provided in the request, use it (backward compatibility)
        if provided_user_id and self._is_valid_user_id(provided_user_id):
            # If quiz requires auth, provided ID must come from authenticated source
            if not quiz_allows_anonymous:
                # Try to authenticate via configured providers
                logger.debug("Quiz requires authentication, validating provided ID")
                return self._authenticate_with_providers(request)

            logger.debug(f"Using provided user_id: {provided_user_id}")
            return AuthResult.success(provided_user_id, "provided")

        # Try non-anonymous providers first
        for provider in self._providers:
            result = provider.authenticate(request)
            if result is not None:
                return result

        # Fall back to anonymous if quiz allows it
        if quiz_allows_anonymous:
            return self._anonymous_provider.authenticate(request)

        # Quiz requires auth but no provider succeeded
        return AuthResult.failure(
            "This quiz requires authentication. Anonymous access is not allowed.",
            "none"
        )

    def _authenticate_with_providers(self, request: 'Request') -> AuthResult:
        """Authenticate using configured providers (no anonymous fallback)."""
        for provider in self._providers:
            result = provider.authenticate(request)
            if result is not None:
                return result

        return AuthResult.failure(
            "This quiz requires authentication. Anonymous access is not allowed.",
            "none"
        )

    def _quiz_allows_anonymous(self, quiz_data: dict | None) -> bool:
        """Check if quiz allows anonymous access (default: True)."""
        if not quiz_data:
            return True  # No quiz data = allow anonymous by default

        quiz_auth = quiz_data.get("metadata", {}).get("auth")
        if quiz_auth is None:
            return True  # No auth settings = allow anonymous

        return quiz_auth.get("allow_anonymous", True)

    def _is_valid_user_id(self, user_id: str) -> bool:
        """Validate a user ID string."""
        if not user_id or len(user_id) > 256:
            return False
        # Allow alphanumeric, underscores, hyphens, and some common chars
        import re
        return bool(re.match(r'^[\w\-\.@]+$', user_id))

    def allows_anonymous(self, quiz_data: dict | None = None) -> bool:
        """
        Check if anonymous access is allowed for a quiz.

        Args:
            quiz_data: Quiz data to check auth settings

        Returns:
            True if anonymous users are allowed
        """
        return self._quiz_allows_anonymous(quiz_data)

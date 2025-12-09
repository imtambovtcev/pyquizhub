"""
FastAPI dependencies for authentication and rate limiting.
"""

from __future__ import annotations

from typing import Optional, Tuple
from fastapi import Header, HTTPException, Request, status

from pyquizhub.config.settings import get_config_manager
from pyquizhub.core.api.rate_limiter import get_rate_limiter


def verify_token_and_rate_limit(
    authorization: Optional[str] = Header(None),
    request: Request = None
) -> Tuple[str, str]:
    """
    Verify authorization token, determine role, and check rate limits.

    Combines authentication and rate limiting in a single dependency.
    Token priority: admin > creator > user

    Args:
        authorization: Authorization header value
        request: FastAPI request

    Returns:
        Tuple of (user_id, role)
        - role: "admin", "creator", or "user"

    Raises:
        HTTPException: If token is invalid or rate limit exceeded
    """
    config = get_config_manager()

    # 1. Verify token and get role
    try:
        user_id, role = config.verify_token_and_get_role(authorization)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )

    # 2. Check rate limits
    rate_limiter = get_rate_limiter()
    role_permissions = config.get_role_permissions(role)

    try:
        rate_limiter.check_rate_limit(
            user_id=user_id,
            role=role,
            limits=role_permissions.rate_limits
        )
    except HTTPException:
        # Rate limit exception already formatted correctly
        raise

    # 3. Add rate limit headers to response (optional but good practice)
    if request:
        remaining = rate_limiter.get_remaining(
            user_id, role, role_permissions.rate_limits
        )
        # Store in request state so endpoint can add headers
        request.state.rate_limit_remaining = remaining

    return user_id, role


def verify_token_only(
    authorization: Optional[str] = Header(None),
    request: Request = None
) -> Tuple[str, str]:
    """
    Verify authorization token without rate limiting.

    Use this for endpoints that don't need rate limiting
    (e.g., health checks, admin-only endpoints).

    Args:
        authorization: Authorization header value
        request: FastAPI request

    Returns:
        Tuple of (user_id, role)

    Raises:
        HTTPException: If token is invalid
    """
    config = get_config_manager()

    try:
        user_id, role = config.verify_token_and_get_role(authorization)
        return user_id, role
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )


# Backwards compatibility alias
verify_token = verify_token_only


def user_token_with_rate_limit(request: Request) -> None:
    """
    Dependency for quiz endpoints that validates user token and applies rate limits.

    This is specifically for quiz-taking endpoints (start_quiz, submit_answer, etc.)
    where we want to rate limit based on the user token.

    Args:
        request: FastAPI Request object containing headers

    Raises:
        HTTPException: If user token is invalid or rate limit exceeded
    """
    from pyquizhub.config.settings import get_config_manager

    token = request.headers.get("Authorization")
    config_manager = get_config_manager()
    expected_token = config_manager.get_token("user")

    if token != expected_token:
        raise HTTPException(status_code=403, detail="Invalid user token")

    # Apply rate limiting for user role
    rate_limiter = get_rate_limiter()
    role_permissions = config_manager.get_role_permissions("user")

    # Use a stable user identifier (IP address or anonymous user)
    # For anonymous quiz-taking, use IP address as identifier
    user_identifier = request.client.host if request.client else "anonymous"

    try:
        rate_limiter.check_rate_limit(
            user_id=user_identifier,
            role="user",
            limits=role_permissions.rate_limits
        )
    except HTTPException:
        raise

    # Store remaining limits in request state
    remaining = rate_limiter.get_remaining(
        user_identifier, "user", role_permissions.rate_limits
    )
    request.state.rate_limit_remaining = remaining

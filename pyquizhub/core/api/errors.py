"""
Standardized error response handling for PyQuizHub API.

This module provides utilities for creating consistent error responses
across all API endpoints, ensuring a uniform error format for clients.
"""

from __future__ import annotations

from typing import Any
from fastapi import HTTPException, status


def error_response(
    message: str,
    status_code: int = status.HTTP_400_BAD_REQUEST,
    details: list[str] | None = None,
    field: str | None = None,
    code: str | None = None
) -> dict[str, Any]:
    """
    Create a standardized error response.

    Args:
        message: Human-readable error summary
        status_code: HTTP status code (default: 400)
        details: List of specific error details (optional)
        field: Field name that caused the error (optional)
        code: Error code for programmatic handling (optional)

    Returns:
        Standardized error response dictionary

    Examples:
        >>> error_response("Quiz validation failed", details=["Missing 'questions' field"])
        {'error': {'message': 'Quiz validation failed', 'details': ['Missing \'questions\' field']}}

        >>> error_response("Invalid quiz data", field="metadata.title", code="VALIDATION_ERROR")
        {'error': {'message': 'Invalid quiz data', 'field': 'metadata.title', 'code': 'VALIDATION_ERROR'}}
    """
    error_dict: dict[str, Any] = {"message": message}

    if details is not None:
        error_dict["details"] = details

    if field is not None:
        error_dict["field"] = field

    if code is not None:
        error_dict["code"] = code

    return {"error": error_dict}


def raise_error(
    message: str,
    status_code: int = status.HTTP_400_BAD_REQUEST,
    details: list[str] | None = None,
    field: str | None = None,
    code: str | None = None
) -> None:
    """
    Raise an HTTPException with standardized error format.

    Args:
        message: Human-readable error summary
        status_code: HTTP status code (default: 400)
        details: List of specific error details (optional)
        field: Field name that caused the error (optional)
        code: Error code for programmatic handling (optional)

    Raises:
        HTTPException: With standardized error response format

    Examples:
        >>> raise_error("Quiz not found", status_code=404, code="NOT_FOUND")

        >>> raise_error(
        ...     "Validation failed",
        ...     status_code=400,
        ...     details=["Missing 'questions' field", "Invalid 'metadata.title'"],
        ...     code="VALIDATION_ERROR"
        ... )
    """
    raise HTTPException(
        status_code=status_code,
        detail=error_response(message, status_code, details, field, code)
    )


# Common error response helpers
def validation_error(details: list[str], field: str | None = None) -> None:
    """Raise a validation error with details."""
    raise_error(
        message="Validation failed",
        status_code=status.HTTP_400_BAD_REQUEST,
        details=details,
        field=field,
        code="VALIDATION_ERROR"
    )


def not_found_error(resource: str, resource_id: str | None = None) -> None:
    """Raise a not found error."""
    message = f"{resource} not found"
    if resource_id:
        message = f"{resource} '{resource_id}' not found"

    raise_error(
        message=message,
        status_code=status.HTTP_404_NOT_FOUND,
        code="NOT_FOUND"
    )


def permission_error(message: str, details: list[str] | None = None) -> None:
    """Raise a permission denied error."""
    raise_error(
        message=message,
        status_code=status.HTTP_403_FORBIDDEN,
        details=details,
        code="PERMISSION_DENIED"
    )


def authentication_error(message: str = "Authentication failed") -> None:
    """Raise an authentication error."""
    raise_error(
        message=message,
        status_code=status.HTTP_401_UNAUTHORIZED,
        code="AUTHENTICATION_FAILED"
    )


def server_error(message: str = "Internal server error", details: list[str] | None = None) -> None:
    """Raise a server error."""
    raise_error(
        message=message,
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        details=details,
        code="SERVER_ERROR"
    )


def storage_error(operation: str) -> None:
    """Raise a storage operation error."""
    raise_error(
        message=f"Storage operation failed: {operation}",
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        code="STORAGE_ERROR"
    )

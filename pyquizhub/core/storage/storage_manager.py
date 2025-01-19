"""
Abstract interface for storage management.

This module defines the abstract base class for storage management, which
includes methods for managing users, quizzes, tokens, results, and sessions.
"""

from typing import Any, Dict, List, Optional
from abc import ABC, abstractmethod
from datetime import datetime


class StorageManager(ABC):
    """Abstract interface for storage management."""

    @abstractmethod
    def get_users(self) -> Dict[str, Any]:
        """Fetch all users."""
        pass

    @abstractmethod
    def add_users(self, users: Dict[str, Any]) -> None:
        """Add or update users."""
        pass

    @abstractmethod
    def get_quiz(self, quiz_id: str) -> Dict[str, Any]:
        """Fetch a quiz by its ID."""
        pass

    @abstractmethod
    def add_quiz(self, quiz_id: str, quiz_data: Dict[str, Any]) -> None:
        """Add or update a quiz."""
        pass

    # Tokens
    @abstractmethod
    def get_tokens(self) -> List[Dict[str, Any]]:
        """Fetch all tokens."""
        pass

    @abstractmethod
    def add_tokens(self, tokens: List[Dict[str, Any]]) -> None:
        """Add or update tokens."""
        pass

    @abstractmethod
    def remove_token(self, token: str) -> None:
        """Remove a token."""
        pass

    @abstractmethod
    def get_all_tokens(self) -> Dict[str, List[Dict[str, Any]]]:
        """Fetch all tokens grouped by quiz."""
        pass

    @abstractmethod
    def get_tokens_by_quiz(self, quiz_id: str) -> List[Dict[str, Any]]:
        """Fetch tokens for a specific quiz."""
        pass

    @abstractmethod
    def get_token_type(self, token: str) -> Optional[str]:
        """Fetch the type of a token."""
        pass

    # Results
    @abstractmethod
    def get_results(self, user_id: str, quiz_id: str, session_id: str) -> Optional[Dict[str, Any]]:
        """Fetch results for a specific user, quiz, and session."""
        pass

    @abstractmethod
    def add_results(self, user_id: str, quiz_id: str, session_id: str, results: Dict[str, Any]) -> None:
        """Add or update results."""
        pass

    @abstractmethod
    def get_all_results(self) -> Dict[str, Dict[str, Any]]:
        """Fetch all results."""
        pass

    @abstractmethod
    def get_results_by_quiz(self, quiz_id: str) -> Dict[str, Dict[str, Any]]:
        """Fetch results for a specific quiz."""
        pass

    @abstractmethod
    def get_results_by_user(self, user_id: str) -> Dict[str, Dict[str, Any]]:
        """Fetch results for a specific user."""
        pass

    @abstractmethod
    def get_results_by_quiz_and_user(self, quiz_id: str, user_id: str) -> Dict[str, Dict[str, Any]]:
        """Fetch results for a specific quiz and user."""
        pass

    # Sessions
    @abstractmethod
    def get_all_sessions(self) -> Dict[str, List[str]]:
        """Fetch all sessions grouped by user."""
        pass

    @abstractmethod
    def get_sessions_by_user(self, user_id: str) -> List[str]:
        """Fetch sessions for a specific user."""
        pass

    @abstractmethod
    def get_sessions_by_quiz(self, quiz_id: str) -> List[str]:
        """Fetch sessions for a specific quiz."""
        pass

    @abstractmethod
    def get_sessions_by_quiz_and_user(self, quiz_id: str, user_id: str) -> List[str]:
        """Fetch sessions for a specific quiz and user."""
        pass

    @abstractmethod
    def user_has_permission_for_quiz_creation(self, user_id: str) -> bool:
        """Check if a user has permission to create quizzes."""
        pass

    @abstractmethod
    def get_participated_users(self, quiz_id: str) -> List[str]:
        """Fetch users who participated in a specific quiz."""
        pass

    @abstractmethod
    def get_quiz_id_by_token(self, token: str) -> Optional[str]:
        """Fetch the quiz ID associated with a token."""
        pass

    @abstractmethod
    def get_all_quizzes(self) -> Dict[str, Any]:
        """Fetch all quizzes."""
        pass

    def add_result(self, user_id: str, quiz_id: str, session_id: str, result: dict):
        """Add or update a result."""
        result["timestamp"] = datetime.now().isoformat()
        # ...existing code...

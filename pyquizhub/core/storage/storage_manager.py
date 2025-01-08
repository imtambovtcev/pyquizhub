from typing import Any, Dict, List, Optional
from abc import ABC, abstractmethod


class StorageManager(ABC):
    """Abstract interface for storage management."""

    @abstractmethod
    def get_users(self) -> Dict[str, Any]:
        pass

    @abstractmethod
    def add_users(self, users: Dict[str, Any]) -> None:
        pass

    @abstractmethod
    def get_quiz(self, quiz_id: str) -> Dict[str, Any]:
        pass

    @abstractmethod
    def add_quiz(self, quiz_id: str, quiz_data: Dict[str, Any]) -> None:
        pass

    # Tokens
    @abstractmethod
    def get_tokens(self) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    def add_tokens(self, tokens: List[Dict[str, Any]]) -> None:
        pass

    @abstractmethod
    def remove_token(self, token: str) -> None:
        pass

    @abstractmethod
    def get_all_tokens(self) -> Dict[str, List[Dict[str, Any]]]:
        pass

    @abstractmethod
    def get_tokens_by_quiz(self, quiz_id: str) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    def get_token_type(self, token: str) -> Optional[str]:
        pass

    # Results
    @abstractmethod
    def get_results(self, user_id: str, quiz_id: str, session_id: str) -> Optional[Dict[str, Any]]:
        pass

    @abstractmethod
    def add_results(self, user_id: str, quiz_id: str, session_id: str, results: Dict[str, Any]) -> None:
        pass

    @abstractmethod
    def get_all_results(self) -> Dict[str, Dict[str, Any]]:
        pass

    @abstractmethod
    def get_results_by_quiz(self, quiz_id: str) -> Dict[str, Dict[str, Any]]:
        pass

    @abstractmethod
    def get_results_by_user(self, user_id: str) -> Dict[str, Dict[str, Any]]:
        pass

    @abstractmethod
    def get_results_by_quiz_and_user(self, quiz_id: str, user_id: str) -> Dict[str, Dict[str, Any]]:
        pass

    # Sessions
    @abstractmethod
    def get_all_sessions(self) -> Dict[str, List[str]]:
        pass

    @abstractmethod
    def get_sessions_by_user(self, user_id: str) -> List[str]:
        pass

    @abstractmethod
    def get_sessions_by_quiz(self, quiz_id: str) -> List[str]:
        pass

    @abstractmethod
    def get_sessions_by_quiz_and_user(self, quiz_id: str, user_id: str) -> List[str]:
        pass

    @abstractmethod
    def user_has_permission_for_quiz_creation(self, user_id: str) -> bool:
        pass

    @abstractmethod
    def get_participated_users(self, quiz_id: str) -> List[str]:
        pass

    @abstractmethod
    def get_quiz_id_by_token(self, token: str) -> Optional[str]:
        pass

    @abstractmethod
    def get_all_quizzes(self) -> Dict[str, Any]:
        pass

from typing import Any, Dict, List, Optional


class StorageManager:
    """Abstract interface for storage management."""

    def get_users(self) -> Dict[str, Any]:
        raise NotImplementedError

    def add_users(self, users: Dict[str, Any]) -> None:
        raise NotImplementedError

    def get_quiz(self, quiz_id: str) -> Dict[str, Any]:
        raise NotImplementedError

    def add_quiz(self, quiz_id: str, quiz_data: Dict[str, Any]) -> None:
        raise NotImplementedError

    def get_results(self, user_id: str, quiz_id: str) -> Optional[Dict[str, Any]]:
        raise NotImplementedError

    def add_results(self, user_id: str, quiz_id: str, results: Dict[str, Any]) -> None:
        raise NotImplementedError

    def get_tokens(self) -> List[Dict[str, Any]]:
        raise NotImplementedError

    def add_tokens(self, tokens: List[Dict[str, Any]]) -> None:
        raise NotImplementedError

    def user_has_permission_for_quiz_creation(self, user_id: str) -> bool:
        raise NotImplementedError

    def get_participated_users(self, quiz_id: str) -> List[str]:
        raise NotImplementedError

    def get_quiz_id_by_token(self, token: str) -> Optional[str]:
        raise NotImplementedError

    def remove_token(self, token: str) -> None:
        raise NotImplementedError

    def get_all_quizzes(self) -> Dict[str, Any]:
        raise NotImplementedError

    def get_all_tokens(self) -> Dict[str, Any]:
        raise NotImplementedError

    def get_token_type(self, token: str) -> Optional[str]:
        raise NotImplementedError

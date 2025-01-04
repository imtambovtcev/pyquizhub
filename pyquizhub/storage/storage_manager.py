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

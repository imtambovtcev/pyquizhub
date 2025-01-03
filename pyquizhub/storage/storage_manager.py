from typing import Any, Dict, List, Optional


class StorageManager:
    """Abstract interface for storage management."""

    def load_users(self) -> Dict[str, Any]:
        raise NotImplementedError

    def save_users(self, users: Dict[str, Any]) -> None:
        raise NotImplementedError

    def load_quiz(self, quiz_id: str) -> Dict[str, Any]:
        raise NotImplementedError

    def save_quiz(self, quiz_id: str, quiz_data: Dict[str, Any]) -> None:
        raise NotImplementedError

    def load_results(self, user_id: str, quiz_id: str) -> Optional[Dict[str, Any]]:
        raise NotImplementedError

    def save_results(self, user_id: str, quiz_id: str, results: Dict[str, Any]) -> None:
        raise NotImplementedError

    def load_tokens(self) -> List[Dict[str, Any]]:
        raise NotImplementedError

    def save_tokens(self, tokens: List[Dict[str, Any]]) -> None:
        raise NotImplementedError

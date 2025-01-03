import os
import json
from typing import Any, Dict, List, Optional
from .storage_manager import StorageManager


class FileStorageManager(StorageManager):
    def __init__(self, base_dir: str):
        self.base_dir = base_dir
        os.makedirs(self.base_dir, exist_ok=True)
        os.makedirs(os.path.join(self.base_dir, "quizzes"), exist_ok=True)
        os.makedirs(os.path.join(self.base_dir, "results"), exist_ok=True)

        # Initialize default files
        if not os.path.exists(os.path.join(self.base_dir, "users.json")):
            self._write_json("users.json", {})
        if not os.path.exists(os.path.join(self.base_dir, "tokens.json")):
            self._write_json("tokens.json", [])

    def _read_json(self, filename: str) -> Any:
        filepath = os.path.join(self.base_dir, filename)
        with open(filepath, "r") as f:
            return json.load(f)

    def _write_json(self, filename: str, data: Any) -> None:
        filepath = os.path.join(self.base_dir, filename)
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, "w") as f:
            json.dump(data, f, indent=4)

    def load_users(self) -> Dict[str, Any]:
        return self._read_json("users.json")

    def save_users(self, users: Dict[str, Any]) -> None:
        self._write_json("users.json", users)

    def load_quiz(self, quiz_id: str) -> Dict[str, Any]:
        filepath = os.path.join(self.base_dir, "quizzes", f"{quiz_id}.json")
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Quiz {quiz_id} not found.")
        return self._read_json(filepath)

    def save_quiz(self, quiz_id: str, quiz_data: Dict[str, Any]) -> None:
        filepath = os.path.join(self.base_dir, "quizzes", f"{quiz_id}.json")
        self._write_json(filepath, quiz_data)

    def load_results(self, user_id: str, quiz_id: str) -> Optional[Dict[str, Any]]:
        filepath = os.path.join(self.base_dir, "results",
                                user_id, f"{quiz_id}_results.json")
        if not os.path.exists(filepath):
            return None
        return self._read_json(filepath)

    def save_results(self, user_id: str, quiz_id: str, results: Dict[str, Any]) -> None:
        user_dir = os.path.join(self.base_dir, "results", user_id)
        os.makedirs(user_dir, exist_ok=True)
        filepath = os.path.join(user_dir, f"{quiz_id}_results.json")
        self._write_json(filepath, results)

    def load_tokens(self) -> List[Dict[str, Any]]:
        return self._read_json("tokens.json")

    def save_tokens(self, tokens: List[Dict[str, Any]]) -> None:
        self._write_json("tokens.json", tokens)

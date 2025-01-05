import os
import json
from typing import Any, Dict, List, Optional
from .storage_manager import StorageManager
import logging
logging.basicConfig(level=logging.INFO)


class FileStorageManager(StorageManager):
    def __init__(self, base_dir: str):
        self.base_dir = base_dir

        logging.info(f"Using file storage at {base_dir}")
        os.makedirs(self.base_dir, exist_ok=True)
        os.makedirs(os.path.join(self.base_dir, "quizzes"), exist_ok=True)
        os.makedirs(os.path.join(self.base_dir, "results"), exist_ok=True)

        # Initialize default files
        if not os.path.exists(os.path.join(self.base_dir, "users.json")):
            self._write_json("users.json", {})
        if not os.path.exists(os.path.join(self.base_dir, "tokens.json")):
            self._write_json("tokens.json", [])

        # Load existing data from the filesystem
        self.users = self._load("users.json")
        self.tokens = self._load("tokens.json")
        self.quizzes = {}
        quizzes_dir = os.path.join(self.base_dir, "quizzes")
        for quiz_file in os.listdir(quizzes_dir):
            if quiz_file.endswith(".json"):
                quiz_id = os.path.splitext(quiz_file)[0]
                logging.info(f"Loading quiz {quiz_id}")
                self.quizzes[quiz_id] = self.get_quiz(quiz_id)
        self.results = {}
        results_dir = os.path.join(self.base_dir, "results")
        for user_id in os.listdir(results_dir):
            user_results_dir = os.path.join(results_dir, user_id)
            if os.path.isdir(user_results_dir):
                self.results[user_id] = {}
                for result_file in os.listdir(user_results_dir):
                    if result_file.endswith("_results.json"):
                        quiz_id = result_file.replace("_results.json", "")
                        self.results[user_id][quiz_id] = self.load_results(
                            user_id, quiz_id)

    def _read_json(self, filename: str) -> Any:
        filepath = os.path.join(self.base_dir, filename)
        with open(filepath, "r") as f:
            return json.load(f)

    def _write_json(self, filename: str, data: Any) -> None:
        filepath = os.path.join(self.base_dir, filename)
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, "w") as f:
            json.dump(data, f, indent=4)

    def _load(self, filename: str) -> Any:
        return self._read_json(filename)

    def _save(self, filename: str, data: Any) -> None:
        self._write_json(filename, data)

    def get_users(self) -> Dict[str, Any]:
        return self.users

    def add_users(self, users: Dict[str, Any]) -> None:
        self.users.update(users)
        self._save("users.json", self.users)

    def get_quiz(self, quiz_id: str) -> Dict[str, Any]:
        filepath = os.path.join("quizzes", f"{quiz_id}.json")
        if not os.path.exists(os.path.join(self.base_dir, filepath)):
            raise FileNotFoundError(f"Quiz {quiz_id} not found.")
        return self._read_json(filepath)

    def add_quiz(self, quiz_id: str, quiz_data: Dict[str, Any], creator_id: str) -> None:
        quiz_data["creator_id"] = creator_id
        filepath = os.path.join(self.base_dir, "quizzes", f"{quiz_id}.json")
        self._write_json(filepath, quiz_data)

    def get_results(self, user_id: str, quiz_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve the results of a quiz for a specific user.

        Args:
            user_id (str): The ID of the user.
            quiz_id (str): The ID of the quiz.

        Returns:
            Optional[Dict[str, Any]]: A dictionary containing the results in the format:
                {
                    'user_id': <user_id>,
                    'quiz_id': <quiz_id>,
                    'scores': <scores_dict>,
                    'answers': <answers_dict>
                }
                or None if the results file does not exist.
        """
        filepath = os.path.join(self.base_dir, "results",
                                user_id, f"{quiz_id}_results.json")
        if not os.path.exists(filepath):
            return None
        results = self._read_json(filepath)
        return {
            'user_id': user_id,
            'quiz_id': quiz_id,
            'scores': results.get('scores', {}),
            'answers': results.get('answers', {})
        }

    def add_results(self, user_id: str, quiz_id: str, results: Dict[str, Any]) -> None:
        filepath = f"results/{user_id}/{quiz_id}_results.json"
        print(f"Saving results to {filepath}")
        print(f"{results = }")
        self._write_json(filepath, results)

    def get_tokens(self) -> List[Dict[str, Any]]:
        return self.tokens

    def add_tokens(self, tokens: List[Dict[str, Any]]) -> None:
        self.tokens.extend(tokens)
        self._save("tokens.json", self.tokens)

    def remove_token(self, token: str) -> None:
        self.tokens = [t for t in self.tokens if t["token"] != token]
        self._save("tokens.json", self.tokens)

    def user_has_permission_for_quiz_creation(self, user_id: str) -> bool:
        user = self.users.get(user_id)
        if user and "create" in user.get("permissions", []):
            return True
        return False

    def get_participated_users(self, quiz_id: str) -> List[str]:
        participated_users = []
        results_dir = os.path.join(self.base_dir, "results")
        for user_id in os.listdir(results_dir):
            user_results_dir = os.path.join(results_dir, user_id)
            if os.path.isdir(user_results_dir):
                result_file = os.path.join(
                    user_results_dir, f"{quiz_id}_results.json")
                if os.path.exists(result_file):
                    participated_users.append(user_id)
        return participated_users

    def get_quiz_id_by_token(self, token: str) -> Optional[str]:
        for token_entry in self.tokens:
            if token_entry["token"] == token:
                return token_entry["quiz_id"]
        return None

    def get_token_type(self, token: str) -> Optional[str]:
        for token_entry in self.tokens:
            if token_entry["token"] == token:
                return token_entry["type"]
        return None

    def get_all_quizzes(self) -> Dict[str, Dict[str, Any]]:
        quizzes_dir = os.path.join(self.base_dir, "quizzes")
        quizzes = {}
        for quiz_file in os.listdir(quizzes_dir):
            if quiz_file.endswith(".json"):
                quiz_id = os.path.splitext(quiz_file)[0]
                quizzes[quiz_id] = self.get_quiz(quiz_id)
        return quizzes

    def get_all_tokens(self) -> Dict[str, List[Dict[str, Any]]]:
        tokens_by_quiz = {}
        for token_entry in self.tokens:
            quiz_id = token_entry["quiz_id"]
            if quiz_id not in tokens_by_quiz:
                tokens_by_quiz[quiz_id] = []
            tokens_by_quiz[quiz_id].append(token_entry)
        return tokens_by_quiz

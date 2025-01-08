import os
import json
from typing import Any, Dict, List, Optional
from .storage_manager import StorageManager
import logging
from datetime import datetime
logging.basicConfig(level=logging.INFO)


class FileStorageManager(StorageManager):
    def __init__(self, base_dir: str):
        self.base_dir = base_dir
        self.reinit()

    def reinit(self):
        logging.info(f"Using file storage at {self.base_dir}")
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
                        parts = result_file.split("_")
                        quiz_id = parts[0]
                        session_id = parts[1]
                        if quiz_id not in self.results[user_id]:
                            self.results[user_id][quiz_id] = {}
                        self.results[user_id][quiz_id][session_id] = self.get_results(
                            user_id, quiz_id, session_id)

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
        filepath = f"quizzes/{quiz_id}.json"
        self._write_json(filepath, quiz_data)

    # Results
    def get_results(self, user_id: str, quiz_id: str, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve the results of a quiz for a specific user session.

        Args:
            user_id (str): The ID of the user.
            quiz_id (str): The ID of the quiz.
            session_id (str): The ID of the session.

        Returns:
            Optional[Dict[str, Any]]: A dictionary containing the results in the format:
                {
                    'user_id': <user_id>,
                    'quiz_id': <quiz_id>,
                    'session_id': <session_id>,
                    'scores': <scores_dict>,
                    'answers': <answers_dict>,
                    'timestamp': <timestamp>
                }
                or None if the results do not exist.
        """
        result = self.results.get(user_id, {}).get(quiz_id, {}).get(session_id)
        if result:
            return {
                'user_id': user_id,
                'quiz_id': quiz_id,
                'session_id': session_id,
                'scores': result.get('scores', {}),
                'answers': result.get('answers', {}),
                'timestamp': result.get('timestamp')
            }
        return None

    def add_results(self, user_id: str, quiz_id: str, session_id: str, results: Dict[str, Any]) -> None:
        results["timestamp"] = datetime.now().isoformat()
        if user_id not in self.results:
            self.results[user_id] = {}
        if quiz_id not in self.results[user_id]:
            self.results[user_id][quiz_id] = {}
        self.results[user_id][quiz_id][session_id] = results
        filepath = f"results/{user_id}/{quiz_id}_{session_id}_results.json"
        self._write_json(filepath, results)

    def get_all_results(self) -> Dict[str, Dict[str, Any]]:
        return self.results

    def get_results_by_quiz(self, quiz_id: str) -> Dict[str, Dict[str, Any]]:
        results_by_user = {}
        for user_id, quizzes in self.results.items():
            if quiz_id in quizzes:
                results_by_user[user_id] = quizzes[quiz_id]
        return results_by_user

    def get_results_by_user(self, user_id: str) -> Dict[str, Dict[str, Any]]:
        return self.results.get(user_id, {})

    def get_results_by_quiz_and_user(self, quiz_id: str, user_id: str) -> Dict[str, Dict[str, Any]]:
        return self.results.get(user_id, {}).get(quiz_id, {})

    # Tokens
    def get_tokens(self) -> List[Dict[str, Any]]:
        return self.tokens

    def add_tokens(self, tokens: List[Dict[str, Any]]) -> None:
        self.tokens.extend(tokens)
        self._save("tokens.json", self.tokens)

    def remove_token(self, token: str) -> None:
        self.tokens = [t for t in self.tokens if t["token"] != token]
        self._save("tokens.json", self.tokens)

    def get_all_tokens(self) -> Dict[str, List[Dict[str, Any]]]:
        tokens_by_quiz = {}
        for token_entry in self.tokens:
            quiz_id = token_entry["quiz_id"]
            if quiz_id not in tokens_by_quiz:
                tokens_by_quiz[quiz_id] = []
            tokens_by_quiz[quiz_id].append(token_entry)
        return tokens_by_quiz

    def get_tokens_by_quiz(self, quiz_id: str) -> List[Dict[str, Any]]:
        return [token for token in self.tokens if token["quiz_id"] == quiz_id]

    def get_token_type(self, token: str) -> Optional[str]:
        for token_entry in self.tokens:
            if token_entry["token"] == token:
                return token_entry["type"]
        return None

    def user_has_permission_for_quiz_creation(self, user_id: str) -> bool:
        user = self.users.get(user_id)
        if user and "create" in user.get("permissions", []):
            return True
        return False

    def get_participated_users(self, quiz_id: str) -> List[str]:
        participated_users = []
        for user_id, quizzes in self.results.items():
            if quiz_id in quizzes:
                participated_users.append(user_id)
        return participated_users

    def get_quiz_id_by_token(self, token: str) -> Optional[str]:
        for token_entry in self.tokens:
            if token_entry["token"] == token:
                return token_entry["quiz_id"]
        return None

    def get_all_quizzes(self) -> Dict[str, Dict[str, Any]]:
        quizzes_dir = os.path.join(self.base_dir, "quizzes")
        quizzes = {}
        for quiz_file in os.listdir(quizzes_dir):
            if quiz_file.endswith(".json"):
                quiz_id = os.path.splitext(quiz_file)[0]
                quizzes[quiz_id] = self.get_quiz(quiz_id)
        return quizzes

    def get_results_by_user_and_quiz(self, user_id: str, quiz_id: str) -> Dict[str, Dict[str, Any]]:
        return self.results.get(user_id, {}).get(quiz_id, {})

    def get_session_ids_by_user_and_quiz(self, user_id: str, quiz_id: str) -> List[str]:
        return list(self.results.get(user_id, {}).get(quiz_id, {}).keys())

    # Sessions
    def get_all_sessions(self) -> Dict[str, List[str]]:
        sessions_by_user = {}
        for user_id, quizzes in self.results.items():
            sessions_by_user[user_id] = []
            for quiz_id, sessions in quizzes.items():
                sessions_by_user[user_id].extend(sessions.keys())
        return sessions_by_user

    def get_sessions_by_user(self, user_id: str) -> List[str]:
        sessions = []
        for quiz_id, quiz_sessions in self.results.get(user_id, {}).items():
            sessions.extend(quiz_sessions.keys())
        return sessions

    def get_sessions_by_quiz(self, quiz_id: str) -> List[str]:
        sessions = []
        for user_id, quizzes in self.results.items():
            if quiz_id in quizzes:
                sessions.extend(quizzes[quiz_id].keys())
        return sessions

    def get_sessions_by_quiz_and_user(self, quiz_id: str, user_id: str) -> List[str]:
        return list(self.results.get(user_id, {}).get(quiz_id, {}).keys())

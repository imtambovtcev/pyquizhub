"""
File storage manager implementation.

This module provides an implementation of the StorageManager interface using
the filesystem for persistent storage of users, quizzes, tokens, results, and sessions.
"""

import os
import json
from typing import Any, Dict, List, Optional
from .storage_manager import StorageManager
from pyquizhub.config.settings import get_logger
from datetime import datetime


class FileStorageManager(StorageManager):
    """
    File storage manager for managing users, quizzes, tokens, results, and sessions.

    This class provides methods to interact with the filesystem for storing and
    retrieving quiz-related data.
    """

    def __init__(self, base_dir: str):
        """
        Initialize the FileStorageManager with a base directory.

        Args:
            base_dir (str): Base directory for storing files
        """
        self.logger = get_logger(__name__)
        self.logger.debug(
            f"Initializing FileStorageManager with base directory: {base_dir}")
        self.base_dir = base_dir
        self.reinit()

    def reinit(self):
        """
        Reinitialize the file storage by creating necessary directories and loading existing data.
        """
        self.logger.debug(f"Reinitializing file storage at {self.base_dir}")
        self.logger.info(f"Using file storage at {self.base_dir}")
        os.makedirs(self.base_dir, exist_ok=True)
        os.makedirs(os.path.join(self.base_dir, "quizzes"), exist_ok=True)
        os.makedirs(os.path.join(self.base_dir, "results"), exist_ok=True)
        os.makedirs(os.path.join(self.base_dir, "sessions"), exist_ok=True)

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
                self.logger.info(f"Loading quiz {quiz_id}")
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
                        self.results[user_id][quiz_id][session_id] = self._load(
                            f"results/{user_id}/{result_file}")

    def _read_json(self, filename: str) -> Any:
        """
        Read JSON data from a file.

        Args:
            filename (str): Name of the file to read

        Returns:
            Any: Parsed JSON data
        """
        filepath = os.path.join(self.base_dir, filename)
        self.logger.debug(f"Reading JSON file: {filepath}")
        with open(filepath, "r") as f:
            return json.load(f)

    def _write_json(self, filename: str, data: Any) -> None:
        """
        Write JSON data to a file.

        Args:
            filename (str): Name of the file to write
            data (Any): Data to write to the file
        """
        filepath = os.path.join(self.base_dir, filename)
        self.logger.debug(f"Writing JSON file: {filepath}")
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, "w") as f:
            json.dump(data, f, indent=4)

    def _load(self, filename: str) -> Any:
        """
        Load data from a file.

        Args:
            filename (str): Name of the file to load

        Returns:
            Any: Loaded data
        """
        self.logger.debug(f"Loading data from file: {filename}")
        return self._read_json(filename)

    def _save(self, filename: str, data: Any) -> None:
        """
        Save data to a file.

        Args:
            filename (str): Name of the file to save
            data (Any): Data to save to the file
        """
        self.logger.debug(f"Saving data to file: {filename}")
        self._write_json(filename, data)

    def get_users(self) -> Dict[str, Any]:
        """Fetch all users."""
        self.logger.debug("Fetching all users")
        return self.users

    def add_users(self, users: Dict[str, Any]) -> None:
        """Add or update users."""
        self.logger.debug(f"Adding users: {users}")
        self.users.update(users)
        self._save("users.json", self.users)

    def get_quiz(self, quiz_id: str) -> Dict[str, Any]:
        """Fetch a quiz by its ID."""
        filepath = os.path.join("quizzes", f"{quiz_id}.json")
        self.logger.debug(f"Fetching quiz with ID: {quiz_id}")
        if not os.path.exists(os.path.join(self.base_dir, filepath)):
            raise FileNotFoundError(f"Quiz {quiz_id} not found.")
        return self._read_json(filepath)

    def add_quiz(self,
                 quiz_id: str,
                 quiz_data: Dict[str,
                                 Any],
                 creator_id: str) -> None:
        """Add or update a quiz."""
        self.logger.debug(f"Adding quiz with ID: {quiz_id}")
        quiz_data["creator_id"] = creator_id
        filepath = f"quizzes/{quiz_id}.json"
        self._write_json(filepath, quiz_data)

    # Results
    def get_results(self, user_id: str, quiz_id: str,
                    session_id: str) -> Optional[Dict[str, Any]]:
        """Fetch results for a specific user, quiz, and session."""
        self.logger.debug(
            f"Fetching results for user {user_id}, quiz {quiz_id}, session {session_id}")
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

    def add_results(self, user_id: str, quiz_id: str,
                    session_id: str, results: Dict[str, Any]) -> None:
        """Add or update results."""
        self.logger.debug(
            f"Adding results for user {user_id}, quiz {quiz_id}, session {session_id}")
        results["timestamp"] = datetime.now().isoformat()
        if user_id not in self.results:
            self.results[user_id] = {}
        if quiz_id not in self.results[user_id]:
            self.results[user_id][quiz_id] = {}
        self.results[user_id][quiz_id][session_id] = results
        filepath = f"results/{user_id}/{quiz_id}_{session_id}_results.json"
        self._write_json(filepath, results)

    def get_all_results(self) -> Dict[str, Dict[str, Any]]:
        """Fetch all results."""
        self.logger.debug("Fetching all results")
        results_by_user = {}
        for user_id, quizzes in self.results.items():
            if user_id not in results_by_user:
                results_by_user[user_id] = {}
            for quiz_id, sessions in quizzes.items():
                if quiz_id not in results_by_user[user_id]:
                    results_by_user[user_id][quiz_id] = {}
                for session_id, result in sessions.items():
                    results_by_user[user_id][quiz_id][session_id] = {
                        "user_id": user_id,
                        "quiz_id": quiz_id,
                        "session_id": session_id,
                        "scores": result.get("scores", {}),
                        "answers": result.get("answers", {}),
                        "timestamp": result.get("timestamp")
                    }
        return results_by_user

    def get_results_by_quiz(self, quiz_id: str) -> Dict[str, Dict[str, Any]]:
        """Fetch results for a specific quiz."""
        self.logger.debug(f"Fetching results by quiz ID: {quiz_id}")
        results_by_user = {}
        for user_id, quizzes in self.results.items():
            if quiz_id in quizzes:
                self.logger.info(
                    f"User {user_id} participated in quiz {quiz_id}")
                self.logger.debug(f"Quizzes: {quizzes}")
                for session_id, result in quizzes[quiz_id].items():
                    if user_id not in results_by_user:
                        results_by_user[user_id] = {}
                    results_by_user[user_id][session_id] = {
                        "user_id": user_id,
                        "quiz_id": quiz_id,
                        "session_id": session_id,
                        "scores": result.get("scores", {}) if result else {},
                        "answers": result.get("answers", {}) if result else {},
                        "timestamp": result.get("timestamp") if result else {}
                    }
        return results_by_user

    def get_results_by_user(self, user_id: str) -> Dict[str, Dict[str, Any]]:
        """Fetch results for a specific user."""
        self.logger.debug(f"Fetching results by user ID: {user_id}")
        results_by_quiz = {}
        for quiz_id, sessions in self.results.get(user_id, {}).items():
            for session_id, result in sessions.items():
                if quiz_id not in results_by_quiz:
                    results_by_quiz[quiz_id] = {}
                results_by_quiz[quiz_id][session_id] = {
                    "user_id": user_id,
                    "quiz_id": quiz_id,
                    "session_id": session_id,
                    "scores": result.get("scores", {}),
                    "answers": result.get("answers", {}),
                    "timestamp": result.get("timestamp")
                }
        return results_by_quiz

    def get_results_by_quiz_and_user(
            self, quiz_id: str, user_id: str) -> Dict[str, Dict[str, Any]]:
        """Fetch results for a specific quiz and user."""
        self.logger.debug(
            f"Fetching results for quiz ID: {quiz_id} and user ID: {user_id}")
        results_by_session = {}
        for session_id, result in self.results.get(
                user_id, {}).get(quiz_id, {}).items():
            results_by_session[session_id] = {
                "user_id": user_id,
                "quiz_id": quiz_id,
                "session_id": session_id,
                "scores": result.get("scores", {}),
                "answers": result.get("answers", {}),
                "timestamp": result.get("timestamp")
            }
        return results_by_session

    # Tokens
    def get_tokens(self) -> List[Dict[str, Any]]:
        """Fetch all tokens."""
        self.logger.debug("Fetching all tokens")
        return self.tokens

    def add_tokens(self, tokens: List[Dict[str, Any]]) -> None:
        """Add or update tokens."""
        self.logger.debug(f"Adding tokens: {tokens}")
        self.tokens.extend(tokens)
        self._save("tokens.json", self.tokens)

    def remove_token(self, token: str) -> None:
        """Remove a token."""
        self.logger.debug(f"Removing token: {token}")
        self.tokens = [t for t in self.tokens if t["token"] != token]
        self._save("tokens.json", self.tokens)

    def get_all_tokens(self) -> Dict[str, List[Dict[str, Any]]]:
        """Fetch all tokens grouped by quiz."""
        self.logger.debug("Fetching all tokens grouped by quiz")
        tokens_by_quiz = {}
        for token_entry in self.tokens:
            quiz_id = token_entry["quiz_id"]
            if quiz_id not in tokens_by_quiz:
                tokens_by_quiz[quiz_id] = []
            tokens_by_quiz[quiz_id].append(token_entry)
        return tokens_by_quiz

    def get_tokens_by_quiz(self, quiz_id: str) -> List[Dict[str, Any]]:
        """Fetch tokens for a specific quiz."""
        self.logger.debug(f"Fetching tokens for quiz ID: {quiz_id}")
        return [token for token in self.tokens if token["quiz_id"] == quiz_id]

    def get_token_type(self, token: str) -> Optional[str]:
        """Fetch the type of a token."""
        self.logger.debug(f"Fetching token type for token: {token}")
        for token_entry in self.tokens:
            if token_entry["token"] == token:
                return token_entry["type"]
        return None

    def user_has_permission_for_quiz_creation(self, user_id: str) -> bool:
        """Check if a user has permission to create quizzes."""
        self.logger.debug(
            f"Checking if user {user_id} has permission for quiz creation")
        user = self.users.get(user_id)
        if user and "create" in user.get("permissions", []):
            return True
        return False

    def get_participated_users(self, quiz_id: str) -> List[str]:
        """Fetch users who participated in a specific quiz."""
        self.logger.debug(
            f"Fetching users who participated in quiz ID: {quiz_id}")
        participated_users = []
        for user_id, quizzes in self.results.items():
            if quiz_id in quizzes:
                participated_users.append(user_id)
        return participated_users

    def get_quiz_id_by_token(self, token: str) -> Optional[str]:
        """Fetch the quiz ID associated with a token."""
        self.logger.debug(f"Fetching quiz ID for token: {token}")
        for token_entry in self.tokens:
            if token_entry["token"] == token:
                return token_entry["quiz_id"]
        return None

    def get_all_quizzes(self) -> Dict[str, Dict[str, Any]]:
        """Fetch all quizzes."""
        self.logger.debug("Fetching all quizzes")
        quizzes_dir = os.path.join(self.base_dir, "quizzes")
        quizzes = {}
        for quiz_file in os.listdir(quizzes_dir):
            if quiz_file.endswith(".json"):
                quiz_id = os.path.splitext(quiz_file)[0]
                quizzes[quiz_id] = self.get_quiz(quiz_id)
        return quizzes

    def get_results_by_user_and_quiz(
            self, user_id: str, quiz_id: str) -> Dict[str, Dict[str, Any]]:
        """Fetch results for a specific user and quiz."""
        self.logger.debug(
            f"Fetching results for user ID: {user_id} and quiz ID: {quiz_id}")
        return self.results.get(user_id, {}).get(quiz_id, {})

    def get_session_ids_by_user_and_quiz(
            self, user_id: str, quiz_id: str) -> List[str]:
        """Fetch session IDs for a specific user and quiz."""
        self.logger.debug(
            f"Fetching session IDs for user ID: {user_id} and quiz ID: {quiz_id}")
        return list(self.results.get(user_id, {}).get(quiz_id, {}).keys())

    # Sessions
    def get_all_sessions(self) -> Dict[str, List[str]]:
        """Fetch all sessions grouped by user."""
        self.logger.debug("Fetching all sessions grouped by user")
        sessions_by_user = {}
        for user_id, quizzes in self.results.items():
            sessions_by_user[user_id] = []
            for quiz_id, sessions in quizzes.items():
                sessions_by_user[user_id].extend(sessions.keys())
        return sessions_by_user

    def get_sessions_by_user(self, user_id: str) -> List[str]:
        """Fetch sessions for a specific user."""
        self.logger.debug(f"Fetching sessions for user ID: {user_id}")
        sessions = []
        for quiz_id, quiz_sessions in self.results.get(user_id, {}).items():
            sessions.extend(quiz_sessions.keys())
        return sessions

    def get_sessions_by_quiz(self, quiz_id: str) -> List[str]:
        """Fetch sessions for a specific quiz."""
        self.logger.debug(f"Fetching sessions for quiz ID: {quiz_id}")
        sessions = []
        for user_id, quizzes in self.results.items():
            if quiz_id in quizzes:
                sessions.extend(quizzes[quiz_id].keys())
        return sessions

    def get_sessions_by_quiz_and_user(
            self, quiz_id: str, user_id: str) -> List[str]:
        """Fetch sessions for a specific quiz and user."""
        self.logger.debug(
            f"Fetching sessions for quiz ID: {quiz_id} and user ID: {user_id}")
        return list(self.results.get(user_id, {}).get(quiz_id, {}).keys())

    def save_session_state(self, session_data: Dict[str, Any]) -> None:
        """
        Save complete session state to filesystem.

        Args:
            session_data: Dictionary containing session metadata and engine state
        """
        session_id = session_data["session_id"]
        filepath = f"sessions/{session_id}.json"
        self._write_json(filepath, session_data)
        self.logger.info(f"Saved session state for session {session_id}")

    def load_session_state(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Load session state from filesystem.

        Args:
            session_id: Unique session identifier

        Returns:
            Session data dictionary or None if not found
        """
        filepath = f"sessions/{session_id}.json"
        try:
            session_data = self._read_json(filepath)
            self.logger.debug(f"Loaded session state for session {session_id}")
            return session_data
        except FileNotFoundError:
            self.logger.warning(f"Session {session_id} not found")
            return None

    def update_session_state(self, session_id: str,
                             session_data: Dict[str, Any]) -> None:
        """
        Update existing session state in filesystem.

        Args:
            session_id: Unique session identifier
            session_data: Updated session data dictionary
        """
        # For file storage, update is the same as save
        self.save_session_state(session_data)
        self.logger.debug(f"Updated session state for session {session_id}")

    def delete_session_state(self, session_id: str) -> None:
        """
        Delete session state file.

        Args:
            session_id: Unique session identifier
        """
        filepath = os.path.join(
            self.base_dir, "sessions", f"{session_id}.json")
        if os.path.exists(filepath):
            os.remove(filepath)
            self.logger.info(f"Deleted session state for session {session_id}")
        else:
            self.logger.warning(
                f"Attempted to delete non-existent session {session_id}")

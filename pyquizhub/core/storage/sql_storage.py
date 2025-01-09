from sqlalchemy import create_engine, MetaData, Table, Column, String, JSON, select, insert, update, delete
from sqlalchemy.exc import IntegrityError
from typing import Any, Dict, List, Optional
from datetime import datetime
from .storage_manager import StorageManager


class SQLStorageManager(StorageManager):
    def __init__(self, connection_string: str):
        self.engine = create_engine(connection_string)
        self.metadata = MetaData()

        # Define tables
        self.users_table = Table(
            "users", self.metadata,
            Column("id", String, primary_key=True),
            Column("permissions", JSON)
        )
        self.quizzes_table = Table(
            "quizzes", self.metadata,
            Column("id", String, primary_key=True),
            Column("creator_id", String),
            Column("data", JSON)
        )
        self.results_table = Table(
            "results", self.metadata,
            Column("user_id", String, primary_key=True),
            Column("quiz_id", String, primary_key=True),
            Column("session_id", String, primary_key=True),
            Column("scores", JSON),
            Column("answers", JSON),
            Column("timestamp", String)
        )
        self.tokens_table = Table(
            "tokens", self.metadata,
            Column("token", String, primary_key=True),
            Column("quiz_id", String),
            Column("type", String)
        )

        # Create tables if they don't exist
        self.metadata.create_all(self.engine)

    def _execute(self, query):
        with self.engine.connect() as conn:
            result = conn.execute(query)
            conn.commit()  # Ensure changes are saved
            return result

    def get_users(self) -> Dict[str, Any]:
        query = select(self.users_table)
        result = self._execute(query)
        return {row._mapping["id"]: row._mapping["permissions"] for row in result}

    def add_users(self, users: Dict[str, Any]) -> None:
        for user_id, permissions in users.items():
            query = insert(self.users_table).values(
                id=user_id, permissions=permissions)
            try:
                self._execute(query)
            except IntegrityError:
                query = update(self.users_table).where(
                    self.users_table.c.id == user_id
                ).values(permissions=permissions)
                self._execute(query)

    def get_quiz(self, quiz_id: str) -> Dict[str, Any]:
        query = select(self.quizzes_table).where(
            self.quizzes_table.c.id == quiz_id)
        result = self._execute(query).fetchone()
        if not result:
            raise FileNotFoundError(f"Quiz {quiz_id} not found.")
        return result._mapping["data"]

    def add_quiz(self, quiz_id: str, quiz_data: Dict[str, Any], creator_id: str) -> None:
        query = insert(self.quizzes_table).values(
            id=quiz_id, creator_id=creator_id, data=quiz_data)
        try:
            self._execute(query)
        except IntegrityError:
            query = update(self.quizzes_table).where(
                self.quizzes_table.c.id == quiz_id
            ).values(creator_id=creator_id, data=quiz_data)
            self._execute(query)

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
                    'answers': <answers_dict>
                }
                or None if the results file does not exist.
        """
        query = select(self.results_table).where(
            self.results_table.c.user_id == user_id,
            self.results_table.c.quiz_id == quiz_id,
            self.results_table.c.session_id == session_id
        )
        result = self._execute(query).fetchone()
        return dict(result._mapping) if result else None

    def add_results(self, user_id: str, quiz_id: str, session_id: str, results: Dict[str, Any]) -> None:
        results["timestamp"] = datetime.now().isoformat()
        query = insert(self.results_table).values(
            user_id=user_id, quiz_id=quiz_id, session_id=session_id, scores=results[
                "scores"], answers=results["answers"], timestamp=results["timestamp"]
        )
        try:
            self._execute(query)
        except IntegrityError:
            query = update(self.results_table).where(
                self.results_table.c.user_id == user_id,
                self.results_table.c.quiz_id == quiz_id,
                self.results_table.c.session_id == session_id
            ).values(scores=results["scores"], answers=results["answers"], timestamp=results["timestamp"])
            self._execute(query)

    def get_tokens(self) -> List[Dict[str, Any]]:
        query = select(self.tokens_table)
        result = self._execute(query)
        return [dict(row._mapping) for row in result]

    def add_tokens(self, tokens: List[Dict[str, Any]]) -> None:
        for token in tokens:
            query = insert(self.tokens_table).values(token)
            try:
                self._execute(query)
            except IntegrityError:
                query = update(self.tokens_table).where(
                    self.tokens_table.c.token == token["token"]
                ).values(quiz_id=token["quiz_id"], type=token["type"])
                self._execute(query)

    def remove_token(self, token: str) -> None:
        query = delete(self.tokens_table).where(
            self.tokens_table.c.token == token)
        self._execute(query)

    def get_all_tokens(self) -> Dict[str, List[Dict[str, Any]]]:
        query = select(self.tokens_table)
        result = self._execute(query)
        tokens_by_quiz = {}
        for row in result:
            quiz_id = row._mapping["quiz_id"]
            if quiz_id not in tokens_by_quiz:
                tokens_by_quiz[quiz_id] = []
            tokens_by_quiz[quiz_id].append(dict(row._mapping))
        return tokens_by_quiz

    def get_tokens_by_quiz(self, quiz_id: str) -> List[Dict[str, Any]]:
        query = select(self.tokens_table).where(
            self.tokens_table.c.quiz_id == quiz_id)
        result = self._execute(query)
        return [dict(row._mapping) for row in result]

    def get_token_type(self, token: str) -> Optional[str]:
        query = select(self.tokens_table.c.type).where(
            self.tokens_table.c.token == token
        )
        result = self._execute(query).fetchone()
        return result._mapping["type"] if result else None

    def get_participated_users(self, quiz_id: str) -> List[str]:
        query = select(self.results_table.c.user_id).where(
            self.results_table.c.quiz_id == quiz_id
        )
        result = self._execute(query)
        return [row._mapping["user_id"] for row in result]

    def user_has_permission_for_quiz_creation(self, user_id: str) -> bool:
        query = select(self.users_table.c.permissions).where(
            self.users_table.c.id == user_id)
        result = self._execute(query).fetchone()
        if result and "create" in result._mapping["permissions"]:
            return True
        return False

    def get_quiz_id_by_token(self, token: str) -> Optional[str]:
        query = select(self.tokens_table.c.quiz_id).where(
            self.tokens_table.c.token == token)
        result = self._execute(query).fetchone()
        return result._mapping["quiz_id"] if result else None

    def get_all_quizzes(self) -> Dict[str, Dict[str, Any]]:
        query = select(self.quizzes_table)
        result = self._execute(query)
        return {row._mapping["id"]: dict(row._mapping) for row in result}

    def get_all_results(self) -> Dict[str, Dict[str, Any]]:
        query = select(self.results_table)
        result = self._execute(query)
        results_by_user = {}
        for row in result:
            user_id = row._mapping["user_id"]
            if user_id not in results_by_user:
                results_by_user[user_id] = {}
            quiz_id = row._mapping["quiz_id"]
            if quiz_id not in results_by_user[user_id]:
                results_by_user[user_id][quiz_id] = {}
            session_id = row._mapping["session_id"]
            results_by_user[user_id][quiz_id][session_id] = dict(row._mapping)
        return results_by_user

    def get_results_by_quiz(self, quiz_id: str) -> Dict[str, Dict[str, Any]]:
        query = select(self.results_table).where(
            self.results_table.c.quiz_id == quiz_id
        )
        result = self._execute(query)
        results_by_user = {}
        for row in result:
            user_id = row._mapping["user_id"]
            session_id = row._mapping["session_id"]
            if user_id not in results_by_user:
                results_by_user[user_id] = {}
            results_by_user[user_id][session_id] = {
                "user_id": user_id,
                "quiz_id": quiz_id,
                "session_id": session_id,
                "scores": row._mapping["scores"],
                "answers": row._mapping["answers"],
                "timestamp": row._mapping["timestamp"]
            }
        return results_by_user

    def get_results_by_user(self, user_id: str) -> Dict[str, Dict[str, Any]]:
        query = select(self.results_table).where(
            self.results_table.c.user_id == user_id
        )
        result = self._execute(query)
        results_by_quiz = {}
        for row in result:
            quiz_id = row._mapping["quiz_id"]
            session_id = row._mapping["session_id"]
            if quiz_id not in results_by_quiz:
                results_by_quiz[quiz_id] = {}
            results_by_quiz[quiz_id][session_id] = {
                "user_id": user_id,
                "quiz_id": quiz_id,
                "session_id": session_id,
                "scores": row._mapping["scores"],
                "answers": row._mapping["answers"],
                "timestamp": row._mapping["timestamp"]
            }
        return results_by_quiz

    def get_results_by_user_and_quiz(self, user_id: str, quiz_id: str) -> Dict[str, Dict[str, Any]]:
        query = select(self.results_table).where(
            self.results_table.c.user_id == user_id,
            self.results_table.c.quiz_id == quiz_id
        )
        result = self._execute(query)
        return {row._mapping["session_id"]: dict(row._mapping) for row in result}

    def get_results_by_quiz_and_user(self, quiz_id: str, user_id: str) -> Dict[str, Dict[str, Any]]:
        query = select(self.results_table).where(
            self.results_table.c.quiz_id == quiz_id,
            self.results_table.c.user_id == user_id
        )
        result = self._execute(query)
        return {row._mapping["session_id"]: dict(row._mapping) for row in result}

    def get_session_ids_by_user_and_quiz(self, user_id: str, quiz_id: str) -> List[str]:
        query = select(self.results_table.c.session_id).where(
            self.results_table.c.user_id == user_id,
            self.results_table.c.quiz_id == quiz_id
        )
        result = self._execute(query)
        return [row._mapping["session_id"] for row in result]

    def get_all_sessions(self) -> Dict[str, List[str]]:
        query = select(self.results_table)
        result = self._execute(query)
        sessions_by_user = {}
        for row in result:
            user_id = row._mapping["user_id"]
            if user_id not in sessions_by_user:
                sessions_by_user[user_id] = []
            sessions_by_user[user_id].append(row._mapping["session_id"])
        return sessions_by_user

    def get_sessions_by_user(self, user_id: str) -> List[str]:
        query = select(self.results_table.c.session_id).where(
            self.results_table.c.user_id == user_id
        )
        result = self._execute(query)
        return [row._mapping["session_id"] for row in result]

    def get_sessions_by_quiz(self, quiz_id: str) -> List[str]:
        query = select(self.results_table.c.session_id).where(
            self.results_table.c.quiz_id == quiz_id
        )
        result = self._execute(query)
        return [row._mapping["session_id"] for row in result]

    def get_sessions_by_quiz_and_user(self, quiz_id: str, user_id: str) -> List[str]:
        query = select(self.results_table.c.session_id).where(
            self.results_table.c.quiz_id == quiz_id,
            self.results_table.c.user_id == user_id
        )
        result = self._execute(query)
        return [row._mapping["session_id"] for row in result]

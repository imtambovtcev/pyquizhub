from sqlalchemy import create_engine, MetaData, Table, Column, String, JSON, select, insert, update
from sqlalchemy.exc import IntegrityError
from typing import Any, Dict, List, Optional
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
            Column("scores", JSON),
            Column("answers", JSON)
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
        query = select(self.results_table).where(
            self.results_table.c.user_id == user_id,
            self.results_table.c.quiz_id == quiz_id
        )
        result = self._execute(query).fetchone()
        return dict(result._mapping) if result else None

    def add_results(self, user_id: str, quiz_id: str, results: Dict[str, Any]) -> None:
        query = insert(self.results_table).values(
            user_id=user_id, quiz_id=quiz_id, scores=results["scores"], answers=results["answers"]
        )
        try:
            self._execute(query)
        except IntegrityError:
            query = update(self.results_table).where(
                self.results_table.c.user_id == user_id,
                self.results_table.c.quiz_id == quiz_id
            ).values(scores=results["scores"], answers=results["answers"])
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

"""
SQL storage manager implementation.

This module provides an implementation of the StorageManager interface using
an SQL database for persistent storage of users, quizzes, tokens, results, and sessions.
"""

from sqlalchemy import create_engine, MetaData, Table, Column, String, JSON, select, insert, update, delete, inspect
from sqlalchemy.exc import IntegrityError
from typing import Any, Dict, List, Optional
from datetime import datetime
from .storage_manager import StorageManager
import logging


class SQLStorageManager(StorageManager):
    """
    SQL storage manager for managing users, quizzes, tokens, results, and sessions.

    This class provides methods to interact with an SQL database for storing and
    retrieving quiz-related data.
    """

    def __init__(self, connection_string: str):
        """
        Initialize the SQLStorageManager with a database connection string.

        Args:
            connection_string (str): Database connection string
        """
        self.logger = logging.getLogger(__name__)
        self.logger.debug(
            f"Initializing SQLStorageManager with connection string: {connection_string}")
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
        self.sessions_table = Table(
            "sessions", self.metadata,
            Column("session_id", String, primary_key=True),
            Column("user_id", String),
            Column("quiz_id", String),
            Column("current_question_id", JSON),
            Column("scores", JSON),
            Column("answers", JSON),
            Column("completed", String),
            Column("created_at", String),
            Column("updated_at", String),
            Column("api_data", JSON)
        )

        # Create tables if they don't exist
        self.metadata.create_all(self.engine)
        # Determine whether the sessions table actually has the api_data column
        try:
            inspector = inspect(self.engine)
            cols = [c["name"] for c in inspector.get_columns("sessions")]
            self._sessions_has_api_data = "api_data" in cols
            if not self._sessions_has_api_data:
                self.logger.info(
                    "Detected sessions table without 'api_data' column; running in compatibility mode")
        except Exception:
            # If introspection fails, assume column exists (safe default)
            self._sessions_has_api_data = True

    def _execute(self, query):
        """
        Execute a database query.

        Args:
            query: SQLAlchemy query object

        Returns:
            Result of the query execution
        """
        self.logger.debug(f"Executing query: {query}")
        with self.engine.connect() as conn:
            result = conn.execute(query)
            conn.commit()  # Ensure changes are saved
            return result

    def get_users(self) -> Dict[str, Any]:
        """Fetch all users."""
        self.logger.debug("Fetching all users")
        query = select(self.users_table)
        result = self._execute(query)
        return {row._mapping["id"]: row._mapping["permissions"]
                for row in result}

    def add_users(self, users: Dict[str, Any]) -> None:
        """Add or update users."""
        self.logger.debug(f"Adding users: {users}")
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
        """Fetch a quiz by its ID."""
        self.logger.debug(f"Fetching quiz with ID: {quiz_id}")
        query = select(self.quizzes_table).where(
            self.quizzes_table.c.id == quiz_id)
        result = self._execute(query).fetchone()
        if not result:
            raise FileNotFoundError(f"Quiz {quiz_id} not found.")
        return result._mapping["data"]

    def add_quiz(self,
                 quiz_id: str,
                 quiz_data: Dict[str,
                                 Any],
                 creator_id: str) -> None:
        """Add or update a quiz."""
        self.logger.debug(f"Adding quiz with ID: {quiz_id}")
        query = insert(self.quizzes_table).values(
            id=quiz_id, creator_id=creator_id, data=quiz_data)
        try:
            self._execute(query)
        except IntegrityError:
            query = update(self.quizzes_table).where(
                self.quizzes_table.c.id == quiz_id
            ).values(creator_id=creator_id, data=quiz_data)
            self._execute(query)

    def get_results(self, user_id: str, quiz_id: str,
                    session_id: str) -> Optional[Dict[str, Any]]:
        """Fetch results for a specific user, quiz, and session."""
        self.logger.debug(
            f"Fetching results for user {user_id}, quiz {quiz_id}, session {session_id}")
        query = select(self.results_table).where(
            self.results_table.c.user_id == user_id,
            self.results_table.c.quiz_id == quiz_id,
            self.results_table.c.session_id == session_id
        )
        result = self._execute(query).fetchone()
        return dict(result._mapping) if result else None

    def add_results(self, user_id: str, quiz_id: str,
                    session_id: str, results: Dict[str, Any]) -> None:
        """Add or update results."""
        self.logger.debug(
            f"Adding results for user {user_id}, quiz {quiz_id}, session {session_id}")
        results["timestamp"] = datetime.now().isoformat()
        query = insert(
            self.results_table).values(
            user_id=user_id,
            quiz_id=quiz_id,
            session_id=session_id,
            scores=results["scores"],
            answers=results["answers"],
            timestamp=results["timestamp"])
        try:
            self._execute(query)
        except IntegrityError:
            query = update(
                self.results_table).where(
                self.results_table.c.user_id == user_id,
                self.results_table.c.quiz_id == quiz_id,
                self.results_table.c.session_id == session_id).values(
                scores=results["scores"],
                answers=results["answers"],
                timestamp=results["timestamp"])
            self._execute(query)

    def get_tokens(self) -> List[Dict[str, Any]]:
        """Fetch all tokens."""
        self.logger.debug("Fetching all tokens")
        query = select(self.tokens_table)
        result = self._execute(query)
        return [dict(row._mapping) for row in result]

    def add_tokens(self, tokens: List[Dict[str, Any]]) -> None:
        """Add or update tokens."""
        self.logger.debug(f"Adding tokens: {tokens}")
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
        """Remove a token."""
        self.logger.debug(f"Removing token: {token}")
        query = delete(self.tokens_table).where(
            self.tokens_table.c.token == token)
        self._execute(query)

    def get_all_tokens(self) -> Dict[str, List[Dict[str, Any]]]:
        """Fetch all tokens grouped by quiz."""
        self.logger.debug("Fetching all tokens grouped by quiz")
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
        """Fetch tokens for a specific quiz."""
        self.logger.debug(f"Fetching tokens for quiz ID: {quiz_id}")
        query = select(self.tokens_table).where(
            self.tokens_table.c.quiz_id == quiz_id)
        result = self._execute(query)
        return [dict(row._mapping) for row in result]

    def get_token_type(self, token: str) -> Optional[str]:
        """Fetch the type of a token."""
        self.logger.debug(f"Fetching token type for token: {token}")
        query = select(self.tokens_table.c.type).where(
            self.tokens_table.c.token == token
        )
        result = self._execute(query).fetchone()
        return result._mapping["type"] if result else None

    def get_participated_users(self, quiz_id: str) -> List[str]:
        """Fetch users who participated in a specific quiz."""
        self.logger.debug(
            f"Fetching participated users for quiz ID: {quiz_id}")
        query = select(self.results_table.c.user_id).where(
            self.results_table.c.quiz_id == quiz_id
        )
        result = self._execute(query)
        return [row._mapping["user_id"] for row in result]

    def user_has_permission_for_quiz_creation(self, user_id: str) -> bool:
        """Check if a user has permission to create quizzes."""
        self.logger.debug(
            f"Checking if user {user_id} has permission for quiz creation")
        query = select(self.users_table.c.permissions).where(
            self.users_table.c.id == user_id)
        result = self._execute(query).fetchone()
        if result and "create" in result._mapping["permissions"]:
            return True
        return False

    def get_quiz_id_by_token(self, token: str) -> Optional[str]:
        """Fetch the quiz ID associated with a token."""
        self.logger.debug(f"Fetching quiz ID for token: {token}")
        query = select(self.tokens_table.c.quiz_id).where(
            self.tokens_table.c.token == token)
        result = self._execute(query).fetchone()
        return result._mapping["quiz_id"] if result else None

    def get_all_quizzes(self) -> Dict[str, Dict[str, Any]]:
        """Fetch all quizzes."""
        self.logger.debug("Fetching all quizzes")
        query = select(self.quizzes_table)
        result = self._execute(query)
        return {row._mapping["id"]: dict(row._mapping) for row in result}

    def get_all_results(self) -> Dict[str, Dict[str, Any]]:
        """Fetch all results."""
        self.logger.debug("Fetching all results")
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
        """Fetch results for a specific quiz."""
        self.logger.debug(f"Fetching results by quiz ID: {quiz_id}")
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
        """Fetch results for a specific user."""
        self.logger.debug(f"Fetching results by user ID: {user_id}")
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

    def get_results_by_user_and_quiz(
            self, user_id: str, quiz_id: str) -> Dict[str, Dict[str, Any]]:
        """Fetch results for a specific quiz and user."""
        self.logger.debug(
            f"Fetching results by user ID: {user_id} and quiz ID: {quiz_id}")
        query = select(self.results_table).where(
            self.results_table.c.user_id == user_id,
            self.results_table.c.quiz_id == quiz_id
        )
        result = self._execute(query)
        return {
            row._mapping["session_id"]: dict(
                row._mapping) for row in result}

    def get_results_by_quiz_and_user(
            self, quiz_id: str, user_id: str) -> Dict[str, Dict[str, Any]]:
        """Fetch results for a specific quiz and user."""
        self.logger.debug(
            f"Fetching results by quiz ID: {quiz_id} and user ID: {user_id}")
        query = select(self.results_table).where(
            self.results_table.c.quiz_id == quiz_id,
            self.results_table.c.user_id == user_id
        )
        result = self._execute(query)
        return {
            row._mapping["session_id"]: dict(
                row._mapping) for row in result}

    def get_session_ids_by_user_and_quiz(
            self, user_id: str, quiz_id: str) -> List[str]:
        """Fetch session IDs for a specific user and quiz."""
        self.logger.debug(
            f"Fetching session IDs by user ID: {user_id} and quiz ID: {quiz_id}")
        query = select(self.results_table.c.session_id).where(
            self.results_table.c.user_id == user_id,
            self.results_table.c.quiz_id == quiz_id
        )
        result = self._execute(query)
        return [row._mapping["session_id"] for row in result]

    def get_all_sessions(self) -> Dict[str, List[str]]:
        """Fetch all sessions."""
        self.logger.debug("Fetching all sessions")
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
        """Fetch sessions for a specific user."""
        self.logger.debug(f"Fetching sessions by user ID: {user_id}")
        query = select(self.results_table.c.session_id).where(
            self.results_table.c.user_id == user_id
        )
        result = self._execute(query)
        return [row._mapping["session_id"] for row in result]

    def get_sessions_by_quiz(self, quiz_id: str) -> List[str]:
        """Fetch sessions for a specific quiz."""
        self.logger.debug(f"Fetching sessions by quiz ID: {quiz_id}")
        query = select(self.results_table.c.session_id).where(
            self.results_table.c.quiz_id == quiz_id
        )
        result = self._execute(query)
        return [row._mapping["session_id"] for row in result]

    def get_sessions_by_quiz_and_user(
            self, quiz_id: str, user_id: str) -> List[str]:
        """Fetch sessions for a specific quiz and user."""
        self.logger.debug(
            f"Fetching sessions by quiz ID: {quiz_id} and user ID: {user_id}")
        query = select(self.results_table.c.session_id).where(
            self.results_table.c.quiz_id == quiz_id,
            self.results_table.c.user_id == user_id
        )
        result = self._execute(query)
        return [row._mapping["session_id"] for row in result]

    # Session State Management (for stateless engine)
    def save_session_state(self, session_data: Dict[str, Any]) -> None:
        """
        Save complete session state to database.

        Args:
            session_data: Dictionary containing session metadata and engine state
        """
        session_id = session_data["session_id"]
        query = insert(self.sessions_table).values(
            session_id=session_id,
            user_id=session_data["user_id"],
            quiz_id=session_data["quiz_id"],
            current_question_id=session_data["current_question_id"],
            scores=session_data["scores"],
            answers=session_data["answers"],
            completed=str(session_data["completed"]),
            created_at=session_data["created_at"],
            updated_at=session_data["updated_at"],
            api_data=session_data.get("api_data", {}) if getattr(
                self, "_sessions_has_api_data", True) else None
        )
        try:
            self._execute(query)
            self.logger.info(f"Saved session state for session {session_id}")
        except IntegrityError:
            # Session already exists, update instead
            self.update_session_state(session_id, session_data)
        except Exception as e:
            # Backwards compatibility: older databases may not have the api_data
            # column. If the insert fails due to a missing column, retry without
            # api_data to avoid failing the entire request.
            msg = str(e)
            if "api_data" in msg or "UndefinedColumn" in msg:
                self.logger.warning(
                    "api_data column missing in sessions table; retrying insert without api_data")
                fallback_query = insert(self.sessions_table).values(
                    session_id=session_id,
                    user_id=session_data["user_id"],
                    quiz_id=session_data["quiz_id"],
                    current_question_id=session_data["current_question_id"],
                    scores=session_data["scores"],
                    answers=session_data["answers"],
                    completed=str(session_data["completed"]),
                    created_at=session_data["created_at"],
                    updated_at=session_data["updated_at"]
                )
                try:
                    self._execute(fallback_query)
                    self.logger.info(
                        f"Saved session state for session {session_id} (without api_data)")
                except Exception:
                    # Re-raise original if fallback also fails
                    raise
            else:
                raise

    def load_session_state(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Load session state from database.

        Args:
            session_id: Unique session identifier

        Returns:
            Session data dictionary or None if not found
        """
        # Build select list conditionally depending on whether api_data column
        # exists in the sessions table (compatibility with old DBs).
        cols = [
            self.sessions_table.c.session_id,
            self.sessions_table.c.user_id,
            self.sessions_table.c.quiz_id,
            self.sessions_table.c.current_question_id,
            self.sessions_table.c.scores,
            self.sessions_table.c.answers,
            self.sessions_table.c.completed,
            self.sessions_table.c.created_at,
            self.sessions_table.c.updated_at,
        ]
        if getattr(self, "_sessions_has_api_data", True):
            cols.append(self.sessions_table.c.api_data)

        query = select(*cols).where(
            self.sessions_table.c.session_id == session_id
        )
        result = self._execute(query).fetchone()
        if not result:
            self.logger.warning(f"Session {session_id} not found")
            return None

        session_data = dict(result._mapping)
        # Convert 'completed' from string back to boolean
        session_data["completed"] = session_data["completed"] == "True"
        # Ensure api_data exists in returned dict for compatibility
        if "api_data" not in session_data:
            session_data["api_data"] = {}
        self.logger.debug(f"Loaded session state for session {session_id}")
        return session_data

    def update_session_state(self, session_id: str,
                             session_data: Dict[str, Any]) -> None:
        """
        Update existing session state in database.

        Args:
            session_id: Unique session identifier
            session_data: Updated session data dictionary
        """
        # Build update values conditionally depending on whether api_data exists
        values = dict(
            user_id=session_data["user_id"],
            quiz_id=session_data["quiz_id"],
            current_question_id=session_data["current_question_id"],
            scores=session_data["scores"],
            answers=session_data["answers"],
            completed=str(session_data["completed"]),
            created_at=session_data["created_at"],
            updated_at=session_data["updated_at"],
        )
        if getattr(self, "_sessions_has_api_data", True):
            values["api_data"] = session_data.get("api_data", {})

        query = update(self.sessions_table).where(
            self.sessions_table.c.session_id == session_id
        ).values(**values)
        try:
            self._execute(query)
            self.logger.debug(
                f"Updated session state for session {session_id}")
        except Exception as e:
            msg = str(e)
            if "api_data" in msg or "UndefinedColumn" in msg:
                self.logger.warning(
                    "api_data column missing in sessions table; retrying update without api_data")
                fallback_query = update(self.sessions_table).where(
                    self.sessions_table.c.session_id == session_id
                ).values(
                    user_id=session_data["user_id"],
                    quiz_id=session_data["quiz_id"],
                    current_question_id=session_data["current_question_id"],
                    scores=session_data["scores"],
                    answers=session_data["answers"],
                    completed=str(session_data["completed"]),
                    created_at=session_data["created_at"],
                    updated_at=session_data["updated_at"]
                )
                self._execute(fallback_query)
                self.logger.debug(
                    f"Updated session state for session {session_id} (without api_data)")
            else:
                raise

    def delete_session_state(self, session_id: str) -> None:
        """
        Delete session state from database.

        Args:
            session_id: Unique session identifier
        """
        query = delete(self.sessions_table).where(
            self.sessions_table.c.session_id == session_id
        )
        self._execute(query)
        self.logger.info(f"Deleted session state for session {session_id}")

"""
Core quiz engine implementation.

This module provides the main quiz engine functionality including:
- Quiz session management
- Question flow control 
- Score tracking
- Answer validation
- Question transitions
"""

import json
from .safe_evaluator import SafeEvaluator
from .json_validator import QuizJSONValidator
from pyquizhub.config.settings import get_logger


class QuizEngine:
    """
    Core quiz engine that manages quiz sessions and flow.

    This class handles:
    - Quiz data validation and loading
    - Session management for multiple users
    - Question progression logic
    - Score calculation
    - Answer processing

    Attributes:
        quiz (dict): The loaded and validated quiz data
        sessions (dict): Active quiz sessions by session ID
        logger: Logger instance for engine events
    """

    def __init__(self, quiz_data: dict):
        """
        Initialize the QuizEngine with quiz data.

        Args:
            quiz_data (dict): The quiz definition data to load

        Raises:
            ValueError: If quiz validation fails
        """
        self.quiz = self.load_quiz(quiz_data)
        self.sessions = {}
        self.logger = get_logger(__name__)

    def load_quiz(self, quiz_data: dict) -> dict:
        """
        Validate and load the quiz data.

        Args:
            quiz_data (dict): Quiz definition to validate and load

        Returns:
            dict: Validated quiz data

        Raises:
            ValueError: If quiz validation fails
        """
        validation_result = QuizJSONValidator.validate(quiz_data)
        if validation_result["errors"]:
            raise ValueError(
                f"Quiz validation failed: {validation_result['errors']}")
        return quiz_data

    def get_results(self, session_id: str) -> dict:
        """
        Get the current results for a quiz session.

        Args:
            session_id (str): ID of the quiz session

        Returns:
            dict: Session results containing:
                - scores (dict): Current score values
                - answers (list): List of provided answers

        Raises:
            ValueError: If session does not exist
        """
        session = self.sessions.get(session_id)
        if not session:
            raise ValueError("No active session for this session ID.")
        return {
            "scores": session["scores"],
            "answers": session["answers"]
        }

    def start_quiz(self, session_id: str) -> dict:
        """
        Start a new quiz session.

        Args:
            session_id (str): ID for the new session

        Returns:
            dict: First question data and metadata
        """
        if session_id in self.sessions:
            self.logger.warning(
                f"Quiz session already active for session {session_id}.")
            return {
                **self.get_current_question_id_and_data(session_id),
                "warning": "Quiz session already active for this session."
            }
        self.sessions[session_id] = {
            "current_question_id": self.quiz["questions"][0]["id"],
            "scores": {key: 0 for key in self.quiz.get("scores", {}).keys()},
            "answers": []
        }
        self.logger.info(f"Started quiz session {session_id}")
        return self.get_current_question(session_id)

    def get_current_question_id_and_data(self, session_id):
        question = self.get_current_question(session_id)

        if question is None:
            return None
        return {'id': question['id'], 'data': question['data']}

    def get_current_question(self, session_id: str) -> dict:
        """
        Get the current question for a session.

        Args:
            session_id (str): ID of the quiz session

        Returns:
            dict: Current question data or None if quiz is complete

        Raises:
            ValueError: If session or question not found
        """
        session = self.sessions.get(session_id)
        if not session:
            raise ValueError("No active session for this session ID.")
        question_id = session["current_question_id"]
        if question_id is None:
            return None  # Return None if the quiz is complete
        question = next(
            (q for q in self.quiz.get("questions", [])
             if q.get("id") == question_id), None
        )
        if not question:
            raise ValueError(f"Question with ID {question_id} not found.")
        self.logger.debug(f"Question {question_id}: {question}")
        return question

    def answer_question(self, session_id: str, answer: any) -> dict:
        """
        Process an answer and advance to next question.

        Args:
            session_id (str): ID of the quiz session
            answer: The provided answer value

        Returns:
            dict: Next question data or completion status

        Raises:
            ValueError: If session not found or answer invalid
        """
        session = self.sessions.get(session_id)
        if not session:
            raise ValueError("No active session for this session ID.")

        current_question = self.get_current_question(session_id)
        if current_question is None:
            return self.end_quiz(session_id)

        # Validate answer based on question type
        question_type = current_question["data"]["type"]
        try:
            if question_type == "integer":
                answer = int(answer)
            elif question_type == "float":
                answer = float(answer)
            elif question_type == "multiple_select":
                if not isinstance(answer, list):
                    raise ValueError(
                        "Answer must be a list of selected options.")
                for option in answer:
                    if option not in [opt["value"] for opt in current_question["data"]["options"]]:
                        raise ValueError(f"Invalid option selected: {option}")
            elif question_type == "multiple_choice":
                if answer not in [opt["value"] for opt in current_question["data"]["options"]]:
                    raise ValueError(f"Invalid option selected: {answer}")
        except ValueError as e:
            self.logger.error(
                f"Invalid answer for question {current_question['id']}: {e}")
            return {
                "id": current_question["id"],
                "data": current_question["data"],
                "error": str(e)
            }

        session["answers"].append(
            {"question_id": current_question["id"], "answer": answer}
        )

        # Update scores based on the answer
        for update in current_question.get("score_updates", []):
            condition = update.get("condition", "true")
            if SafeEvaluator.eval_expr(condition, {"answer": answer, **session["scores"]}):
                for score, expr in update.get("update", {}).items():
                    session["scores"][score] = SafeEvaluator.eval_expr(
                        expr, session["scores"])

        # Determine the next question
        next_question_id = self._get_next_question(
            current_question["id"], session["scores"]
        )

        self.logger.debug(f"Next question ID: {next_question_id}")

        if next_question_id is not None:
            session["current_question_id"] = next_question_id
            return self.get_current_question_id_and_data(session_id)
        else:
            session["current_question_id"] = None
            return self.end_quiz(session_id)

    def _get_next_question(self, current_question_id: str, scores: dict) -> str:
        """
        Determine the next question based on conditions.

        Args:
            current_question_id (str): ID of the current question
            scores (dict): Current session scores

        Returns:
            str: ID of next question or None if quiz complete
        """
        transitions = self.quiz.get("transitions", {}).get(
            str(current_question_id), [])
        for condition in transitions:
            expression = condition.get(
                "expression", "true")  # Default to "true"
            next_question_id = condition.get("next_question_id")
            if SafeEvaluator.eval_expr(expression, scores):
                return next_question_id
        return None

    def end_quiz(self, session_id: str) -> dict:
        """
        End a quiz session.

        Args:
            session_id (str): ID of the quiz session to end

        Returns:
            dict: Final quiz status message

        Raises:
            ValueError: If session not found
        """
        session = self.sessions.get(session_id)
        if not session:
            raise ValueError("No active session for this session ID.")
        self.logger.info(f"Ending quiz session {session_id}")
        return {'id': None,  'data': {"type": 'final_message', "text": "Quiz completed!" if session["current_question_id"] is None else "Quiz still in progress, but the quiz was terminated."}}

"""
Core quiz engine implementation.

This module provides the main quiz engine functionality including:
- Quiz logic processing (stateless)
- Question flow control 
- Score calculation
- Answer validation
- Question transitions

The engine is completely stateless - it doesn't store any session data.
All state is passed in and returned from methods.
"""

import json
from datetime import datetime
from typing import Optional, Dict, Any
from .safe_evaluator import SafeEvaluator
from .json_validator import QuizJSONValidator
from pyquizhub.config.settings import get_logger


class QuizEngine:
    """
    Pure quiz engine - only handles quiz logic.

    The engine is stateless and operates as a pure transformation:
    (quiz_definition, current_state, answer) → new_state

    It has no awareness of:
    - User IDs
    - Session IDs
    - Persistence
    - HTTP/networking

    This class handles:
    - Quiz data validation and loading
    - Question progression logic
    - Score calculation
    - Answer validation

    Attributes:
        quiz (dict): The loaded and validated quiz data
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

    def start_quiz(self) -> dict:
        """
        Create initial quiz state.

        Returns:
            dict: Initial state dictionary containing:
                - current_question_id: ID of the first question
                - scores: Dictionary of score keys initialized to 0
                - answers: Empty list for storing answers
                - completed: False (quiz not completed)
        """
        initial_state = {
            "current_question_id": self.quiz["questions"][0]["id"],
            "scores": {key: 0 for key in self.quiz.get("scores", {}).keys()},
            "answers": [],
            "completed": False
        }
        self.logger.info("Created initial quiz state")
        return initial_state

    def get_current_question(self, state: dict) -> Optional[dict]:
        """
        Get current question from state.

        Args:
            state: Current session state dict containing at minimum:
                - current_question_id: ID of current question

        Returns:
            Question data dictionary or None if quiz is completed

        Raises:
            ValueError: If question ID in state is not found in quiz
        """
        question_id = state["current_question_id"]
        if question_id is None:
            return None  # Quiz is complete
        
        question = next(
            (q for q in self.quiz.get("questions", [])
             if q.get("id") == question_id),
            None
        )
        
        if not question:
            raise ValueError(f"Question with ID {question_id} not found.")
        
        self.logger.debug(f"Retrieved question {question_id}")
        return question

    def answer_question(self, state: dict, answer: any) -> dict:
        """
        Process answer and return NEW state (pure function).

        This method does NOT mutate the input state. It creates and returns
        a new state dictionary with the updated values.

        Args:
            state: Current session state dict containing:
                - current_question_id: ID of current question
                - scores: Dictionary of current scores
                - answers: List of previous answers
                - completed: Boolean completion status
            answer: User's answer to the current question

        Returns:
            New state dictionary with:
                - Updated scores based on conditional logic
                - Answer recorded in answers list
                - Updated current_question_id
                - Updated completed status

        Raises:
            ValueError: If quiz is already completed or answer is invalid
        """
        # Get current question
        current_question = self.get_current_question(state)
        if current_question is None:
            raise ValueError("Quiz already completed")
        
        # Validate answer format
        self._validate_answer(current_question, answer)
        
        # Create new state (don't mutate input)
        new_state = {
            "current_question_id": state["current_question_id"],
            "scores": state["scores"].copy(),
            "answers": state["answers"].copy(),
            "completed": state["completed"]
        }
        
        # Update scores based on conditional logic
        score_updates = current_question.get("score_updates", [])
        for condition_group in score_updates:
            condition = condition_group.get("condition", "true")
            if SafeEvaluator.eval_expr(condition, {"answer": answer, **new_state["scores"]}):
                for score_key, expr in condition_group.get("update", {}).items():
                    new_state["scores"][score_key] = SafeEvaluator.eval_expr(
                        expr, new_state["scores"]
                    )
        
        # Record answer with timestamp
        new_state["answers"].append({
            "question_id": new_state["current_question_id"],
            "answer": answer,
            "timestamp": datetime.now().isoformat()
        })
        
        # Determine next question
        next_question_id = self._get_next_question(
            new_state["current_question_id"],
            new_state["scores"]
        )
        
        new_state["current_question_id"] = next_question_id
        new_state["completed"] = (next_question_id is None)
        
        self.logger.debug(
            f"Processed answer for question {current_question['id']}, "
            f"next question: {next_question_id}"
        )
        
        return new_state
    
    def _validate_answer(self, question: dict, answer: any) -> None:
        """
        Validate answer format based on question type.

        Args:
            question: Question dictionary containing type and validation rules
            answer: User's answer to validate

        Raises:
            ValueError: If answer format is invalid for the question type
        """
        question_type = question["data"]["type"]

        try:
            if question_type == "integer":
                int(answer)  # Validate can convert to int
            elif question_type == "multiple_select":
                if not isinstance(answer, list):
                    raise ValueError(
                        "Answer must be a list of selected options."
                    )
                valid_options = [
                    opt["value"]
                    for opt in question["data"]["options"]
                ]
                for option in answer:
                    if option not in valid_options:
                        raise ValueError(f"Invalid option selected: {option}")
            elif question_type == "multiple_choice":
                valid_options = [
                    opt["value"]
                    for opt in question["data"]["options"]
                ]
                if answer not in valid_options:
                    raise ValueError(f"Invalid option selected: {answer}")
        except (ValueError, TypeError) as e:
            self.logger.error(
                f"Invalid answer for question {question['id']}: {e}")
            raise ValueError(f"Invalid answer: {str(e)}")

    def _get_next_question(self, current_question_id: int, scores: dict) -> Optional[int]:
        """
        Determine next question based on transitions and scores.

        Args:
            current_question_id: ID of the current question
            scores: Dictionary of current score values

        Returns:
            ID of next question or None if quiz should end
        """
        transitions = self.quiz.get("transitions", {}).get(
            str(current_question_id), []
        )
        for transition in transitions:
            expression = transition.get("expression", "true")
            next_question_id = transition.get("next_question_id")
            if SafeEvaluator.eval_expr(expression, scores):
                return next_question_id
        return None

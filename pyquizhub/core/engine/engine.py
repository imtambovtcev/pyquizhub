"""
Core quiz engine implementation.

This module provides the main quiz engine functionality including:
- Quiz logic processing (stateless)
- Question flow control
- Score calculation
- Answer validation
- Question transitions
- External API integration

The engine is completely stateless - it doesn't store any session data.
All state is passed in and returned from methods.
"""

import json
from datetime import datetime
from typing import Optional, Dict, Any
from .safe_evaluator import SafeEvaluator
from .json_validator import QuizJSONValidator
from .api_integration import APIIntegrationManager, RequestTiming
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
        self.api_manager = APIIntegrationManager()

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
                - api_data: Dictionary for storing API responses (if quiz has API integrations)
                - api_credentials: Dictionary for storing dynamic API credentials
        """
        initial_state = {
            "current_question_id": self.quiz["questions"][0]["id"],
            "scores": {key: 0 for key in self.quiz.get("scores", {}).keys()},
            "answers": [],
            "completed": False,
            "api_data": {},
            "api_credentials": {}
        }

        # Execute ON_QUIZ_START API calls
        initial_state = self._execute_api_calls(
            initial_state,
            RequestTiming.ON_QUIZ_START,
            context={}
        )

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
                - api_data: Dictionary of API responses
                - api_credentials: Dictionary of API credentials
            answer: User's answer to the current question

        Returns:
            New state dictionary with:
                - Updated scores based on conditional logic
                - Answer recorded in answers list
                - Updated current_question_id
                - Updated completed status
                - Updated API data

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
            "completed": state["completed"],
            "api_data": state.get("api_data", {}).copy(),
            "api_credentials": state.get("api_credentials", {}).copy()
        }

        # Execute AFTER_ANSWER API calls
        context = {
            "question_id": new_state["current_question_id"],
            "answer": answer,
            **new_state["scores"]
        }
        new_state = self._execute_api_calls(
            new_state,
            RequestTiming.AFTER_ANSWER,
            context=context,
            question_id=new_state["current_question_id"]
        )

        # Update scores based on conditional logic
        score_updates = current_question.get("score_updates", [])
        for condition_group in score_updates:
            condition = condition_group.get("condition", "true")
            # Add API data to evaluation context
            eval_context = {
                "answer": answer,
                **new_state["scores"],
                "api": self._create_api_context(new_state)
            }
            if SafeEvaluator.eval_expr(condition, eval_context):
                for score_key, expr in condition_group.get("update", {}).items():
                    new_state["scores"][score_key] = SafeEvaluator.eval_expr(
                        expr, {
                            **new_state["scores"], "api": self._create_api_context(new_state)}
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

        # Execute BEFORE_QUESTION API calls for next question
        if next_question_id is not None:
            context = {
                "question_id": next_question_id,
                **new_state["scores"]
            }
            new_state = self._execute_api_calls(
                new_state,
                RequestTiming.BEFORE_QUESTION,
                context=context,
                question_id=next_question_id
            )
        else:
            # Execute ON_QUIZ_END API calls
            new_state = self._execute_api_calls(
                new_state,
                RequestTiming.ON_QUIZ_END,
                context={"final_scores": new_state["scores"]}
            )

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
            elif question_type == "float":
                float(answer)  # Validate can convert to float
            elif question_type == "multiple_select":
                if not isinstance(answer, list):
                    raise ValueError(
                        "Answer must be a list of selected options.")
                valid_options = [opt["value"]
                                 for opt in question["data"]["options"]]
                for option in answer:
                    if option not in valid_options:
                        raise ValueError(f"Invalid option selected: {option}")
            elif question_type == "multiple_choice":
                valid_options = [opt["value"]
                                 for opt in question["data"]["options"]]
                if answer not in valid_options:
                    raise ValueError(f"Invalid option selected: {answer}")
        except (ValueError, TypeError) as e:
            self.logger.error(
                f"Invalid answer for question {question['id']}: {e}")
            raise ValueError(f"Invalid answer: {str(e)}")

    def _get_next_question(
            self,
            current_question_id: int,
            scores: dict) -> Optional[int]:
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

    def _execute_api_calls(
        self,
        state: Dict[str, Any],
        timing: RequestTiming,
        context: Dict[str, Any],
        question_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Execute API calls for the given timing.

        Args:
            state: Current session state
            timing: When to execute (BEFORE_QUESTION, AFTER_ANSWER, etc.)
            context: Context data (scores, answer, etc.)
            question_id: Question ID (for question-specific API calls)

        Returns:
            Updated session state with API responses
        """
        # Get API configurations from quiz
        api_configs = self.quiz.get("api_integrations", [])

        for api_config in api_configs:
            # Check if this API call matches the timing
            if api_config.get("timing") != timing.value:
                continue

            # Check if this is question-specific
            if "question_id" in api_config:
                if api_config["question_id"] != question_id:
                    continue

            # Execute the API call
            try:
                state = self.api_manager.execute_api_call(
                    api_config,
                    state,
                    context
                )
            except Exception as e:
                self.logger.error(f"API call failed: {e}")
                # Continue with quiz even if API call fails

        return state

    def _create_api_context(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create API context for use in expressions.

        This allows accessing API data in conditions like:
        api.weather.temperature > 20

        Args:
            state: Current session state

        Returns:
            Dictionary of API data accessible by ID
        """
        api_context = {}
        api_data = state.get("api_data", {})

        for api_id, api_entry in api_data.items():
            if api_entry.get("success", False):
                api_context[api_id] = api_entry.get("response", {})

        return api_context

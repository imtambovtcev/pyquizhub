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

from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from .safe_evaluator import SafeEvaluator
from .json_validator import QuizJSONValidator
from .api_integration import APIIntegrationManager, RequestTiming
from pyquizhub.logging.setup import get_logger


class QuizEngine:
    """Stateless quiz engine.

    The engine is pure/functional: it accepts quiz data at construction and
    performs operations on explicit state dictionaries passed to its methods.

    Public contract (used by API layer):
    - __init__(quiz_data): load/validate quiz
    - start_quiz() -> state dict: create initial state
    - get_current_question(state) -> question dict | None
    - answer_question(state, answer) -> new state dict

    The engine will treat missing optional quiz fields (api_integrations,
    questions, scores, transitions) as empty collections to be defensive.
    """

    def __init__(self, quiz_data: dict):
        """Initialize engine and normalize quiz data."""
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
        if validation_result.get("errors"):
            raise ValueError(
                f"Quiz validation failed: {validation_result['errors']}")

        # Normalize optional fields to safe defaults so engine logic
        # can assume consistent types (avoid None where lists/dicts expected)
        if quiz_data.get("api_integrations") is None:
            quiz_data["api_integrations"] = []

        # Support both old (scores) and new (variables) formats
        if quiz_data.get("variables") is not None:
            # New format: extract default values from variables
            if quiz_data.get("scores") is None:
                quiz_data["scores"] = {}
            for var_name, var_config in quiz_data["variables"].items():
                # Use explicit default if provided, otherwise use type-based
                # defaults
                if "default" in var_config:
                    quiz_data["scores"][var_name] = var_config["default"]
                else:
                    # Fallback to type-based defaults
                    var_type = var_config.get("type", "integer")
                    if var_type == "integer":
                        quiz_data["scores"][var_name] = 0
                    elif var_type == "float":
                        quiz_data["scores"][var_name] = 0.0
                    elif var_type == "string":
                        quiz_data["scores"][var_name] = ""
                    elif var_type == "boolean":
                        quiz_data["scores"][var_name] = False
                    elif var_type == "array":
                        quiz_data["scores"][var_name] = []
        else:
            # Old format: just use scores
            if quiz_data.get("scores") is None:
                quiz_data["scores"] = {}

        if quiz_data.get("questions") is None:
            quiz_data["questions"] = []
        if quiz_data.get("transitions") is None:
            quiz_data["transitions"] = {}

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
        first_qs = self.quiz.get("questions", [])
        if not first_qs:
            raise ValueError("Quiz has no questions")

        initial_state = {
            "current_question_id": first_qs[0]["id"],
            "scores": self.quiz.get("scores", {}).copy(),
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

        # Execute BEFORE_QUESTION API calls for the first question
        first_question_id = initial_state["current_question_id"]
        initial_state = self._execute_api_calls(
            initial_state,
            RequestTiming.BEFORE_QUESTION,
            context={
                "question_id": first_question_id,
                **initial_state["scores"]},
            question_id=first_question_id)

        self.logger.info("Created initial quiz state")
        return initial_state

    def get_current_question(self, state: dict) -> dict | None:
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
        question_id = state.get("current_question_id")
        if question_id is None:
            return None  # Quiz is complete

        question = next(
            (q for q in self.quiz.get("questions", [])
             if q.get("id") == question_id),
            None
        )

        if not question:
            raise ValueError(f"Question with ID {question_id} not found.")

        # Apply templating to question text with API data
        question = self._apply_question_templating(question, state)

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
            "current_question_id": state.get("current_question_id"),
            "scores": state.get("scores", {}).copy(),
            "answers": state.get("answers", []).copy(),
            "completed": state.get("completed", False),
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
            api_context = self._create_api_context(new_state)
            self.logger.debug(f"API context for evaluation: {api_context}")
            self.logger.debug(
                f"Full api_data in state: {new_state.get('api_data', {})}")
            eval_context = {
                "answer": answer,
                **new_state["scores"],
                "api": api_context
            }
            self.logger.debug(f"Eval context: {eval_context}")
            if SafeEvaluator.eval_expr(condition, eval_context):
                for score_key, expr in condition_group.get(
                        "update", {}).items():
                    new_state["scores"][score_key] = SafeEvaluator.eval_expr(
                        expr, {
                            "answer": answer,
                            **new_state["scores"],
                            "api": self._create_api_context(new_state)}
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
            new_state["scores"],
            answer
        )

        new_state["current_question_id"] = next_question_id
        new_state["completed"] = (next_question_id is None)

        # Apply score_updates for final_message questions when transitioning to
        # them
        if next_question_id is not None:
            next_question = next(
                (q for q in self.quiz.get("questions", [])
                 if q.get("id") == next_question_id),
                None
            )
            if next_question and next_question.get(
                    "data", {}).get("type") == "final_message":
                # Apply score_updates for final_message without requiring an
                # answer
                score_updates = next_question.get("score_updates", [])
                for condition_group in score_updates:
                    condition = condition_group.get("condition", "true")
                    api_context = self._create_api_context(new_state)
                    eval_context = {
                        **new_state["scores"],
                        "api": api_context
                    }
                    if SafeEvaluator.eval_expr(condition, eval_context):
                        for score_key, expr in condition_group.get(
                                "update", {}).items():
                            new_state["scores"][score_key] = SafeEvaluator.eval_expr(
                                expr, {
                                    **new_state["scores"],
                                    "api": self._create_api_context(new_state)}
                            )

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
            scores: dict,
            answer: Any = None) -> int | None:
        """
        Determine next question based on transitions and scores.

        Args:
            current_question_id: ID of the current question
            scores: Dictionary of current score values
            answer: The answer to the current question (for transition conditions)

        Returns:
            ID of next question or None if quiz should end
        """
        transitions = self.quiz.get("transitions", {}).get(
            str(current_question_id), []
        )
        for transition in transitions:
            expression = transition.get("expression", "true")
            next_question_id = transition.get("next_question_id")
            # Include answer in context for transition expressions
            context = {
                "answer": answer,
                **scores} if answer is not None else scores
            if SafeEvaluator.eval_expr(expression, context):
                return next_question_id
        return None

    def _execute_api_calls(
        self,
        state: dict[str, Any],
        timing: RequestTiming,
        context: dict[str, Any],
        question_id: int | None = None
    ) -> dict[str, Any]:
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
        # Get API configurations from quiz (ensure iterable)
        api_configs = self.quiz.get("api_integrations") or []

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

    def _create_api_context(self, state: dict[str, Any]) -> dict[str, Any]:
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

        self.logger.debug(f"Creating API context from api_data: {api_data}")

        for api_id, api_entry in api_data.items():
            self.logger.debug(f"Processing API {api_id}: {api_entry}")
            if api_entry.get("success", False):
                api_context[api_id] = api_entry.get("response", {})
                self.logger.debug(
                    f"Added {api_id} to API context: {api_context[api_id]}")
            else:
                self.logger.warning(f"API {api_id} not successful, skipping")

        self.logger.debug(f"Final API context: {api_context}")
        return api_context

    def _apply_question_templating(
            self, question: dict[str, Any], state: dict[str, Any]) -> dict[str, Any]:
        """
        Apply templating to question text and image URLs by replacing placeholders.

        Replaces placeholders like:
        - {api.joke_api.setup} with actual API response data
        - {variables.var_name} with current variable values

        Args:
            question: Question dictionary
            state: Current session state with api_data and scores

        Returns:
            Question dictionary with templated text and image_url
        """
        import copy
        import re

        # Create a deep copy to avoid modifying the original question
        templated_question = copy.deepcopy(question)

        # Get API context
        api_context = self._create_api_context(state)

        # Get the question text and image_url
        question_text = templated_question.get("data", {}).get("text", "")
        image_url = templated_question.get("data", {}).get("image_url", "")

        # Apply templating to both text and image_url
        for field_name, field_value in [("text", question_text), ("image_url", image_url)]:
            if not field_value:
                continue

            # Find and replace {api.api_id.field} placeholders
            api_placeholders = re.findall(r'\{api\.([^}]+)\}', field_value)

            for placeholder in api_placeholders:
                # Split the placeholder into parts (e.g., "joke_api.setup" ->
                # ["joke_api", "setup"])
                parts = placeholder.split('.')
                api_id = parts[0]

                # Navigate through the API context
                value = api_context.get(api_id)
                for part in parts[1:]:
                    if isinstance(value, dict):
                        value = value.get(part)
                    else:
                        break

                # Replace the placeholder with the actual value
                if value is not None:
                    templated_question["data"][field_name] = templated_question["data"][field_name].replace(
                        f"{{api.{placeholder}}}",
                        str(value)
                    )
                    self.logger.debug(
                        f"Replaced {{api.{placeholder}}} in {field_name} with {value}")
                else:
                    self.logger.warning(
                        f"Could not resolve placeholder {{api.{placeholder}}} in {field_name}")

            # Find and replace {variables.var_name} placeholders
            var_placeholders = re.findall(r'\{variables\.([^}]+)\}', field_value)

            for var_name in var_placeholders:
                # Get variable value from state scores
                scores = state.get("scores", {})
                value = scores.get(var_name)

                # Replace the placeholder with the actual value
                if value is not None:
                    templated_question["data"][field_name] = templated_question["data"][field_name].replace(
                        f"{{variables.{var_name}}}",
                        str(value)
                    )
                    self.logger.debug(
                        f"Replaced {{variables.{var_name}}} in {field_name} with {value}")
                else:
                    self.logger.warning(
                        f"Could not resolve variable placeholder {{variables.{var_name}}} in {field_name}")

        return templated_question

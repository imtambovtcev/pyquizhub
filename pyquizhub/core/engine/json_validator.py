import json
from .safe_evaluator import SafeEvaluator
from pyquizhub.config.config_utils import get_logger

logger = get_logger(__name__)


class QuizJSONValidator:
    @staticmethod
    def validate(quiz_data):
        """
        Validate the JSON structure and contents, returning detailed validation results.

        Args:
            quiz_data (dict): The quiz data as a dictionary.

        Returns:
            dict: A dictionary containing 'errors' and 'warnings'.
        """
        logger.debug(f"Validating quiz data: {quiz_data}")
        errors = []
        warnings = []

        # Ensure the data is a dictionary
        if not isinstance(quiz_data, dict):
            errors.append("Top-level JSON structure must be a dictionary.")
            return {"errors": errors, "warnings": warnings}

        # Validate top-level keys
        required_keys = {"metadata", "scores", "questions", "transitions"}
        missing_keys = required_keys - quiz_data.keys()
        if missing_keys:
            errors.append(f"Missing required top-level keys: {missing_keys}")
            return {"errors": errors, "warnings": warnings}

        # Default variables for validation
        default_variables = quiz_data.get("scores", {}).copy()

        # Validate scores
        if not isinstance(quiz_data["scores"], dict):
            errors.append("The 'scores' field must be a dictionary.")
        elif "answer" in quiz_data["scores"]:
            errors.append(
                "The 'scores' field must not contain the special variable 'answer'.")

        # Validate questions
        question_ids = set()
        questions = quiz_data.get("questions", [])
        if not isinstance(questions, list):
            errors.append("The 'questions' field must be a list.")
            questions = []

        for question in questions:
            if not isinstance(question, dict):
                errors.append(f"Question must be a dictionary: {question}")
                continue

            if not all(key in question for key in ["id", "data"]):
                errors.append(f"Invalid question format: {question}")
                continue

            if question["id"] in question_ids:
                errors.append(f"Duplicate question ID found: {question['id']}")
            question_ids.add(question["id"])

            data = question["data"]
            if not isinstance(data, dict):
                errors.append(f"Question data must be a dictionary: {data}")
                continue

            if not all(key in data for key in ["text", "type"]):
                errors.append(f"Invalid question data format: {data}")
                continue

            current_answer_type = None
            if data["type"] == "multiple_choice":
                current_answer_type = str
                if "options" not in data:
                    errors.append(
                        f"Multiple choice question missing options: {data}")
            elif data["type"] == "multiple_select":
                current_answer_type = list
                if "options" not in data:
                    errors.append(
                        f"Multiple select question missing options: {data}")
            elif data["type"] == "text":
                current_answer_type = str
                if "options" in data:
                    errors.append(
                        f"Question type '{data['type']}' should not have options: {data}")
            elif data["type"] == "integer":
                current_answer_type = int
                if "options" in data:
                    errors.append(
                        f"Question type '{data['type']}' should not have options: {data}")
            elif data["type"] == "float":
                current_answer_type = float
                if "options" in data:
                    errors.append(
                        f"Question type '{data['type']}' should not have options: {data}")

            if "score_updates" in question:
                score_updates = question["score_updates"]
                if not isinstance(score_updates, list):
                    errors.append(
                        f"Score updates must be a list in question {question['id']}.")
                    continue
                for update in score_updates:
                    if not isinstance(update, dict):
                        errors.append(
                            f"Score update must be a dictionary in question {question['id']}.")
                        continue
                    if not all(key in update for key in ["condition", "update"]):
                        errors.append(
                            f"Invalid score update format in question {question['id']}: {update}")
                        continue
                    # Validate conditions and updates
                    try:

                        allowed_variables = {
                            **default_variables, "answer": current_answer_type()} if current_answer_type else default_variables
                        SafeEvaluator.eval_expr(
                            update["condition"], allowed_variables)
                        for expr in update["update"].values():
                            SafeEvaluator.eval_expr(
                                expr, allowed_variables)
                    except Exception as e:
                        errors.append(
                            f"Invalid score update condition or expression in question {question['id']}: {e}")

        # Validate transitions
        transitions = quiz_data.get("transitions", {})
        if not isinstance(transitions, dict):
            errors.append("The 'transitions' field must be a dictionary.")
            transitions = {}

        for question_id, conditions in transitions.items():
            if not isinstance(conditions, list):
                errors.append(
                    f"Transitions for question {question_id} must be a list.")
                continue

            trivial_condition_found = False
            for idx, condition in enumerate(conditions):
                if not isinstance(condition, dict):
                    errors.append(
                        f"Transition condition must be a dictionary in question {question_id}: {condition}")
                    continue

                expression = condition.get("expression", "true")
                next_question_id = condition.get("next_question_id")

                # Validate condition expression
                try:
                    SafeEvaluator.eval_expr(
                        expression, {**default_variables, "answer": current_answer_type()})
                except Exception as e:
                    errors.append(
                        f"Invalid transition expression in question {question_id}: {e}")
                    continue

                # Check for warnings
                if expression == "true":
                    trivial_condition_found = True
                elif trivial_condition_found:
                    warnings.append(
                        f"Non-trivial condition after trivial condition in question {question_id}."
                    )

                # Warn if there's no trivial condition at the end
                if idx == len(conditions) - 1 and expression != "true":
                    warnings.append(
                        f"Last condition in transitions for question {question_id} is not trivial, which may result in unexpected quiz termination."
                    )

                # Validate next_question_id
                if next_question_id is not None and next_question_id not in question_ids:
                    errors.append(
                        f"Invalid next_question_id in question {question_id}: {next_question_id} does not exist."
                    )

        return {"errors": errors, "warnings": warnings}

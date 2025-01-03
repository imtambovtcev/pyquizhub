import json
from .safe_evaluator import SafeEvaluator


class QuizJSONValidator:
    @staticmethod
    def validate(quiz_json):
        """Validate the JSON structure and contents."""
        with open(quiz_json, "r") as f:
            data = json.load(f)

        # Validate top-level keys
        required_keys = {"metadata", "scores", "questions", "transitions"}
        if not required_keys.issubset(data.keys()):
            raise ValueError("Missing required top-level keys.")

        # Default variables for validation
        default_variables = {"answer": None, **data.get("scores", {})}

        # Validate questions
        for question in data["questions"]:
            if "id" not in question or "text" not in question or "type" not in question:
                raise ValueError(f"Invalid question format: {question}")

            if question["type"] == "multiple_choice" and "options" not in question:
                raise ValueError(
                    f"Multiple choice question missing options: {question}")

            if "score_updates" in question:
                for update in question["score_updates"]:
                    if "condition" not in update or "update" not in update:
                        raise ValueError(
                            f"Invalid score update format: {update}")
                    # Validate conditions and updates
                    try:
                        SafeEvaluator.eval_expr(
                            update["condition"], default_variables)
                        for expr in update["update"].values():
                            SafeEvaluator.eval_expr(expr, default_variables)
                    except Exception as e:
                        raise ValueError(
                            f"Invalid score update condition or expression: {e}")

        # Validate transitions
        for transition in data["transitions"]:
            for condition in transition["conditions"]:
                if "expression" not in condition or "next_question_id" not in condition:
                    raise ValueError(f"Invalid transition format: {condition}")
                # Validate the condition expression
                try:
                    SafeEvaluator.eval_expr(
                        condition["expression"], default_variables)
                except Exception as e:
                    raise ValueError(f"Invalid transition expression: {e}")

        return True  # JSON is valid

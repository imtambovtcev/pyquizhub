import json
from .safe_evaluator import SafeEvaluator
from .json_validator import QuizJSONValidator


class QuizEngine:
    def __init__(self, quiz_json):
        self.quiz = None
        self.scores = {}
        self.current_question = None
        self.load_quiz(quiz_json)

    def load_quiz(self, quiz_json):
        """Load and initialize quiz from a JSON file."""
        try:
            with open(quiz_json, "r") as f:
                self.quiz = json.load(f)
        except Exception as e:
            raise ValueError(f"Failed to load quiz: {e}")

        # Ensure quiz passes validation
        QuizJSONValidator.validate(quiz_json)

        # Initialize scores
        self.scores = self.quiz.get("scores", {})

        # Start with the first question
        self.current_question = self.quiz["questions"][0]

    def get_current_question(self):
        """Return the current question."""
        return self.current_question

    def answer_question(self, answer):
        """Process the answer and update scores."""
        question = self.current_question
        for update in question.get("score_updates", []):
            if SafeEvaluator.eval_expr(update["condition"], {"answer": answer, **self.scores}):
                for score, expr in update["update"].items():
                    self.scores[score] = SafeEvaluator.eval_expr(
                        expr, self.scores)

        # Determine the next question
        self.current_question = self._get_next_question()

    def _get_next_question(self):
        """Determine the next question based on transitions."""
        for transition in self.quiz["transitions"]:
            for condition in transition["conditions"]:
                if SafeEvaluator.eval_expr(condition["expression"], self.scores):
                    next_question_id = condition["next_question_id"]
                    # Find the next question in the questions list
                    next_question = next(
                        (q for q in self.quiz["questions"]
                         if q["id"] == next_question_id),
                        None
                    )
                    if next_question:
                        return next_question
        return None  # No valid transition found, quiz ends

    def is_quiz_finished(self):
        """Check if the quiz has ended."""
        return self.current_question is None

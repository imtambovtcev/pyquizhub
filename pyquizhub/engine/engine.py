import json
from .safe_evaluator import SafeEvaluator
from .json_validator import QuizJSONValidator
import logging


class QuizEngine:
    def __init__(self, quiz_data):
        """Initialize the QuizEngine with quiz data."""
        self.quiz = self.load_quiz(quiz_data)
        self.sessions = {}  # Active user sessions

    def load_quiz(self, quiz_data):
        """Validate and load the quiz data."""
        validation_result = QuizJSONValidator.validate(quiz_data)
        if validation_result["errors"]:
            raise ValueError(
                f"Quiz validation failed: {validation_result['errors']}")
        return quiz_data

    def get_results(self, session_id):
        session = self.sessions.get(session_id)
        if not session:
            raise ValueError("No active session for this session ID.")
        return {
            "scores": session["scores"],
            "answers": session["answers"]
        }

    def start_quiz(self, session_id):
        if session_id in self.sessions:
            logging.warning(
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
        return self.get_current_question(session_id)

    def get_current_question_id_and_data(self, session_id):
        question = self.get_current_question(session_id)

        if question is None:
            return None
        return {'id': question['id'], 'data': question['data']}

    def get_current_question(self, session_id):
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
        print(f"Question {question_id}: {question}")
        return question

    def answer_question(self, session_id, answer):
        session = self.sessions.get(session_id)
        if not session:
            raise ValueError("No active session for this session ID.")

        current_question = self.get_current_question(session_id)
        if current_question is None:
            return self.end_quiz(session_id)

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

        print(f"Next question ID: {next_question_id}")

        if next_question_id is not None:
            session["current_question_id"] = next_question_id
            return self.get_current_question_id_and_data(session_id)
        else:
            session["current_question_id"] = None
            return self.end_quiz(session_id)

    def _get_next_question(self, current_question_id, scores):
        transitions = self.quiz.get("transitions", {}).get(
            str(current_question_id), [])
        for condition in transitions:
            expression = condition.get(
                "expression", "true")  # Default to "true"
            next_question_id = condition.get("next_question_id")
            if SafeEvaluator.eval_expr(expression, scores):
                return next_question_id
        return None

    def end_quiz(self, session_id):
        session = self.sessions.get(session_id)
        if not session:
            raise ValueError("No active session for this session ID.")
        return {'id': None,  'data': {"type": 'final_message', "text": "Quiz completed!" if session["current_question_id"] is None else "Quiz still in progress, but the quiz was terminated."}}

import pytest
from pyquizhub.core.engine.engine import QuizEngine
import json
import uuid
import os

# Load test quiz data


def load_quiz_data(file_path):
    with open(file_path, "r") as f:
        return json.load(f)

# Extract the correct answer from the quiz metadata


def extract_answer(quiz_data):
    description = quiz_data["metadata"]["description"]
    answer_prefix = "Correct answer: "
    if answer_prefix in description:
        answer_str = description.split(answer_prefix)[1].strip()
        try:
            return json.loads(answer_str.replace("'", "\""))
        except json.JSONDecodeError:
            return answer_str
    return None


jsons_dir = os.path.join(os.path.dirname(__file__), "test_quiz_jsons")

# Collect all test quiz files
test_quiz_files = [f for f in os.listdir(
    jsons_dir) if f.startswith("test_quiz")]


def test_complex_quiz_flow():
    """Test the flow of the complex quiz."""
    quiz_data = load_quiz_data(os.path.join(os.path.dirname(
        __file__), "test_quiz_jsons", "complex_quiz.json"))
    engine = QuizEngine(quiz_data)

    # Start the quiz for a user
    user_id = "user2"
    session_id = str(uuid.uuid4())
    engine.start_quiz(session_id)

    # Check initial question
    assert engine.get_current_question(session_id)["id"] == 1

    # Check initial scores
    assert engine.sessions[session_id]["scores"]["fruits"] == 0
    assert engine.sessions[session_id]["scores"]["apples"] == 0
    assert engine.sessions[session_id]["scores"]["pears"] == 0

    # Answer the first question
    result = engine.answer_question(session_id, "yes")
    assert engine.sessions[session_id]["scores"]["fruits"] == 1
    assert engine.sessions[session_id]["scores"]["apples"] == 2
    assert engine.sessions[session_id]["scores"]["pears"] == 0

    # Simulate moving to the next question
    result = engine.answer_question(session_id, "yes")
    assert result["id"] is None
    assert result["data"]["type"] == "final_message"

    # Final check of the results
    results = engine.get_results(session_id)
    expected_results = {'scores': {'fruits': 2, 'apples': 2, 'pears': 2}, 'answers': [
        {'question_id': 1, 'answer': 'yes'}, {'question_id': 2, 'answer': 'yes'}]}
    assert results == expected_results


def test_complex_quiz_loop_flow():
    """Test the flow of the complex quiz."""
    quiz_data = load_quiz_data(os.path.join(os.path.dirname(
        __file__), "test_quiz_jsons", "complex_quiz.json"))
    engine = QuizEngine(quiz_data)

    # Start the quiz for a user
    user_id = "user2"
    session_id = str(uuid.uuid4())
    engine.start_quiz(session_id)

    # Check initial question
    assert engine.get_current_question(session_id)["id"] == 1

    # Check initial scores
    assert engine.sessions[session_id]["scores"]["fruits"] == 0
    assert engine.sessions[session_id]["scores"]["apples"] == 0
    assert engine.sessions[session_id]["scores"]["pears"] == 0

    # Answer the first question
    result = engine.answer_question(session_id, "no")
    assert engine.sessions[session_id]["scores"]["fruits"] == 0
    assert engine.sessions[session_id]["scores"]["apples"] == -1
    assert engine.sessions[session_id]["scores"]["pears"] == 0

    # Answer the first question again
    result = engine.answer_question(session_id, "yes")
    assert engine.sessions[session_id]["scores"]["fruits"] == 1
    assert engine.sessions[session_id]["scores"]["apples"] == 1
    assert engine.sessions[session_id]["scores"]["pears"] == 0

    # Simulate moving to the next question
    result = engine.answer_question(session_id, "yes")
    assert result["id"] is None
    assert result["data"]["type"] == "final_message"


def test_invalid_score_updates():
    """Test that invalid score updates raise errors."""
    invalid_quiz_data = load_quiz_data(
        os.path.join(os.path.dirname(
            __file__), "test_quiz_jsons", "invalid_quiz_bad_score_update.json")
    )
    with pytest.raises(ValueError):
        QuizEngine(invalid_quiz_data)


def test_invalid_transitions():
    """Test that invalid transitions raise errors."""
    invalid_quiz_data = load_quiz_data(
        os.path.join(os.path.dirname(
            __file__), "test_quiz_jsons", "invalid_quiz_bad_transition.json")
    )
    with pytest.raises(ValueError):
        QuizEngine(invalid_quiz_data)


@pytest.mark.parametrize("quiz_file", test_quiz_files)
def test_quiz_types(quiz_file):
    """Test the flow of various quiz types."""
    quiz_data = load_quiz_data(os.path.join(jsons_dir, quiz_file))
    engine = QuizEngine(quiz_data)

    # Extract the correct answer from the quiz metadata
    answer = extract_answer(quiz_data)
    assert answer is not None, f"Correct answer not found in metadata for {quiz_file}"

    # Start the quiz for a user
    session_id = str(uuid.uuid4())
    engine.start_quiz(session_id)

    # Answer the question
    result = engine.answer_question(session_id, answer)
    assert engine.sessions[session_id]["scores"]["score_a"] == 1

import pytest
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

# Collect all test quiz files (exclude file_types quiz - it's for E2E testing)
test_quiz_files = [f for f in os.listdir(
    jsons_dir) if f.startswith("test_quiz") and "file_types" not in f]


def test_complex_quiz_flow():
    """Test the flow of the complex quiz with stateless engine."""
    from pyquizhub.core.engine.engine import QuizEngine
    quiz_data = load_quiz_data(os.path.join(os.path.dirname(
        __file__), "test_quiz_jsons", "complex_quiz.json"))
    engine = QuizEngine(quiz_data)

    # Start the quiz (no session_id parameter)
    state = engine.start_quiz()

    # Check initial question
    current_question = engine.get_current_question(state)
    assert current_question["id"] == 1

    # Check initial scores
    assert state["scores"]["fruits"] == 0
    assert state["scores"]["apples"] == 0
    assert state["scores"]["pears"] == 0

    # Answer the first question (returns new state)
    new_state = engine.answer_question(state, "yes")
    assert new_state["scores"]["fruits"] == 1
    assert new_state["scores"]["apples"] == 2
    assert new_state["scores"]["pears"] == 0

    # Simulate moving to the next question
    new_state = engine.answer_question(new_state, "yes")
    assert new_state["completed"] is True
    assert new_state["current_question_id"] is None

    # Verify next question is None
    next_question = engine.get_current_question(new_state)
    assert next_question is None

    # Final check of the results
    expected_scores = {'fruits': 2, 'apples': 2, 'pears': 2}
    assert new_state["scores"] == expected_scores
    assert len(new_state["answers"]) == 2
    assert new_state["answers"][0]["question_id"] == 1
    assert new_state["answers"][0]["answer"] == "yes"
    assert new_state["answers"][1]["question_id"] == 2
    assert new_state["answers"][1]["answer"] == "yes"


def test_complex_quiz_loop_flow():
    """Test the flow of the complex quiz with loop (stateless engine)."""
    from pyquizhub.core.engine.engine import QuizEngine
    quiz_data = load_quiz_data(os.path.join(os.path.dirname(
        __file__), "test_quiz_jsons", "complex_quiz.json"))
    engine = QuizEngine(quiz_data)

    # Start the quiz (no session_id parameter)
    state = engine.start_quiz()

    # Check initial question
    current_question = engine.get_current_question(state)
    assert current_question["id"] == 1

    # Check initial scores
    assert state["scores"]["fruits"] == 0
    assert state["scores"]["apples"] == 0
    assert state["scores"]["pears"] == 0

    # Answer the first question with "no"
    state = engine.answer_question(state, "no")
    assert state["scores"]["fruits"] == 0
    assert state["scores"]["apples"] == -1
    assert state["scores"]["pears"] == 0

    # Answer the first question again with "yes" (looped back)
    state = engine.answer_question(state, "yes")
    assert state["scores"]["fruits"] == 1
    assert state["scores"]["apples"] == 1
    assert state["scores"]["pears"] == 0

    # Simulate moving to the next question
    state = engine.answer_question(state, "yes")
    assert state["completed"] is True
    assert state["current_question_id"] is None

    # Verify next question is None
    next_question = engine.get_current_question(state)
    assert next_question is None


def test_invalid_score_updates():
    """Test that invalid score updates raise errors."""
    from pyquizhub.core.engine.engine import QuizEngine
    invalid_quiz_data = load_quiz_data(
        os.path.join(os.path.dirname(
            __file__), "test_quiz_jsons", "invalid_quiz_bad_score_update.json")
    )
    with pytest.raises(ValueError):
        QuizEngine(invalid_quiz_data)


def test_invalid_transitions():
    """Test that invalid transitions raise errors."""
    from pyquizhub.core.engine.engine import QuizEngine
    invalid_quiz_data = load_quiz_data(
        os.path.join(os.path.dirname(
            __file__), "test_quiz_jsons", "invalid_quiz_bad_transition.json")
    )
    with pytest.raises(ValueError):
        QuizEngine(invalid_quiz_data)


@pytest.mark.parametrize("quiz_file", test_quiz_files)
def test_quiz_types(quiz_file):
    """Test the flow of various quiz types with stateless engine."""
    from pyquizhub.core.engine.engine import QuizEngine
    quiz_data = load_quiz_data(os.path.join(jsons_dir, quiz_file))
    engine = QuizEngine(quiz_data)

    # Extract the correct answer from the quiz metadata
    answer = extract_answer(quiz_data)
    assert answer is not None, f"Correct answer not found in metadata for {quiz_file}"

    # Start the quiz (no session_id parameter)
    state = engine.start_quiz()

    # Answer the question
    new_state = engine.answer_question(state, answer)
    assert new_state["scores"]["score_a"] == 1

import pytest
from pyquizhub.engine.engine import QuizEngine


def test_complex_quiz_flow():
    """Test the flow of the complex quiz."""
    engine = QuizEngine("tests/test_quiz_jsons/complex_quiz.json")

    # Start the quiz for a user
    user_id = "user2"
    engine.start_quiz(user_id)

    # Check initial question
    assert engine.get_current_question(user_id)["id"] == 1

    # Check initial scores
    assert engine.sessions[user_id]["scores"]["fruits"] == 0
    assert engine.sessions[user_id]["scores"]["apples"] == 0
    assert engine.sessions[user_id]["scores"]["pears"] == 0

    # Answer the first question
    result = engine.answer_question(user_id, "yes")
    assert engine.sessions[user_id]["scores"]["fruits"] == 1
    assert engine.sessions[user_id]["scores"]["apples"] == 2
    assert engine.sessions[user_id]["scores"]["pears"] == 0

    # Simulate moving to the next question
    result = engine.answer_question(user_id, "yes")
    assert result.get("message") == "Quiz completed!"
    assert result["scores"]["fruits"] == 2
    assert result["scores"]["apples"] == 2
    assert result["scores"]["pears"] == 2


def test_invalid_score_updates():
    """Test that invalid score updates raise errors."""
    with pytest.raises(ValueError):
        QuizEngine("tests/test_quiz_jsons/invalid_quiz_bad_score_update.json")


def test_invalid_transitions():
    """Test that invalid transitions raise errors."""
    with pytest.raises(ValueError):
        QuizEngine("tests/test_quiz_jsons/invalid_quiz_bad_transition.json")

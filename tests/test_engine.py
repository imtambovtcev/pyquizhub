import pytest
from pyquizhub.engine import QuizEngine


def test_simple_quiz_flow():
    """Test the flow of the simple quiz."""
    engine = QuizEngine("tests/test_quiz_jsons/simple_quiz.json")

    # Check initial question
    assert engine.get_current_question()["id"] == 1

    # Answer the first question
    engine.answer_question("yes")

    # Check scores
    assert engine.scores["score_a"] == 1

    # Check if the quiz loops to the same question
    assert engine.get_current_question()["id"] == 1
    assert not engine.is_quiz_finished()


def test_complex_quiz_flow():
    """Test the flow of the complex quiz."""
    engine = QuizEngine("tests/test_quiz_jsons/complex_quiz.json")

    # Check initial question
    assert engine.get_current_question()["id"] == 1

    # Answer the first question
    engine.answer_question("yes")
    assert engine.scores["fruits"] == 1
    assert engine.scores["apples"] == 2
    print("Scores after first answer:", engine.scores)

    # Simulate moving to the next question
    print("Current question before next answer:", engine.get_current_question())
    engine.answer_question("yes")
    print("Scores after second answer:", engine.scores)


def test_quiz_end():
    """Test if the engine correctly identifies the end of the quiz."""
    engine = QuizEngine("tests/test_quiz_jsons/simple_quiz.json")

    # Simulate answering the only question and finishing the quiz
    engine.answer_question("yes")
    engine.answer_question("yes")  # Simulating looping
    assert not engine.is_quiz_finished()


def test_invalid_score_updates():
    """Test that invalid score updates raise errors."""
    with pytest.raises(ValueError):
        QuizEngine("tests/test_quiz_jsons/invalid_quiz_bad_score_update.json")


def test_invalid_transitions():
    """Test that invalid transitions raise errors."""
    with pytest.raises(ValueError):
        QuizEngine("tests/test_quiz_jsons/invalid_quiz_bad_transition.json")

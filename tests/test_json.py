import pytest
from pyquizhub.engine.json_validator import QuizJSONValidator

# Define paths to the test JSON files
VALID_JSON_FILES = [
    "tests/test_quiz_jsons/simple_quiz.json",
    "tests/test_quiz_jsons/complex_quiz.json"
]

INVALID_JSON_FILES = [
    "tests/test_quiz_jsons/invalid_quiz_missing_keys.json",
    "tests/test_quiz_jsons/invalid_quiz_bad_score_update.json",
    "tests/test_quiz_jsons/invalid_quiz_bad_transition.json",
    "tests/test_quiz_jsons/invalid_quiz_non_iterable_questions.json",
    "tests/test_quiz_jsons/invalid_quiz_duplicate_question_ids.json",
    "tests/test_quiz_jsons/invalid_quiz_unexpected_top_level.json",
    "tests/test_quiz_jsons/invalid_quiz_invalid_condition_expression.json"
]

WARNING_JSON_FILES = [
    "tests/test_quiz_jsons/warning_non_trivial_after_trivial.json",
    "tests/test_quiz_jsons/warning_no_trivial_condition.json"
]


@pytest.mark.parametrize("json_file", VALID_JSON_FILES)
def test_valid_json_files(json_file):
    """Test that valid JSON files pass validation without errors."""
    result = QuizJSONValidator.validate(json_file)
    assert len(result["errors"]) == 0, f"Unexpected errors: {result['errors']}"
    assert len(result["warnings"]
               ) == 0, f"Unexpected warnings: {result['warnings']}"


@pytest.mark.parametrize("json_file", INVALID_JSON_FILES)
def test_invalid_json_files(json_file):
    """Test that invalid JSON files produce errors."""
    result = QuizJSONValidator.validate(json_file)
    assert len(result["errors"]) > 0, f"Expected errors, but none were found."
    assert len(result["warnings"]) >= 0  # Warnings may or may not exist


@pytest.mark.parametrize("json_file", WARNING_JSON_FILES)
def test_warning_json_files(json_file):
    """Test that JSON files with warnings produce the correct warnings."""
    result = QuizJSONValidator.validate(json_file)
    assert len(result["errors"]) == 0, f"Unexpected errors: {result['errors']}"
    assert len(result["warnings"]
               ) > 0, "Expected warnings, but none were found."

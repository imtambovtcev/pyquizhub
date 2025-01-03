import pytest
from pyquizhub.json_validator import QuizJSONValidator

# Define paths to the test JSON files
VALID_JSON_FILES = [
    "tests/test_quiz_jsons/simple_quiz.json",
    "tests/test_quiz_jsons/complex_quiz.json"
]

INVALID_JSON_FILES = [
    "tests/test_quiz_jsons/invalid_quiz_missing_keys.json",
    "tests/test_quiz_jsons/invalid_quiz_bad_score_update.json",
    "tests/test_quiz_jsons/invalid_quiz_bad_transition.json"
]


@pytest.mark.parametrize("json_file", VALID_JSON_FILES)
def test_valid_json_files(json_file):
    """Test that valid JSON files pass validation."""
    assert QuizJSONValidator.validate(json_file) is True


@pytest.mark.parametrize("json_file", INVALID_JSON_FILES)
def test_invalid_json_files(json_file):
    """Test that invalid JSON files fail validation."""
    with pytest.raises(ValueError):
        QuizJSONValidator.validate(json_file)

import pytest
from pyquizhub.core.engine.json_validator import QuizJSONValidator
import json
import os
# Helper function to load quiz data


def load_quiz_data(file_path):
    with open(file_path, "r") as f:
        return json.load(f)


jsons_dir = os.path.join(os.path.dirname(__file__), "test_quiz_jsons")

# Define paths to the test JSON files
VALID_JSON_FILES = [
    jsons_dir+"/simple_quiz.json",
    jsons_dir+"/complex_quiz.json",
]

INVALID_JSON_FILES = [
    jsons_dir+"/invalid_quiz_missing_keys.json",
    jsons_dir+"/invalid_quiz_bad_score_update.json",
    jsons_dir+"/invalid_quiz_bad_transition.json",
    jsons_dir+"/invalid_quiz_non_iterable_questions.json",
    jsons_dir+"/invalid_quiz_duplicate_question_ids.json",
    jsons_dir+"/invalid_quiz_unexpected_top_level.json",
    jsons_dir+"/invalid_quiz_invalid_condition_expression.json",
]

WARNING_JSON_FILES = [
    jsons_dir+"/warning_non_trivial_after_trivial.json",
    jsons_dir+"/warning_no_trivial_condition.json",
]


@pytest.mark.parametrize("json_file", VALID_JSON_FILES)
def test_valid_json_files(json_file):
    """Test that valid JSON files pass validation without errors."""
    quiz_data = load_quiz_data(json_file)
    result = QuizJSONValidator.validate(quiz_data)
    assert len(result["errors"]) == 0, f"Unexpected errors: {result['errors']}"
    assert len(result["warnings"]
               ) == 0, f"Unexpected warnings: {result['warnings']}"


@pytest.mark.parametrize("json_file", INVALID_JSON_FILES)
def test_invalid_json_files(json_file):
    """Test that invalid JSON files produce errors."""
    quiz_data = load_quiz_data(json_file)
    result = QuizJSONValidator.validate(quiz_data)
    assert len(result["errors"]) > 0, f"Expected errors, but none were found."
    assert len(result["warnings"]) >= 0  # Warnings may or may not exist


@pytest.mark.parametrize("json_file", WARNING_JSON_FILES)
def test_warning_json_files(json_file):
    """Test that JSON files with warnings produce the correct warnings."""
    quiz_data = load_quiz_data(json_file)
    result = QuizJSONValidator.validate(quiz_data)
    assert len(result["errors"]) == 0, f"Unexpected errors: {result['errors']}"
    assert len(result["warnings"]
               ) > 0, "Expected warnings, but none were found."

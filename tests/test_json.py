import pytest
import json
import os
# Helper function to load quiz data


def load_quiz_data(file_path):
    with open(file_path, "r") as f:
        return json.load(f)


jsons_dir = os.path.join(os.path.dirname(__file__), "test_quiz_jsons")

# Automatically define paths to the test JSON files
VALID_JSON_FILES = []
INVALID_JSON_FILES = []
WARNING_JSON_FILES = []

for file_name in os.listdir(jsons_dir):
    if "_quiz" in file_name and file_name.endswith(".json"):
        if file_name.startswith("invalid"):
            INVALID_JSON_FILES.append(os.path.join(jsons_dir, file_name))
        elif file_name.startswith("warning"):
            WARNING_JSON_FILES.append(os.path.join(jsons_dir, file_name))
        else:
            VALID_JSON_FILES.append(os.path.join(jsons_dir, file_name))


@pytest.mark.parametrize("json_file", VALID_JSON_FILES)
def test_valid_json_files(json_file):
    """Test that valid JSON files pass validation without errors."""
    from pyquizhub.core.engine.json_validator import QuizJSONValidator
    quiz_data = load_quiz_data(json_file)
    result = QuizJSONValidator.validate(quiz_data)
    assert len(result["errors"]) == 0, f"Unexpected errors: {result['errors']}"

    # Old format files using 'scores' will have deprecation warning
    # New format files using 'variables' should have no warnings
    if "variables" in quiz_data:
        assert len(result["warnings"]) == 0, f"Unexpected warnings: {result['warnings']}"
    else:
        # Old format - expect deprecation warning
        assert any("DEPRECATED" in w for w in result["warnings"]), \
            "Expected deprecation warning for old 'scores' format"


@pytest.mark.parametrize("json_file", INVALID_JSON_FILES)
def test_invalid_json_files(json_file):
    """Test that invalid JSON files produce errors."""
    from pyquizhub.core.engine.json_validator import QuizJSONValidator
    quiz_data = load_quiz_data(json_file)
    result = QuizJSONValidator.validate(quiz_data)
    assert len(result["errors"]) > 0, f"Expected errors, but none were found."
    assert len(result["warnings"]) >= 0  # Warnings may or may not exist


@pytest.mark.parametrize("json_file", WARNING_JSON_FILES)
def test_warning_json_files(json_file):
    """Test that JSON files with warnings produce the correct warnings."""
    from pyquizhub.core.engine.json_validator import QuizJSONValidator
    quiz_data = load_quiz_data(json_file)
    result = QuizJSONValidator.validate(quiz_data)
    assert len(result["errors"]) == 0, f"Unexpected errors: {result['errors']}"
    assert len(result["warnings"]
               ) > 0, "Expected warnings, but none were found."

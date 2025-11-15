"""
Tests for automatic default value generation based on type.
"""
import pytest
from pyquizhub.core.engine.json_validator import QuizJSONValidator


class TestAutomaticDefaults:
    """Test that default values are auto-generated when not provided."""

    def test_integer_auto_default(self):
        """Test that integer variables get default value of 0."""
        quiz_data = {
            "metadata": {"title": "Test", "description": "Test"},
            "variables": {
                "score": {
                    "type": "integer",
                    "mutable_by": ["engine"]
                    # No default specified - should auto-generate 0
                }
            },
            "questions": [{"id": 1, "data": {"text": "?", "type": "text"}}],
            "transitions": {"1": [{"expression": "true", "next_question_id": None}]}
        }

        result = QuizJSONValidator.validate(quiz_data)
        assert len(result["errors"]) == 0, f"Errors: {result['errors']}"

    def test_float_auto_default(self):
        """Test that float variables get default value of 0.0."""
        quiz_data = {
            "metadata": {"title": "Test", "description": "Test"},
            "variables": {
                "temperature": {
                    "type": "float",
                    "mutable_by": ["api"]
                    # No default specified - should auto-generate 0.0
                }
            },
            "questions": [{"id": 1, "data": {"text": "?", "type": "text"}}],
            "transitions": {"1": [{"expression": "true", "next_question_id": None}]}
        }

        result = QuizJSONValidator.validate(quiz_data)
        assert len(result["errors"]) == 0, f"Errors: {result['errors']}"

    def test_boolean_auto_default(self):
        """Test that boolean variables get default value of false."""
        quiz_data = {
            "metadata": {"title": "Test", "description": "Test"},
            "variables": {
                "completed": {
                    "type": "boolean",
                    "mutable_by": ["engine"]
                    # No default specified - should auto-generate false
                }
            },
            "questions": [{"id": 1, "data": {"text": "?", "type": "text"}}],
            "transitions": {"1": [{"expression": "true", "next_question_id": None}]}
        }

        result = QuizJSONValidator.validate(quiz_data)
        assert len(result["errors"]) == 0, f"Errors: {result['errors']}"

    def test_string_auto_default(self):
        """Test that string variables get default value of empty string."""
        quiz_data = {
            "metadata": {"title": "Test", "description": "Test"},
            "variables": {
                "user_name": {
                    "type": "string",
                    "mutable_by": ["user"]
                    # No default specified - should auto-generate ""
                }
            },
            "questions": [{"id": 1, "data": {"text": "?", "type": "text"}}],
            "transitions": {"1": [{"expression": "true", "next_question_id": None}]}
        }

        result = QuizJSONValidator.validate(quiz_data)
        assert len(result["errors"]) == 0, f"Errors: {result['errors']}"

    def test_array_auto_default(self):
        """Test that array variables get default value of empty array."""
        quiz_data = {
            "metadata": {"title": "Test", "description": "Test"},
            "variables": {
                "selected_items": {
                    "type": "array",
                    "array_item_type": "string",  # Required for arrays
                    "mutable_by": ["user"]
                    # No default specified - should auto-generate []
                }
            },
            "questions": [{"id": 1, "data": {"text": "?", "type": "text"}}],
            "transitions": {"1": [{"expression": "true", "next_question_id": None}]}
        }

        result = QuizJSONValidator.validate(quiz_data)
        assert len(result["errors"]) == 0, f"Errors: {result['errors']}"

    def test_object_type_not_allowed(self):
        """Test that object type is NOT allowed for security reasons."""
        quiz_data = {
            "metadata": {"title": "Test", "description": "Test"},
            "variables": {
                "user_data": {
                    "type": "object",
                    "mutable_by": ["engine"]
                }
            },
            "questions": [{"id": 1, "data": {"text": "?", "type": "text"}}],
            "transitions": {"1": [{"expression": "true", "next_question_id": None}]}
        }

        result = QuizJSONValidator.validate(quiz_data)
        # Should reject object type
        assert len(result["errors"]) > 0
        assert any("object" in e.lower() for e in result["errors"])

    def test_explicit_default_overrides_auto_default(self):
        """Test that explicit default value overrides auto-generated one."""
        quiz_data = {
            "metadata": {"title": "Test", "description": "Test"},
            "variables": {
                "score": {
                    "type": "integer",
                    "default": 100,  # Explicit non-zero default
                    "mutable_by": ["engine"]
                }
            },
            "questions": [{"id": 1, "data": {"text": "?", "type": "text"}}],
            "transitions": {"1": [{"expression": "true", "next_question_id": None}]}
        }

        result = QuizJSONValidator.validate(quiz_data)
        assert len(result["errors"]) == 0, f"Errors: {result['errors']}"

    def test_minimal_variable_definition(self):
        """Test that only type and mutable_by are required."""
        quiz_data = {
            "metadata": {"title": "Test", "description": "Test"},
            "variables": {
                "minimal": {
                    "type": "integer",
                    "mutable_by": ["engine"]
                    # No default, no tags, no description, no constraints
                }
            },
            "questions": [{"id": 1, "data": {"text": "?", "type": "text"}}],
            "transitions": {"1": [{"expression": "true", "next_question_id": None}]}
        }

        result = QuizJSONValidator.validate(quiz_data)
        assert len(result["errors"]) == 0, f"Errors: {result['errors']}"


class TestRequiredFields:
    """Test validation of required fields."""

    def test_missing_type_rejected(self):
        """Test that missing 'type' field is rejected."""
        quiz_data = {
            "metadata": {"title": "Test", "description": "Test"},
            "variables": {
                "bad_var": {
                    # "type": "integer",  # Missing!
                    "mutable_by": ["engine"]
                }
            },
            "questions": [{"id": 1, "data": {"text": "?", "type": "text"}}],
            "transitions": {"1": [{"expression": "true", "next_question_id": None}]}
        }

        result = QuizJSONValidator.validate(quiz_data)
        assert len(result["errors"]) > 0
        assert any("missing required fields" in e.lower() for e in result["errors"])

    def test_missing_mutable_by_rejected(self):
        """Test that missing 'mutable_by' field is rejected."""
        quiz_data = {
            "metadata": {"title": "Test", "description": "Test"},
            "variables": {
                "bad_var": {
                    "type": "integer"
                    # "mutable_by": ["engine"]  # Missing!
                }
            },
            "questions": [{"id": 1, "data": {"text": "?", "type": "text"}}],
            "transitions": {"1": [{"expression": "true", "next_question_id": None}]}
        }

        result = QuizJSONValidator.validate(quiz_data)
        assert len(result["errors"]) > 0
        assert any("missing required fields" in e.lower() for e in result["errors"])

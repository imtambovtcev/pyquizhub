"""
Tests for QuizJSONValidator with new variables format.
"""
import pytest
from pyquizhub.core.engine.json_validator import QuizJSONValidator


class TestVariablesFormatValidation:
    """Test validation of new variables format."""

    def test_valid_variables_format(self):
        """Test that valid variables format passes validation."""
        quiz_data = {
            "metadata": {
                "title": "Test Quiz",
                "description": "Test"
            },
            "variables": {
                "score": {
                    "type": "integer",
                    "default": 0,
                    "mutable_by": ["engine"],
                    "tags": ["leaderboard"],
                    "description": "Player score"
                },
                "user_name": {
                    "type": "string",
                    "default": "",
                    "mutable_by": ["user"],
                    "tags": ["user_input", "private"],
                    "constraints": {
                        "max_length": 50
                    }
                }
            },
            "questions": [
                {
                    "id": 1,
                    "data": {
                        "text": "What is your name?",
                        "type": "text"
                    }
                }
            ],
            "transitions": {
                "1": [
                    {"expression": "true", "next_question_id": None}
                ]
            }
        }

        result = QuizJSONValidator.validate(quiz_data)
        assert len(result["errors"]) == 0, f"Unexpected errors: {result['errors']}"
        assert len(result["warnings"]) == 0, f"Unexpected warnings: {result['warnings']}"

    def test_old_scores_format_shows_deprecation_warning(self):
        """Test that old scores format shows deprecation warning."""
        quiz_data = {
            "metadata": {
                "title": "Old Format Quiz",
                "description": "Test"
            },
            "scores": {
                "score": 0
            },
            "questions": [
                {
                    "id": 1,
                    "data": {
                        "text": "Question?",
                        "type": "text"
                    }
                }
            ],
            "transitions": {
                "1": [
                    {"expression": "true", "next_question_id": None}
                ]
            }
        }

        result = QuizJSONValidator.validate(quiz_data)
        assert len(result["errors"]) == 0
        assert len(result["warnings"]) > 0
        assert any("DEPRECATED" in w for w in result["warnings"])

    def test_invalid_variable_type(self):
        """Test that invalid variable type is rejected."""
        quiz_data = {
            "metadata": {"title": "Test", "description": "Test"},
            "variables": {
                "bad_var": {
                    "type": "invalid_type",
                    "default": 0,
                    "mutable_by": ["engine"]
                }
            },
            "questions": [{"id": 1, "data": {"text": "?", "type": "text"}}],
            "transitions": {"1": [{"expression": "true", "next_question_id": None}]}
        }

        result = QuizJSONValidator.validate(quiz_data)
        assert len(result["errors"]) > 0
        assert any("invalid type" in e.lower() for e in result["errors"])

    def test_missing_required_variable_fields(self):
        """Test that missing required fields are caught."""
        quiz_data = {
            "metadata": {"title": "Test", "description": "Test"},
            "variables": {
                "incomplete_var": {
                    "type": "integer"
                    # Missing default and mutable_by
                }
            },
            "questions": [{"id": 1, "data": {"text": "?", "type": "text"}}],
            "transitions": {"1": [{"expression": "true", "next_question_id": None}]}
        }

        result = QuizJSONValidator.validate(quiz_data)
        assert len(result["errors"]) > 0
        assert any("missing required fields" in e.lower() for e in result["errors"])

    def test_multiple_leaderboard_variables_rejected(self):
        """Test that multiple leaderboard variables are rejected."""
        quiz_data = {
            "metadata": {"title": "Test", "description": "Test"},
            "variables": {
                "score1": {
                    "type": "integer",
                    "default": 0,
                    "mutable_by": ["engine"],
                    "tags": ["leaderboard"]
                },
                "score2": {
                    "type": "integer",
                    "default": 0,
                    "mutable_by": ["engine"],
                    "tags": ["leaderboard"]
                }
            },
            "questions": [{"id": 1, "data": {"text": "?", "type": "text"}}],
            "transitions": {"1": [{"expression": "true", "next_question_id": None}]}
        }

        result = QuizJSONValidator.validate(quiz_data)
        assert len(result["errors"]) > 0
        assert any("leaderboard" in e.lower() for e in result["errors"])

    def test_invalid_tag_rejected(self):
        """Test that invalid tags are rejected."""
        quiz_data = {
            "metadata": {"title": "Test", "description": "Test"},
            "variables": {
                "var": {
                    "type": "integer",
                    "default": 0,
                    "mutable_by": ["engine"],
                    "tags": ["invalid_tag"]
                }
            },
            "questions": [{"id": 1, "data": {"text": "?", "type": "text"}}],
            "transitions": {"1": [{"expression": "true", "next_question_id": None}]}
        }

        result = QuizJSONValidator.validate(quiz_data)
        assert len(result["errors"]) > 0
        assert any("invalid tag" in e.lower() for e in result["errors"])

    def test_score_tag_must_be_numeric(self):
        """Test that score tag requires numeric type."""
        quiz_data = {
            "metadata": {"title": "Test", "description": "Test"},
            "variables": {
                "bad_score": {
                    "type": "string",
                    "default": "",
                    "mutable_by": ["engine"],
                    "tags": ["score"]
                }
            },
            "questions": [{"id": 1, "data": {"text": "?", "type": "text"}}],
            "transitions": {"1": [{"expression": "true", "next_question_id": None}]}
        }

        result = QuizJSONValidator.validate(quiz_data)
        assert len(result["errors"]) > 0
        assert any("score" in e.lower() and ("integer" in e.lower() or "float" in e.lower()) for e in result["errors"])

    def test_answer_reserved_variable_name(self):
        """Test that 'answer' is a reserved variable name."""
        quiz_data = {
            "metadata": {"title": "Test", "description": "Test"},
            "variables": {
                "answer": {
                    "type": "string",
                    "default": "",
                    "mutable_by": ["user"]
                }
            },
            "questions": [{"id": 1, "data": {"text": "?", "type": "text"}}],
            "transitions": {"1": [{"expression": "true", "next_question_id": None}]}
        }

        result = QuizJSONValidator.validate(quiz_data)
        assert len(result["errors"]) > 0
        assert any("answer" in e.lower() and "special" in e.lower() for e in result["errors"])

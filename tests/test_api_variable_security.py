"""
Tests for API variable security model.

With the new architecture:
- API responses populate predefined variables declared in API integration's extract_response
- Variables just need to be mutable by API
- NO source_api/response_path in variable definitions
- API integration defines which variables it populates and how
"""
import pytest
from pyquizhub.core.engine.variable_types import (
    VariableDefinition, VariableType, MutableBy, VariableTag, VariableConstraints
)


class TestAPIVariableSecurity:
    """Test that API data can only go into predefined, type-validated variables."""

    def test_api_variable_basic_definition(self):
        """Test that API variables are just regular variables mutable by API."""
        var = VariableDefinition(
            name="temp",
            type=VariableType.FLOAT,
            default=0,
            mutable_by=[MutableBy.API],
            tags={VariableTag.API_DATA}  # Manually tag as API_DATA
        )

        # API_DATA tag implies SANITIZED and SAFE_FOR_API
        assert VariableTag.API_DATA in var.tags
        assert VariableTag.SANITIZED in var.tags
        assert VariableTag.SAFE_FOR_API in var.tags
        assert var.is_safe_for_api_use()

    def test_api_variable_with_type_constraints(self):
        """Test that API variables can have type constraints for additional validation."""
        var = VariableDefinition(
            name="temp",
            type=VariableType.FLOAT,
            default=0,
            mutable_by=[MutableBy.API],
            tags={VariableTag.API_DATA},
            constraints=VariableConstraints(
                min_value=-100,
                max_value=100
            )
        )

        assert var.constraints.min_value == -100
        assert var.constraints.max_value == 100
        assert VariableTag.SAFE_FOR_API in var.tags

    def test_string_api_variable_with_enum_is_safe(self):
        """Test that string API variables with enum constraint are safe for API requests."""
        var = VariableDefinition(
            name="weather_condition",
            type=VariableType.STRING,
            default="",
            mutable_by=[MutableBy.API],
            tags={VariableTag.API_DATA},
            constraints=VariableConstraints(
                enum=["sunny", "cloudy", "rainy", "snowy"]
            )
        )

        # String with enum is safe for API
        assert VariableTag.API_DATA in var.tags
        assert VariableTag.SANITIZED in var.tags
        assert VariableTag.SAFE_FOR_API in var.tags

    def test_string_api_variable_without_enum(self):
        """Test that string API variables without enum get API_DATA but handling depends on usage."""
        var = VariableDefinition(
            name="city_name",
            type=VariableType.STRING,
            default="",
            mutable_by=[MutableBy.API],
            tags={VariableTag.API_DATA}
        )

        # Gets API_DATA and SANITIZED but not automatically SAFE_FOR_API
        # (SAFE_FOR_API only added if enum constraint present for strings)
        assert VariableTag.API_DATA in var.tags
        assert VariableTag.SANITIZED in var.tags
        # Free-text strings from API are sanitized but not safe to use in other API requests

    def test_multiple_api_variables(self):
        """Test that multiple variables can be populated by API (defined in API integration)."""
        temp_var = VariableDefinition(
            name="temperature",
            type=VariableType.FLOAT,
            default=0,
            mutable_by=[MutableBy.API],
            tags={VariableTag.API_DATA}
        )

        wind_var = VariableDefinition(
            name="wind_speed",
            type=VariableType.FLOAT,
            default=0,
            mutable_by=[MutableBy.API],
            tags={VariableTag.API_DATA}
        )

        # Both are valid API variables
        assert VariableTag.API_DATA in temp_var.tags
        assert VariableTag.API_DATA in wind_var.tags
        assert temp_var.can_be_modified_by(MutableBy.API)
        assert wind_var.can_be_modified_by(MutableBy.API)


class TestAPIIntegrationValidation:
    """Test validation of API integrations in quiz JSON."""

    def test_quiz_with_api_variable(self):
        """Test that quiz validator accepts variables that will be populated by API."""
        from pyquizhub.core.engine.json_validator import QuizJSONValidator

        quiz_data = {
            "metadata": {"title": "Weather Quiz", "description": "Test"},
            "variables": {
                "actual_temp": {
                    "type": "float",
                    "default": 0,
                    "mutable_by": ["api"],
                    "tags": ["api_data"],
                    "constraints": {
                        "min_value": -100,
                        "max_value": 100
                    }
                }
            },
            "api_integrations": [
                {
                    "id": "temp",
                    "url": "https://api.example.com/weather",
                    "method": "GET"
                }
            ],
            "questions": [{"id": 1, "data": {"text": "Test", "type": "text"}}],
            "transitions": {"1": [{"expression": "true", "next_question_id": None}]}
        }

        result = QuizJSONValidator.validate(quiz_data)
        assert len(result["errors"]) == 0, f"Errors: {result['errors']}"

    def test_quiz_with_array_variable(self):
        """Test that array variables require array_item_type."""
        from pyquizhub.core.engine.json_validator import QuizJSONValidator

        quiz_data = {
            "metadata": {"title": "Test", "description": "Test"},
            "variables": {
                "items": {
                    "type": "array",
                    "array_item_type": "string",
                    "default": [],
                    "mutable_by": ["user"]
                }
            },
            "questions": [{"id": 1, "data": {"text": "Test", "type": "text"}}],
            "transitions": {"1": [{"expression": "true", "next_question_id": None}]}
        }

        result = QuizJSONValidator.validate(quiz_data)
        assert len(result["errors"]) == 0, f"Errors: {result['errors']}"

    def test_quiz_rejects_array_without_item_type(self):
        """Test that validator rejects array variables without array_item_type."""
        from pyquizhub.core.engine.json_validator import QuizJSONValidator

        quiz_data = {
            "metadata": {"title": "Test", "description": "Test"},
            "variables": {
                "bad_array": {
                    "type": "array",
                    "default": [],
                    "mutable_by": ["user"]
                    # Missing array_item_type!
                }
            },
            "questions": [{"id": 1, "data": {"text": "Test", "type": "text"}}],
            "transitions": {"1": [{"expression": "true", "next_question_id": None}]}
        }

        result = QuizJSONValidator.validate(quiz_data)
        assert len(result["errors"]) > 0
        assert any("array_item_type" in e.lower() for e in result["errors"])

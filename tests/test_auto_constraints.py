"""
Tests for automatic constraint application.

When variables have no constraints specified, reasonable defaults should be applied
to prevent abuse (excessively long strings, huge arrays, unreasonable numbers).
"""
import pytest
from pyquizhub.core.engine.json_validator import QuizJSONValidator


class TestAutoConstraints:
    """Test that constraints are automatically applied when not specified."""

    def test_user_string_gets_max_length(self):
        """Test that user input strings get automatic max_length constraint."""
        quiz_data = {
            "metadata": {"title": "Test", "description": "Test"},
            "variables": {
                "user_comment": {
                    "type": "string",
                    "mutable_by": ["user"]
                    # No constraints specified - should auto-apply max_length
                }
            },
            "questions": [{"id": 1, "data": {"text": "?", "type": "text"}}],
            "transitions": {"1": [{"expression": "true", "next_question_id": None}]}
        }

        result = QuizJSONValidator.validate(quiz_data)
        assert len(result["errors"]) == 0, f"Errors: {result['errors']}"

        # Variable should have constraints with max_length
        var_errors, var_warnings, var_defs = QuizJSONValidator._validate_variables(
            quiz_data["variables"]
        )
        assert "user_comment" in var_defs
        assert var_defs["user_comment"].constraints is not None
        assert var_defs["user_comment"].constraints.max_length == 1000

    def test_api_string_gets_larger_max_length(self):
        """Test that API strings get larger max_length than user strings."""
        quiz_data = {
            "metadata": {"title": "Test", "description": "Test"},
            "variables": {
                "api_response": {
                    "type": "string",
                    "mutable_by": ["api"]
                    # No constraints - should auto-apply larger max_length
                }
            },
            "questions": [{"id": 1, "data": {"text": "?", "type": "text"}}],
            "transitions": {"1": [{"expression": "true", "next_question_id": None}]}
        }

        var_errors, var_warnings, var_defs = QuizJSONValidator._validate_variables(
            quiz_data["variables"]
        )
        assert "api_response" in var_defs
        assert var_defs["api_response"].constraints is not None
        # API strings can be longer than user strings
        assert var_defs["api_response"].constraints.max_length == 10000

    def test_score_integer_gets_reasonable_bounds(self):
        """Test that score integers get reasonable min/max bounds."""
        quiz_data = {
            "metadata": {"title": "Test", "description": "Test"},
            "variables": {
                "player_score": {
                    "type": "integer",
                    "mutable_by": ["engine"],
                    "tags": ["score"]
                    # No constraints - should auto-apply bounds
                }
            },
            "questions": [{"id": 1, "data": {"text": "?", "type": "text"}}],
            "transitions": {"1": [{"expression": "true", "next_question_id": None}]}
        }

        var_errors, var_warnings, var_defs = QuizJSONValidator._validate_variables(
            quiz_data["variables"]
        )
        assert "player_score" in var_defs
        assert var_defs["player_score"].constraints is not None
        # Score variables get ±1 billion bounds
        assert var_defs["player_score"].constraints.min_value == -1_000_000_000
        assert var_defs["player_score"].constraints.max_value == 1_000_000_000

    def test_leaderboard_score_gets_bounds(self):
        """Test that leaderboard variables get reasonable bounds."""
        quiz_data = {
            "metadata": {"title": "Test", "description": "Test"},
            "variables": {
                "final_score": {
                    "type": "float",
                    "mutable_by": ["engine"],
                    "tags": ["leaderboard"]
                    # No constraints - should auto-apply bounds
                }
            },
            "questions": [{"id": 1, "data": {"text": "?", "type": "text"}}],
            "transitions": {"1": [{"expression": "true", "next_question_id": None}]}
        }

        var_errors, var_warnings, var_defs = QuizJSONValidator._validate_variables(
            quiz_data["variables"]
        )
        assert "final_score" in var_defs
        assert var_defs["final_score"].constraints is not None
        # Leaderboard gets ±1 billion bounds
        assert var_defs["final_score"].constraints.min_value == -1_000_000_000.0
        assert var_defs["final_score"].constraints.max_value == 1_000_000_000.0

    def test_regular_integer_gets_64bit_bounds(self):
        """Test that non-score integers get 64-bit signed int bounds."""
        quiz_data = {
            "metadata": {"title": "Test", "description": "Test"},
            "variables": {
                "counter": {
                    "type": "integer",
                    "mutable_by": ["engine"]
                    # No score tag - should get full 64-bit bounds
                }
            },
            "questions": [{"id": 1, "data": {"text": "?", "type": "text"}}],
            "transitions": {"1": [{"expression": "true", "next_question_id": None}]}
        }

        var_errors, var_warnings, var_defs = QuizJSONValidator._validate_variables(
            quiz_data["variables"]
        )
        assert "counter" in var_defs
        assert var_defs["counter"].constraints is not None
        # Regular integers get full 64-bit bounds
        assert var_defs["counter"].constraints.min_value == -9_223_372_036_854_775_808
        assert var_defs["counter"].constraints.max_value == 9_223_372_036_854_775_807

    def test_user_array_gets_max_items(self):
        """Test that user input arrays get automatic max_items constraint."""
        quiz_data = {
            "metadata": {"title": "Test", "description": "Test"},
            "variables": {
                "selected_options": {
                    "type": "array",
                    "array_item_type": "string",
                    "mutable_by": ["user"]
                    # No constraints - should auto-apply max_items
                }
            },
            "questions": [{"id": 1, "data": {"text": "?", "type": "text"}}],
            "transitions": {"1": [{"expression": "true", "next_question_id": None}]}
        }

        var_errors, var_warnings, var_defs = QuizJSONValidator._validate_variables(
            quiz_data["variables"]
        )
        assert "selected_options" in var_defs
        assert var_defs["selected_options"].constraints is not None
        # User arrays get max 100 items
        assert var_defs["selected_options"].constraints.max_items == 100

    def test_engine_array_gets_larger_max_items(self):
        """Test that engine/API arrays get larger max_items than user arrays."""
        quiz_data = {
            "metadata": {"title": "Test", "description": "Test"},
            "variables": {
                "api_results": {
                    "type": "array",
                    "array_item_type": "integer",
                    "mutable_by": ["api"]
                    # No constraints - should auto-apply larger max_items
                }
            },
            "questions": [{"id": 1, "data": {"text": "?", "type": "text"}}],
            "transitions": {"1": [{"expression": "true", "next_question_id": None}]}
        }

        var_errors, var_warnings, var_defs = QuizJSONValidator._validate_variables(
            quiz_data["variables"]
        )
        assert "api_results" in var_defs
        assert var_defs["api_results"].constraints is not None
        # API arrays can have more items
        assert var_defs["api_results"].constraints.max_items == 10000

    def test_explicit_constraints_override_auto_constraints(self):
        """Test that explicit constraints override auto-generated ones."""
        quiz_data = {
            "metadata": {"title": "Test", "description": "Test"},
            "variables": {
                "custom_string": {
                    "type": "string",
                    "mutable_by": ["user"],
                    "constraints": {
                        "max_length": 50  # Custom limit
                    }
                }
            },
            "questions": [{"id": 1, "data": {"text": "?", "type": "text"}}],
            "transitions": {"1": [{"expression": "true", "next_question_id": None}]}
        }

        var_errors, var_warnings, var_defs = QuizJSONValidator._validate_variables(
            quiz_data["variables"]
        )
        assert "custom_string" in var_defs
        assert var_defs["custom_string"].constraints is not None
        # Should use explicit constraint, not auto-generated
        assert var_defs["custom_string"].constraints.max_length == 50

    def test_boolean_has_no_constraints(self):
        """Test that boolean variables have no numeric constraints."""
        quiz_data = {
            "metadata": {"title": "Test", "description": "Test"},
            "variables": {
                "is_complete": {
                    "type": "boolean",
                    "mutable_by": ["engine"]
                    # Booleans don't need constraints
                }
            },
            "questions": [{"id": 1, "data": {"text": "?", "type": "text"}}],
            "transitions": {"1": [{"expression": "true", "next_question_id": None}]}
        }

        var_errors, var_warnings, var_defs = QuizJSONValidator._validate_variables(
            quiz_data["variables"]
        )
        assert "is_complete" in var_defs
        # Boolean should have constraints object but all fields None
        assert var_defs["is_complete"].constraints is not None
        assert var_defs["is_complete"].constraints.max_length is None
        assert var_defs["is_complete"].constraints.min_value is None
        assert var_defs["is_complete"].constraints.max_items is None


class TestConstraintEnforcement:
    """Test that auto-applied constraints are actually enforced."""

    def test_user_string_exceeding_auto_limit_rejected(self):
        """Test that strings exceeding auto-applied max_length are rejected at runtime."""
        from pyquizhub.core.engine.variable_types import (
            VariableDefinition, VariableType, MutableBy, VariableStore
        )

        # Create variable with auto-constraints
        var_def = VariableDefinition(
            name="comment",
            type=VariableType.STRING,
            default="",
            mutable_by=[MutableBy.USER],
            constraints=QuizJSONValidator._auto_apply_constraints(
                VariableType.STRING,
                [MutableBy.USER],
                set()
            )
        )

        store = VariableStore({"comment": var_def})

        # Try to set string that's too long (> 1000 chars)
        long_string = "x" * 1001
        with pytest.raises(ValueError, match="maximum"):
            store.set("comment", long_string, MutableBy.USER)

    def test_array_exceeding_auto_limit_rejected(self):
        """Test that arrays exceeding auto-applied max_items are rejected at runtime."""
        from pyquizhub.core.engine.variable_types import (
            VariableDefinition, VariableType, MutableBy, VariableStore
        )

        # Create array variable with auto-constraints
        var_def = VariableDefinition(
            name="items",
            type=VariableType.ARRAY,
            array_item_type=VariableType.INTEGER,
            default=[],
            mutable_by=[MutableBy.USER],
            constraints=QuizJSONValidator._auto_apply_constraints(
                VariableType.ARRAY,
                [MutableBy.USER],
                set()
            )
        )

        store = VariableStore({"items": var_def})

        # Try to set array that's too large (> 100 items)
        large_array = list(range(101))
        with pytest.raises(ValueError, match="maximum"):
            store.set("items", large_array, MutableBy.USER)

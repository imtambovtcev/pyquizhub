"""
Tests for the tag-based variable system.

These tests verify:
- Variable type enforcement
- Tag auto-application
- Tag validation
- Variable constraints
- Safety classification
"""

import pytest
from pyquizhub.core.engine.variable_types import (
    VariableType,
    VariableTag,
    MutableBy,
    VariableDefinition,
    VariableConstraints,
    VariableStore,
    FallbackBehavior,
    FallbackConfig
)


class TestVariableDefinition:
    """Test variable definition and tag auto-application."""

    def test_score_must_be_numeric(self):
        """Test that variables with 'score' tag must be numeric."""
        # Valid: int score
        var = VariableDefinition(
            name="points",
            type=VariableType.INTEGER,
            default=0,
            mutable_by=[MutableBy.ENGINE],
            tags={VariableTag.SCORE}
        )
        assert VariableTag.SCORE in var.tags
        assert VariableTag.PUBLIC in var.tags  # Auto-added

        # Invalid: string score
        with pytest.raises(ValueError, match="score.*must be integer or float"):
            VariableDefinition(
                name="invalid_score",
                type=VariableType.STRING,
                default="",
                mutable_by=[MutableBy.ENGINE],
                tags={VariableTag.SCORE}
            )

    def test_score_automatically_becomes_public(self):
        """Test that score tag automatically adds public tag."""
        var = VariableDefinition(
            name="user_score",
            type=VariableType.FLOAT,
            default=0.0,
            mutable_by=[MutableBy.ENGINE],
            tags={VariableTag.SCORE}
        )

        assert VariableTag.PUBLIC in var.tags
        assert var.is_score()
        assert var.is_public()

    def test_numeric_types_are_safe_for_api(self):
        """Test that numeric types automatically get safe_for_api tag."""
        # Integer
        var_int = VariableDefinition(
            name="count",
            type=VariableType.INTEGER,
            default=0,
            mutable_by=[MutableBy.USER]
        )
        assert var_int.is_safe_for_api_use()
        assert VariableTag.SAFE_FOR_API in var_int.tags

        # Float
        var_float = VariableDefinition(
            name="temperature",
            type=VariableType.FLOAT,
            default=0.0,
            mutable_by=[MutableBy.API]
        )
        assert var_float.is_safe_for_api_use()

        # Boolean
        var_bool = VariableDefinition(
            name="is_correct",
            type=VariableType.BOOLEAN,
            default=False,
            mutable_by=[MutableBy.ENGINE]
        )
        assert var_bool.is_safe_for_api_use()

    def test_string_with_enum_is_safe_for_api(self):
        """Test that strings with enum constraints are safe for API."""
        var = VariableDefinition(
            name="city",
            type=VariableType.STRING,
            default="berlin",
            mutable_by=[MutableBy.USER],
            tags={VariableTag.USER_INPUT},
            constraints=VariableConstraints(
                enum=["berlin", "london", "paris"]
            )
        )

        # Enum makes it safe despite being user input
        assert var.is_safe_for_api_use()
        assert VariableTag.SAFE_FOR_API in var.tags
        assert VariableTag.SANITIZED in var.tags

    def test_free_text_string_is_not_safe_for_api(self):
        """Test that free-text strings are NOT safe for API."""
        var = VariableDefinition(
            name="user_comment",
            type=VariableType.STRING,
            default="",
            mutable_by=[MutableBy.USER],
            tags={VariableTag.USER_INPUT}
        )

        # No enum = not safe
        assert not var.is_safe_for_api_use()
        assert VariableTag.SAFE_FOR_API not in var.tags
        assert VariableTag.UNTRUSTED in var.tags

    def test_user_input_tag_implies_untrusted(self):
        """Test that user_input tag automatically adds untrusted tag."""
        var = VariableDefinition(
            name="answer",
            type=VariableType.STRING,
            default="",
            mutable_by=[MutableBy.USER],
            tags={VariableTag.USER_INPUT}
        )

        assert VariableTag.UNTRUSTED in var.tags

    def test_api_data_tag_implies_sanitized_and_safe(self):
        """Test that api_data tag adds sanitized and safe_for_api tags."""
        var = VariableDefinition(
            name="weather_temp",
            type=VariableType.FLOAT,
            default=0.0,
            mutable_by=[MutableBy.API],
            tags={VariableTag.API_DATA}
        )

        assert VariableTag.SANITIZED in var.tags
        assert VariableTag.SAFE_FOR_API in var.tags
        assert var.is_safe_for_api_use()

    def test_api_data_tag_manually_applied(self):
        """Test that API_DATA tag can be manually added and implies SANITIZED and SAFE_FOR_API."""
        var = VariableDefinition(
            name="temperature",
            type=VariableType.FLOAT,
            default=0.0,
            mutable_by=[MutableBy.API],
            tags={VariableTag.API_DATA}  # Manually add API_DATA tag
        )

        # API_DATA tag should imply SANITIZED and SAFE_FOR_API
        assert VariableTag.API_DATA in var.tags
        assert VariableTag.SANITIZED in var.tags
        assert VariableTag.SAFE_FOR_API in var.tags
        assert var.is_safe_for_api_use()

    def test_default_visibility_is_private(self):
        """Test that variables without visibility tag default to private."""
        var = VariableDefinition(
            name="internal_state",
            type=VariableType.INTEGER,
            default=0,
            mutable_by=[MutableBy.ENGINE]
        )

        assert VariableTag.PRIVATE in var.tags
        assert not var.is_public()

    def test_cannot_be_both_public_and_private(self):
        """Test that variable can't be both public and private."""
        with pytest.raises(ValueError, match="cannot be both PUBLIC and PRIVATE"):
            VariableDefinition(
                name="invalid",
                type=VariableType.INTEGER,
                default=0,
                mutable_by=[MutableBy.ENGINE],
                tags={VariableTag.PUBLIC, VariableTag.PRIVATE}
            )

    def test_immutable_requires_empty_mutable_by(self):
        """Test that immutable tag requires empty mutable_by."""
        # Valid immutable
        var = VariableDefinition(
            name="constant",
            type=VariableType.STRING,
            default="fixed_value",
            mutable_by=[],
            tags={VariableTag.IMMUTABLE}
        )
        assert var.is_immutable()

        # Invalid: immutable but mutable_by not empty
        with pytest.raises(ValueError, match="immutable.*mutable_by"):
            VariableDefinition(
                name="invalid",
                type=VariableType.STRING,
                default="",
                mutable_by=[MutableBy.USER],
                tags={VariableTag.IMMUTABLE}
            )

    def test_leaderboard_must_be_numeric(self):
        """Test that leaderboard tag requires numeric type."""
        # Valid: integer leaderboard
        var_int = VariableDefinition(
            name="total_score",
            type=VariableType.INTEGER,
            default=0,
            mutable_by=[MutableBy.ENGINE],
            tags={VariableTag.LEADERBOARD}
        )
        assert VariableTag.LEADERBOARD in var_int.tags

        # Valid: float leaderboard
        var_float = VariableDefinition(
            name="accuracy",
            type=VariableType.FLOAT,
            default=0.0,
            mutable_by=[MutableBy.ENGINE],
            tags={VariableTag.LEADERBOARD}
        )
        assert VariableTag.LEADERBOARD in var_float.tags

        # Invalid: string leaderboard
        with pytest.raises(ValueError, match="leaderboard.*must be integer or float"):
            VariableDefinition(
                name="invalid_leaderboard",
                type=VariableType.STRING,
                default="",
                mutable_by=[MutableBy.ENGINE],
                tags={VariableTag.LEADERBOARD}
            )

    def test_leaderboard_tag_implies_score_and_public(self):
        """Test that leaderboard tag automatically adds score and public tags."""
        var = VariableDefinition(
            name="rank_score",
            type=VariableType.INTEGER,
            default=0,
            mutable_by=[MutableBy.ENGINE],
            tags={VariableTag.LEADERBOARD}
        )

        # LEADERBOARD should imply both SCORE and PUBLIC
        assert VariableTag.LEADERBOARD in var.tags
        assert VariableTag.SCORE in var.tags
        assert VariableTag.PUBLIC in var.tags
        assert var.is_score()
        assert var.is_public()


class TestVariableStore:
    """Test variable store runtime operations."""

    def test_variable_store_initialization(self):
        """Test that variable store initializes with default values."""
        definitions = {
            "score": VariableDefinition(
                name="score",
                type=VariableType.INTEGER,
                default=0,
                mutable_by=[MutableBy.ENGINE],
                tags={VariableTag.SCORE}
            ),
            "city": VariableDefinition(
                name="city",
                type=VariableType.STRING,
                default="berlin",
                mutable_by=[MutableBy.USER],
                constraints=VariableConstraints(
                    enum=["berlin", "london"]
                )
            )
        }

        store = VariableStore(definitions)

        # Check defaults are set
        assert store.get("score") == 0
        assert store.get("city") == "berlin"

    def test_set_variable_with_type_validation(self):
        """Test that setting variables enforces type."""
        var_def = VariableDefinition(
            name="count",
            type=VariableType.INTEGER,
            default=0,
            mutable_by=[MutableBy.USER]
        )
        store = VariableStore({"count": var_def})

        # Valid: int
        store.set("count", 42, MutableBy.USER)
        assert store.get("count") == 42

        # Valid: coercible to int
        store.set("count", "123", MutableBy.USER)
        assert store.get("count") == 123

        # Invalid: cannot coerce
        with pytest.raises(ValueError, match="expects integer"):
            store.set("count", "not_a_number", MutableBy.USER)

    def test_set_variable_respects_mutability(self):
        """Test that only authorized actors can modify variables."""
        var_def = VariableDefinition(
            name="api_result",
            type=VariableType.FLOAT,
            default=0.0,
            mutable_by=[MutableBy.API]  # Only API can modify
        )
        store = VariableStore({"api_result": var_def})

        # API can modify
        store.set("api_result", 25.5, MutableBy.API)
        assert store.get("api_result") == 25.5

        # User cannot modify
        with pytest.raises(PermissionError, match="cannot modify"):
            store.set("api_result", 30.0, MutableBy.USER)

    def test_immutable_variables_cannot_be_modified(self):
        """Test that immutable variables reject all modifications."""
        var_def = VariableDefinition(
            name="constant",
            type=VariableType.STRING,
            default="fixed",
            mutable_by=[],
            tags={VariableTag.IMMUTABLE}
        )
        store = VariableStore({"constant": var_def})

        # Cannot modify even with correct actor
        with pytest.raises(PermissionError, match="cannot modify"):
            store.set("constant", "changed", MutableBy.ENGINE)

    def test_constraints_min_max_validation(self):
        """Test that numeric constraints are enforced."""
        var_def = VariableDefinition(
            name="temperature",
            type=VariableType.FLOAT,
            default=20.0,
            mutable_by=[MutableBy.USER],
            constraints=VariableConstraints(
                min_value=-50.0,
                max_value=50.0
            )
        )
        store = VariableStore({"temperature": var_def})

        # Valid: within range
        store.set("temperature", 25.0, MutableBy.USER)
        assert store.get("temperature") == 25.0

        # Invalid: below min
        with pytest.raises(ValueError, match="below minimum"):
            store.set("temperature", -100.0, MutableBy.USER)

        # Invalid: above max
        with pytest.raises(ValueError, match="above maximum"):
            store.set("temperature", 100.0, MutableBy.USER)

    def test_constraints_enum_validation(self):
        """Test that enum constraints are enforced."""
        var_def = VariableDefinition(
            name="choice",
            type=VariableType.STRING,
            default="a",
            mutable_by=[MutableBy.USER],
            constraints=VariableConstraints(
                enum=["a", "b", "c"]
            )
        )
        store = VariableStore({"choice": var_def})

        # Valid: in enum
        store.set("choice", "b", MutableBy.USER)
        assert store.get("choice") == "b"

        # Invalid: not in enum
        with pytest.raises(ValueError, match="not in allowed values"):
            store.set("choice", "d", MutableBy.USER)

    def test_constraints_string_length(self):
        """Test that string length constraints are enforced."""
        var_def = VariableDefinition(
            name="comment",
            type=VariableType.STRING,
            default="",
            mutable_by=[MutableBy.USER],
            constraints=VariableConstraints(
                min_length=1,
                max_length=100
            )
        )
        store = VariableStore({"comment": var_def})

        # Valid: within length
        store.set("comment", "Good quiz!", MutableBy.USER)
        assert store.get("comment") == "Good quiz!"

        # Invalid: too short
        with pytest.raises(ValueError, match="below minimum"):
            store.set("comment", "", MutableBy.USER)

        # Invalid: too long
        with pytest.raises(ValueError, match="above maximum"):
            store.set("comment", "a" * 101, MutableBy.USER)

    def test_get_scores(self):
        """Test retrieving all score variables."""
        definitions = {
            "user_score": VariableDefinition(
                name="user_score",
                type=VariableType.INTEGER,
                default=10,
                mutable_by=[MutableBy.ENGINE],
                tags={VariableTag.SCORE}
            ),
            "bonus_points": VariableDefinition(
                name="bonus_points",
                type=VariableType.INTEGER,
                default=5,
                mutable_by=[MutableBy.ENGINE],
                tags={VariableTag.SCORE}
            ),
            "internal_state": VariableDefinition(
                name="internal_state",
                type=VariableType.INTEGER,
                default=0,
                mutable_by=[MutableBy.ENGINE]
                # No SCORE tag
            )
        }

        store = VariableStore(definitions)
        scores = store.get_scores()

        # Should only include score-tagged variables
        assert "user_score" in scores
        assert "bonus_points" in scores
        assert "internal_state" not in scores

        assert scores["user_score"] == 10
        assert scores["bonus_points"] == 5

    def test_get_public_variables(self):
        """Test retrieving all public variables."""
        definitions = {
            "public_score": VariableDefinition(
                name="public_score",
                type=VariableType.INTEGER,
                default=100,
                mutable_by=[MutableBy.ENGINE],
                tags={VariableTag.PUBLIC}
            ),
            "private_state": VariableDefinition(
                name="private_state",
                type=VariableType.INTEGER,
                default=0,
                mutable_by=[MutableBy.ENGINE],
                tags={VariableTag.PRIVATE}
            )
        }

        store = VariableStore(definitions)
        public_vars = store.get_public_variables()

        assert "public_score" in public_vars
        assert "private_state" not in public_vars

    def test_get_by_tag(self):
        """Test filtering variables by tag."""
        definitions = {
            "user_input_1": VariableDefinition(
                name="user_input_1",
                type=VariableType.STRING,
                default="",
                mutable_by=[MutableBy.USER],
                tags={VariableTag.USER_INPUT}
            ),
            "user_input_2": VariableDefinition(
                name="user_input_2",
                type=VariableType.STRING,
                default="",
                mutable_by=[MutableBy.USER],
                tags={VariableTag.USER_INPUT}
            ),
            "api_data": VariableDefinition(
                name="api_data",
                type=VariableType.FLOAT,
                default=0.0,
                mutable_by=[MutableBy.API],
                tags={VariableTag.API_DATA}
            )
        }

        store = VariableStore(definitions)
        user_inputs = store.get_by_tag(VariableTag.USER_INPUT)

        assert "user_input_1" in user_inputs
        assert "user_input_2" in user_inputs
        assert "api_data" not in user_inputs

    def test_only_one_leaderboard_variable_allowed(self):
        """Test that only one variable can have leaderboard tag."""
        # Valid: one leaderboard variable
        definitions_valid = {
            "main_score": VariableDefinition(
                name="main_score",
                type=VariableType.INTEGER,
                default=0,
                mutable_by=[MutableBy.ENGINE],
                tags={VariableTag.LEADERBOARD}
            ),
            "bonus_points": VariableDefinition(
                name="bonus_points",
                type=VariableType.INTEGER,
                default=0,
                mutable_by=[MutableBy.ENGINE],
                tags={VariableTag.SCORE}  # SCORE but not LEADERBOARD
            )
        }
        store = VariableStore(definitions_valid)
        assert store.get_leaderboard_score() is not None

        # Invalid: multiple leaderboard variables
        definitions_invalid = {
            "score_1": VariableDefinition(
                name="score_1",
                type=VariableType.INTEGER,
                default=0,
                mutable_by=[MutableBy.ENGINE],
                tags={VariableTag.LEADERBOARD}
            ),
            "score_2": VariableDefinition(
                name="score_2",
                type=VariableType.INTEGER,
                default=0,
                mutable_by=[MutableBy.ENGINE],
                tags={VariableTag.LEADERBOARD}
            )
        }

        with pytest.raises(ValueError, match="Only ONE variable can have 'leaderboard' tag"):
            VariableStore(definitions_invalid)

    def test_get_leaderboard_score(self):
        """Test retrieving the leaderboard score variable."""
        # Quiz with leaderboard variable
        definitions = {
            "total_score": VariableDefinition(
                name="total_score",
                type=VariableType.INTEGER,
                default=100,
                mutable_by=[MutableBy.ENGINE],
                tags={VariableTag.LEADERBOARD}
            ),
            "bonus_points": VariableDefinition(
                name="bonus_points",
                type=VariableType.INTEGER,
                default=5,
                mutable_by=[MutableBy.ENGINE],
                tags={VariableTag.SCORE}
            )
        }

        store = VariableStore(definitions)
        leaderboard_score = store.get_leaderboard_score()

        assert leaderboard_score is not None
        assert leaderboard_score[0] == "total_score"
        assert leaderboard_score[1] == 100

        # Quiz without leaderboard variable
        definitions_no_leaderboard = {
            "some_score": VariableDefinition(
                name="some_score",
                type=VariableType.INTEGER,
                default=50,
                mutable_by=[MutableBy.ENGINE],
                tags={VariableTag.SCORE}
            )
        }

        store_no_leaderboard = VariableStore(definitions_no_leaderboard)
        assert store_no_leaderboard.get_leaderboard_score() is None


class TestVariableSerialization:
    """Test variable definition serialization."""

    def test_to_dict_includes_tags(self):
        """Test that to_dict includes tags."""
        var = VariableDefinition(
            name="score",
            type=VariableType.INTEGER,
            default=0,
            mutable_by=[MutableBy.ENGINE],
            tags={VariableTag.SCORE},
            description="User score"
        )

        data = var.to_dict()

        assert data["name"] == "score"
        assert data["type"] == "integer"
        assert data["default"] == 0
        assert "engine" in data["mutable_by"]
        assert "score" in data["tags"]
        assert "public" in data["tags"]  # Auto-added
        assert data["description"] == "User score"

    def test_from_dict_reconstructs_variable(self):
        """Test that from_dict properly reconstructs variable."""
        data = {
            "type": "float",
            "default": 25.0,
            "mutable_by": ["api"],
            "tags": ["api_data"],
            "description": "Temperature from API"
        }

        var = VariableDefinition.from_dict("temperature", data)

        assert var.name == "temperature"
        assert var.type == VariableType.FLOAT
        assert var.default == 25.0
        assert MutableBy.API in var.mutable_by
        assert VariableTag.API_DATA in var.tags
        assert VariableTag.SANITIZED in var.tags  # Auto-added
        assert var.description == "Temperature from API"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

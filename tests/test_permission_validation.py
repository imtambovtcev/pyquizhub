"""
Tests for permission-aware validation.

The validator is user-agnostic - it only knows about permission tiers.
It checks if a given permission tier has rights to use the features in a quiz.
"""
import pytest
from pyquizhub.core.engine.json_validator import QuizJSONValidator
from pyquizhub.core.engine.variable_types import CreatorPermissionTier


class TestPermissionValidation:
    """Test that permission tier validation works correctly."""

    def test_simple_quiz_allowed_for_all_tiers(self):
        """Test that simple quiz without API integrations is allowed for all tiers."""
        quiz_data = {
            "metadata": {"title": "Simple Quiz", "description": "No APIs"},
            "variables": {
                "score": {
                    "type": "integer",
                    "mutable_by": ["engine"]
                }
            },
            "questions": [{"id": 1, "data": {"text": "Question?", "type": "text"}}],
            "transitions": {"1": [{"expression": "true", "next_question_id": None}]}
        }

        # All tiers should pass
        for tier in [
                CreatorPermissionTier.RESTRICTED,
                CreatorPermissionTier.STANDARD,
                CreatorPermissionTier.ADVANCED,
                CreatorPermissionTier.ADMIN]:
            result = QuizJSONValidator.validate(quiz_data, tier)
            assert len(result["errors"]) == 0
            assert len(result["permission_errors"]) == 0, \
                f"Tier {tier.value} should allow simple quiz without APIs"

    def test_restricted_allows_fixed_url_get(self):
        """Test that RESTRICTED tier allows fixed URL GET requests."""
        quiz_data = {
            "metadata": {"title": "Test", "description": "Test"},
            "variables": {
                "temp": {"type": "float", "mutable_by": ["api"]}
            },
            "api_integrations": [
                {
                    "id": "weather",
                    "url": "https://api.example.com/weather",
                    "method": "GET"
                }
            ],
            "questions": [{"id": 1, "data": {"text": "Q", "type": "text"}}],
            "transitions": {"1": [{"expression": "true", "next_question_id": None}]}
        }

        result = QuizJSONValidator.validate(
            quiz_data, CreatorPermissionTier.RESTRICTED)
        assert len(result["errors"]) == 0
        assert len(result["permission_errors"]) == 0

    def test_restricted_rejects_post_method(self):
        """Test that RESTRICTED tier rejects POST requests."""
        quiz_data = {
            "metadata": {"title": "Test", "description": "Test"},
            "variables": {
                "result": {"type": "string", "mutable_by": ["api"]}
            },
            "api_integrations": [
                {
                    "id": "submit",
                    "url": "https://api.example.com/submit",
                    "method": "POST"
                }
            ],
            "questions": [{"id": 1, "data": {"text": "Q", "type": "text"}}],
            "transitions": {"1": [{"expression": "true", "next_question_id": None}]}
        }

        result = QuizJSONValidator.validate(
            quiz_data, CreatorPermissionTier.RESTRICTED)
        assert len(result["permission_errors"]) > 0
        assert any("POST method" in err for err in result["permission_errors"])
        assert any(
            "RESTRICTED tier only allows GET" in err for err in result["permission_errors"])

    def test_restricted_rejects_url_template(self):
        """Test that RESTRICTED tier rejects dynamic URL templates."""
        quiz_data = {
            "metadata": {"title": "Test", "description": "Test"},
            "variables": {
                "city": {"type": "string", "mutable_by": ["user"]},
                "temp": {"type": "float", "mutable_by": ["api"]}
            },
            "api_integrations": [
                {
                    "id": "weather",
                    "method": "GET",
                    "prepare_request": {
                        "url_template": "https://api.example.com/weather/{city}"
                    }
                }
            ],
            "questions": [{"id": 1, "data": {"text": "Q", "type": "text"}}],
            "transitions": {"1": [{"expression": "true", "next_question_id": None}]}
        }

        result = QuizJSONValidator.validate(
            quiz_data, CreatorPermissionTier.RESTRICTED)
        assert len(result["permission_errors"]) > 0
        assert any(
            "url_template" in err for err in result["permission_errors"])
        assert any(
            "RESTRICTED tier only allows fixed URLs" in err for err in result["permission_errors"])

    def test_standard_rejects_url_template(self):
        """Test that STANDARD tier also rejects url_template (only query params allowed)."""
        quiz_data = {
            "metadata": {"title": "Test", "description": "Test"},
            "variables": {
                "city": {"type": "string", "mutable_by": ["user"]},
                "temp": {"type": "float", "mutable_by": ["api"]}
            },
            "api_integrations": [
                {
                    "id": "weather",
                    "method": "GET",
                    "prepare_request": {
                        "url_template": "https://api.example.com/weather/{city}"
                    }
                }
            ],
            "questions": [{"id": 1, "data": {"text": "Q", "type": "text"}}],
            "transitions": {"1": [{"expression": "true", "next_question_id": None}]}
        }

        result = QuizJSONValidator.validate(
            quiz_data, CreatorPermissionTier.STANDARD)
        assert len(result["permission_errors"]) > 0
        assert any(
            "url_template" in err for err in result["permission_errors"])
        assert any(
            "STANDARD tier only allows variables in query parameters" in err for err in result["permission_errors"])

    def test_advanced_allows_url_template(self):
        """Test that ADVANCED tier allows dynamic URL templates."""
        quiz_data = {
            "metadata": {"title": "Test", "description": "Test"},
            "variables": {
                "city": {"type": "string", "mutable_by": ["user"]},
                "temp": {"type": "float", "mutable_by": ["api"]}
            },
            "api_integrations": [
                {
                    "id": "weather",
                    "method": "GET",
                    "prepare_request": {
                        "url_template": "https://api.example.com/weather/{city}"
                    }
                }
            ],
            "questions": [{"id": 1, "data": {"text": "Q", "type": "text"}}],
            "transitions": {"1": [{"expression": "true", "next_question_id": None}]}
        }

        result = QuizJSONValidator.validate(
            quiz_data, CreatorPermissionTier.ADVANCED)
        assert len(result["errors"]) == 0
        assert len(result["permission_errors"]) == 0

    def test_advanced_allows_post_with_body_template(self):
        """Test that ADVANCED tier allows POST with body templates."""
        quiz_data = {
            "metadata": {"title": "Test", "description": "Test"},
            "variables": {
                "user_input": {"type": "string", "mutable_by": ["user"]},
                "response": {"type": "string", "mutable_by": ["api"]}
            },
            "api_integrations": [
                {
                    "id": "submit",
                    "url": "https://api.example.com/submit",
                    "method": "POST",
                    "body_template": {
                        "data": "{user_input}"
                    }
                }
            ],
            "questions": [{"id": 1, "data": {"text": "Q", "type": "text"}}],
            "transitions": {"1": [{"expression": "true", "next_question_id": None}]}
        }

        result = QuizJSONValidator.validate(
            quiz_data, CreatorPermissionTier.ADVANCED)
        assert len(result["errors"]) == 0
        assert len(result["permission_errors"]) == 0

    def test_standard_rejects_body_template(self):
        """Test that STANDARD tier rejects body templates."""
        quiz_data = {
            "metadata": {"title": "Test", "description": "Test"},
            "variables": {
                "user_input": {"type": "string", "mutable_by": ["user"]},
                "response": {"type": "string", "mutable_by": ["api"]}
            },
            "api_integrations": [
                {
                    "id": "submit",
                    "method": "POST",
                    "prepare_request": {
                        "url_template": "https://api.example.com/submit",
                        "body_template": {
                            "data": "{user_input}"
                        }
                    }
                }
            ],
            "questions": [{"id": 1, "data": {"text": "Q", "type": "text"}}],
            "transitions": {"1": [{"expression": "true", "next_question_id": None}]}
        }

        result = QuizJSONValidator.validate(
            quiz_data, CreatorPermissionTier.STANDARD)
        assert len(result["permission_errors"]) > 0
        assert any(
            "body template" in err for err in result["permission_errors"])
        assert any(
            "ADVANCED tier" in err for err in result["permission_errors"])

    def test_api_count_limits(self):
        """Test that API count limits are enforced per tier."""
        # Create quiz with 6 API integrations
        api_integrations = [
            {
                "id": f"api_{i}",
                "url": f"https://api.example.com/endpoint{i}",
                "method": "GET"
            }
            for i in range(6)
        ]

        quiz_data = {
            "metadata": {"title": "Test", "description": "Test"},
            "variables": {
                "result": {"type": "string", "mutable_by": ["api"]}
            },
            "api_integrations": api_integrations,
            "questions": [{"id": 1, "data": {"text": "Q", "type": "text"}}],
            "transitions": {"1": [{"expression": "true", "next_question_id": None}]}
        }

        # RESTRICTED allows max 5 - should fail
        result = QuizJSONValidator.validate(
            quiz_data, CreatorPermissionTier.RESTRICTED)
        assert len(result["permission_errors"]) > 0
        assert any(
            "max 5" in err and "has 6" in err for err in result["permission_errors"])

        # STANDARD allows max 20 - should pass
        result = QuizJSONValidator.validate(
            quiz_data, CreatorPermissionTier.STANDARD)
        assert len(result["permission_errors"]) == 0

        # ADVANCED allows max 50 - should pass
        result = QuizJSONValidator.validate(
            quiz_data, CreatorPermissionTier.ADVANCED)
        assert len(result["permission_errors"]) == 0

        # ADMIN allows unlimited - should pass
        result = QuizJSONValidator.validate(
            quiz_data, CreatorPermissionTier.ADMIN)
        assert len(result["permission_errors"]) == 0

    def test_restricted_rejects_custom_auth(self):
        """Test that RESTRICTED tier rejects custom authentication."""
        quiz_data = {
            "metadata": {"title": "Test", "description": "Test"},
            "variables": {
                "result": {"type": "string", "mutable_by": ["api"]}
            },
            "api_integrations": [
                {
                    "id": "api",
                    "url": "https://api.example.com/data",
                    "method": "GET",
                    "authentication": {
                        "type": "bearer_token",
                        "token": "secret"
                    }
                }
            ],
            "questions": [{"id": 1, "data": {"text": "Q", "type": "text"}}],
            "transitions": {"1": [{"expression": "true", "next_question_id": None}]}
        }

        result = QuizJSONValidator.validate(
            quiz_data, CreatorPermissionTier.RESTRICTED)
        assert len(result["permission_errors"]) > 0
        assert any(
            "authentication" in err for err in result["permission_errors"])

    def test_admin_bypasses_all_restrictions(self):
        """Test that ADMIN tier bypasses all restrictions."""
        # Create quiz with all restricted features
        quiz_data = {
            "metadata": {"title": "Test", "description": "Test"},
            "variables": {
                "city": {"type": "string", "mutable_by": ["user"]},
                "data": {"type": "string", "mutable_by": ["user"]},
                "result": {"type": "string", "mutable_by": ["api"]}
            },
            "api_integrations": [
                {
                    "id": "api1",
                    "method": "POST",
                    "prepare_request": {
                        "url_template": "https://api.example.com/{city}",
                        "body_template": {"input": "{data}"}
                    },
                    "authentication": {
                        "type": "custom",
                        "token": "{auth_token}"
                    }
                }
            ],
            "questions": [{"id": 1, "data": {"text": "Q", "type": "text"}}],
            "transitions": {"1": [{"expression": "true", "next_question_id": None}]}
        }

        result = QuizJSONValidator.validate(
            quiz_data, CreatorPermissionTier.ADMIN)
        assert len(result["errors"]) == 0
        assert len(result["permission_errors"]) == 0

    def test_default_tier_is_restricted(self):
        """Test that default permission tier is RESTRICTED for security."""
        quiz_data = {
            "metadata": {"title": "Test", "description": "Test"},
            "variables": {
                "result": {"type": "string", "mutable_by": ["api"]}
            },
            "api_integrations": [
                {
                    "id": "api",
                    "url": "https://api.example.com/data",
                    "method": "POST"  # Not allowed for RESTRICTED
                }
            ],
            "questions": [{"id": 1, "data": {"text": "Q", "type": "text"}}],
            "transitions": {"1": [{"expression": "true", "next_question_id": None}]}
        }

        # Validate without specifying tier - should default to RESTRICTED
        result = QuizJSONValidator.validate(quiz_data)
        assert len(result["permission_errors"]) > 0
        assert any("POST method" in err for err in result["permission_errors"])

    def test_permission_errors_separate_from_structural_errors(self):
        """Test that permission errors are separate from structural errors."""
        quiz_data = {
            "metadata": {"title": "Test", "description": "Test"},
            "variables": {
                "bad_var": {
                    # Missing required 'type' field - structural error
                    "mutable_by": ["engine"]
                },
                "result": {"type": "string", "mutable_by": ["api"]}
            },
            "api_integrations": [
                {
                    "id": "api",
                    "url": "https://api.example.com/data",
                    "method": "POST"  # Permission error for RESTRICTED
                }
            ],
            "questions": [{"id": 1, "data": {"text": "Q", "type": "text"}}],
            "transitions": {"1": [{"expression": "true", "next_question_id": None}]}
        }

        result = QuizJSONValidator.validate(
            quiz_data, CreatorPermissionTier.RESTRICTED)

        # Should have both structural errors and permission errors
        # Structural error from missing 'type'
        assert len(result["errors"]) > 0
        # Permission error from POST method
        assert len(result["permission_errors"]) > 0

        # Verify they are separate
        assert "errors" in result
        assert "permission_errors" in result
        assert result["errors"] != result["permission_errors"]

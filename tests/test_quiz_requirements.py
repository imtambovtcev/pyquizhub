"""
Tests for Quiz Requirements Analyzer.

Tests the detection of quiz requirements and permission checking.
"""

from __future__ import annotations

import pytest
from pyquizhub.core.engine.quiz_requirements import (
    QuizRequirementsAnalyzer,
    QuizRequirements,
    PermissionCheckResult,
    URLAccessPattern,
)
from pyquizhub.config.settings import (
    RolePermissions,
    RateLimitSettings,
    FileUploadPermissions,
    APIIntegrationPermissions,
)


class TestURLAccessPattern:
    """Test URL access pattern parsing."""

    def test_fully_fixed_url(self):
        """Test parsing a fully fixed URL."""
        pattern = URLAccessPattern.parse("https://api.example.com/v1/data")

        assert pattern.is_fully_dynamic is False
        assert pattern.has_variable_suffix is False
        assert pattern.fixed_prefix == "https://api.example.com/v1/data"
        assert pattern.original_template == "https://api.example.com/v1/data"

    def test_url_with_variable_suffix(self):
        """Test URL with variable part at the end."""
        pattern = URLAccessPattern.parse("https://api.example.com/v1/{city}/weather")

        assert pattern.is_fully_dynamic is False
        assert pattern.has_variable_suffix is True
        assert pattern.fixed_prefix == "https://api.example.com/v1/"

    def test_url_with_variable_in_path(self):
        """Test URL with variable in middle of path."""
        pattern = URLAccessPattern.parse("https://api.example.com/{version}/data")

        assert pattern.is_fully_dynamic is False
        assert pattern.has_variable_suffix is True
        assert pattern.fixed_prefix == "https://api.example.com/"

    def test_fully_dynamic_url(self):
        """Test fully dynamic URL (single variable)."""
        pattern = URLAccessPattern.parse("{variables.api_url}")

        assert pattern.is_fully_dynamic is True
        assert pattern.has_variable_suffix is False
        assert pattern.fixed_prefix == ""

    def test_url_starting_with_variable(self):
        """Test URL starting with variable but has more."""
        pattern = URLAccessPattern.parse("{base_url}/v1/data")

        assert pattern.is_fully_dynamic is True
        assert pattern.has_variable_suffix is True
        assert pattern.fixed_prefix == ""

    def test_empty_url(self):
        """Test empty URL."""
        pattern = URLAccessPattern.parse("")

        assert pattern.is_fully_dynamic is False
        assert pattern.has_variable_suffix is False
        assert pattern.fixed_prefix == ""

    def test_localhost_url(self):
        """Test localhost URL."""
        pattern = URLAccessPattern.parse("http://localhost:8000/api/data")

        assert pattern.is_fully_dynamic is False
        assert pattern.has_variable_suffix is False
        assert pattern.fixed_prefix == "http://localhost:8000/api/data"

    def test_serialization_roundtrip(self):
        """Test to_dict and from_dict."""
        original = URLAccessPattern.parse("https://api.example.com/{city}/weather")
        data = original.to_dict()
        restored = URLAccessPattern.from_dict(data)

        assert restored.original_template == original.original_template
        assert restored.fixed_prefix == original.fixed_prefix
        assert restored.has_variable_suffix == original.has_variable_suffix
        assert restored.is_fully_dynamic == original.is_fully_dynamic

    def test_permission_matching_wildcard(self):
        """Test permission matching with wildcard."""
        pattern = URLAccessPattern.parse("https://api.example.com/v1/data")

        assert pattern.matches_permission("*") is True

    def test_permission_matching_exact(self):
        """Test permission matching with exact URL."""
        pattern = URLAccessPattern.parse("https://api.example.com/v1/data")

        assert pattern.matches_permission("https://api.example.com/v1/data") is True
        assert pattern.matches_permission("https://api.example.com/v1/other") is False

    def test_permission_matching_prefix_wildcard(self):
        """Test permission matching with prefix wildcard."""
        pattern = URLAccessPattern.parse("https://api.example.com/v1/users/123")

        assert pattern.matches_permission("https://api.example.com/*") is True
        assert pattern.matches_permission("https://api.example.com/v1/*") is True
        assert pattern.matches_permission("https://other.com/*") is False


class TestQuizRequirementsAnalyzer:
    """Test quiz requirements analysis."""

    def test_simple_quiz_no_requirements(self):
        """Test a simple quiz with no special requirements."""
        quiz_data = {
            "metadata": {"title": "Simple Quiz", "version": "1.0"},
            "questions": [
                {
                    "id": 1,
                    "data": {
                        "type": "multiple_choice",
                        "text": "What is 2+2?",
                        "options": [
                            {"label": "3", "value": "3"},
                            {"label": "4", "value": "4"},
                        ]
                    }
                }
            ]
        }

        requirements = QuizRequirementsAnalyzer.analyze(quiz_data)

        assert requirements.requires_api_integrations is False
        assert requirements.requires_file_uploads is False
        assert requirements.has_external_attachments is False
        assert requirements.max_questions == 1

    def test_quiz_with_api_integrations(self):
        """Test detection of API integration requirements."""
        quiz_data = {
            "metadata": {"title": "API Quiz", "version": "1.0"},
            "api_integrations": [
                {
                    "id": "weather_api",
                    "method": "GET",
                    "timing": "before_question",
                    "question_id": 1,
                    "prepare_request": {
                        "url_template": "https://api.weather.com/v1/forecast",
                    }
                },
                {
                    "id": "local_api",
                    "method": "POST",
                    "timing": "after_answer",
                    "question_id": 2,
                    "prepare_request": {
                        "url_template": "http://localhost:8000/analyze",
                    }
                }
            ],
            "questions": [
                {"id": 1, "data": {"type": "text", "text": "Q1"}},
                {"id": 2, "data": {"type": "text", "text": "Q2"}},
            ]
        }

        requirements = QuizRequirementsAnalyzer.analyze(quiz_data)

        assert requirements.requires_api_integrations is True
        assert len(requirements.api_integrations) == 2
        assert "api.weather.com" in requirements.api_hosts
        assert "localhost" in requirements.api_hosts

    def test_quiz_with_file_uploads(self):
        """Test detection of file upload requirements."""
        quiz_data = {
            "metadata": {"title": "File Upload Quiz", "version": "1.0"},
            "questions": [
                {
                    "id": 1,
                    "data": {
                        "type": "file_upload",
                        "text": "Upload your document",
                        "allowed_types": ["document", "image"],
                        "required": True,
                    }
                }
            ]
        }

        requirements = QuizRequirementsAnalyzer.analyze(quiz_data)

        assert requirements.requires_file_uploads is True
        assert len(requirements.file_uploads) == 1
        assert "document" in requirements.file_categories_needed
        assert "image" in requirements.file_categories_needed

    def test_quiz_with_attachments(self):
        """Test detection of external attachments."""
        quiz_data = {
            "metadata": {"title": "Image Quiz", "version": "1.0"},
            "questions": [
                {
                    "id": 1,
                    "data": {
                        "type": "multiple_choice",
                        "text": "What is this?",
                        "attachments": [
                            {
                                "type": "image",
                                "url": "https://example.com/image.jpg"
                            }
                        ],
                        "options": [{"label": "A", "value": "a"}]
                    }
                }
            ]
        }

        requirements = QuizRequirementsAnalyzer.analyze(quiz_data)

        assert requirements.has_external_attachments is True
        assert len(requirements.attachments) == 1
        assert "example.com" in requirements.attachment_hosts

    def test_quiz_with_variable_url_attachments(self):
        """Test detection of variable URL patterns in attachments."""
        quiz_data = {
            "metadata": {"title": "Dynamic Image Quiz", "version": "1.0"},
            "questions": [
                {
                    "id": 1,
                    "data": {
                        "type": "multiple_choice",
                        "text": "Look at {variables.image_name}",
                        "attachments": [
                            {
                                "type": "image",
                                "url": "{variables.dynamic_url}"
                            }
                        ],
                        "options": [{"label": "A", "value": "a"}]
                    }
                }
            ]
        }

        requirements = QuizRequirementsAnalyzer.analyze(quiz_data)

        assert requirements.has_external_attachments is True
        # Check the new URLAccessPattern structure
        assert requirements.attachments[0].url_pattern.is_fully_dynamic is True
        assert requirements.attachments[0].url_pattern.original_template == "{variables.dynamic_url}"

    def test_quiz_with_regex_validation(self):
        """Test detection of regex usage."""
        quiz_data = {
            "metadata": {"title": "Regex Quiz", "version": "1.0"},
            "questions": [
                {
                    "id": 1,
                    "data": {
                        "type": "text",
                        "text": "Enter your email",
                        "constraints": {
                            "pattern": r"^[\w.-]+@[\w.-]+\.\w+$"
                        }
                    }
                }
            ]
        }

        requirements = QuizRequirementsAnalyzer.analyze(quiz_data)

        assert requirements.uses_regex is True

    def test_requirements_to_dict_and_back(self):
        """Test serialization roundtrip."""
        quiz_data = {
            "metadata": {"title": "Full Quiz", "version": "1.0"},
            "api_integrations": [
                {
                    "id": "test_api",
                    "method": "GET",
                    "timing": "before_question",
                    "question_id": 1,
                    "prepare_request": {
                        "url_template": "https://api.test.com/data",
                    }
                }
            ],
            "questions": [
                {
                    "id": 1,
                    "data": {
                        "type": "file_upload",
                        "text": "Upload file",
                        "allowed_types": ["document"],
                    }
                }
            ]
        }

        original = QuizRequirementsAnalyzer.analyze(quiz_data)
        data = original.to_dict()
        restored = QuizRequirements.from_dict(data)

        assert restored.requires_api_integrations == original.requires_api_integrations
        assert restored.requires_file_uploads == original.requires_file_uploads
        assert restored.api_hosts == original.api_hosts


class TestPermissionChecking:
    """Test permission checking against requirements."""

    @pytest.fixture
    def admin_permissions(self):
        """Admin permissions - full access."""
        return RolePermissions(
            rate_limits=RateLimitSettings(),
            file_uploads=FileUploadPermissions(
                enabled=True,
                max_file_size_mb=100,
                allowed_categories=["images", "audio", "video", "documents", "archives"],
                quota_mb=10000
            ),
            api_integrations=APIIntegrationPermissions(
                enabled=True,
                allowed_hosts=["*"],
                max_requests_per_quiz=1000
            )
        )

    @pytest.fixture
    def creator_permissions(self):
        """Creator permissions - limited access."""
        return RolePermissions(
            rate_limits=RateLimitSettings(),
            file_uploads=FileUploadPermissions(
                enabled=True,
                max_file_size_mb=10,
                allowed_categories=["images", "documents"],
                quota_mb=100
            ),
            api_integrations=APIIntegrationPermissions(
                enabled=True,
                allowed_hosts=["localhost", "127.0.0.1"],
                max_requests_per_quiz=20
            )
        )

    @pytest.fixture
    def user_permissions(self):
        """User permissions - minimal access."""
        return RolePermissions(
            rate_limits=RateLimitSettings(),
            file_uploads=FileUploadPermissions(
                enabled=False,
                max_file_size_mb=2,
                allowed_categories=["documents"],
                quota_mb=10
            ),
            api_integrations=APIIntegrationPermissions(
                enabled=False,
                allowed_hosts=[],
                max_requests_per_quiz=0
            )
        )

    def test_simple_quiz_allowed_for_all(self, admin_permissions, creator_permissions, user_permissions):
        """Test simple quiz is allowed for all roles."""
        quiz_data = {
            "metadata": {"title": "Simple Quiz", "version": "1.0"},
            "questions": [
                {"id": 1, "data": {"type": "text", "text": "Q1"}}
            ]
        }

        requirements = QuizRequirementsAnalyzer.analyze(quiz_data)

        for perms in [admin_permissions, creator_permissions, user_permissions]:
            result = QuizRequirementsAnalyzer.check_permissions(requirements, perms)
            assert result.allowed is True

    def test_api_quiz_denied_for_user(self, user_permissions):
        """Test API quiz is denied for user role."""
        quiz_data = {
            "metadata": {"title": "API Quiz", "version": "1.0"},
            "api_integrations": [
                {
                    "id": "test",
                    "method": "GET",
                    "timing": "before_question",
                    "prepare_request": {"url_template": "http://api.example.com/data"}
                }
            ],
            "questions": [{"id": 1, "data": {"type": "text", "text": "Q1"}}]
        }

        requirements = QuizRequirementsAnalyzer.analyze(quiz_data)
        result = QuizRequirementsAnalyzer.check_permissions(requirements, user_permissions)

        assert result.allowed is False
        assert len(result.missing_permissions) > 0
        assert "API integrations" in result.missing_permissions[0]

    def test_external_api_denied_for_creator(self, creator_permissions):
        """Test external API hosts denied for creator role."""
        quiz_data = {
            "metadata": {"title": "External API Quiz", "version": "1.0"},
            "api_integrations": [
                {
                    "id": "external",
                    "method": "GET",
                    "timing": "before_question",
                    "prepare_request": {"url_template": "https://api.external.com/data"}
                }
            ],
            "questions": [{"id": 1, "data": {"type": "text", "text": "Q1"}}]
        }

        requirements = QuizRequirementsAnalyzer.analyze(quiz_data)
        result = QuizRequirementsAnalyzer.check_permissions(requirements, creator_permissions)

        assert result.allowed is False
        assert any("api.external.com" in msg for msg in result.missing_permissions)

    def test_local_api_allowed_for_creator(self, creator_permissions):
        """Test local API hosts allowed for creator role."""
        quiz_data = {
            "metadata": {"title": "Local API Quiz", "version": "1.0"},
            "api_integrations": [
                {
                    "id": "local",
                    "method": "GET",
                    "timing": "before_question",
                    "prepare_request": {"url_template": "http://localhost:8000/data"}
                }
            ],
            "questions": [{"id": 1, "data": {"type": "text", "text": "Q1"}}]
        }

        requirements = QuizRequirementsAnalyzer.analyze(quiz_data)
        result = QuizRequirementsAnalyzer.check_permissions(requirements, creator_permissions)

        assert result.allowed is True

    def test_file_upload_denied_for_user(self, user_permissions):
        """Test file upload quiz denied for user role."""
        quiz_data = {
            "metadata": {"title": "File Quiz", "version": "1.0"},
            "questions": [
                {
                    "id": 1,
                    "data": {
                        "type": "file_upload",
                        "text": "Upload",
                        "allowed_types": ["document"]
                    }
                }
            ]
        }

        requirements = QuizRequirementsAnalyzer.analyze(quiz_data)
        result = QuizRequirementsAnalyzer.check_permissions(requirements, user_permissions)

        assert result.allowed is False
        assert any("File uploads" in msg for msg in result.missing_permissions)

    def test_video_upload_denied_for_creator(self, creator_permissions):
        """Test video file category denied for creator role."""
        quiz_data = {
            "metadata": {"title": "Video Quiz", "version": "1.0"},
            "questions": [
                {
                    "id": 1,
                    "data": {
                        "type": "file_upload",
                        "text": "Upload video",
                        "allowed_types": ["video"]
                    }
                }
            ]
        }

        requirements = QuizRequirementsAnalyzer.analyze(quiz_data)
        result = QuizRequirementsAnalyzer.check_permissions(requirements, creator_permissions)

        assert result.allowed is False
        assert any("video" in msg for msg in result.missing_permissions)

    def test_admin_can_do_everything(self, admin_permissions):
        """Test admin role can create any quiz."""
        quiz_data = {
            "metadata": {"title": "Complex Quiz", "version": "1.0"},
            "api_integrations": [
                {
                    "id": "external",
                    "method": "POST",
                    "timing": "before_question",
                    "prepare_request": {"url_template": "https://any.external.api.com/data"}
                }
            ],
            "questions": [
                {
                    "id": 1,
                    "data": {
                        "type": "file_upload",
                        "text": "Upload any file",
                        "allowed_types": ["video", "audio", "archives"]
                    }
                }
            ]
        }

        requirements = QuizRequirementsAnalyzer.analyze(quiz_data)
        result = QuizRequirementsAnalyzer.check_permissions(requirements, admin_permissions)

        assert result.allowed is True
        assert len(result.missing_permissions) == 0

    def test_external_attachments_generate_warning(self, admin_permissions):
        """Test that external attachments generate a warning."""
        quiz_data = {
            "metadata": {"title": "Image Quiz", "version": "1.0"},
            "questions": [
                {
                    "id": 1,
                    "data": {
                        "type": "multiple_choice",
                        "text": "Q1",
                        "attachments": [
                            {"type": "image", "url": "https://example.com/img.jpg"}
                        ],
                        "options": [{"label": "A", "value": "a"}]
                    }
                }
            ]
        }

        requirements = QuizRequirementsAnalyzer.analyze(quiz_data)
        result = QuizRequirementsAnalyzer.check_permissions(requirements, admin_permissions)

        assert result.allowed is True
        assert len(result.warnings) > 0
        assert "attachments" in result.warnings[0].lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

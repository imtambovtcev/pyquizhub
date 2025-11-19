"""
Tests for image URL permission tier enforcement.

This module tests that different permission tiers have appropriate
restrictions on image URL usage:
- RESTRICTED: Fixed HTTPS URLs from whitelisted services only (Cloudinary, Imgur, Unsplash, etc.)
- STANDARD: Fixed URLs (any domain) + SAFE_FOR_API variables
- ADVANCED: Full variable substitution
- ADMIN: Bypass some checks
"""

import pytest
import json
from pyquizhub.core.engine.json_validator import QuizJSONValidator
from pyquizhub.core.engine.variable_types import CreatorPermissionTier


class TestRestrictedTierImagePermissions:
    """Test RESTRICTED tier image URL permissions."""

    def test_restricted_allows_fixed_https_image(self):
        """Test RESTRICTED tier allows fixed HTTPS image URLs from whitelisted services."""
        quiz_data = {
            "metadata": {
                "title": "Test Quiz",
                "version": "2.0"
            },
            "variables": {
                "score": {
                    "type": "integer",
                    "mutable_by": ["engine"],
                    "tags": ["score"]
                }
            },
            "questions": [
                {
                    "id": 1,
                    "data": {
                        "text": "Question with image",
                        "type": "multiple_choice",
                        "image_url": "https://i.imgur.com/abc123.png",
                        "options": [
                            {"label": "A", "value": "a"}
                        ]
                    }
                }
            ],
            "transitions": {
                "1": [{"expression": "true", "next_question_id": None}]
            }
        }

        result = QuizJSONValidator.validate(
            quiz_data,
            CreatorPermissionTier.RESTRICTED
        )

        assert len(result["errors"]) == 0
        assert len(result["permission_errors"]) == 0

    def test_restricted_rejects_http_image(self):
        """Test RESTRICTED tier rejects HTTP image URLs."""
        quiz_data = {
            "metadata": {
                "title": "Test Quiz",
                "version": "2.0"
            },
            "variables": {
                "score": {
                    "type": "integer",
                    "mutable_by": ["engine"],
                    "tags": ["score"]
                }
            },
            "questions": [
                {
                    "id": 1,
                    "data": {
                        "text": "Question with HTTP image",
                        "type": "multiple_choice",
                        "image_url": "http://example.com/image.png",
                        "options": [
                            {"label": "A", "value": "a"}
                        ]
                    }
                }
            ],
            "transitions": {
                "1": [{"expression": "true", "next_question_id": None}]
            }
        }

        result = QuizJSONValidator.validate(
            quiz_data,
            CreatorPermissionTier.RESTRICTED
        )

        # Should have permission error about HTTP
        assert any(
            "non-HTTPS" in err for err in result["permission_errors"]
        )

    def test_restricted_rejects_variable_substitution(self):
        """Test RESTRICTED tier rejects variable substitution in image URLs."""
        quiz_data = {
            "metadata": {
                "title": "Test Quiz",
                "version": "2.0"
            },
            "variables": {
                "score": {
                    "type": "integer",
                    "mutable_by": ["engine"],
                    "tags": ["score"]
                },
                "image_id": {
                    "type": "string",
                    "mutable_by": ["engine"],
                    "tags": ["safe_for_api"],
                    "constraints": {"enum": ["dog", "cat"]},
                    "default": "dog"
                }
            },
            "questions": [
                {
                    "id": 1,
                    "data": {
                        "text": "Question",
                        "type": "multiple_choice",
                        "image_url": "https://example.com/{variables.image_id}.png",
                        "options": [
                            {"label": "A", "value": "a"}
                        ]
                    }
                }
            ],
            "transitions": {
                "1": [{"expression": "true", "next_question_id": None}]
            }
        }

        result = QuizJSONValidator.validate(
            quiz_data,
            CreatorPermissionTier.RESTRICTED
        )

        # Should have permission error about variable substitution
        assert any(
            "variable substitution" in err for err in result["permission_errors"]
        )


class TestStandardTierImagePermissions:
    """Test STANDARD tier image URL permissions."""

    def test_standard_allows_safe_variables(self):
        """Test STANDARD tier allows SAFE_FOR_API variables in image URLs."""
        quiz_data = {
            "metadata": {
                "title": "Test Quiz",
                "version": "2.0"
            },
            "variables": {
                "score": {
                    "type": "integer",
                    "mutable_by": ["engine"],
                    "tags": ["score"]
                },
                "image_format": {
                    "type": "string",
                    "mutable_by": ["engine"],
                    "tags": ["safe_for_api"],
                    "constraints": {"enum": ["png", "jpeg", "webp"]},
                    "default": "png"
                }
            },
            "questions": [
                {
                    "id": 1,
                    "data": {
                        "text": "Question",
                        "type": "multiple_choice",
                        "image_url": "https://httpbin.org/image/{variables.image_format}",
                        "options": [
                            {"label": "A", "value": "a"}
                        ]
                    }
                }
            ],
            "transitions": {
                "1": [{"expression": "true", "next_question_id": None}]
            }
        }

        result = QuizJSONValidator.validate(
            quiz_data,
            CreatorPermissionTier.STANDARD
        )

        assert len(result["errors"]) == 0
        assert len(result["permission_errors"]) == 0

    def test_standard_rejects_unsafe_variables(self):
        """Test STANDARD tier rejects unsafe variables in image URLs."""
        quiz_data = {
            "metadata": {
                "title": "Test Quiz",
                "version": "2.0"
            },
            "variables": {
                "score": {
                    "type": "integer",
                    "mutable_by": ["engine"],
                    "tags": ["score"]
                },
                "user_input": {
                    "type": "string",
                    "mutable_by": ["user"],
                    "tags": ["user_input"],
                    "default": ""
                }
            },
            "questions": [
                {
                    "id": 1,
                    "data": {
                        "text": "Question",
                        "type": "multiple_choice",
                        "image_url": "https://example.com/{variables.user_input}.png",
                        "options": [
                            {"label": "A", "value": "a"}
                        ]
                    }
                }
            ],
            "transitions": {
                "1": [{"expression": "true", "next_question_id": None}]
            }
        }

        result = QuizJSONValidator.validate(
            quiz_data,
            CreatorPermissionTier.STANDARD
        )

        # Should have permission error about unsafe variable
        assert any(
            "unsafe variable" in err for err in result["permission_errors"]
        )

    def test_standard_allows_http_with_warning(self):
        """Test STANDARD tier allows HTTP (unlike RESTRICTED)."""
        quiz_data = {
            "metadata": {
                "title": "Test Quiz",
                "version": "2.0"
            },
            "variables": {
                "score": {
                    "type": "integer",
                    "mutable_by": ["engine"],
                    "tags": ["score"]
                }
            },
            "questions": [
                {
                    "id": 1,
                    "data": {
                        "text": "Question",
                        "type": "multiple_choice",
                        "image_url": "http://example.com/image.png",
                        "options": [
                            {"label": "A", "value": "a"}
                        ]
                    }
                }
            ],
            "transitions": {
                "1": [{"expression": "true", "next_question_id": None}]
            }
        }

        result = QuizJSONValidator.validate(
            quiz_data,
            CreatorPermissionTier.STANDARD
        )

        # STANDARD tier should NOT have HTTP restriction
        assert not any(
            "non-HTTPS" in err for err in result["permission_errors"]
        )


class TestAdvancedTierImagePermissions:
    """Test ADVANCED tier image URL permissions."""

    def test_advanced_allows_unsafe_variables(self):
        """Test ADVANCED tier allows unsafe variables in image URLs."""
        quiz_data = {
            "metadata": {
                "title": "Test Quiz",
                "version": "2.0"
            },
            "variables": {
                "score": {
                    "type": "integer",
                    "mutable_by": ["engine"],
                    "tags": ["score"]
                },
                "api_image_url": {
                    "type": "string",
                    "mutable_by": ["api"],
                    "tags": ["api_data"],
                    "default": ""
                }
            },
            "questions": [
                {
                    "id": 1,
                    "data": {
                        "text": "Question",
                        "type": "multiple_choice",
                        "image_url": "{variables.api_image_url}",
                        "options": [
                            {"label": "A", "value": "a"}
                        ]
                    }
                }
            ],
            "transitions": {
                "1": [{"expression": "true", "next_question_id": None}]
            }
        }

        result = QuizJSONValidator.validate(
            quiz_data,
            CreatorPermissionTier.ADVANCED
        )

        assert len(result["permission_errors"]) == 0

    def test_advanced_allows_http(self):
        """Test ADVANCED tier allows HTTP URLs."""
        quiz_data = {
            "metadata": {
                "title": "Test Quiz",
                "version": "2.0"
            },
            "variables": {
                "score": {
                    "type": "integer",
                    "mutable_by": ["engine"],
                    "tags": ["score"]
                }
            },
            "questions": [
                {
                    "id": 1,
                    "data": {
                        "text": "Question",
                        "type": "multiple_choice",
                        "image_url": "http://example.com/image.png",
                        "options": [
                            {"label": "A", "value": "a"}
                        ]
                    }
                }
            ],
            "transitions": {
                "1": [{"expression": "true", "next_question_id": None}]
            }
        }

        result = QuizJSONValidator.validate(
            quiz_data,
            CreatorPermissionTier.ADVANCED
        )

        assert len(result["permission_errors"]) == 0


class TestImageURLValidationErrors:
    """Test validation errors for malformed image URLs."""

    def test_invalid_image_url_format(self):
        """Test invalid image URL format is caught."""
        quiz_data = {
            "metadata": {
                "title": "Test Quiz",
                "version": "2.0"
            },
            "variables": {
                "score": {
                    "type": "integer",
                    "mutable_by": ["engine"],
                    "tags": ["score"]
                }
            },
            "questions": [
                {
                    "id": 1,
                    "data": {
                        "text": "Question",
                        "type": "multiple_choice",
                        "image_url": "not a valid url",
                        "options": [
                            {"label": "A", "value": "a"}
                        ]
                    }
                }
            ],
            "transitions": {
                "1": [{"expression": "true", "next_question_id": None}]
            }
        }

        result = QuizJSONValidator.validate(
            quiz_data,
            CreatorPermissionTier.ADMIN
        )

        assert any(
            "invalid image_url" in err for err in result["errors"]
        )

    def test_image_url_must_be_string(self):
        """Test image_url must be a string."""
        quiz_data = {
            "metadata": {
                "title": "Test Quiz",
                "version": "2.0"
            },
            "variables": {
                "score": {
                    "type": "integer",
                    "mutable_by": ["engine"],
                    "tags": ["score"]
                }
            },
            "questions": [
                {
                    "id": 1,
                    "data": {
                        "text": "Question",
                        "type": "multiple_choice",
                        "image_url": 12345,  # Not a string
                        "options": [
                            {"label": "A", "value": "a"}
                        ]
                    }
                }
            ],
            "transitions": {
                "1": [{"expression": "true", "next_question_id": None}]
            }
        }

        result = QuizJSONValidator.validate(
            quiz_data,
            CreatorPermissionTier.ADMIN
        )

        assert any(
            "image_url must be a string" in err for err in result["errors"]
        )

    def test_undefined_variable_in_image_url(self):
        """Test undefined variable reference in image_url is caught."""
        quiz_data = {
            "metadata": {
                "title": "Test Quiz",
                "version": "2.0"
            },
            "variables": {
                "score": {
                    "type": "integer",
                    "mutable_by": ["engine"],
                    "tags": ["score"]
                }
            },
            "questions": [
                {
                    "id": 1,
                    "data": {
                        "text": "Question",
                        "type": "multiple_choice",
                        "image_url": "https://example.com/{variables.undefined_var}.png",
                        "options": [
                            {"label": "A", "value": "a"}
                        ]
                    }
                }
            ],
            "transitions": {
                "1": [{"expression": "true", "next_question_id": None}]
            }
        }

        result = QuizJSONValidator.validate(
            quiz_data,
            CreatorPermissionTier.ADMIN
        )

        assert any(
            "undefined variable" in err for err in result["errors"]
        )

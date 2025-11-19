"""
Tests for image URL pattern restrictions based on permission tiers.

This module tests that:
1. RESTRICTED tier is blocked from using non-whitelisted image URLs
2. RESTRICTED tier can use whitelisted image services
3. Higher tiers (STANDARD, ADVANCED, ADMIN) can bypass restrictions
"""

import pytest
from pyquizhub.core.engine.json_validator import QuizJSONValidator
from pyquizhub.core.engine.variable_types import CreatorPermissionTier


class TestRESTRICTEDTierPatternRestrictions:
    """Test URL pattern restrictions for RESTRICTED tier."""

    def test_restricted_tier_blocked_from_arbitrary_url(self):
        """Test RESTRICTED tier cannot use arbitrary image URLs."""
        quiz_data = {
            "metadata": {
                "title": "Test Quiz",
                "version": "2.0"
            },
            "variables": {
                "score": {
                    "type": "integer",
                    "mutable_by": ["engine"],
                    "tags": ["score"],
                    "default": 0
                }
            },
            "questions": [
                {
                    "id": 1,
                    "data": {
                        "text": "Question",
                        "type": "multiple_choice",
                        "attachments": [
                            {
                                "type": "image",
                                "url": "https://example.com/random/image.png"
                            }
                        ],
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
            creator_tier=CreatorPermissionTier.RESTRICTED
        )

        # Should have permission error
        assert len(result["permission_errors"]) > 0
        assert any("non-whitelisted service" in error for error in result["permission_errors"])
        assert any("RESTRICTED tier only allows approved image hosting services" in error
                   for error in result["permission_errors"])

    def test_restricted_tier_allows_imgur(self):
        """Test RESTRICTED tier can use Imgur URLs."""
        quiz_data = {
            "metadata": {
                "title": "Test Quiz",
                "version": "2.0"
            },
            "variables": {
                "score": {
                    "type": "integer",
                    "mutable_by": ["engine"],
                    "tags": ["score"],
                    "default": 0
                }
            },
            "questions": [
                {
                    "id": 1,
                    "data": {
                        "text": "Question",
                        "type": "multiple_choice",
                        "attachments": [
                            {
                                "type": "image",
                                "url": "https://i.imgur.com/abc123.png"
                            }
                        ],
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
            creator_tier=CreatorPermissionTier.RESTRICTED
        )

        # Should NOT have permission error about whitelisting
        whitelist_errors = [e for e in result["permission_errors"] if "non-whitelisted" in e]
        assert len(whitelist_errors) == 0

    def test_restricted_tier_allows_unsplash(self):
        """Test RESTRICTED tier can use Unsplash URLs."""
        quiz_data = {
            "metadata": {
                "title": "Test Quiz",
                "version": "2.0"
            },
            "variables": {
                "score": {
                    "type": "integer",
                    "mutable_by": ["engine"],
                    "tags": ["score"],
                    "default": 0
                }
            },
            "questions": [
                {
                    "id": 1,
                    "data": {
                        "text": "Question",
                        "type": "multiple_choice",
                        "attachments": [
                            {
                                "type": "image",
                                "url": "https://images.unsplash.com/photo-123?w=800"
                            }
                        ],
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
            creator_tier=CreatorPermissionTier.RESTRICTED
        )

        # Should NOT have permission error about whitelisting
        whitelist_errors = [e for e in result["permission_errors"] if "non-whitelisted" in e]
        assert len(whitelist_errors) == 0

    def test_restricted_tier_allows_cloudinary(self):
        """Test RESTRICTED tier can use Cloudinary URLs."""
        quiz_data = {
            "metadata": {
                "title": "Test Quiz",
                "version": "2.0"
            },
            "variables": {
                "score": {
                    "type": "integer",
                    "mutable_by": ["engine"],
                    "tags": ["score"],
                    "default": 0
                }
            },
            "questions": [
                {
                    "id": 1,
                    "data": {
                        "text": "Question",
                        "type": "multiple_choice",
                        "attachments": [
                            {
                                "type": "image",
                                "url": "https://res.cloudinary.com/demo/image/upload/sample.jpg"
                            }
                        ],
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
            creator_tier=CreatorPermissionTier.RESTRICTED
        )

        # Should NOT have permission error about whitelisting
        whitelist_errors = [e for e in result["permission_errors"] if "non-whitelisted" in e]
        assert len(whitelist_errors) == 0

    def test_restricted_tier_allows_placeholder_services(self):
        """Test RESTRICTED tier can use placeholder image services."""
        placeholder_urls = [
            "https://via.placeholder.com/350x150",
            "https://placehold.co/600x400",
            "https://picsum.photos/200/300",
            "https://dummyimage.com/600x400/000/fff"
        ]

        for url in placeholder_urls:
            quiz_data = {
                "metadata": {
                    "title": "Test Quiz",
                    "version": "2.0"
                },
                "variables": {
                    "score": {
                        "type": "integer",
                        "mutable_by": ["engine"],
                        "tags": ["score"],
                        "default": 0
                    }
                },
                "questions": [
                    {
                        "id": 1,
                        "data": {
                            "text": "Question",
                            "type": "multiple_choice",
                            "attachments": [
                                {
                                    "type": "image",
                                    "url": url
                                }
                            ],
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
                creator_tier=CreatorPermissionTier.RESTRICTED
            )

            # Should NOT have permission error about whitelisting
            whitelist_errors = [e for e in result["permission_errors"] if "non-whitelisted" in e]
            assert len(whitelist_errors) == 0, f"URL {url} should be allowed but got errors: {whitelist_errors}"

    def test_restricted_tier_allows_httpbin(self):
        """Test RESTRICTED tier can use httpbin for testing."""
        quiz_data = {
            "metadata": {
                "title": "Test Quiz",
                "version": "2.0"
            },
            "variables": {
                "score": {
                    "type": "integer",
                    "mutable_by": ["engine"],
                    "tags": ["score"],
                    "default": 0
                }
            },
            "questions": [
                {
                    "id": 1,
                    "data": {
                        "text": "Question",
                        "type": "multiple_choice",
                        "attachments": [
                            {
                                "type": "image",
                                "url": "https://httpbin.org/image/png"
                            }
                        ],
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
            creator_tier=CreatorPermissionTier.RESTRICTED
        )

        # Should NOT have permission error about whitelisting
        whitelist_errors = [e for e in result["permission_errors"] if "non-whitelisted" in e]
        assert len(whitelist_errors) == 0

    def test_restricted_tier_allows_github_and_wikimedia(self):
        """Test RESTRICTED tier can use GitHub and Wikimedia URLs."""
        allowed_urls = [
            "https://raw.githubusercontent.com/user/repo/main/image.png",
            "https://user-images.githubusercontent.com/123456/image.jpg",
            "https://upload.wikimedia.org/wikipedia/commons/a/ab/Example.png"
        ]

        for url in allowed_urls:
            quiz_data = {
                "metadata": {
                    "title": "Test Quiz",
                    "version": "2.0"
                },
                "variables": {
                    "score": {
                        "type": "integer",
                        "mutable_by": ["engine"],
                        "tags": ["score"],
                        "default": 0
                    }
                },
                "questions": [
                    {
                        "id": 1,
                        "data": {
                            "text": "Question",
                            "type": "multiple_choice",
                            "attachments": [
                                {
                                    "type": "image",
                                    "url": url
                                }
                            ],
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
                creator_tier=CreatorPermissionTier.RESTRICTED
            )

            # Should NOT have permission error about whitelisting
            whitelist_errors = [e for e in result["permission_errors"] if "non-whitelisted" in e]
            assert len(whitelist_errors) == 0, f"URL {url} should be allowed but got errors: {whitelist_errors}"


class TestHigherTiersBypassRestrictions:
    """Test that STANDARD, ADVANCED, and ADMIN tiers can bypass URL pattern restrictions."""

    @pytest.mark.parametrize("tier", [
        CreatorPermissionTier.STANDARD,
        CreatorPermissionTier.ADVANCED,
        CreatorPermissionTier.ADMIN
    ])
    def test_higher_tiers_can_use_arbitrary_urls(self, tier):
        """Test STANDARD/ADVANCED/ADMIN tiers can use any HTTPS image URL."""
        quiz_data = {
            "metadata": {
                "title": "Test Quiz",
                "version": "2.0"
            },
            "variables": {
                "score": {
                    "type": "integer",
                    "mutable_by": ["engine"],
                    "tags": ["score"],
                    "default": 0
                }
            },
            "questions": [
                {
                    "id": 1,
                    "data": {
                        "text": "Question",
                        "type": "multiple_choice",
                        "attachments": [
                            {
                                "type": "image",
                                "url": "https://some-random-server.com/path/to/image.png"
                            }
                        ],
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

        result = QuizJSONValidator.validate(quiz_data, creator_tier=tier)

        # Should NOT have permission error about whitelisting
        whitelist_errors = [e for e in result["permission_errors"] if "non-whitelisted" in e]
        assert len(whitelist_errors) == 0, f"Tier {tier.value} should bypass whitelist restrictions"


class TestVariableImageURLsExemptFromPatternCheck:
    """Test that URLs with variable substitution are not checked against patterns."""

    def test_restricted_tier_variable_url_not_checked_for_patterns(self):
        """Test RESTRICTED tier with variable URL gets different permission error, not pattern error."""
        quiz_data = {
            "metadata": {
                "title": "Test Quiz",
                "version": "2.0"
            },
            "variables": {
                "score": {
                    "type": "integer",
                    "mutable_by": ["engine"],
                    "tags": ["score"],
                    "default": 0
                },
                "image_type": {
                    "type": "string",
                    "mutable_by": ["engine"],
                    "tags": ["safe_for_api"],
                    "default": "png"
                }
            },
            "questions": [
                {
                    "id": 1,
                    "data": {
                        "text": "Question",
                        "type": "multiple_choice",
                        "attachments": [
                            {
                                "type": "image",
                                "url": "https://random-site.com/image.{variables.image_type}"
                            }
                        ],
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
            creator_tier=CreatorPermissionTier.RESTRICTED
        )

        # Should have permission error about variable substitution (RESTRICTED can't use variables)
        # but NOT about non-whitelisted service
        assert len(result["permission_errors"]) > 0
        assert any("variable substitution" in error for error in result["permission_errors"])
        assert not any("non-whitelisted" in error for error in result["permission_errors"])

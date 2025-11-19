"""
Tests for image URL variable substitution at runtime.

This module tests that:
1. Engine correctly applies variable substitution to image URLs
2. Fixed image URLs pass through unchanged
3. Variable-based image URLs get properly templated
4. API-based image URLs work correctly
"""

import pytest
import json
from pyquizhub.core.engine.engine import QuizEngine


class TestFixedImageURL:
    """Test fixed image URLs in questions."""

    def test_fixed_image_url_unchanged(self):
        """Test fixed image URL passes through unchanged."""
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
                        "image_url": "https://example.com/test.png",
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

        engine = QuizEngine(quiz_data)
        state = engine.start_quiz()

        question = engine.get_current_question(state)

        assert question["data"]["image_url"] == "https://example.com/test.png"


class TestVariableSubstitutionInImageURL:
    """Test variable substitution in image URLs."""

    def test_variable_substitution_in_image_url(self):
        """Test variables are correctly substituted in image URL."""
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

        engine = QuizEngine(quiz_data)
        state = engine.start_quiz()

        question = engine.get_current_question(state)

        # Variable should be substituted
        assert question["data"]["image_url"] == "https://httpbin.org/image/png"

    def test_multiple_variables_in_image_url(self):
        """Test multiple variables in image URL are substituted."""
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
                "category": {
                    "type": "string",
                    "mutable_by": ["engine"],
                    "tags": ["safe_for_api"],
                    "constraints": {"enum": ["dogs", "cats", "birds"]},
                    "default": "dogs"
                },
                "image_id": {
                    "type": "integer",
                    "mutable_by": ["engine"],
                    "tags": ["safe_for_api"],
                    "default": 42
                }
            },
            "questions": [
                {
                    "id": 1,
                    "data": {
                        "text": "Question",
                        "type": "multiple_choice",
                        "image_url": "https://example.com/{variables.category}/{variables.image_id}.png",
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

        engine = QuizEngine(quiz_data)
        state = engine.start_quiz()

        question = engine.get_current_question(state)

        # Both variables should be substituted
        assert question["data"]["image_url"] == "https://example.com/dogs/42.png"

    def test_variable_changes_reflected_in_image_url(self):
        """Test that variable changes are reflected in image URL."""
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
                "level": {
                    "type": "string",
                    "mutable_by": ["engine"],
                    "tags": ["public", "safe_for_api"],
                    "constraints": {"enum": ["beginner", "intermediate", "advanced"]},
                    "default": "beginner"
                }
            },
            "questions": [
                {
                    "id": 1,
                    "data": {
                        "text": "Question 1",
                        "type": "multiple_choice",
                        "options": [
                            {"label": "Right", "value": "right"},
                            {"label": "Wrong", "value": "wrong"}
                        ]
                    },
                    "score_updates": [
                        {
                            "condition": "answer == 'right'",
                            "update": {
                                "level": "'advanced'"
                            }
                        }
                    ]
                },
                {
                    "id": 2,
                    "data": {
                        "text": "Question 2 - Level: {variables.level}",
                        "type": "multiple_choice",
                        "image_url": "https://example.com/{variables.level}.png",
                        "options": [
                            {"label": "A", "value": "a"}
                        ]
                    }
                }
            ],
            "transitions": {
                "1": [{"expression": "true", "next_question_id": 2}],
                "2": [{"expression": "true", "next_question_id": None}]
            }
        }

        engine = QuizEngine(quiz_data)
        state = engine.start_quiz()

        # Answer the first question correctly to update level
        state = engine.answer_question(state, "right")

        question = engine.get_current_question(state)

        # Level should be updated to 'advanced' in image URL
        assert question["data"]["image_url"] == "https://example.com/advanced.png"
        assert "advanced" in question["data"]["text"]


class TestAPIBasedImageURL:
    """Test API-based image URLs."""

    def test_api_image_url_substitution(self):
        """Test image URL from API response is substituted."""
        from unittest.mock import patch, Mock

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
                "dog_image_url": {
                    "type": "string",
                    "mutable_by": ["api"],
                    "tags": ["api_data", "public"]
                }
            },
            "api_integrations": [
                {
                    "id": "random_dog",
                    "url": "https://dog.ceo/api/breeds/image/random",
                    "method": "GET",
                    "timing": "before_question",
                    "question_id": 1,
                    "extract_response": {
                        "variables": {
                            "dog_image_url": {
                                "path": "message",
                                "type": "string"
                            }
                        }
                    }
                }
            ],
            "questions": [
                {
                    "id": 1,
                    "data": {
                        "text": "Do you like this dog?",
                        "type": "multiple_choice",
                        "image_url": "{variables.dog_image_url}",
                        "options": [
                            {"label": "Yes", "value": "yes"},
                            {"label": "No", "value": "no"}
                        ]
                    }
                }
            ],
            "transitions": {
                "1": [{"expression": "true", "next_question_id": None}]
            }
        }

        # Mock the API response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "message": "https://images.dog.ceo/breeds/hound-afghan/n02088094_1003.jpg",
            "status": "success"
        }

        with patch('requests.request', return_value=mock_response) as mock_request:
            engine = QuizEngine(quiz_data)
            state = engine.start_quiz()

            # Verify API was called
            assert mock_request.called, "API should have been called during start_quiz"

            question = engine.get_current_question(state)

            # Verify the API-fetched image URL is substituted
            assert question["data"]["image_url"] == "https://images.dog.ceo/breeds/hound-afghan/n02088094_1003.jpg", \
                f"Expected dog image URL, got: {question['data'].get('image_url')}, state.scores={state['scores']}"

            # Verify the variable was set from API
            assert state["scores"]["dog_image_url"] == "https://images.dog.ceo/breeds/hound-afghan/n02088094_1003.jpg"


class TestEdgeCases:
    """Test edge cases in image URL templating."""

    def test_missing_image_url_field(self):
        """Test questions without image_url field work normally."""
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
                        "text": "Question without image",
                        "type": "multiple_choice",
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

        engine = QuizEngine(quiz_data)
        state = engine.start_quiz()

        question = engine.get_current_question(state)

        # Should not have image_url field
        assert "image_url" not in question["data"]

    def test_empty_image_url(self):
        """Test empty image_url is handled gracefully."""
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
                        "image_url": "",
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

        engine = QuizEngine(quiz_data)
        state = engine.start_quiz()

        question = engine.get_current_question(state)

        # Empty string should remain empty
        assert question["data"]["image_url"] == ""

import pytest
import json
import uuid
import os

# Load test quiz data


def load_quiz_data(file_path):
    with open(file_path, "r") as f:
        return json.load(f)

# Extract the correct answer from the quiz metadata


def extract_answer(quiz_data):
    description = quiz_data["metadata"]["description"]
    answer_prefix = "Correct answer: "
    if answer_prefix in description:
        answer_str = description.split(answer_prefix)[1].strip()
        try:
            return json.loads(answer_str.replace("'", "\""))
        except json.JSONDecodeError:
            return answer_str
    return None


jsons_dir = os.path.join(os.path.dirname(__file__), "test_quiz_jsons")

# Collect all test quiz files (exclude file_types and input_types quizzes
# - they're for E2E testing)
test_quiz_files = [f for f in os.listdir(jsons_dir) if f.startswith(
    "test_quiz") and "file_types" not in f and "input_types" not in f and "image_info" not in f]


async def test_complex_quiz_flow():
    """Test the flow of the complex quiz with stateless engine."""
    from pyquizhub.core.engine.engine import QuizEngine
    quiz_data = load_quiz_data(os.path.join(os.path.dirname(
        __file__), "test_quiz_jsons", "complex_quiz.json"))
    engine = QuizEngine(quiz_data)

    # Start the quiz (no session_id parameter)
    state = await engine.start_quiz()

    # Check initial question
    current_question = engine.get_current_question(state)
    assert current_question["id"] == 1

    # Check initial scores
    assert state["scores"]["fruits"] == 0
    assert state["scores"]["apples"] == 0
    assert state["scores"]["pears"] == 0

    # Answer the first question (returns new state)
    new_state = await engine.answer_question(state, "yes")
    assert new_state["scores"]["fruits"] == 1
    assert new_state["scores"]["apples"] == 2
    assert new_state["scores"]["pears"] == 0

    # Simulate moving to the next question
    new_state = await engine.answer_question(new_state, "yes")
    assert new_state["completed"] is True
    assert new_state["current_question_id"] is None

    # Verify next question is None
    next_question = engine.get_current_question(new_state)
    assert next_question is None

    # Final check of the results
    expected_scores = {'fruits': 2, 'apples': 2, 'pears': 2}
    assert new_state["scores"] == expected_scores
    assert len(new_state["answers"]) == 2
    assert new_state["answers"][0]["question_id"] == 1
    assert new_state["answers"][0]["answer"] == "yes"
    assert new_state["answers"][1]["question_id"] == 2
    assert new_state["answers"][1]["answer"] == "yes"


async def test_complex_quiz_loop_flow():
    """Test the flow of the complex quiz with loop (stateless engine)."""
    from pyquizhub.core.engine.engine import QuizEngine
    quiz_data = load_quiz_data(os.path.join(os.path.dirname(
        __file__), "test_quiz_jsons", "complex_quiz.json"))
    engine = QuizEngine(quiz_data)

    # Start the quiz (no session_id parameter)
    state = await engine.start_quiz()

    # Check initial question
    current_question = engine.get_current_question(state)
    assert current_question["id"] == 1

    # Check initial scores
    assert state["scores"]["fruits"] == 0
    assert state["scores"]["apples"] == 0
    assert state["scores"]["pears"] == 0

    # Answer the first question with "no"
    state = await engine.answer_question(state, "no")
    assert state["scores"]["fruits"] == 0
    assert state["scores"]["apples"] == -1
    assert state["scores"]["pears"] == 0

    # Answer the first question again with "yes" (looped back)
    state = await engine.answer_question(state, "yes")
    assert state["scores"]["fruits"] == 1
    assert state["scores"]["apples"] == 1
    assert state["scores"]["pears"] == 0

    # Simulate moving to the next question
    state = await engine.answer_question(state, "yes")
    assert state["completed"] is True
    assert state["current_question_id"] is None

    # Verify next question is None
    next_question = engine.get_current_question(state)
    assert next_question is None


def test_invalid_score_updates():
    """Test that invalid score updates raise errors."""
    from pyquizhub.core.engine.engine import QuizEngine
    invalid_quiz_data = load_quiz_data(
        os.path.join(os.path.dirname(
            __file__), "test_quiz_jsons", "invalid_quiz_bad_score_update.json")
    )
    with pytest.raises(ValueError):
        QuizEngine(invalid_quiz_data)


def test_invalid_transitions():
    """Test that invalid transitions raise errors."""
    from pyquizhub.core.engine.engine import QuizEngine
    invalid_quiz_data = load_quiz_data(
        os.path.join(os.path.dirname(
            __file__), "test_quiz_jsons", "invalid_quiz_bad_transition.json")
    )
    with pytest.raises(ValueError):
        QuizEngine(invalid_quiz_data)


@pytest.mark.parametrize("quiz_file", test_quiz_files)
async def test_quiz_types(quiz_file):
    """Test the flow of various quiz types with stateless engine."""
    from pyquizhub.core.engine.engine import QuizEngine
    quiz_data = load_quiz_data(os.path.join(jsons_dir, quiz_file))
    engine = QuizEngine(quiz_data)

    # Extract the correct answer from the quiz metadata
    answer = extract_answer(quiz_data)
    assert answer is not None, f"Correct answer not found in metadata for {quiz_file}"

    # Start the quiz (no session_id parameter)
    state = await engine.start_quiz()

    # Answer the question
    new_state = await engine.answer_question(state, answer)
    assert new_state["scores"]["score_a"] == 1


class TestFileUploadAnswerEnrichment:
    """Tests for file_upload answer enrichment with file metadata."""

    @pytest.fixture
    def mock_file_storage(self):
        """Create a mock file storage that returns metadata."""
        from unittest.mock import AsyncMock, Mock
        from pyquizhub.core.storage.file.backend import FileMetadata

        storage = AsyncMock()
        storage.get_metadata = AsyncMock(return_value=FileMetadata(
            file_id="test-file-123",
            filename="test_image.png",
            category="images",
            size_bytes=12345,
            mime_type="image/png",
            extension="png",
            image_width=800,
            image_height=600,
        ))
        return storage

    @pytest.fixture
    def file_upload_quiz(self):
        """Create a quiz with file_upload question type."""
        return {
            "metadata": {
                "title": "File Upload Test",
                "description": "Test file upload metadata enrichment",
                "version": "1.0"
            },
            "variables": {
                "uploaded_file_id": {
                    "type": "string",
                    "mutable_by": ["engine"],
                    "tags": ["private"],
                    "default": ""
                },
                "file_size": {
                    "type": "integer",
                    "mutable_by": ["engine"],
                    "tags": ["public"],
                    "default": 0
                },
                "file_ext": {
                    "type": "string",
                    "mutable_by": ["engine"],
                    "tags": ["public"],
                    "default": ""
                },
                "img_width": {
                    "type": "integer",
                    "mutable_by": ["engine"],
                    "tags": ["public"],
                    "default": 0
                },
                "img_height": {
                    "type": "integer",
                    "mutable_by": ["engine"],
                    "tags": ["public"],
                    "default": 0
                }
            },
            "questions": [
                {
                    "id": 1,
                    "data": {
                        "type": "file_upload",
                        "text": "Upload an image",
                        "allowed_types": ["images"]
                    },
                    "score_updates": [
                        {
                            "condition": "answer.file_id != ''",
                            "update": {
                                "uploaded_file_id": "answer.file_id",
                                "file_size": "answer.size_bytes",
                                "file_ext": "answer.extension",
                                "img_width": "answer.image_width",
                                "img_height": "answer.image_height"
                            }
                        }
                    ]
                },
                {
                    "id": 2,
                    "data": {
                        "type": "final_message",
                        "text": "File uploaded: {variables.file_size} bytes"
                    }
                }
            ],
            "transitions": {
                "1": [{"expression": "true", "next_question_id": 2}],
                "2": [{"expression": "true", "next_question_id": None}]
            }
        }

    async def test_file_upload_answer_enrichment(
            self, file_upload_quiz, mock_file_storage):
        """Test that file_upload answers are enriched with metadata."""
        from pyquizhub.core.engine.engine import QuizEngine

        engine = QuizEngine(file_upload_quiz, file_storage=mock_file_storage)
        state = await engine.start_quiz()

        # Answer with a file_id
        answer = {"file_id": "test-file-123"}
        new_state = await engine.answer_question(state, answer)

        # Check that metadata was stored in variables
        assert new_state["scores"]["uploaded_file_id"] == "test-file-123"
        assert new_state["scores"]["file_size"] == 12345
        assert new_state["scores"]["file_ext"] == "png"
        assert new_state["scores"]["img_width"] == 800
        assert new_state["scores"]["img_height"] == 600

    async def test_file_upload_without_storage_returns_original_answer(
            self, file_upload_quiz):
        """Test that without file_storage, original answer is used."""
        from pyquizhub.core.engine.engine import QuizEngine

        # No file_storage provided
        engine = QuizEngine(file_upload_quiz, file_storage=None)
        state = await engine.start_quiz()

        # Answer with a file_id - should not fail, just use original answer
        answer = {"file_id": "test-file-123"}
        new_state = await engine.answer_question(state, answer)

        # Only file_id should be stored (no enrichment)
        assert new_state["scores"]["uploaded_file_id"] == "test-file-123"
        # Other fields remain at default because answer.size_bytes etc. don't exist
        assert new_state["scores"]["file_size"] == 0

    async def test_file_upload_with_file_not_found(
            self, file_upload_quiz):
        """Test graceful handling when file not found in storage."""
        from pyquizhub.core.engine.engine import QuizEngine
        from unittest.mock import AsyncMock

        # Create mock storage that raises FileNotFoundError
        mock_storage = AsyncMock()
        mock_storage.get_metadata = AsyncMock(
            side_effect=FileNotFoundError("File not found"))

        engine = QuizEngine(file_upload_quiz, file_storage=mock_storage)
        state = await engine.start_quiz()

        # Answer with a file_id - should not fail
        answer = {"file_id": "nonexistent-file"}
        new_state = await engine.answer_question(state, answer)

        # Original answer should be used
        assert new_state["scores"]["uploaded_file_id"] == "nonexistent-file"

    async def test_enrich_file_upload_answer_includes_all_fields(
            self, mock_file_storage):
        """Test that _enrich_file_upload_answer includes all metadata fields."""
        from pyquizhub.core.engine.engine import QuizEngine

        quiz_data = {
            "metadata": {"title": "Test", "version": "1.0"},
            "variables": {},
            "questions": [],
            "transitions": {}
        }
        engine = QuizEngine(quiz_data, file_storage=mock_file_storage)

        original_answer = {"file_id": "test-file-123"}
        enriched = await engine._enrich_file_upload_answer(original_answer)

        # Check all expected fields are present
        assert enriched["file_id"] == "test-file-123"
        assert enriched["size_bytes"] == 12345
        assert enriched["extension"] == "png"
        assert enriched["filename"] == "test_image.png"
        assert enriched["mime_type"] == "image/png"
        assert enriched["image_width"] == 800
        assert enriched["image_height"] == 600

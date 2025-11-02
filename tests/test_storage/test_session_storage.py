"""
Tests for session state management in storage backends.

This module tests the session persistence functionality for both
FileStorageManager and SQLStorageManager to ensure sessions can be
saved, loaded, updated, and deleted correctly.
"""

import pytest
import os
import tempfile
from datetime import datetime
from pyquizhub.core.storage.file_storage import FileStorageManager
from pyquizhub.core.storage.sql_storage import SQLStorageManager


@pytest.fixture
def file_storage():
    """Fixture for file-based storage manager."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = FileStorageManager(tmpdir)
        yield storage


@pytest.fixture
def sql_storage():
    """Fixture for SQL-based storage manager."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmpfile:
        db_path = tmpfile.name
    storage = SQLStorageManager(f"sqlite:///{db_path}")
    yield storage
    os.unlink(db_path)


def create_sample_session_data(session_id="test-session-123"):
    """Create sample session data for testing."""
    return {
        "session_id": session_id,
        "user_id": "test_user",
        "quiz_id": "test_quiz",
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
        "current_question_id": 1,
        "scores": {"fruits": 5, "apples": 3},
        "answers": [
            {"question_id": 1, "answer": "yes", "timestamp": datetime.now().isoformat()}
        ],
        "completed": False
    }


class TestSessionStorage:
    """Test session storage operations for both storage backends."""

    @pytest.mark.parametrize("storage_fixture", ["file_storage", "sql_storage"])
    def test_save_and_load_session(self, storage_fixture, request):
        """Test saving and loading a session."""
        storage = request.getfixturevalue(storage_fixture)
        
        # Create and save session
        session_data = create_sample_session_data()
        storage.save_session_state(session_data)
        
        # Load session
        loaded_session = storage.load_session_state(session_data["session_id"])
        
        # Verify all fields match
        assert loaded_session is not None
        assert loaded_session["session_id"] == session_data["session_id"]
        assert loaded_session["user_id"] == session_data["user_id"]
        assert loaded_session["quiz_id"] == session_data["quiz_id"]
        assert loaded_session["current_question_id"] == session_data["current_question_id"]
        assert loaded_session["scores"] == session_data["scores"]
        assert len(loaded_session["answers"]) == len(session_data["answers"])
        assert loaded_session["completed"] == session_data["completed"]

    @pytest.mark.parametrize("storage_fixture", ["file_storage", "sql_storage"])
    def test_load_nonexistent_session(self, storage_fixture, request):
        """Test loading a session that doesn't exist returns None."""
        storage = request.getfixturevalue(storage_fixture)
        
        loaded_session = storage.load_session_state("nonexistent-session")
        
        assert loaded_session is None

    @pytest.mark.parametrize("storage_fixture", ["file_storage", "sql_storage"])
    def test_update_session_state(self, storage_fixture, request):
        """Test updating an existing session."""
        storage = request.getfixturevalue(storage_fixture)
        
        # Create and save initial session
        session_data = create_sample_session_data()
        storage.save_session_state(session_data)
        
        # Update session data
        session_data["current_question_id"] = 2
        session_data["scores"]["fruits"] = 10
        session_data["answers"].append({
            "question_id": 2, 
            "answer": "no", 
            "timestamp": datetime.now().isoformat()
        })
        session_data["updated_at"] = datetime.now().isoformat()
        
        storage.update_session_state(session_data["session_id"], session_data)
        
        # Load and verify updates
        loaded_session = storage.load_session_state(session_data["session_id"])
        
        assert loaded_session["current_question_id"] == 2
        assert loaded_session["scores"]["fruits"] == 10
        assert len(loaded_session["answers"]) == 2

    @pytest.mark.parametrize("storage_fixture", ["file_storage", "sql_storage"])
    def test_delete_session_state(self, storage_fixture, request):
        """Test deleting a session."""
        storage = request.getfixturevalue(storage_fixture)
        
        # Create and save session
        session_data = create_sample_session_data()
        storage.save_session_state(session_data)
        
        # Verify session exists
        loaded_session = storage.load_session_state(session_data["session_id"])
        assert loaded_session is not None
        
        # Delete session
        storage.delete_session_state(session_data["session_id"])
        
        # Verify session is gone
        loaded_session = storage.load_session_state(session_data["session_id"])
        assert loaded_session is None

    @pytest.mark.parametrize("storage_fixture", ["file_storage", "sql_storage"])
    def test_multiple_sessions(self, storage_fixture, request):
        """Test handling multiple sessions simultaneously."""
        storage = request.getfixturevalue(storage_fixture)
        
        # Create and save multiple sessions
        session1 = create_sample_session_data("session-1")
        session2 = create_sample_session_data("session-2")
        session3 = create_sample_session_data("session-3")
        
        storage.save_session_state(session1)
        storage.save_session_state(session2)
        storage.save_session_state(session3)
        
        # Verify all sessions can be loaded independently
        loaded1 = storage.load_session_state("session-1")
        loaded2 = storage.load_session_state("session-2")
        loaded3 = storage.load_session_state("session-3")
        
        assert loaded1["session_id"] == "session-1"
        assert loaded2["session_id"] == "session-2"
        assert loaded3["session_id"] == "session-3"
        
        # Delete one session and verify others remain
        storage.delete_session_state("session-2")
        
        assert storage.load_session_state("session-1") is not None
        assert storage.load_session_state("session-2") is None
        assert storage.load_session_state("session-3") is not None

    @pytest.mark.parametrize("storage_fixture", ["file_storage", "sql_storage"])
    def test_session_completion_workflow(self, storage_fixture, request):
        """Test the complete workflow: create, update multiple times, complete, delete."""
        storage = request.getfixturevalue(storage_fixture)
        
        # Start session
        session_data = create_sample_session_data()
        session_data["current_question_id"] = 1
        session_data["completed"] = False
        storage.save_session_state(session_data)
        
        # Answer question 1
        session_data["current_question_id"] = 2
        session_data["scores"]["fruits"] = 5
        session_data["answers"].append({
            "question_id": 2,
            "answer": "yes",
            "timestamp": datetime.now().isoformat()
        })
        storage.update_session_state(session_data["session_id"], session_data)
        
        # Answer question 2
        session_data["current_question_id"] = 3
        session_data["scores"]["fruits"] = 10
        session_data["answers"].append({
            "question_id": 3,
            "answer": "no",
            "timestamp": datetime.now().isoformat()
        })
        storage.update_session_state(session_data["session_id"], session_data)
        
        # Complete quiz
        session_data["current_question_id"] = None
        session_data["completed"] = True
        storage.update_session_state(session_data["session_id"], session_data)
        
        # Verify completed state
        loaded_session = storage.load_session_state(session_data["session_id"])
        assert loaded_session["completed"] is True
        assert loaded_session["current_question_id"] is None
        assert len(loaded_session["answers"]) == 3
        
        # Clean up completed session
        storage.delete_session_state(session_data["session_id"])
        assert storage.load_session_state(session_data["session_id"]) is None

    @pytest.mark.parametrize("storage_fixture", ["file_storage", "sql_storage"])
    def test_session_with_complex_data(self, storage_fixture, request):
        """Test session storage with complex nested data structures."""
        storage = request.getfixturevalue(storage_fixture)
        
        # Create session with complex data
        session_data = create_sample_session_data()
        session_data["scores"] = {
            "category_a": 10,
            "category_b": 20,
            "category_c": 0,
            "nested": {"level1": {"level2": 5}}
        }
        session_data["answers"] = [
            {
                "question_id": 1,
                "answer": ["option1", "option2", "option3"],
                "timestamp": datetime.now().isoformat(),
                "metadata": {"confidence": 0.9}
            },
            {
                "question_id": 2,
                "answer": {"text": "complex answer", "selected": [1, 2, 3]},
                "timestamp": datetime.now().isoformat()
            }
        ]
        
        storage.save_session_state(session_data)
        loaded_session = storage.load_session_state(session_data["session_id"])
        
        # Verify complex structures are preserved
        assert loaded_session["scores"]["nested"]["level1"]["level2"] == 5
        assert len(loaded_session["answers"][0]["answer"]) == 3
        assert loaded_session["answers"][1]["answer"]["text"] == "complex answer"
        assert loaded_session["answers"][0]["metadata"]["confidence"] == 0.9

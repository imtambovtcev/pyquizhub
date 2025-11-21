"""
Tests for file attachment system.

Tests file metadata storage, FileAttachment abstraction, and security.
"""

from __future__ import annotations

import pytest
from datetime import datetime, timedelta, timezone
import tempfile
import shutil
from pathlib import Path

from pyquizhub.core.files.models import FileMetadata, FileAttachment
from pyquizhub.core.files.file_file_storage import FileBasedFileStorage
from pyquizhub.core.files.sql_file_storage import SQLFileStorage


@pytest.fixture
def temp_dir():
    """Create temporary directory for file storage tests."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)


@pytest.fixture
def file_storage(temp_dir):
    """Create file-based storage for testing."""
    return FileBasedFileStorage(temp_dir)


@pytest.fixture(params=["file", "sql"])
def storage_backend(request, temp_dir):
    """Parameterized fixture for both storage backends."""
    if request.param == "file":
        return FileBasedFileStorage(temp_dir)
    else:  # sql
        # Use SQLite for testing
        db_path = Path(temp_dir) / "test.db"
        return SQLFileStorage(f"sqlite:///{db_path}")


class TestFileMetadata:
    """Test FileMetadata model."""

    def test_create_new_metadata(self):
        """Test creating new file metadata."""
        metadata = FileMetadata.create_new(
            file_type="image",
            platform="telegram",
            platform_data={"file_id": "AgACAgIAAxkBAAIC..."},
            user_id="user_123",
            mime_type="image/jpeg",
            size_bytes=245760,
            filename="dog.jpg",
            session_id="session_abc",
            quiz_id="quiz_001"
        )

        assert metadata.file_id is not None
        assert len(metadata.file_id) == 36  # UUID format
        assert metadata.file_type == "image"
        assert metadata.platform == "telegram"
        assert metadata.platform_data == {"file_id": "AgACAgIAAxkBAAIC..."}
        assert metadata.user_id == "user_123"
        assert metadata.created_at is not None

    def test_to_safe_dict_removes_platform_data(self):
        """Test that to_safe_dict never includes platform data."""
        metadata = FileMetadata.create_new(
            file_type="image",
            platform="telegram",
            platform_data={"file_id": "SENSITIVE_DATA", "token": "BOT_TOKEN"},
            user_id="user_123"
        )

        safe_dict = metadata.to_safe_dict()

        assert "platform" not in safe_dict
        assert "platform_data" not in safe_dict
        assert "file_id" in safe_dict
        assert "file_type" in safe_dict
        assert safe_dict["file_id"] == metadata.file_id

    def test_to_dict_includes_platform_data(self):
        """Test that to_dict includes platform data for storage."""
        metadata = FileMetadata.create_new(
            file_type="image",
            platform="telegram",
            platform_data={"file_id": "AgACAgIAAxkBAAIC..."},
            user_id="user_123"
        )

        full_dict = metadata.to_dict()

        assert "platform" in full_dict
        assert "platform_data" in full_dict
        assert full_dict["platform"] == "telegram"
        assert full_dict["platform_data"] == {"file_id": "AgACAgIAAxkBAAIC..."}

    def test_from_dict_roundtrip(self):
        """Test serialization roundtrip."""
        original = FileMetadata.create_new(
            file_type="image",
            platform="discord",
            platform_data={"url": "https://cdn.discord.com/..."},
            user_id="user_456",
            filename="image.png"
        )

        # Serialize and deserialize
        data = original.to_dict()
        restored = FileMetadata.from_dict(data)

        assert restored.file_id == original.file_id
        assert restored.file_type == original.file_type
        assert restored.platform == original.platform
        assert restored.platform_data == original.platform_data
        assert restored.user_id == original.user_id


class TestFileAttachment:
    """Test FileAttachment abstraction."""

    def test_get_reference_uri(self):
        """Test file reference URI generation."""
        metadata = FileMetadata.create_new(
            file_type="image",
            platform="url",
            platform_data={"url": "https://example.com/image.jpg"},
            user_id="user_789"
        )
        attachment = FileAttachment(metadata)

        uri = attachment.get_reference_uri()

        assert uri.startswith("file://")
        assert metadata.file_id in uri

    def test_parse_reference_uri(self):
        """Test parsing file reference URIs."""
        file_id = "f7e3d9a1-4b2c-4e8f-9d6a-123456789abc"
        uri = f"file://{file_id}"

        parsed_id = FileAttachment.parse_reference_uri(uri)

        assert parsed_id == file_id

    def test_parse_invalid_uri(self):
        """Test parsing invalid URIs returns None."""
        assert FileAttachment.parse_reference_uri("not-a-file-uri") is None
        assert FileAttachment.parse_reference_uri("http://example.com") is None
        assert FileAttachment.parse_reference_uri(123) is None

    def test_is_file_reference(self):
        """Test checking if value is a file reference."""
        assert FileAttachment.is_file_reference("file://abc123") is True
        assert FileAttachment.is_file_reference("http://example.com") is False
        assert FileAttachment.is_file_reference(123) is False
        assert FileAttachment.is_file_reference(None) is False

    def test_get_url_for_telegram_adapter(self):
        """Test getting URL for Telegram adapter."""
        metadata = FileMetadata.create_new(
            file_type="image",
            platform="telegram",
            platform_data={"file_id": "AgACAgIAAxkBAAIC..."},
            user_id="user_123"
        )
        attachment = FileAttachment(metadata)

        url = attachment.get_url_for_adapter("telegram")

        # Telegram adapter gets the file_id directly
        assert url == "AgACAgIAAxkBAAIC..."

    def test_get_url_for_web_adapter_with_telegram_file(self):
        """Test getting URL for web adapter with Telegram file."""
        metadata = FileMetadata.create_new(
            file_type="image",
            platform="telegram",
            platform_data={"file_id": "AgACAgIAAxkBAAIC..."},
            user_id="user_123"
        )
        attachment = FileAttachment(metadata)

        url = attachment.get_url_for_adapter("web")

        # Web adapter gets proxy API URL (no bot token exposed)
        assert url.startswith("/api/files/")
        assert "/download" in url
        assert metadata.file_id in url

    def test_get_url_for_public_url_file(self):
        """Test getting URL for public URL file."""
        metadata = FileMetadata.create_new(
            file_type="image",
            platform="url",
            platform_data={"url": "https://i.imgur.com/abc123.png"},
            user_id="user_123"
        )
        attachment = FileAttachment(metadata)

        # Public URL - safe to return to any adapter
        assert attachment.get_url_for_adapter("telegram") == "https://i.imgur.com/abc123.png"
        assert attachment.get_url_for_adapter("discord") == "https://i.imgur.com/abc123.png"
        assert attachment.get_url_for_adapter("web") == "https://i.imgur.com/abc123.png"

    def test_to_safe_dict_never_exposes_platform_data(self):
        """Test that FileAttachment.to_safe_dict never exposes sensitive data."""
        metadata = FileMetadata.create_new(
            file_type="image",
            platform="telegram",
            platform_data={
                "file_id": "SENSITIVE",
                "bot_token": "123456:ABC-DEF..."
            },
            user_id="user_123"
        )
        attachment = FileAttachment(metadata)

        safe_dict = attachment.to_safe_dict()

        assert "platform" not in safe_dict
        assert "platform_data" not in safe_dict
        assert "file_id" in safe_dict


class TestFileStorage:
    """Test file storage backends."""

    def test_store_and_retrieve_metadata(self, storage_backend):
        """Test storing and retrieving file metadata."""
        metadata = FileMetadata.create_new(
            file_type="image",
            platform="telegram",
            platform_data={"file_id": "AgACAgIAAxkBAAIC..."},
            user_id="user_123",
            session_id="session_abc"
        )

        # Store
        file_id = storage_backend.store_file_metadata(metadata)
        assert file_id == metadata.file_id

        # Retrieve
        retrieved = storage_backend.get_file_metadata(file_id)
        assert retrieved is not None
        assert retrieved.file_id == metadata.file_id
        assert retrieved.platform == "telegram"
        assert retrieved.platform_data == {"file_id": "AgACAgIAAxkBAAIC..."}

    def test_get_nonexistent_file(self, storage_backend):
        """Test retrieving non-existent file returns None."""
        result = storage_backend.get_file_metadata("nonexistent-id")
        assert result is None

    def test_update_metadata(self, storage_backend):
        """Test updating file metadata."""
        metadata = FileMetadata.create_new(
            file_type="image",
            platform="url",
            platform_data={"url": "https://example.com/image.jpg"},
            user_id="user_123"
        )

        file_id = storage_backend.store_file_metadata(metadata)

        # Update
        updated = storage_backend.update_file_metadata(
            file_id,
            {"description": "Updated description"}
        )
        assert updated is True

        # Verify update
        retrieved = storage_backend.get_file_metadata(file_id)
        assert retrieved.description == "Updated description"

    def test_delete_metadata(self, storage_backend):
        """Test deleting file metadata."""
        metadata = FileMetadata.create_new(
            file_type="image",
            platform="url",
            platform_data={"url": "https://example.com/image.jpg"},
            user_id="user_123"
        )

        file_id = storage_backend.store_file_metadata(metadata)

        # Delete
        deleted = storage_backend.delete_file_metadata(file_id)
        assert deleted is True

        # Verify deletion
        retrieved = storage_backend.get_file_metadata(file_id)
        assert retrieved is None

    def test_get_files_for_session(self, storage_backend):
        """Test getting all files for a session."""
        session_id = "session_xyz"

        # Create multiple files for the session
        for i in range(3):
            metadata = FileMetadata.create_new(
                file_type="image",
                platform="url",
                platform_data={"url": f"https://example.com/image{i}.jpg"},
                user_id=f"user_{i}",
                session_id=session_id
            )
            storage_backend.store_file_metadata(metadata)

        # Get files for session
        files = storage_backend.get_files_for_session(session_id)

        assert len(files) == 3
        assert all(f.session_id == session_id for f in files)

    def test_get_files_for_user(self, storage_backend):
        """Test getting all files for a user."""
        user_id = "user_special"

        # Create files for user across different sessions
        for i in range(2):
            metadata = FileMetadata.create_new(
                file_type="image",
                platform="url",
                platform_data={"url": f"https://example.com/image{i}.jpg"},
                user_id=user_id,
                session_id=f"session_{i}"
            )
            storage_backend.store_file_metadata(metadata)

        # Get files for user
        files = storage_backend.get_files_for_user(user_id)

        assert len(files) == 2
        assert all(f.user_id == user_id for f in files)

    def test_cleanup_expired_files(self, storage_backend):
        """Test cleaning up expired files."""
        # Create expired file
        expired_metadata = FileMetadata.create_new(
            file_type="image",
            platform="url",
            platform_data={"url": "https://example.com/expired.jpg"},
            user_id="user_123",
            expires_at=datetime.now(timezone.utc) - timedelta(days=1)  # Expired yesterday
        )
        storage_backend.store_file_metadata(expired_metadata)

        # Create non-expired file
        active_metadata = FileMetadata.create_new(
            file_type="image",
            platform="url",
            platform_data={"url": "https://example.com/active.jpg"},
            user_id="user_123",
            expires_at=datetime.now(timezone.utc) + timedelta(days=1)  # Expires tomorrow
        )
        storage_backend.store_file_metadata(active_metadata)

        # Cleanup
        deleted_count = storage_backend.cleanup_expired_files()

        assert deleted_count == 1

        # Verify expired file is gone
        assert storage_backend.get_file_metadata(expired_metadata.file_id) is None

        # Verify active file still exists
        assert storage_backend.get_file_metadata(active_metadata.file_id) is not None

    def test_get_storage_stats(self, storage_backend):
        """Test getting storage statistics."""
        # Create some files
        for i in range(3):
            metadata = FileMetadata.create_new(
                file_type="image",
                platform="url",
                platform_data={"url": f"https://example.com/image{i}.jpg"},
                user_id="user_123",
                size_bytes=1024 * (i + 1)  # 1KB, 2KB, 3KB
            )
            storage_backend.store_file_metadata(metadata)

        # Get stats
        stats = storage_backend.get_storage_stats()

        assert stats['file_count'] == 3
        assert stats['total_bytes'] == 1024 + 2048 + 3072  # 6KB total

    def test_get_storage_stats_for_user(self, storage_backend):
        """Test getting storage statistics for specific user."""
        user_id = "user_stats_test"

        # Create files for specific user
        for i in range(2):
            metadata = FileMetadata.create_new(
                file_type="image",
                platform="url",
                platform_data={"url": f"https://example.com/image{i}.jpg"},
                user_id=user_id,
                size_bytes=1024
            )
            storage_backend.store_file_metadata(metadata)

        # Create files for other user
        metadata = FileMetadata.create_new(
            file_type="image",
            platform="url",
            platform_data={"url": "https://example.com/other.jpg"},
            user_id="other_user",
            size_bytes=1024
        )
        storage_backend.store_file_metadata(metadata)

        # Get stats for specific user
        stats = storage_backend.get_storage_stats(user_id)

        assert stats['file_count'] == 2
        assert stats['total_bytes'] == 2048  # 2KB

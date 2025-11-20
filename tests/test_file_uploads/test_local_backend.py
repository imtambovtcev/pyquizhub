"""Tests for LocalStorageBackend."""

from __future__ import annotations

import io
import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock

from pyquizhub.core.storage.file.local_backend import LocalStorageBackend
from pyquizhub.core.storage.file.backend import FileMetadata


@pytest.fixture
def temp_storage_dir():
    """Create temporary storage directory."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    # Cleanup
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def mock_config():
    """Create mock configuration."""
    config = Mock()
    config.file_storage.allowed_types.archives.max_decompressed_size_mb = 500
    return config


@pytest.fixture
async def storage_backend(temp_storage_dir, mock_config):
    """Create LocalStorageBackend instance."""
    backend = LocalStorageBackend(temp_storage_dir, mock_config)
    await backend._ensure_db()
    return backend


@pytest.mark.asyncio
async def test_save_and_retrieve_file(storage_backend, temp_storage_dir):
    """Test saving and retrieving a file."""
    # Create test file
    file_content = b"test file content"
    file_data = io.BytesIO(file_content)

    # Create metadata
    metadata = FileMetadata(
        file_id="test-uuid-123",
        filename="test.txt",
        category="documents",
        size_bytes=len(file_content),
        mime_type="text/plain",
        extension="txt",
        uploader_id="user1",
        quiz_id=None,
    )

    # Save file
    file_id = await storage_backend.save(file_data, metadata)
    assert file_id == "test-uuid-123"

    # Verify file exists on disk
    files_dir = Path(temp_storage_dir) / "files"
    assert files_dir.exists()

    # Retrieve file
    retrieved_data, retrieved_metadata = await storage_backend.retrieve(file_id)

    # Verify content
    assert retrieved_data.read() == file_content

    # Verify metadata
    assert retrieved_metadata.file_id == metadata.file_id
    assert retrieved_metadata.filename == metadata.filename
    assert retrieved_metadata.category == metadata.category
    assert retrieved_metadata.size_bytes == metadata.size_bytes


@pytest.mark.asyncio
async def test_file_exists(storage_backend):
    """Test checking if file exists."""
    # File doesn't exist
    exists = await storage_backend.exists("nonexistent-id")
    assert not exists

    # Create file
    file_data = io.BytesIO(b"test")
    metadata = FileMetadata(
        file_id="exists-test",
        filename="test.txt",
        category="documents",
        size_bytes=4,
        extension="txt",
    )
    await storage_backend.save(file_data, metadata)

    # File now exists
    exists = await storage_backend.exists("exists-test")
    assert exists


@pytest.mark.asyncio
async def test_delete_file(storage_backend):
    """Test deleting a file."""
    # Create file
    file_data = io.BytesIO(b"test content to delete")
    metadata = FileMetadata(
        file_id="delete-test",
        filename="delete.txt",
        category="documents",
        size_bytes=22,
        extension="txt",
    )
    await storage_backend.save(file_data, metadata)

    # Verify file exists
    assert await storage_backend.exists("delete-test")

    # Delete file
    success = await storage_backend.delete("delete-test")
    assert success

    # Verify file no longer exists
    assert not await storage_backend.exists("delete-test")

    # Deleting again should return False
    success = await storage_backend.delete("delete-test")
    assert not success


@pytest.mark.asyncio
async def test_get_metadata(storage_backend):
    """Test getting file metadata without retrieving content."""
    # Create file
    file_data = io.BytesIO(b"metadata test")
    metadata = FileMetadata(
        file_id="metadata-test",
        filename="meta.txt",
        category="documents",
        size_bytes=13,
        mime_type="text/plain",
        checksum="sha256:abc123",
        uploader_id="user2",
        quiz_id="quiz1",
        extension="txt",
    )
    await storage_backend.save(file_data, metadata)

    # Get metadata
    retrieved_meta = await storage_backend.get_metadata("metadata-test")

    assert retrieved_meta.file_id == "metadata-test"
    assert retrieved_meta.filename == "meta.txt"
    assert retrieved_meta.category == "documents"
    assert retrieved_meta.size_bytes == 13
    assert retrieved_meta.mime_type == "text/plain"
    assert retrieved_meta.checksum == "sha256:abc123"
    assert retrieved_meta.uploader_id == "user2"
    assert retrieved_meta.quiz_id == "quiz1"


@pytest.mark.asyncio
async def test_get_download_url(storage_backend):
    """Test getting download URL."""
    # Create file
    file_data = io.BytesIO(b"download url test")
    metadata = FileMetadata(
        file_id="download-url-test",
        filename="download.txt",
        category="documents",
        size_bytes=17,
        extension="txt",
    )
    await storage_backend.save(file_data, metadata)

    # Get download URL
    url = await storage_backend.get_download_url("download-url-test")

    assert url == "/api/files/download/download-url-test"


@pytest.mark.asyncio
async def test_get_quota_usage(storage_backend):
    """Test quota usage calculation."""
    # Initially empty
    usage = await storage_backend.get_quota_usage()
    assert usage == 0

    # Add files
    file1_data = io.BytesIO(b"x" * 1024)  # 1 KB
    metadata1 = FileMetadata(
        file_id="quota1",
        filename="file1.txt",
        category="documents",
        size_bytes=1024,
        uploader_id="user1",
        extension="txt",
    )
    await storage_backend.save(file1_data, metadata1)

    file2_data = io.BytesIO(b"y" * 2048)  # 2 KB
    metadata2 = FileMetadata(
        file_id="quota2",
        filename="file2.txt",
        category="documents",
        size_bytes=2048,
        uploader_id="user2",
        extension="txt",
    )
    await storage_backend.save(file2_data, metadata2)

    # Total usage
    usage = await storage_backend.get_quota_usage()
    assert usage == 1024 + 2048

    # Usage by user
    usage_user1 = await storage_backend.get_quota_usage(user_id="user1")
    assert usage_user1 == 1024

    usage_user2 = await storage_backend.get_quota_usage(user_id="user2")
    assert usage_user2 == 2048


@pytest.mark.asyncio
async def test_list_files(storage_backend):
    """Test listing files with filters."""
    # Create multiple files
    for i in range(3):
        file_data = io.BytesIO(f"file {i}".encode())
        metadata = FileMetadata(
            file_id=f"list-test-{i}",
            filename=f"file{i}.txt",
            category="documents",
            size_bytes=len(f"file {i}"),
            uploader_id="user1" if i < 2 else "user2",
            quiz_id="quiz1" if i == 0 else None,
            extension="txt",
        )
        await storage_backend.save(file_data, metadata)

    # List all files
    all_files = await storage_backend.list_files()
    assert len(all_files) >= 3

    # List by user
    user1_files = await storage_backend.list_files(user_id="user1")
    assert len(user1_files) == 2

    user2_files = await storage_backend.list_files(user_id="user2")
    assert len(user2_files) == 1

    # List by quiz
    quiz_files = await storage_backend.list_files(quiz_id="quiz1")
    assert len(quiz_files) == 1
    assert quiz_files[0].file_id == "list-test-0"

    # List by category
    doc_files = await storage_backend.list_files(category="documents")
    assert len(doc_files) >= 3


@pytest.mark.asyncio
async def test_file_permissions(storage_backend, temp_storage_dir):
    """Test that saved files have correct permissions (read-only)."""
    # Create file
    file_data = io.BytesIO(b"permission test")
    metadata = FileMetadata(
        file_id="perm-test",
        filename="perm.txt",
        category="documents",
        size_bytes=15,
        extension="txt",
    )
    await storage_backend.save(file_data, metadata)

    # Get storage path
    retrieved_meta = await storage_backend.get_metadata("perm-test")

    # Find the file on disk (check it exists and has read-only permissions)
    files_dir = Path(temp_storage_dir) / "files"
    saved_files = list(files_dir.rglob("perm-test.txt"))

    assert len(saved_files) > 0
    file_path = saved_files[0]

    # Check permissions (should be 0o444 - read-only)
    import stat
    mode = file_path.stat().st_mode
    # Check that write bit is not set for owner
    assert not bool(mode & stat.S_IWUSR)


@pytest.mark.asyncio
async def test_retrieve_nonexistent_file(storage_backend):
    """Test retrieving a file that doesn't exist."""
    with pytest.raises(FileNotFoundError):
        await storage_backend.retrieve("nonexistent-file-id")


@pytest.mark.asyncio
async def test_get_metadata_nonexistent(storage_backend):
    """Test getting metadata for nonexistent file."""
    with pytest.raises(FileNotFoundError):
        await storage_backend.get_metadata("nonexistent-file-id")

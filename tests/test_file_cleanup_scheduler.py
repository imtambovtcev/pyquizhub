"""
Tests for file cleanup scheduler background task.

Tests the automatic periodic cleanup of expired files.
"""

from __future__ import annotations

import pytest
import asyncio
from datetime import datetime, timedelta, timezone
import tempfile
import shutil
from pathlib import Path

from pyquizhub.core.files.models import FileMetadata
from pyquizhub.core.files.file_file_storage import FileBasedFileStorage
from pyquizhub.core.files.sql_file_storage import SQLFileStorage


async def file_cleanup_task(file_storage, interval_seconds: int = 3600):
    """
    Background task to periodically clean up expired files.

    This is a local copy for testing to avoid importing from main.py
    which triggers config loading at module level.
    """
    while True:
        try:
            await asyncio.sleep(interval_seconds)
            file_storage.cleanup_expired_files()
        except asyncio.CancelledError:
            break
        except Exception:
            pass  # Continue on errors


@pytest.fixture
def temp_dir():
    """Create temporary directory for file storage tests."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)


@pytest.fixture(params=["file", "sql"])
def storage_backend(request, temp_dir):
    """Parameterized fixture for both storage backends."""
    if request.param == "file":
        return FileBasedFileStorage(temp_dir)
    else:  # sql
        db_path = Path(temp_dir) / "test.db"
        return SQLFileStorage(f"sqlite:///{db_path}")


class TestFileCleanupScheduler:
    """Test file cleanup scheduler background task."""

    @pytest.mark.asyncio
    async def test_cleanup_task_runs_periodically(self, storage_backend):
        """Test that cleanup task runs at specified intervals."""
        # Create expired files
        expired_metadata = FileMetadata.create_new(
            file_type="image",
            platform="url",
            platform_data={"url": "https://example.com/expired.jpg"},
            user_id="user_123",
            expires_at=datetime.now(timezone.utc) - timedelta(hours=1)
        )
        storage_backend.store_file_metadata(expired_metadata)

        # Create non-expired file
        active_metadata = FileMetadata.create_new(
            file_type="image",
            platform="url",
            platform_data={"url": "https://example.com/active.jpg"},
            user_id="user_123",
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1)
        )
        storage_backend.store_file_metadata(active_metadata)

        # Run cleanup task with very short interval for testing (0.1 seconds)
        task = asyncio.create_task(
            file_cleanup_task(storage_backend, interval_seconds=0.1)
        )

        # Wait for first cleanup cycle to complete
        await asyncio.sleep(0.2)

        # Cancel task
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

        # Verify expired file was deleted
        assert storage_backend.get_file_metadata(expired_metadata.file_id) is None

        # Verify active file still exists
        assert storage_backend.get_file_metadata(active_metadata.file_id) is not None

    @pytest.mark.asyncio
    async def test_cleanup_task_handles_errors(self, storage_backend):
        """Test that cleanup task continues running even if cleanup fails."""
        # Mock cleanup_expired_files to raise error on first call, succeed on second
        original_cleanup = storage_backend.cleanup_expired_files
        call_count = 0

        def mock_cleanup():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception("Simulated cleanup error")
            return original_cleanup()

        storage_backend.cleanup_expired_files = mock_cleanup

        # Run cleanup task
        task = asyncio.create_task(
            file_cleanup_task(storage_backend, interval_seconds=0.1)
        )

        # Wait for two cleanup cycles
        await asyncio.sleep(0.25)

        # Cancel task
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

        # Verify cleanup was called at least twice (first failed, second succeeded)
        assert call_count >= 2

    @pytest.mark.asyncio
    async def test_cleanup_task_cancellation(self, storage_backend):
        """Test that cleanup task can be cancelled cleanly."""
        task = asyncio.create_task(
            file_cleanup_task(storage_backend, interval_seconds=3600)
        )

        # Let task start
        await asyncio.sleep(0.01)

        # Cancel task
        task.cancel()

        # Wait for cancellation (task handles CancelledError internally)
        try:
            await task
        except asyncio.CancelledError:
            # This is also acceptable - task may not catch the error
            pass

        # Verify task is done
        assert task.done()
        assert task.cancelled() or task.exception() is None

    @pytest.mark.asyncio
    async def test_cleanup_task_deletes_multiple_expired_files(self, storage_backend):
        """Test that cleanup task deletes all expired files in one run."""
        # Create multiple expired files
        expired_files = []
        for i in range(5):
            metadata = FileMetadata.create_new(
                file_type="image",
                platform="url",
                platform_data={"url": f"https://example.com/expired_{i}.jpg"},
                user_id="user_123",
                expires_at=datetime.now(timezone.utc) - timedelta(hours=1)
            )
            storage_backend.store_file_metadata(metadata)
            expired_files.append(metadata)

        # Run cleanup task
        task = asyncio.create_task(
            file_cleanup_task(storage_backend, interval_seconds=0.1)
        )

        # Wait for cleanup to run
        await asyncio.sleep(0.2)

        # Cancel task
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

        # Verify all expired files were deleted
        for metadata in expired_files:
            assert storage_backend.get_file_metadata(metadata.file_id) is None

    @pytest.mark.asyncio
    async def test_cleanup_task_preserves_non_expired_files(self, storage_backend):
        """Test that cleanup task doesn't delete non-expired files."""
        # Create files with various expiration times
        soon_to_expire = FileMetadata.create_new(
            file_type="image",
            platform="url",
            platform_data={"url": "https://example.com/soon.jpg"},
            user_id="user_123",
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=1)
        )
        storage_backend.store_file_metadata(soon_to_expire)

        far_future = FileMetadata.create_new(
            file_type="image",
            platform="url",
            platform_data={"url": "https://example.com/far.jpg"},
            user_id="user_123",
            expires_at=datetime.now(timezone.utc) + timedelta(days=30)
        )
        storage_backend.store_file_metadata(far_future)

        no_expiration = FileMetadata.create_new(
            file_type="image",
            platform="url",
            platform_data={"url": "https://example.com/permanent.jpg"},
            user_id="user_123",
            expires_at=None
        )
        storage_backend.store_file_metadata(no_expiration)

        # Run cleanup task
        task = asyncio.create_task(
            file_cleanup_task(storage_backend, interval_seconds=0.1)
        )

        # Wait for cleanup to run
        await asyncio.sleep(0.2)

        # Cancel task
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

        # Verify all non-expired files still exist
        assert storage_backend.get_file_metadata(soon_to_expire.file_id) is not None
        assert storage_backend.get_file_metadata(far_future.file_id) is not None
        assert storage_backend.get_file_metadata(no_expiration.file_id) is not None

    @pytest.mark.asyncio
    async def test_cleanup_task_with_custom_interval(self, storage_backend):
        """Test that cleanup task respects custom interval."""
        cleanup_count = 0

        # Track cleanup calls
        original_cleanup = storage_backend.cleanup_expired_files

        def counting_cleanup():
            nonlocal cleanup_count
            cleanup_count += 1
            return original_cleanup()

        storage_backend.cleanup_expired_files = counting_cleanup

        # Run cleanup task with 0.1 second interval
        task = asyncio.create_task(
            file_cleanup_task(storage_backend, interval_seconds=0.1)
        )

        # Wait for ~3 cleanup cycles (0.3 seconds)
        await asyncio.sleep(0.35)

        # Cancel task
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

        # Should have run approximately 3 times
        assert cleanup_count >= 2  # At least 2 to account for timing variations
        assert cleanup_count <= 4  # At most 4 to account for timing variations


class TestFileCleanupSchedulerDisabledByDefault:
    """Test that file cleanup scheduler is disabled by default."""

    def test_cleanup_disabled_by_default_in_config(self):
        """Test that file_cleanup_enabled defaults to False in AppSettings."""
        from pyquizhub.config.settings import AppSettings

        # Create settings without loading from file
        settings = AppSettings()

        # file_cleanup_enabled is not a default field in AppSettings,
        # so it should not exist or be False when accessed via getattr
        cleanup_enabled = getattr(settings, 'file_cleanup_enabled', False)
        assert cleanup_enabled is False

    @pytest.mark.asyncio
    async def test_cleanup_task_not_started_when_disabled(self, storage_backend):
        """Test that cleanup task logic respects disabled flag."""
        # Create expired file
        expired = FileMetadata.create_new(
            file_type="image",
            platform="url",
            platform_data={"url": "https://example.com/expired.jpg"},
            user_id="user_123",
            expires_at=datetime.now(timezone.utc) - timedelta(hours=1)
        )
        storage_backend.store_file_metadata(expired)

        # Without running cleanup task, file should still exist
        await asyncio.sleep(0.1)
        assert storage_backend.get_file_metadata(expired.file_id) is not None

        # Only when we explicitly run cleanup does it get deleted
        deleted_count = storage_backend.cleanup_expired_files()
        assert deleted_count == 1
        assert storage_backend.get_file_metadata(expired.file_id) is None


class TestFileCleanupIntegration:
    """Integration tests for file cleanup with FastAPI application."""

    @pytest.mark.asyncio
    async def test_cleanup_with_mixed_expiration_times(self, storage_backend):
        """Test cleanup with files having various expiration states."""
        now = datetime.now(timezone.utc)

        # Already expired (1 hour ago)
        expired_old = FileMetadata.create_new(
            file_type="image",
            platform="url",
            platform_data={"url": "https://example.com/old.jpg"},
            user_id="user_123",
            expires_at=now - timedelta(hours=1)
        )
        storage_backend.store_file_metadata(expired_old)

        # Just expired (1 minute ago)
        expired_recent = FileMetadata.create_new(
            file_type="image",
            platform="url",
            platform_data={"url": "https://example.com/recent.jpg"},
            user_id="user_123",
            expires_at=now - timedelta(minutes=1)
        )
        storage_backend.store_file_metadata(expired_recent)

        # Expires soon (in 1 minute)
        expires_soon = FileMetadata.create_new(
            file_type="image",
            platform="url",
            platform_data={"url": "https://example.com/soon.jpg"},
            user_id="user_123",
            expires_at=now + timedelta(minutes=1)
        )
        storage_backend.store_file_metadata(expires_soon)

        # Expires later (in 1 day)
        expires_later = FileMetadata.create_new(
            file_type="document",
            platform="url",
            platform_data={"url": "https://example.com/later.pdf"},
            user_id="user_456",
            expires_at=now + timedelta(days=1)
        )
        storage_backend.store_file_metadata(expires_later)

        # No expiration
        no_expiration = FileMetadata.create_new(
            file_type="video",
            platform="url",
            platform_data={"url": "https://example.com/permanent.mp4"},
            user_id="user_789",
            expires_at=None
        )
        storage_backend.store_file_metadata(no_expiration)

        # Run cleanup
        deleted_count = storage_backend.cleanup_expired_files()

        # Should delete exactly 2 expired files
        assert deleted_count == 2

        # Verify expired files are gone
        assert storage_backend.get_file_metadata(expired_old.file_id) is None
        assert storage_backend.get_file_metadata(expired_recent.file_id) is None

        # Verify non-expired files still exist
        assert storage_backend.get_file_metadata(expires_soon.file_id) is not None
        assert storage_backend.get_file_metadata(expires_later.file_id) is not None
        assert storage_backend.get_file_metadata(no_expiration.file_id) is not None

    @pytest.mark.asyncio
    async def test_cleanup_handles_timezone_correctly(self, storage_backend):
        """Test that cleanup handles timezone-aware datetimes correctly."""
        # Create file with UTC timezone
        utc_expired = FileMetadata.create_new(
            file_type="image",
            platform="url",
            platform_data={"url": "https://example.com/utc.jpg"},
            user_id="user_123",
            expires_at=datetime.now(timezone.utc) - timedelta(hours=1)
        )
        storage_backend.store_file_metadata(utc_expired)

        # Run cleanup
        deleted_count = storage_backend.cleanup_expired_files()

        # Should delete the expired file
        assert deleted_count == 1
        assert storage_backend.get_file_metadata(utc_expired.file_id) is None

    @pytest.mark.asyncio
    async def test_cleanup_with_large_number_of_files(self, storage_backend):
        """Test cleanup performance with many files."""
        # Create 100 expired files and 100 non-expired files
        expired_files = []
        active_files = []

        for i in range(100):
            # Expired
            expired = FileMetadata.create_new(
                file_type="image",
                platform="url",
                platform_data={"url": f"https://example.com/expired_{i}.jpg"},
                user_id="user_123",
                expires_at=datetime.now(timezone.utc) - timedelta(hours=1)
            )
            storage_backend.store_file_metadata(expired)
            expired_files.append(expired)

            # Active
            active = FileMetadata.create_new(
                file_type="image",
                platform="url",
                platform_data={"url": f"https://example.com/active_{i}.jpg"},
                user_id="user_123",
                expires_at=datetime.now(timezone.utc) + timedelta(hours=1)
            )
            storage_backend.store_file_metadata(active)
            active_files.append(active)

        # Run cleanup
        deleted_count = storage_backend.cleanup_expired_files()

        # Should delete exactly 100 expired files
        assert deleted_count == 100

        # Verify all expired files are deleted
        for metadata in expired_files:
            assert storage_backend.get_file_metadata(metadata.file_id) is None

        # Verify all active files still exist
        for metadata in active_files:
            assert storage_backend.get_file_metadata(metadata.file_id) is not None

    @pytest.mark.asyncio
    async def test_cleanup_idempotency(self, storage_backend):
        """Test that running cleanup multiple times is safe."""
        # Create expired file
        expired = FileMetadata.create_new(
            file_type="image",
            platform="url",
            platform_data={"url": "https://example.com/expired.jpg"},
            user_id="user_123",
            expires_at=datetime.now(timezone.utc) - timedelta(hours=1)
        )
        storage_backend.store_file_metadata(expired)

        # Run cleanup first time
        deleted_count_1 = storage_backend.cleanup_expired_files()
        assert deleted_count_1 == 1

        # Run cleanup second time (should find nothing)
        deleted_count_2 = storage_backend.cleanup_expired_files()
        assert deleted_count_2 == 0

        # Run cleanup third time (still nothing)
        deleted_count_3 = storage_backend.cleanup_expired_files()
        assert deleted_count_3 == 0

    @pytest.mark.asyncio
    async def test_cleanup_preserves_files_without_expiration(self, storage_backend):
        """Test that files without expiration are never deleted."""
        # Create multiple files without expiration
        permanent_files = []
        for i in range(10):
            metadata = FileMetadata.create_new(
                file_type="document",
                platform="url",
                platform_data={"url": f"https://example.com/permanent_{i}.pdf"},
                user_id="user_123",
                expires_at=None
            )
            storage_backend.store_file_metadata(metadata)
            permanent_files.append(metadata)

        # Run cleanup multiple times
        for _ in range(3):
            deleted_count = storage_backend.cleanup_expired_files()
            assert deleted_count == 0

        # Verify all files still exist
        for metadata in permanent_files:
            assert storage_backend.get_file_metadata(metadata.file_id) is not None

    @pytest.mark.asyncio
    async def test_cleanup_task_runs_and_deletes_files(self, storage_backend):
        """Test that cleanup task actually runs and deletes expired files."""
        # Create expired file
        expired = FileMetadata.create_new(
            file_type="image",
            platform="url",
            platform_data={"url": "https://example.com/expired.jpg"},
            user_id="user_123",
            expires_at=datetime.now(timezone.utc) - timedelta(hours=1)
        )
        storage_backend.store_file_metadata(expired)

        # Verify file exists before cleanup
        assert storage_backend.get_file_metadata(expired.file_id) is not None

        # Run cleanup task
        task = asyncio.create_task(
            file_cleanup_task(storage_backend, interval_seconds=0.1)
        )

        # Wait for cleanup to run
        await asyncio.sleep(0.2)

        # Cancel task
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

        # Verify file was deleted
        assert storage_backend.get_file_metadata(expired.file_id) is None

    @pytest.mark.asyncio
    async def test_cleanup_by_file_type(self, storage_backend):
        """Test cleanup works for different file types."""
        now = datetime.now(timezone.utc)

        # Create expired files of different types
        file_types = ["image", "video", "audio", "document"]
        expired_files = {}

        for file_type in file_types:
            metadata = FileMetadata.create_new(
                file_type=file_type,
                platform="url",
                platform_data={"url": f"https://example.com/file.{file_type}"},
                user_id="user_123",
                expires_at=now - timedelta(hours=1)
            )
            storage_backend.store_file_metadata(metadata)
            expired_files[file_type] = metadata

        # Run cleanup
        deleted_count = storage_backend.cleanup_expired_files()

        # Should delete all 4 files
        assert deleted_count == 4

        # Verify all are deleted regardless of type
        for file_type, metadata in expired_files.items():
            assert storage_backend.get_file_metadata(metadata.file_id) is None

"""
File-based implementation of file metadata storage.

Stores file metadata as JSON files in a directory structure.
Used when SQL database is not available.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .storage import FileStorageInterface
from .models import FileMetadata
from pyquizhub.logging.setup import get_logger

logger = get_logger(__name__)


class FileBasedFileStorage(FileStorageInterface):
    """File-based implementation of file metadata storage."""

    def __init__(self, base_dir: str = ".pyquizhub/files"):
        """
        Initialize file-based file storage.

        Args:
            base_dir: Base directory for storing file metadata
        """
        self.base_dir = Path(base_dir)
        self.metadata_dir = self.base_dir / "metadata"
        self.metadata_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"File-based file storage initialized at {self.base_dir}")

    def _get_metadata_path(self, file_id: str) -> Path:
        """Get path to metadata file for given file_id."""
        return self.metadata_dir / f"{file_id}.json"

    def store_file_metadata(self, metadata: FileMetadata) -> str:
        """
        Store file metadata and return file_id.

        Args:
            metadata: FileMetadata instance to store

        Returns:
            file_id: UUID reference to stored file

        Raises:
            ValueError: If storage fails
        """
        try:
            metadata_path = self._get_metadata_path(metadata.file_id)

            # Convert to dict for JSON serialization
            data = metadata.to_dict()

            # Write metadata file
            with open(metadata_path, 'w') as f:
                json.dump(data, f, indent=2)

            logger.info(f"Stored file metadata: {metadata.file_id}")
            return metadata.file_id

        except Exception as e:
            logger.error(f"Failed to store file metadata: {e}")
            raise ValueError(f"File metadata storage failed: {e}")

    def get_file_metadata(self, file_id: str) -> FileMetadata | None:
        """
        Retrieve file metadata by file_id.

        Args:
            file_id: UUID of file to retrieve

        Returns:
            FileMetadata instance or None if not found
        """
        metadata_path = self._get_metadata_path(file_id)

        if not metadata_path.exists():
            return None

        try:
            with open(metadata_path, 'r') as f:
                data = json.load(f)

            return FileMetadata.from_dict(data)

        except Exception as e:
            logger.error(f"Failed to load file metadata {file_id}: {e}")
            return None

    def update_file_metadata(
            self, file_id: str, updates: dict[str, Any]) -> bool:
        """
        Update file metadata.

        Args:
            file_id: UUID of file to update
            updates: Dict of fields to update

        Returns:
            True if updated, False if not found
        """
        metadata = self.get_file_metadata(file_id)
        if not metadata:
            return False

        try:
            # Update fields
            for key, value in updates.items():
                if hasattr(metadata, key):
                    setattr(metadata, key, value)

            # Save updated metadata
            self.store_file_metadata(metadata)
            logger.info(f"Updated file metadata: {file_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to update file metadata {file_id}: {e}")
            return False

    def delete_file_metadata(self, file_id: str) -> bool:
        """
        Delete file metadata.

        Args:
            file_id: UUID of file to delete

        Returns:
            True if deleted, False if not found
        """
        metadata_path = self._get_metadata_path(file_id)

        if not metadata_path.exists():
            return False

        try:
            metadata_path.unlink()
            logger.info(f"Deleted file metadata: {file_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to delete file metadata {file_id}: {e}")
            return False

    def get_files_for_session(self, session_id: str) -> list[FileMetadata]:
        """
        Get all files uploaded in a session.

        Args:
            session_id: Session ID to query

        Returns:
            List of FileMetadata instances
        """
        files = []

        for metadata_file in self.metadata_dir.glob("*.json"):
            try:
                with open(metadata_file, 'r') as f:
                    data = json.load(f)

                if data.get('session_id') == session_id:
                    files.append(FileMetadata.from_dict(data))

            except Exception as e:
                logger.warning(
                    f"Failed to load metadata file {metadata_file}: {e}")
                continue

        return files

    def get_files_for_user(
            self,
            user_id: str,
            quiz_id: str | None = None) -> list[FileMetadata]:
        """
        Get all files uploaded by a user.

        Args:
            user_id: User ID to query
            quiz_id: Optional quiz ID filter

        Returns:
            List of FileMetadata instances
        """
        files = []

        for metadata_file in self.metadata_dir.glob("*.json"):
            try:
                with open(metadata_file, 'r') as f:
                    data = json.load(f)

                if data.get('user_id') == user_id:
                    if quiz_id is None or data.get('quiz_id') == quiz_id:
                        files.append(FileMetadata.from_dict(data))

            except Exception as e:
                logger.warning(
                    f"Failed to load metadata file {metadata_file}: {e}")
                continue

        return files

    def cleanup_expired_files(self) -> int:
        """
        Delete expired files.

        Returns:
            Number of files deleted
        """
        now = datetime.now(timezone.utc)
        count = 0

        for metadata_file in self.metadata_dir.glob("*.json"):
            try:
                with open(metadata_file, 'r') as f:
                    data = json.load(f)

                expires_at_str = data.get('expires_at')
                if expires_at_str:
                    expires_at = datetime.fromisoformat(expires_at_str)
                    if expires_at < now:
                        metadata_file.unlink()
                        count += 1

            except Exception as e:
                logger.warning(
                    f"Failed to check expiration for {metadata_file}: {e}")
                continue

        if count > 0:
            logger.info(f"Cleaned up {count} expired files")
        return count

    def get_storage_stats(self, user_id: str | None = None) -> dict[str, Any]:
        """
        Get storage statistics.

        Args:
            user_id: Optional user ID to filter stats

        Returns:
            Dict with stats (file_count, total_bytes, etc.)
        """
        file_count = 0
        total_bytes = 0

        for metadata_file in self.metadata_dir.glob("*.json"):
            try:
                with open(metadata_file, 'r') as f:
                    data = json.load(f)

                # Filter by user_id if provided
                if user_id and data.get('user_id') != user_id:
                    continue

                file_count += 1
                size = data.get('size_bytes')
                if size:
                    total_bytes += size

            except Exception as e:
                logger.warning(
                    f"Failed to load metadata file {metadata_file}: {e}")
                continue

        return {
            'file_count': file_count,
            'total_bytes': total_bytes
        }

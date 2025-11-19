"""
File storage interface.

Defines abstract interface for storing file metadata.
Implementations handle SQL and file-based storage.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any

from .models import FileMetadata


class FileStorageInterface(ABC):
    """Abstract interface for file metadata storage."""

    @abstractmethod
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
        pass

    @abstractmethod
    def get_file_metadata(self, file_id: str) -> FileMetadata | None:
        """
        Retrieve file metadata by file_id.

        Args:
            file_id: UUID of file to retrieve

        Returns:
            FileMetadata instance or None if not found
        """
        pass

    @abstractmethod
    def update_file_metadata(self, file_id: str, updates: dict[str, Any]) -> bool:
        """
        Update file metadata.

        Args:
            file_id: UUID of file to update
            updates: Dict of fields to update

        Returns:
            True if updated, False if not found
        """
        pass

    @abstractmethod
    def delete_file_metadata(self, file_id: str) -> bool:
        """
        Delete file metadata.

        Args:
            file_id: UUID of file to delete

        Returns:
            True if deleted, False if not found
        """
        pass

    @abstractmethod
    def get_files_for_session(self, session_id: str) -> list[FileMetadata]:
        """
        Get all files uploaded in a session.

        Args:
            session_id: Session ID to query

        Returns:
            List of FileMetadata instances
        """
        pass

    @abstractmethod
    def get_files_for_user(self, user_id: str, quiz_id: str | None = None) -> list[FileMetadata]:
        """
        Get all files uploaded by a user.

        Args:
            user_id: User ID to query
            quiz_id: Optional quiz ID filter

        Returns:
            List of FileMetadata instances
        """
        pass

    @abstractmethod
    def cleanup_expired_files(self) -> int:
        """
        Delete expired files.

        Returns:
            Number of files deleted
        """
        pass

    @abstractmethod
    def get_storage_stats(self, user_id: str | None = None) -> dict[str, Any]:
        """
        Get storage statistics.

        Args:
            user_id: Optional user ID to filter stats

        Returns:
            Dict with stats (file_count, total_bytes, etc.)
        """
        pass

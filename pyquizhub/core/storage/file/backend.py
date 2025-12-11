"""Abstract storage backend for file storage."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import BinaryIO, Any


class FileMetadata:
    """File metadata for storage and retrieval."""

    def __init__(
        self,
        file_id: str,
        filename: str,
        category: str,
        size_bytes: int,
        mime_type: str | None = None,
        checksum: str | None = None,
        uploader_id: str | None = None,
        quiz_id: str | None = None,
        extension: str | None = None,
        image_width: int | None = None,
        image_height: int | None = None,
    ):
        self.file_id = file_id
        self.filename = filename
        self.category = category
        self.size_bytes = size_bytes
        self.mime_type = mime_type
        self.checksum = checksum
        self.uploader_id = uploader_id
        self.quiz_id = quiz_id
        self.extension = extension
        self.image_width = image_width
        self.image_height = image_height

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "file_id": self.file_id,
            "filename": self.filename,
            "category": self.category,
            "size_bytes": self.size_bytes,
            "mime_type": self.mime_type,
            "checksum": self.checksum,
            "uploader_id": self.uploader_id,
            "quiz_id": self.quiz_id,
            "extension": self.extension,
            "image_width": self.image_width,
            "image_height": self.image_height,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> FileMetadata:
        """Create from dictionary."""
        return cls(
            file_id=data["file_id"],
            filename=data["filename"],
            category=data["category"],
            size_bytes=data["size_bytes"],
            mime_type=data.get("mime_type"),
            checksum=data.get("checksum"),
            uploader_id=data.get("uploader_id"),
            quiz_id=data.get("quiz_id"),
            extension=data.get("extension"),
            image_width=data.get("image_width"),
            image_height=data.get("image_height"),
        )


class StorageBackend(ABC):
    """
    Abstract storage backend for file uploads.

    Implementations:
    - LocalStorageBackend: Store files on local filesystem
    - S3StorageBackend: Store files in S3-compatible object storage
    """

    @abstractmethod
    async def save(
        self,
        file_data: BinaryIO,
        metadata: FileMetadata,
    ) -> str:
        """
        Save file to storage backend.

        Args:
            file_data: File binary data stream
            metadata: File metadata

        Returns:
            file_id: Unique identifier for the stored file

        Raises:
            IOError: If save operation fails
        """
        pass

    @abstractmethod
    async def retrieve(self, file_id: str) -> tuple[BinaryIO, FileMetadata]:
        """
        Retrieve file from storage backend.

        Args:
            file_id: Unique file identifier

        Returns:
            Tuple of (file_data, metadata)

        Raises:
            FileNotFoundError: If file does not exist
            IOError: If retrieval fails
        """
        pass

    @abstractmethod
    async def delete(self, file_id: str) -> bool:
        """
        Delete file from storage backend.

        Args:
            file_id: Unique file identifier

        Returns:
            True if file was deleted, False if not found

        Raises:
            IOError: If deletion fails
        """
        pass

    @abstractmethod
    async def exists(self, file_id: str) -> bool:
        """
        Check if file exists in storage.

        Args:
            file_id: Unique file identifier

        Returns:
            True if file exists
        """
        pass

    @abstractmethod
    async def get_metadata(self, file_id: str) -> FileMetadata:
        """
        Get file metadata without retrieving file data.

        Args:
            file_id: Unique file identifier

        Returns:
            FileMetadata object

        Raises:
            FileNotFoundError: If file does not exist
        """
        pass

    @abstractmethod
    async def get_download_url(
            self,
            file_id: str,
            expiry_seconds: int = 3600) -> str:
        """
        Get temporary download URL for file.

        Args:
            file_id: Unique file identifier
            expiry_seconds: URL expiry time in seconds

        Returns:
            Download URL (may be signed/temporary)

        Raises:
            FileNotFoundError: If file does not exist
        """
        pass

    @abstractmethod
    async def get_quota_usage(
            self,
            user_id: str | None = None,
            quiz_id: str | None = None) -> int:
        """
        Get storage quota usage in bytes.

        Args:
            user_id: Filter by user (optional)
            quiz_id: Filter by quiz (optional)

        Returns:
            Total storage used in bytes
        """
        pass

    @abstractmethod
    async def list_files(
        self,
        user_id: str | None = None,
        quiz_id: str | None = None,
        category: str | None = None,
    ) -> list[FileMetadata]:
        """
        List files matching criteria.

        Args:
            user_id: Filter by uploader user ID
            quiz_id: Filter by quiz ID
            category: Filter by file category

        Returns:
            List of FileMetadata objects
        """
        pass

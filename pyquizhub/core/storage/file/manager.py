"""File manager for high-level file operations with quota and access control."""

from __future__ import annotations

import uuid
from typing import BinaryIO, Any

from .validator import FileValidator, ValidationError
from .backend import StorageBackend, FileMetadata


class QuotaInfo:
    """Quota information for a user or quiz."""

    def __init__(
        self,
        used_bytes: int,
        limit_bytes: int,
        file_count: int,
    ):
        self.used_bytes = used_bytes
        self.limit_bytes = limit_bytes
        self.file_count = file_count
        self.available_bytes = max(0, limit_bytes - used_bytes)
        self.usage_percent = (
            used_bytes /
            limit_bytes *
            100) if limit_bytes > 0 else 0

    def has_capacity(self, additional_bytes: int) -> bool:
        """Check if quota can accommodate additional bytes."""
        return (self.used_bytes + additional_bytes) <= self.limit_bytes

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "used_bytes": self.used_bytes,
            "limit_bytes": self.limit_bytes,
            "available_bytes": self.available_bytes,
            "usage_percent": round(self.usage_percent, 2),
            "file_count": self.file_count,
        }


class FileManager:
    """
    High-level file manager with validation, quota management, and access control.

    Features:
    - File upload with multi-layer validation
    - Quota enforcement (per-user, per-quiz, global)
    - Access control (admin, creator, user roles)
    - Secure file retrieval
    - File deletion with authorization
    """

    def __init__(
        self,
        storage_backend: StorageBackend,
        validator: FileValidator,
        config: Any,
    ):
        """
        Initialize file manager.

        Args:
            storage_backend: Storage backend (local/S3)
            validator: File validator
            config: Configuration object
        """
        self.storage = storage_backend
        self.validator = validator
        self.config = config

    async def upload_file(
        self,
        file_data: BinaryIO,
        filename: str,
        uploader_id: str,
        uploader_role: str,
        quiz_id: str | None = None,
    ) -> FileMetadata:
        """
        Upload file with validation and quota checks.

        Args:
            file_data: File binary data stream
            filename: Original filename
            uploader_id: ID of user uploading file
            uploader_role: Role of uploader (admin, creator, user)
            quiz_id: Associated quiz ID (optional)

        Returns:
            FileMetadata object with file_id and download URL

        Raises:
            ValidationError: If file validation fails
            PermissionError: If uploader lacks permission
            IOError: If quota exceeded or storage fails
        """
        # 1. Check if file uploads are enabled
        # TODO: Add file_storage.enabled to config
        # For now, file uploads are always enabled
        enabled = getattr(
            getattr(
                self.config,
                'file_storage',
                None),
            'enabled',
            True)
        if not enabled:
            raise PermissionError("File uploads are disabled")

        # 2. Check upload permissions based on role
        if not self._check_upload_permission(uploader_role, quiz_id):
            raise PermissionError(
                f"Role '{uploader_role}' is not allowed to upload files")

        # 3. Validate file
        is_valid, error_msg, validation_metadata = self.validator.validate_upload(
            file_data, filename, uploader_role)

        if not is_valid:
            raise ValidationError(error_msg or "File validation failed")

        # 4. Check quota
        quota_info = await self.check_quota(uploader_id, quiz_id)
        if not quota_info.has_capacity(validation_metadata["size_bytes"]):
            raise IOError(
                f"Quota exceeded: {quota_info.used_bytes / (1024 * 1024):.1f} MB used, "
                f"{validation_metadata['size_bytes'] / (1024 * 1024):.1f} MB requested, "
                f"{quota_info.limit_bytes / (1024 * 1024):.1f} MB limit"
            )

        # 5. Generate file_id
        file_id = str(uuid.uuid4())

        # 6. Create metadata object
        metadata = FileMetadata(
            file_id=file_id,
            filename=filename,
            category=validation_metadata["category"],
            size_bytes=validation_metadata["size_bytes"],
            mime_type=validation_metadata.get("mime_type"),
            checksum=validation_metadata.get("checksum"),
            uploader_id=uploader_id,
            quiz_id=quiz_id,
            extension=validation_metadata.get("extension"),
        )

        # 7. Save to storage backend
        try:
            await self.storage.save(file_data, metadata)
        except Exception as e:
            raise IOError(f"Failed to save file: {str(e)}") from e

        return metadata

    async def get_file(
        self,
        file_id: str,
        requester_id: str,
        requester_role: str,
    ) -> tuple[BinaryIO, FileMetadata]:
        """
        Retrieve file with access control.

        Args:
            file_id: File identifier
            requester_id: ID of user requesting file
            requester_role: Role of requester (admin, creator, user)

        Returns:
            Tuple of (file_data, metadata)

        Raises:
            FileNotFoundError: If file does not exist
            PermissionError: If requester lacks access
            IOError: If retrieval fails
        """
        # Get file metadata first
        metadata = await self.storage.get_metadata(file_id)

        # Check access permission
        if not self._check_access_permission(
                metadata, requester_id, requester_role):
            raise PermissionError("Access denied to this file")

        # Retrieve file
        return await self.storage.retrieve(file_id)

    async def get_download_url(
        self,
        file_id: str,
        requester_id: str,
        requester_role: str,
        expiry_seconds: int = 3600,
    ) -> str:
        """
        Get download URL with access control.

        Args:
            file_id: File identifier
            requester_id: ID of user requesting URL
            requester_role: Role of requester
            expiry_seconds: URL expiry time in seconds

        Returns:
            Download URL

        Raises:
            FileNotFoundError: If file does not exist
            PermissionError: If requester lacks access
        """
        # Get file metadata first
        metadata = await self.storage.get_metadata(file_id)

        # Check access permission
        if not self._check_access_permission(
                metadata, requester_id, requester_role):
            raise PermissionError("Access denied to this file")

        # Get download URL
        return await self.storage.get_download_url(file_id, expiry_seconds)

    async def delete_file(
        self,
        file_id: str,
        requester_id: str,
        requester_role: str,
    ) -> bool:
        """
        Delete file with authorization.

        Only admins and the file uploader can delete files.

        Args:
            file_id: File identifier
            requester_id: ID of user requesting deletion
            requester_role: Role of requester

        Returns:
            True if file was deleted

        Raises:
            FileNotFoundError: If file does not exist
            PermissionError: If requester lacks permission
            IOError: If deletion fails
        """
        # Get file metadata first
        metadata = await self.storage.get_metadata(file_id)

        # Only admin or uploader can delete
        if requester_role != "admin" and metadata.uploader_id != requester_id:
            raise PermissionError(
                "Only admins or file uploader can delete files")

        # Delete file
        return await self.storage.delete(file_id)

    async def check_quota(
        self,
        user_id: str | None = None,
        quiz_id: str | None = None,
    ) -> QuotaInfo:
        """
        Check storage quota usage.

        Args:
            user_id: User ID to check quota for (optional)
            quiz_id: Quiz ID to check quota for (optional)

        Returns:
            QuotaInfo object with usage details
        """
        # Get current usage
        used_bytes = await self.storage.get_quota_usage(user_id, quiz_id)

        # Get file count
        files = await self.storage.list_files(user_id, quiz_id)
        file_count = len(files)

        # Determine quota limit
        # TODO: Add file_storage.quotas to config
        # Using default values for now
        default_quotas = type('obj', (object,), {
            'per_user_mb': 100,
            'per_quiz_mb': 500,
            'global_limit_mb': 10000
        })()
        quotas = getattr(
            getattr(
                self.config,
                'file_storage',
                None),
            'quotas',
            default_quotas)

        if user_id:
            limit_mb = getattr(quotas, 'per_user_mb', 100)
        elif quiz_id:
            limit_mb = getattr(quotas, 'per_quiz_mb', 500)
        else:
            limit_mb = getattr(quotas, 'global_limit_mb', 10000)

        limit_bytes = limit_mb * 1024 * 1024

        return QuotaInfo(
            used_bytes=used_bytes,
            limit_bytes=limit_bytes,
            file_count=file_count,
        )

    async def list_files(
        self,
        requester_id: str,
        requester_role: str,
        user_id: str | None = None,
        quiz_id: str | None = None,
        category: str | None = None,
    ) -> list[FileMetadata]:
        """
        List files with access control.

        Args:
            requester_id: ID of user requesting list
            requester_role: Role of requester
            user_id: Filter by uploader (optional)
            quiz_id: Filter by quiz (optional)
            category: Filter by category (optional)

        Returns:
            List of FileMetadata objects

        Raises:
            PermissionError: If requester lacks permission
        """
        # Admins can list all files
        if requester_role == "admin":
            return await self.storage.list_files(user_id, quiz_id, category)

        # Users can only list their own files
        if requester_role == "user":
            return await self.storage.list_files(requester_id, quiz_id, category)

        # Creators can list files for their quizzes
        if requester_role == "creator":
            # TODO: Verify quiz ownership when quiz system is integrated
            return await self.storage.list_files(user_id, quiz_id, category)

        raise PermissionError("Invalid role for listing files")

    def _check_upload_permission(self, role: str, quiz_id: str | None) -> bool:
        """
        Check if role is allowed to upload files.

        Args:
            role: User role (admin, creator, user)
            quiz_id: Associated quiz ID (None for user answers)

        Returns:
            True if allowed
        """
        # TODO: Add file_storage.upload config
        # For now, allow all uploads for testing
        return True

    def _check_access_permission(
        self,
        metadata: FileMetadata,
        requester_id: str,
        requester_role: str,
    ) -> bool:
        """
        Check if requester can access file.

        Args:
            metadata: File metadata
            requester_id: ID of requester
            requester_role: Role of requester

        Returns:
            True if access allowed
        """
        # Admins can access all files
        if requester_role == "admin":
            return True

        # Users can access their own uploaded files
        if metadata.uploader_id == requester_id:
            return True

        # TODO: Quiz-based access control (users can access files in quizzes they're taking)
        # This requires integration with quiz permission system

        return False

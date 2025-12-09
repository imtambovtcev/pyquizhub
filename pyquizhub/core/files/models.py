"""
File attachment models.

This module provides secure abstraction for file attachments across platforms.
Platform-specific identifiers (Telegram file_id, Discord URLs) are stored but
NEVER exposed directly to users or quiz creators.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any
from dataclasses import dataclass, field


@dataclass
class FileMetadata:
    """
    Metadata for uploaded file.

    Stores platform-specific identifiers securely without exposing them
    to end users or quiz creators.
    """

    file_id: str
    file_type: str  # 'image', 'document', 'audio', 'video', 'other'
    mime_type: str | None
    size_bytes: int | None
    filename: str | None

    # Platform information (PRIVATE - never exposed)
    platform: str  # 'telegram', 'discord', 'web', 'url'
    platform_data: dict[str, Any]  # Platform-specific identifiers

    # Ownership and lifecycle
    session_id: str | None
    user_id: str
    quiz_id: str | None
    created_at: datetime
    expires_at: datetime | None = None

    # Optional metadata
    description: str | None = None
    tags: list[str] = field(default_factory=list)

    @classmethod
    def create_new(
        cls,
        file_type: str,
        platform: str,
        platform_data: dict[str, Any],
        user_id: str,
        mime_type: str | None = None,
        size_bytes: int | None = None,
        filename: str | None = None,
        session_id: str | None = None,
        quiz_id: str | None = None,
        expires_at: datetime | None = None,
        description: str | None = None,
        tags: list[str] | None = None
    ) -> FileMetadata:
        """Create new file metadata with auto-generated file_id."""
        return cls(
            file_id=str(uuid.uuid4()),
            file_type=file_type,
            mime_type=mime_type,
            size_bytes=size_bytes,
            filename=filename,
            platform=platform,
            platform_data=platform_data,
            session_id=session_id,
            user_id=user_id,
            quiz_id=quiz_id,
            created_at=datetime.now(timezone.utc),
            expires_at=expires_at,
            description=description,
            tags=tags or []
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary (includes platform_data for storage)."""
        return {
            'file_id': self.file_id,
            'file_type': self.file_type,
            'mime_type': self.mime_type,
            'size_bytes': self.size_bytes,
            'filename': self.filename,
            'platform': self.platform,
            'platform_data': self.platform_data,
            'session_id': self.session_id,
            'user_id': self.user_id,
            'quiz_id': self.quiz_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'description': self.description,
            'tags': self.tags}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> FileMetadata:
        """Create from dictionary (includes platform_data from storage)."""
        return cls(
            file_id=data['file_id'],
            file_type=data['file_type'],
            mime_type=data.get('mime_type'),
            size_bytes=data.get('size_bytes'),
            filename=data.get('filename'),
            platform=data['platform'],
            platform_data=data['platform_data'],
            session_id=data.get('session_id'),
            user_id=data['user_id'],
            quiz_id=data.get('quiz_id'),
            created_at=datetime.fromisoformat(
                data['created_at']) if data.get('created_at') else datetime.now(
                timezone.utc),
            expires_at=datetime.fromisoformat(
                data['expires_at']) if data.get('expires_at') else None,
            description=data.get('description'),
            tags=data.get(
                    'tags',
                []))

    def to_safe_dict(self) -> dict[str, Any]:
        """
        Export safe metadata for quiz creators.

        NEVER includes platform or platform_data.
        This is what quiz creators see when they download results.
        """
        return {
            'file_id': self.file_id,
            'file_type': self.file_type,
            'mime_type': self.mime_type,
            'size_bytes': self.size_bytes,
            'filename': self.filename,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'description': self.description
            # platform and platform_data OMITTED for security
        }


class FileAttachment:
    """
    Secure abstraction for file attachments.

    Provides safe access methods without exposing platform-specific identifiers.
    Platform data (Telegram file_id, Discord URLs) is stored but NEVER exposed.
    """

    def __init__(self, metadata: FileMetadata):
        """Initialize from FileMetadata."""
        self.metadata = metadata
        self._platform_data = metadata.platform_data  # PRIVATE

    @property
    def file_id(self) -> str:
        """Public file ID (UUID) - safe to expose."""
        return self.metadata.file_id

    @property
    def file_type(self) -> str:
        """File type: 'image', 'document', 'audio', 'video', 'other'."""
        return self.metadata.file_type

    @property
    def mime_type(self) -> str | None:
        """MIME type (e.g., 'image/jpeg', 'application/pdf')."""
        return self.metadata.mime_type

    @property
    def size_bytes(self) -> int | None:
        """File size in bytes."""
        return self.metadata.size_bytes

    @property
    def filename(self) -> str | None:
        """Original filename if available."""
        return self.metadata.filename

    @property
    def platform(self) -> str:
        """Platform where file was uploaded: 'telegram', 'discord', 'web', 'url'."""
        return self.metadata.platform

    def get_reference_uri(self) -> str:
        """
        Get file reference URI for storage in variables.

        Format: file://{file_id}
        This is what gets stored in quiz session variables.
        """
        return f"file://{self.file_id}"

    @staticmethod
    def parse_reference_uri(uri: str) -> str | None:
        """
        Parse file reference URI to extract file_id.

        Args:
            uri: Reference URI (e.g., "file://f7e3d9a1-4b2c-4e8f-9d6a-...")

        Returns:
            file_id or None if not a valid file URI
        """
        if not isinstance(uri, str):
            return None
        if uri.startswith('file://'):
            return uri[7:]  # Remove 'file://' prefix
        return None

    @staticmethod
    def is_file_reference(value: Any) -> bool:
        """Check if a value is a file reference URI."""
        return isinstance(value, str) and value.startswith('file://')

    def get_url_for_adapter(self,
                            adapter_type: str,
                            adapter_context: dict[str,
                                                  Any] | None = None) -> str | None:
        """
        Get safe URL/identifier for display in specific adapter.

        Args:
            adapter_type: 'telegram', 'discord', 'web', 'api'
            adapter_context: Optional context (bot instance, session, etc.)

        Returns:
            Safe URL/identifier or None if not displayable in this adapter

        Examples:
            - Telegram adapter gets file_id (bot can send by ID)
            - Discord/Web adapters get proxy API URL
            - Never exposes bot tokens or private URLs
        """
        if self.platform == 'url':
            # Public URL - safe to return to anyone
            return self._platform_data.get('url')

        elif self.platform == 'telegram':
            if adapter_type == 'telegram':
                # Return Telegram file_id - bot can send by ID without token
                # exposure
                return self._platform_data.get('file_id')
            else:
                # Other adapters get proxy API URL
                return f"/api/files/{self.file_id}/download"

        elif self.platform == 'discord':
            if adapter_type == 'discord':
                # Discord attachment URL (may be temporary but safe for
                # Discord)
                return self._platform_data.get('url')
            else:
                # Other adapters get proxy API URL
                return f"/api/files/{self.file_id}/download"

        elif self.platform == 'web':
            # Web-uploaded file - always use proxy
            return f"/api/files/{self.file_id}/download"

        return None

    def can_display_in_adapter(self, adapter_type: str) -> bool:
        """Check if file can be displayed in given adapter."""
        return self.get_url_for_adapter(adapter_type) is not None

    def to_safe_dict(self) -> dict[str, Any]:
        """
        Export safe metadata for quiz creators.

        This is what quiz creators see - NO platform data exposed.
        """
        return self.metadata.to_safe_dict()

    def __repr__(self) -> str:
        """String representation for debugging."""
        return f"FileAttachment(file_id={self.file_id}, type={self.file_type}, platform={self.platform})"

"""
SQL implementation of file metadata storage.

Stores file metadata in a separate table from session variables.
Platform-specific identifiers are stored but never exposed to users/creators.
"""

from __future__ import annotations

from sqlalchemy import (
    create_engine, MetaData, Table, Column,
    String, Integer, JSON, DateTime, Text,
    select, insert, update, delete, and_, inspect
)
from sqlalchemy.exc import IntegrityError
from datetime import datetime
from typing import Any

from .storage import FileStorageInterface
from .models import FileMetadata
from pyquizhub.logging.setup import get_logger

logger = get_logger(__name__)


class SQLFileStorage(FileStorageInterface):
    """SQL implementation of file metadata storage."""

    def __init__(self, connection_string: str):
        """
        Initialize SQL file storage.

        Args:
            connection_string: Database connection string
        """
        self.engine = create_engine(connection_string)
        self.metadata = MetaData()

        # Define file_metadata table
        self.file_metadata_table = Table(
            "file_metadata", self.metadata,
            Column("file_id", String(255), primary_key=True),
            Column("file_type", String(50), nullable=False),
            Column("mime_type", String(100)),
            Column("size_bytes", Integer),
            Column("filename", String(500)),

            # Platform information (PRIVATE - never exposed)
            Column("platform", String(50), nullable=False),
            Column("platform_data", JSON, nullable=False),

            # Ownership and lifecycle
            Column("session_id", String(255)),
            Column("user_id", String(255), nullable=False),
            Column("quiz_id", String(255)),
            Column("created_at", DateTime, nullable=False),
            Column("expires_at", DateTime),

            # Optional metadata
            Column("description", Text),
            Column("tags", JSON)
        )

        # Create table if it doesn't exist
        self.metadata.create_all(self.engine)

        logger.info("SQL file storage initialized")

    def _execute(self, query):
        """Execute a database query."""
        with self.engine.connect() as conn:
            result = conn.execute(query)
            conn.commit()
            return result

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
            query = insert(self.file_metadata_table).values(
                file_id=metadata.file_id,
                file_type=metadata.file_type,
                mime_type=metadata.mime_type,
                size_bytes=metadata.size_bytes,
                filename=metadata.filename,
                platform=metadata.platform,
                platform_data=metadata.platform_data,
                session_id=metadata.session_id,
                user_id=metadata.user_id,
                quiz_id=metadata.quiz_id,
                created_at=metadata.created_at,
                expires_at=metadata.expires_at,
                description=metadata.description,
                tags=metadata.tags
            )
            self._execute(query)
            logger.info(f"Stored file metadata: {metadata.file_id}")
            return metadata.file_id

        except IntegrityError as e:
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
        query = select(self.file_metadata_table).where(
            self.file_metadata_table.c.file_id == file_id
        )
        result = self._execute(query).fetchone()

        if not result:
            return None

        row = result._mapping
        return FileMetadata(
            file_id=row['file_id'],
            file_type=row['file_type'],
            mime_type=row['mime_type'],
            size_bytes=row['size_bytes'],
            filename=row['filename'],
            platform=row['platform'],
            platform_data=row['platform_data'],
            session_id=row['session_id'],
            user_id=row['user_id'],
            quiz_id=row['quiz_id'],
            created_at=row['created_at'],
            expires_at=row['expires_at'],
            description=row['description'],
            tags=row['tags'] or []
        )

    def update_file_metadata(self, file_id: str, updates: dict[str, Any]) -> bool:
        """
        Update file metadata.

        Args:
            file_id: UUID of file to update
            updates: Dict of fields to update

        Returns:
            True if updated, False if not found
        """
        query = update(self.file_metadata_table).where(
            self.file_metadata_table.c.file_id == file_id
        ).values(**updates)

        result = self._execute(query)
        updated = result.rowcount > 0

        if updated:
            logger.info(f"Updated file metadata: {file_id}")
        return updated

    def delete_file_metadata(self, file_id: str) -> bool:
        """
        Delete file metadata.

        Args:
            file_id: UUID of file to delete

        Returns:
            True if deleted, False if not found
        """
        query = delete(self.file_metadata_table).where(
            self.file_metadata_table.c.file_id == file_id
        )

        result = self._execute(query)
        deleted = result.rowcount > 0

        if deleted:
            logger.info(f"Deleted file metadata: {file_id}")
        return deleted

    def get_files_for_session(self, session_id: str) -> list[FileMetadata]:
        """
        Get all files uploaded in a session.

        Args:
            session_id: Session ID to query

        Returns:
            List of FileMetadata instances
        """
        query = select(self.file_metadata_table).where(
            self.file_metadata_table.c.session_id == session_id
        )
        results = self._execute(query).fetchall()

        files = []
        for row in results:
            r = row._mapping
            files.append(FileMetadata(
                file_id=r['file_id'],
                file_type=r['file_type'],
                mime_type=r['mime_type'],
                size_bytes=r['size_bytes'],
                filename=r['filename'],
                platform=r['platform'],
                platform_data=r['platform_data'],
                session_id=r['session_id'],
                user_id=r['user_id'],
                quiz_id=r['quiz_id'],
                created_at=r['created_at'],
                expires_at=r['expires_at'],
                description=r['description'],
                tags=r['tags'] or []
            ))

        return files

    def get_files_for_user(self, user_id: str, quiz_id: str | None = None) -> list[FileMetadata]:
        """
        Get all files uploaded by a user.

        Args:
            user_id: User ID to query
            quiz_id: Optional quiz ID filter

        Returns:
            List of FileMetadata instances
        """
        conditions = [self.file_metadata_table.c.user_id == user_id]
        if quiz_id:
            conditions.append(self.file_metadata_table.c.quiz_id == quiz_id)

        query = select(self.file_metadata_table).where(and_(*conditions))
        results = self._execute(query).fetchall()

        files = []
        for row in results:
            r = row._mapping
            files.append(FileMetadata(
                file_id=r['file_id'],
                file_type=r['file_type'],
                mime_type=r['mime_type'],
                size_bytes=r['size_bytes'],
                filename=r['filename'],
                platform=r['platform'],
                platform_data=r['platform_data'],
                session_id=r['session_id'],
                user_id=r['user_id'],
                quiz_id=r['quiz_id'],
                created_at=r['created_at'],
                expires_at=r['expires_at'],
                description=r['description'],
                tags=r['tags'] or []
            ))

        return files

    def cleanup_expired_files(self) -> int:
        """
        Delete expired files.

        Returns:
            Number of files deleted
        """
        now = datetime.utcnow()
        query = delete(self.file_metadata_table).where(
            and_(
                self.file_metadata_table.c.expires_at != None,
                self.file_metadata_table.c.expires_at < now
            )
        )

        result = self._execute(query)
        count = result.rowcount

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
        from sqlalchemy import func

        # Build base query
        if user_id:
            query = select(
                func.count(self.file_metadata_table.c.file_id).label('file_count'),
                func.sum(self.file_metadata_table.c.size_bytes).label('total_bytes')
            ).where(self.file_metadata_table.c.user_id == user_id)
        else:
            query = select(
                func.count(self.file_metadata_table.c.file_id).label('file_count'),
                func.sum(self.file_metadata_table.c.size_bytes).label('total_bytes')
            )

        result = self._execute(query).fetchone()

        if result:
            r = result._mapping
            return {
                'file_count': r['file_count'] or 0,
                'total_bytes': r['total_bytes'] or 0
            }

        return {'file_count': 0, 'total_bytes': 0}

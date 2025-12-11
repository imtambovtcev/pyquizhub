"""Local filesystem storage backend."""

from __future__ import annotations

import aiosqlite
import io
import os
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import BinaryIO, Any

from .backend import StorageBackend, FileMetadata


class LocalStorageBackend(StorageBackend):
    """
    Local filesystem storage backend.

    Files are stored with UUID-based names in date-organized directories:
    - Base directory: /path/to/storage/files/
    - Organization: files/YYYY/MM/DD/uuid.ext
    - Example: files/2025/01/20/a1b2c3d4-e5f6-7890-abcd-ef1234567890.jpg

    Metadata is stored in SQLite database for fast queries.

    Security features:
    - UUID-based filenames (prevent guessing)
    - No execute permissions on stored files
    - Path sanitization
    - Quota enforcement
    """

    def __init__(self, base_dir: str, config: Any):
        """
        Initialize local storage backend.

        Args:
            base_dir: Base directory for file storage
            config: Configuration object
        """
        self.base_dir = Path(base_dir)
        self.config = config
        self.files_dir = self.base_dir / "files"
        self.db_path = self.base_dir / "file_metadata.db"

        # Create directories
        self.files_dir.mkdir(parents=True, exist_ok=True)

        # Initialize database (will be done async in setup())
        self._db_initialized = False

    async def _ensure_db(self):
        """Ensure database is initialized."""
        if self._db_initialized:
            return

        async with aiosqlite.connect(str(self.db_path)) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS file_metadata (
                    file_id TEXT PRIMARY KEY,
                    filename TEXT NOT NULL,
                    category TEXT NOT NULL,
                    extension TEXT,
                    size_bytes INTEGER NOT NULL,
                    mime_type TEXT,
                    checksum TEXT,
                    uploader_id TEXT,
                    quiz_id TEXT,
                    storage_path TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    image_width INTEGER,
                    image_height INTEGER,
                    UNIQUE(storage_path)
                )
            """)

            # Add columns for existing databases (migration)
            try:
                await db.execute(
                    "ALTER TABLE file_metadata ADD COLUMN image_width INTEGER")
            except aiosqlite.OperationalError:
                pass  # Column already exists
            try:
                await db.execute(
                    "ALTER TABLE file_metadata ADD COLUMN image_height INTEGER")
            except aiosqlite.OperationalError:
                pass  # Column already exists

            # Create indexes for common queries
            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_uploader_id ON file_metadata(uploader_id)
            """)
            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_quiz_id ON file_metadata(quiz_id)
            """)
            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_category ON file_metadata(category)
            """)

            await db.commit()

        self._db_initialized = True

    def _generate_storage_path(
            self,
            file_id: str,
            extension: str | None) -> Path:
        """
        Generate storage path for file.

        Format: files/YYYY/MM/DD/uuid.ext

        Args:
            file_id: UUID file identifier
            extension: File extension (without dot)

        Returns:
            Path object for storage location
        """
        now = datetime.now(timezone.utc)
        year = now.strftime("%Y")
        month = now.strftime("%m")
        day = now.strftime("%d")

        # Create date-based subdirectory
        date_dir = self.files_dir / year / month / day
        date_dir.mkdir(parents=True, exist_ok=True)

        # Generate filename with extension
        if extension:
            filename = f"{file_id}.{extension}"
        else:
            filename = file_id

        return date_dir / filename

    async def save(
        self,
        file_data: BinaryIO,
        metadata: FileMetadata,
    ) -> str:
        """
        Save file to local filesystem.

        Args:
            file_data: File binary data stream
            metadata: File metadata (file_id must be set)

        Returns:
            file_id: Unique identifier for the stored file

        Raises:
            IOError: If save operation fails
        """
        await self._ensure_db()

        file_id = metadata.file_id
        if not file_id:
            raise ValueError("file_id must be set in metadata")

        # Generate storage path
        storage_path = self._generate_storage_path(file_id, metadata.extension)

        try:
            # Write file to disk
            file_data.seek(0)
            with open(storage_path, 'wb') as f:
                shutil.copyfileobj(file_data, f)

            # Set file permissions (read-only, no execute)
            os.chmod(storage_path, 0o444)

            # Store metadata in database
            async with aiosqlite.connect(str(self.db_path)) as db:
                await db.execute("""
                    INSERT INTO file_metadata (
                        file_id, filename, category, extension, size_bytes,
                        mime_type, checksum, uploader_id, quiz_id,
                        storage_path, created_at, image_width, image_height
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    file_id,
                    metadata.filename,
                    metadata.category,
                    metadata.extension,
                    metadata.size_bytes,
                    metadata.mime_type,
                    metadata.checksum,
                    metadata.uploader_id,
                    metadata.quiz_id,
                    str(storage_path),
                    datetime.now(timezone.utc).isoformat(),
                    metadata.image_width,
                    metadata.image_height,
                ))
                await db.commit()

            return file_id

        except Exception as e:
            # Clean up file if metadata storage fails
            if storage_path.exists():
                storage_path.unlink()
            raise IOError(f"Failed to save file: {str(e)}") from e

    async def retrieve(self, file_id: str) -> tuple[BinaryIO, FileMetadata]:
        """
        Retrieve file from local filesystem.

        Args:
            file_id: Unique file identifier

        Returns:
            Tuple of (file_data, metadata)

        Raises:
            FileNotFoundError: If file does not exist
            IOError: If retrieval fails
        """
        await self._ensure_db()

        # Get metadata from database
        metadata = await self.get_metadata(file_id)

        # Read file from disk
        async with aiosqlite.connect(str(self.db_path)) as db:
            async with db.execute(
                "SELECT storage_path FROM file_metadata WHERE file_id = ?",
                (file_id,)
            ) as cursor:
                row = await cursor.fetchone()
                if not row:
                    raise FileNotFoundError(f"File not found: {file_id}")

                storage_path = Path(row[0])

        if not storage_path.exists():
            raise FileNotFoundError(f"File data not found on disk: {file_id}")

        try:
            # Read file into BytesIO for compatibility
            with open(storage_path, 'rb') as f:
                file_data = io.BytesIO(f.read())

            return file_data, metadata

        except Exception as e:
            raise IOError(f"Failed to retrieve file: {str(e)}") from e

    async def delete(self, file_id: str) -> bool:
        """
        Delete file from local filesystem.

        Args:
            file_id: Unique file identifier

        Returns:
            True if file was deleted, False if not found

        Raises:
            IOError: If deletion fails
        """
        await self._ensure_db()

        # Get storage path from database
        async with aiosqlite.connect(str(self.db_path)) as db:
            async with db.execute(
                "SELECT storage_path FROM file_metadata WHERE file_id = ?",
                (file_id,)
            ) as cursor:
                row = await cursor.fetchone()
                if not row:
                    return False

                storage_path = Path(row[0])

            # Delete metadata
            await db.execute("DELETE FROM file_metadata WHERE file_id = ?", (file_id,))
            await db.commit()

        # Delete file from disk
        try:
            if storage_path.exists():
                storage_path.unlink()
            return True
        except Exception as e:
            raise IOError(f"Failed to delete file: {str(e)}") from e

    async def exists(self, file_id: str) -> bool:
        """
        Check if file exists in storage.

        Args:
            file_id: Unique file identifier

        Returns:
            True if file exists
        """
        await self._ensure_db()

        async with aiosqlite.connect(str(self.db_path)) as db:
            async with db.execute(
                "SELECT 1 FROM file_metadata WHERE file_id = ?",
                (file_id,)
            ) as cursor:
                row = await cursor.fetchone()
                return row is not None

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
        await self._ensure_db()

        async with aiosqlite.connect(str(self.db_path)) as db:
            async with db.execute("""
                SELECT file_id, filename, category, size_bytes, mime_type,
                       checksum, uploader_id, quiz_id, extension,
                       image_width, image_height
                FROM file_metadata
                WHERE file_id = ?
            """, (file_id,)) as cursor:
                row = await cursor.fetchone()
                if not row:
                    raise FileNotFoundError(f"File not found: {file_id}")

                return FileMetadata(
                    file_id=row[0],
                    filename=row[1],
                    category=row[2],
                    size_bytes=row[3],
                    mime_type=row[4],
                    checksum=row[5],
                    uploader_id=row[6],
                    quiz_id=row[7],
                    extension=row[8],
                    image_width=row[9],
                    image_height=row[10],
                )

    async def get_download_url(
            self,
            file_id: str,
            expiry_seconds: int = 3600) -> str:
        """
        Get download URL for file.

        For local storage, returns API endpoint path (not a direct file path).

        Args:
            file_id: Unique file identifier
            expiry_seconds: Unused for local storage

        Returns:
            Download URL path (e.g., /api/files/download/{file_id})

        Raises:
            FileNotFoundError: If file does not exist
        """
        # Verify file exists
        if not await self.exists(file_id):
            raise FileNotFoundError(f"File not found: {file_id}")

        # Return API endpoint (actual URL construction happens in API layer)
        return f"/api/files/download/{file_id}"

    async def get_quota_usage(
        self,
        user_id: str | None = None,
        quiz_id: str | None = None
    ) -> int:
        """
        Get storage quota usage in bytes.

        Args:
            user_id: Filter by user (optional)
            quiz_id: Filter by quiz (optional)

        Returns:
            Total storage used in bytes
        """
        await self._ensure_db()

        query = "SELECT COALESCE(SUM(size_bytes), 0) FROM file_metadata WHERE 1=1"
        params = []

        if user_id:
            query += " AND uploader_id = ?"
            params.append(user_id)

        if quiz_id:
            query += " AND quiz_id = ?"
            params.append(quiz_id)

        async with aiosqlite.connect(str(self.db_path)) as db:
            async with db.execute(query, params) as cursor:
                row = await cursor.fetchone()
                return row[0] if row else 0

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
        await self._ensure_db()

        query = """
            SELECT file_id, filename, category, size_bytes, mime_type,
                   checksum, uploader_id, quiz_id, extension,
                   image_width, image_height
            FROM file_metadata
            WHERE 1=1
        """
        params = []

        if user_id:
            query += " AND uploader_id = ?"
            params.append(user_id)

        if quiz_id:
            query += " AND quiz_id = ?"
            params.append(quiz_id)

        if category:
            query += " AND category = ?"
            params.append(category)

        query += " ORDER BY created_at DESC"

        files = []
        async with aiosqlite.connect(str(self.db_path)) as db:
            async with db.execute(query, params) as cursor:
                async for row in cursor:
                    files.append(FileMetadata(
                        file_id=row[0],
                        filename=row[1],
                        category=row[2],
                        size_bytes=row[3],
                        mime_type=row[4],
                        checksum=row[5],
                        uploader_id=row[6],
                        quiz_id=row[7],
                        extension=row[8],
                        image_width=row[9],
                        image_height=row[10],
                    ))

        return files

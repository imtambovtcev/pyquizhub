"""File validation for secure file uploads."""

from __future__ import annotations

import hashlib
import mimetypes
import os
import re
import zipfile
from enum import Enum
from pathlib import Path
from typing import BinaryIO, Any

try:
    import magic
    HAS_MAGIC = True
except ImportError:
    HAS_MAGIC = False

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False


class FileTypeCategory(str, Enum):
    """File type categories for validation and configuration."""
    IMAGES = "images"
    AUDIO = "audio"
    VIDEO = "video"
    DOCUMENTS = "documents"
    ARCHIVES = "archives"


class ValidationError(Exception):
    """Raised when file validation fails."""
    pass


class FileValidator:
    """
    Validates file uploads with multi-layer security checks.

    Security layers:
    1. File extension whitelist
    2. MIME type validation
    3. Magic number verification (file header)
    4. Filename sanitization (path traversal, special chars)
    5. File size limits (per-file, per-category)
    6. Special security checks (SVG/XSS, Office macros, zip bombs)
    """

    # File extension to category mapping
    EXTENSION_CATEGORIES = {
        # Images
        "jpg": FileTypeCategory.IMAGES,
        "jpeg": FileTypeCategory.IMAGES,
        "png": FileTypeCategory.IMAGES,
        "gif": FileTypeCategory.IMAGES,
        "webp": FileTypeCategory.IMAGES,
        "svg": FileTypeCategory.IMAGES,
        "bmp": FileTypeCategory.IMAGES,
        "tiff": FileTypeCategory.IMAGES,
        "tif": FileTypeCategory.IMAGES,

        # Audio
        "mp3": FileTypeCategory.AUDIO,
        "wav": FileTypeCategory.AUDIO,
        "ogg": FileTypeCategory.AUDIO,
        "m4a": FileTypeCategory.AUDIO,
        "flac": FileTypeCategory.AUDIO,
        "aac": FileTypeCategory.AUDIO,

        # Video
        "mp4": FileTypeCategory.VIDEO,
        "webm": FileTypeCategory.VIDEO,
        "ogv": FileTypeCategory.VIDEO,
        "mov": FileTypeCategory.VIDEO,
        "avi": FileTypeCategory.VIDEO,

        # Documents
        "pdf": FileTypeCategory.DOCUMENTS,
        "txt": FileTypeCategory.DOCUMENTS,
        "md": FileTypeCategory.DOCUMENTS,
        "doc": FileTypeCategory.DOCUMENTS,
        "docx": FileTypeCategory.DOCUMENTS,
        "xls": FileTypeCategory.DOCUMENTS,
        "xlsx": FileTypeCategory.DOCUMENTS,
        "ppt": FileTypeCategory.DOCUMENTS,
        "pptx": FileTypeCategory.DOCUMENTS,

        # Archives
        "zip": FileTypeCategory.ARCHIVES,
        "tar": FileTypeCategory.ARCHIVES,
        "gz": FileTypeCategory.ARCHIVES,
        "7z": FileTypeCategory.ARCHIVES,
    }

    # Expected MIME types for each category
    CATEGORY_MIME_TYPES = {
        FileTypeCategory.IMAGES: [
            "image/jpeg",
            "image/png",
            "image/gif",
            "image/webp",
            "image/svg+xml",
            "image/bmp",
            "image/tiff",
        ],
        FileTypeCategory.AUDIO: [
            "audio/mpeg",
            "audio/wav",
            "audio/ogg",
            "audio/mp4",
            "audio/flac",
            "audio/aac",
        ],
        FileTypeCategory.VIDEO: [
            "video/mp4",
            "video/webm",
            "video/ogg",
            "video/quicktime",
            "video/x-msvideo",
        ],
        FileTypeCategory.DOCUMENTS: [
            "application/pdf",
            "text/plain",
            "text/markdown",
            "application/msword",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "application/vnd.ms-excel",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "application/vnd.ms-powerpoint",
            "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        ],
        FileTypeCategory.ARCHIVES: [
            "application/zip",
            "application/x-tar",
            "application/gzip",
            "application/x-7z-compressed",
        ],
    }

    # Magic number signatures (file headers) for validation
    MAGIC_SIGNATURES = {
        "jpg": [b"\xFF\xD8\xFF"],
        "png": [b"\x89PNG\r\n\x1a\n"],
        "gif": [b"GIF87a", b"GIF89a"],
        "webp": [b"RIFF"],  # Also check for "WEBP" at offset 8
        "pdf": [b"%PDF-"],
        "zip": [b"PK\x03\x04", b"PK\x05\x06", b"PK\x07\x08"],
        "mp3": [b"\xFF\xFB", b"\xFF\xF3", b"\xFF\xF2", b"ID3"],
        "mp4": [b"\x00\x00\x00\x18ftyp", b"\x00\x00\x00\x1cftyp"],
    }

    def __init__(self, config: Any):
        """
        Initialize file validator.

        Args:
            config: Configuration object with file_storage settings
        """
        self.config = config
        self.magic_detector = None

        # Initialize python-magic if available and enabled
        file_storage = getattr(config, 'file_storage', None)
        validation = getattr(
            file_storage,
            'validation',
            None) if file_storage else None
        magic_check = getattr(validation, 'magic_number_check', False)

        if HAS_MAGIC and magic_check:
            try:
                self.magic_detector = magic.Magic(mime=True)
            except Exception:
                # Fall back to basic checks if magic initialization fails
                self.magic_detector = None

    def validate_upload(
        self,
        file_data: BinaryIO,
        filename: str,
        uploader_role: str,
    ) -> tuple[bool, str | None, dict[str, Any]]:
        """
        Validate a file upload with multi-layer security checks.

        Args:
            file_data: File binary data stream
            filename: Original filename
            uploader_role: Role of uploader (admin, creator, user)

        Returns:
            Tuple of (is_valid, error_message, metadata)
            - is_valid: True if file passes all validation
            - error_message: None if valid, error description if invalid
            - metadata: Dict with file metadata (category, size, mime_type, checksum)

        Raises:
            ValidationError: If validation fails critically
        """
        metadata = {}

        try:
            # 1. Validate filename safety
            if not self._is_filename_safe(filename):
                return False, "Filename contains invalid characters or path traversal attempt", metadata

            # 2. Get file category from extension
            category = self._get_file_category(filename)
            if category is None:
                return False, f"File extension not recognized or not allowed", metadata

            metadata["category"] = category.value

            # 3. Check if category is enabled
            if not self._is_category_enabled(category):
                return False, f"File type '{
                    category.value}' is not allowed by configuration", metadata

            # 4. Check file extension against allowed list
            ext = Path(filename).suffix.lower().lstrip('.')
            if not self._is_extension_allowed(category, ext):
                return False, f"File extension '.{ext}' is not allowed for {
                    category.value}", metadata

            metadata["extension"] = ext

            # 5. Check file size
            file_data.seek(0, os.SEEK_END)
            size_bytes = file_data.tell()
            file_data.seek(0)

            metadata["size_bytes"] = size_bytes

            max_size = self._get_max_size(category)
            if size_bytes > max_size:
                size_mb = size_bytes / (1024 * 1024)
                max_mb = max_size / (1024 * 1024)
                return False, f"File too large ({
                    size_mb:.2f} MB, max {
                    max_mb:.2f} MB)", metadata

            # 6. Verify MIME type
            mime_type = None
            file_storage = getattr(self.config, 'file_storage', None)
            validation = getattr(
                file_storage,
                'validation',
                None) if file_storage else None
            mime_validation = getattr(validation, 'mime_type_validation', True)

            if mime_validation:
                mime_type = self._detect_mime_type(file_data, filename)
                metadata["mime_type"] = mime_type

                if not self._is_mime_type_allowed(category, mime_type):
                    return False, f"MIME type '{mime_type}' not allowed for {
                        category.value}", metadata

            # 7. Check magic numbers (file header)
            magic_check = getattr(
                validation,
                'magic_number_check',
                False) if validation else False

            if magic_check:
                if not self._verify_magic_number(file_data, ext):
                    return False, "File content does not match declared file type (magic number mismatch)", metadata

            # 8. Special security checks per category

            # SVG - XSS risk
            if category == FileTypeCategory.IMAGES and ext == "svg":
                file_storage = getattr(self.config, 'file_storage', None)
                allowed_types = getattr(
                    file_storage,
                    'allowed_types',
                    None) if file_storage else None
                images_config = getattr(
                    allowed_types, 'images', None) if allowed_types else None
                allow_svg = getattr(images_config, 'allow_svg', False)

                if not allow_svg:
                    return False, "SVG files are disabled (XSS/script injection risk)", metadata

            # Office documents - macro risk
            if category == FileTypeCategory.DOCUMENTS:
                if ext in ["doc", "docx", "xls", "xlsx", "ppt", "pptx"]:
                    file_storage = getattr(self.config, 'file_storage', None)
                    allowed_types = getattr(
                        file_storage, 'allowed_types', None) if file_storage else None
                    docs_config = getattr(
                        allowed_types, 'documents', None) if allowed_types else None
                    allow_macros = getattr(
                        docs_config, 'allow_office_macros', False)

                    if not allow_macros:
                        # We can't reliably detect macros without oletools library
                        # For now, block all Office files if macros disabled
                        return False, "Office documents are disabled (macro/malware risk)", metadata

            # Archives - zip bomb, path traversal risk
            if category == FileTypeCategory.ARCHIVES:
                is_safe, error = self._is_archive_safe(file_data, ext)
                if not is_safe:
                    return False, f"Archive failed safety checks: {error}", metadata

            # 9. Calculate checksum if enabled
            file_storage = getattr(self.config, 'file_storage', None)
            validation = getattr(
                file_storage,
                'validation',
                None) if file_storage else None
            calc_checksum = getattr(validation, 'calculate_checksum', False)

            if calc_checksum:
                checksum = self.calculate_checksum(file_data)
                metadata["checksum"] = checksum

            # 10. Extract image dimensions if applicable
            if category == FileTypeCategory.IMAGES:
                width, height = self._extract_image_dimensions(file_data)
                if width and height:
                    metadata["image_width"] = width
                    metadata["image_height"] = height

            # All checks passed
            return True, None, metadata

        except Exception as e:
            return False, f"Validation error: {str(e)}", metadata

    def _is_filename_safe(self, filename: str) -> bool:
        """
        Check if filename is safe (no path traversal, special chars).

        Args:
            filename: Original filename

        Returns:
            True if filename is safe
        """
        # Check length
        file_storage = getattr(self.config, 'file_storage', None)
        validation = getattr(
            file_storage,
            'validation',
            None) if file_storage else None
        max_length = getattr(validation, 'max_filename_length', 255)

        if len(filename) > max_length:
            return False

        # Check for path traversal
        if ".." in filename or "/" in filename or "\\" in filename:
            return False

        # Check for null bytes
        if "\x00" in filename:
            return False

        # Check allowed characters (alphanumeric, dots, dashes, underscores, spaces)
        # Pattern allows: a-z, A-Z, 0-9, -, _, ., space
        allowed_pattern = r'^[a-zA-Z0-9\-_.() ]+$'
        if not re.match(allowed_pattern, filename):
            return False

        return True

    def _get_file_category(self, filename: str) -> FileTypeCategory | None:
        """
        Determine file category from extension.

        Args:
            filename: Filename with extension

        Returns:
            FileTypeCategory or None if unknown
        """
        ext = Path(filename).suffix.lower().lstrip('.')

        # Handle compound extensions (e.g., tar.gz)
        if filename.lower().endswith(".tar.gz"):
            ext = "gz"

        return self.EXTENSION_CATEGORIES.get(ext)

    def _is_category_enabled(self, category: FileTypeCategory) -> bool:
        """
        Check if file category is enabled in configuration.

        Args:
            category: File category

        Returns:
            True if category is enabled
        """
        file_storage = getattr(self.config, 'file_storage', None)
        if not file_storage:
            return True  # Default to enabled if no config

        enabled = getattr(file_storage, 'enabled', True)
        if not enabled:
            return False

        allowed_types = getattr(file_storage, 'allowed_types', None)
        if not allowed_types:
            return True  # Default to enabled if no allowed_types config

        category_config = getattr(allowed_types, category.value, None)
        if not category_config:
            return True  # Default to enabled if no category config

        return getattr(category_config, 'enabled', True)

    def _is_extension_allowed(
            self,
            category: FileTypeCategory,
            ext: str) -> bool:
        """
        Check if specific extension is allowed for category.

        Args:
            category: File category
            ext: File extension (without dot)

        Returns:
            True if extension is allowed
        """
        file_storage = getattr(self.config, 'file_storage', None)
        allowed_types = getattr(
            file_storage,
            'allowed_types',
            None) if file_storage else None
        category_config = getattr(
            allowed_types,
            category.value,
            None) if allowed_types else None

        # Default allowed formats per category
        default_formats = {
            FileTypeCategory.IMAGES: ["jpg", "jpeg", "png", "gif", "webp"],
            FileTypeCategory.AUDIO: ["mp3", "wav", "ogg"],
            FileTypeCategory.VIDEO: ["mp4", "webm"],
            FileTypeCategory.DOCUMENTS: ["pdf", "txt"],
            FileTypeCategory.ARCHIVES: ["zip"],
        }

        allowed_formats = getattr(
            category_config,
            'formats',
            default_formats.get(
                category,
                []))

        # Handle compound extensions
        if ext == "gz":
            # Allow .tar.gz if both tar and gz are in formats
            return "tar.gz" in allowed_formats or "gz" in allowed_formats

        return ext in allowed_formats

    def _get_max_size(self, category: FileTypeCategory) -> int:
        """
        Get maximum file size in bytes for category.

        Args:
            category: File category

        Returns:
            Maximum size in bytes
        """
        file_storage = getattr(self.config, 'file_storage', None)
        allowed_types = getattr(
            file_storage,
            'allowed_types',
            None) if file_storage else None
        category_config = getattr(
            allowed_types,
            category.value,
            None) if allowed_types else None

        # Default max sizes per category (in MB)
        default_sizes = {
            FileTypeCategory.IMAGES: 10,
            FileTypeCategory.AUDIO: 50,
            FileTypeCategory.VIDEO: 100,
            FileTypeCategory.DOCUMENTS: 20,
            FileTypeCategory.ARCHIVES: 50,
        }

        max_size_mb = getattr(
            category_config,
            'max_size_mb',
            default_sizes.get(
                category,
                10))
        return max_size_mb * 1024 * 1024  # Convert to bytes

    def _detect_mime_type(self, file_data: BinaryIO, filename: str) -> str:
        """
        Detect MIME type using magic numbers or filename.

        Args:
            file_data: File binary data
            filename: Filename for fallback detection

        Returns:
            MIME type string
        """
        mime_type = "application/octet-stream"  # Default

        # Try python-magic first (most reliable)
        if self.magic_detector:
            try:
                file_data.seek(0)
                # Read first chunk for magic detection
                chunk = file_data.read(8192)
                file_data.seek(0)

                mime_type = self.magic_detector.from_buffer(chunk)
            except Exception:
                pass

        # Fallback to mimetypes based on filename
        if mime_type == "application/octet-stream":
            guessed_type, _ = mimetypes.guess_type(filename)
            if guessed_type:
                mime_type = guessed_type

        return mime_type

    def _is_mime_type_allowed(
            self,
            category: FileTypeCategory,
            mime_type: str) -> bool:
        """
        Check if MIME type is allowed for category.

        Args:
            category: File category
            mime_type: Detected MIME type

        Returns:
            True if MIME type is allowed
        """
        allowed_types = self.CATEGORY_MIME_TYPES.get(category, [])

        # Exact match
        if mime_type in allowed_types:
            return True

        # Prefix match (e.g., "image/*")
        category_prefix = category.value.rstrip('s')  # "images" -> "image"
        if mime_type.startswith(f"{category_prefix}/"):
            return True

        return False

    def _verify_magic_number(self, file_data: BinaryIO, ext: str) -> bool:
        """
        Verify file magic number (header) matches extension.

        Args:
            file_data: File binary data
            ext: File extension

        Returns:
            True if magic number matches or no signature defined
        """
        signatures = self.MAGIC_SIGNATURES.get(ext)
        if not signatures:
            # No signature defined, pass check
            return True

        file_data.seek(0)
        header = file_data.read(32)  # Read first 32 bytes
        file_data.seek(0)

        # Check if any signature matches
        for sig in signatures:
            if header.startswith(sig):
                return True

            # Special case for WebP (check "WEBP" at offset 8)
            if ext == "webp" and len(header) >= 12:
                if header[8:12] == b"WEBP":
                    return True

        return False

    def _is_archive_safe(self, file_data: BinaryIO,
                         ext: str) -> tuple[bool, str | None]:
        """
        Check if archive is safe (no zip bombs, path traversal).

        Args:
            file_data: File binary data
            ext: File extension

        Returns:
            Tuple of (is_safe, error_message)
        """
        # Only check ZIP files for now (most common)
        if ext != "zip":
            return True, None

        try:
            file_data.seek(0)

            # Check if it's a valid ZIP file
            if not zipfile.is_zipfile(file_data):
                return False, "Invalid ZIP file"

            file_data.seek(0)

            with zipfile.ZipFile(file_data, 'r') as zf:
                # Check for zip bomb (decompression ratio)
                compressed_size = sum(
                    info.compress_size for info in zf.infolist())
                uncompressed_size = sum(
                    info.file_size for info in zf.infolist())

                file_storage = getattr(self.config, 'file_storage', None)
                allowed_types = getattr(
                    file_storage,
                    'allowed_types',
                    None) if file_storage else None
                archives_config = getattr(
                    allowed_types, 'archives', None) if allowed_types else None
                max_decompressed_mb = getattr(
                    archives_config, 'max_decompressed_size_mb', 100)

                max_decompressed_bytes = max_decompressed_mb * 1024 * 1024

                if uncompressed_size > max_decompressed_bytes:
                    return False, f"Archive too large when decompressed ({
                        uncompressed_size / (
                            1024 * 1024):.1f} MB, max {max_decompressed_mb} MB)"

                # Check decompression ratio (warn if > 100:1)
                if compressed_size > 0:
                    ratio = uncompressed_size / compressed_size
                    if ratio > 100:
                        return False, f"Suspicious compression ratio ({
                            ratio:.1f}:1, possible zip bomb)"

                # Check for path traversal in filenames
                for info in zf.infolist():
                    # Normalize path and check for ..
                    normalized = os.path.normpath(info.filename)
                    if normalized.startswith(
                            "..") or os.path.isabs(normalized):
                        return False, f"Archive contains unsafe path: {
                            info.filename}"

            file_data.seek(0)
            return True, None

        except zipfile.BadZipFile:
            return False, "Corrupted ZIP file"
        except Exception as e:
            return False, f"Archive validation error: {str(e)}"

    def calculate_checksum(self, file_data: BinaryIO) -> str:
        """
        Calculate file checksum using configured algorithm.

        Args:
            file_data: File binary data

        Returns:
            Checksum string in format "algorithm:hexdigest"
        """
        file_storage = getattr(self.config, 'file_storage', None)
        validation = getattr(
            file_storage,
            'validation',
            None) if file_storage else None
        algo = getattr(validation, 'checksum_algorithm', 'sha256')

        try:
            h = hashlib.new(algo)
        except ValueError:
            # Fall back to sha256 if algorithm not supported
            algo = "sha256"
            h = hashlib.sha256()

        file_data.seek(0)
        for chunk in iter(lambda: file_data.read(8192), b''):
            h.update(chunk)
        file_data.seek(0)

        return f"{algo}:{h.hexdigest()}"

    def _extract_image_dimensions(
            self, file_data: BinaryIO) -> tuple[int | None, int | None]:
        """
        Extract image dimensions using PIL.

        Args:
            file_data: File binary data

        Returns:
            Tuple of (width, height) or (None, None) if extraction fails
        """
        if not HAS_PIL:
            return None, None

        try:
            file_data.seek(0)
            with Image.open(file_data) as img:
                width, height = img.size
            file_data.seek(0)
            return width, height
        except Exception:
            file_data.seek(0)
            return None, None

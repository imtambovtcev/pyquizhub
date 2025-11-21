"""Tests for FileValidator with security checks."""

from __future__ import annotations

import io
import pytest
from unittest.mock import Mock

from pyquizhub.core.storage.file.validator import FileValidator, FileTypeCategory, ValidationError


@pytest.fixture
def mock_config():
    """Create mock configuration for testing."""
    config = Mock()

    # File storage enabled
    config.file_storage.enabled = True

    # Upload permissions
    config.file_storage.upload.quiz_attachments.enabled = True
    config.file_storage.upload.quiz_attachments.allow_admin = True
    config.file_storage.upload.quiz_attachments.allow_creator = True

    config.file_storage.upload.user_answers.enabled = False
    config.file_storage.upload.user_answers.allow_user = False

    # Image settings
    config.file_storage.allowed_types.images.enabled = True
    config.file_storage.allowed_types.images.formats = ["jpg", "jpeg", "png", "gif", "webp", "svg"]
    config.file_storage.allowed_types.images.max_size_mb = 10
    config.file_storage.allowed_types.images.allow_svg = False

    # Audio settings
    config.file_storage.allowed_types.audio.enabled = True
    config.file_storage.allowed_types.audio.formats = ["mp3", "wav", "ogg"]
    config.file_storage.allowed_types.audio.max_size_mb = 50

    # Video settings
    config.file_storage.allowed_types.video.enabled = True
    config.file_storage.allowed_types.video.formats = ["mp4", "webm", "ogv"]
    config.file_storage.allowed_types.video.max_size_mb = 100

    # Documents settings
    config.file_storage.allowed_types.documents.enabled = True
    config.file_storage.allowed_types.documents.formats = ["pdf", "txt", "md"]
    config.file_storage.allowed_types.documents.max_size_mb = 20
    config.file_storage.allowed_types.documents.allow_office_macros = False

    # Archives settings
    config.file_storage.allowed_types.archives.enabled = True
    config.file_storage.allowed_types.archives.formats = ["zip"]
    config.file_storage.allowed_types.archives.max_size_mb = 50
    config.file_storage.allowed_types.archives.max_decompressed_size_mb = 500

    # Validation settings
    config.file_storage.validation.mime_type_validation = True
    config.file_storage.validation.magic_number_check = False  # Disable magic for tests
    config.file_storage.validation.calculate_checksum = True
    config.file_storage.validation.checksum_algorithm = "sha256"
    config.file_storage.validation.max_filename_length = 255

    return config


def test_validate_filename_safe(mock_config):
    """Test safe filename validation."""
    validator = FileValidator(mock_config)

    # Valid filenames
    assert validator._is_filename_safe("test.jpg")
    assert validator._is_filename_safe("my_file-123.png")
    assert validator._is_filename_safe("document (1).pdf")
    assert validator._is_filename_safe("file with spaces.txt")

    # Invalid filenames
    assert not validator._is_filename_safe("../etc/passwd")  # Path traversal
    assert not validator._is_filename_safe("test/../file.jpg")  # Path traversal
    assert not validator._is_filename_safe("file/test.jpg")  # Directory separator
    assert not validator._is_filename_safe("test\x00.jpg")  # Null byte
    assert not validator._is_filename_safe("a" * 300)  # Too long


def test_get_file_category(mock_config):
    """Test file category detection."""
    validator = FileValidator(mock_config)

    # Images
    assert validator._get_file_category("photo.jpg") == FileTypeCategory.IMAGES
    assert validator._get_file_category("image.PNG") == FileTypeCategory.IMAGES
    assert validator._get_file_category("logo.svg") == FileTypeCategory.IMAGES

    # Audio
    assert validator._get_file_category("song.mp3") == FileTypeCategory.AUDIO
    assert validator._get_file_category("sound.WAV") == FileTypeCategory.AUDIO

    # Video
    assert validator._get_file_category("movie.mp4") == FileTypeCategory.VIDEO
    assert validator._get_file_category("clip.WEBM") == FileTypeCategory.VIDEO

    # Documents
    assert validator._get_file_category("document.pdf") == FileTypeCategory.DOCUMENTS
    assert validator._get_file_category("readme.txt") == FileTypeCategory.DOCUMENTS

    # Archives
    assert validator._get_file_category("archive.zip") == FileTypeCategory.ARCHIVES
    assert validator._get_file_category("backup.tar.gz") == FileTypeCategory.ARCHIVES

    # Unknown
    assert validator._get_file_category("unknown.xyz") is None


def test_validate_file_size(mock_config):
    """Test file size validation."""
    validator = FileValidator(mock_config)

    # Small image - should pass
    small_data = b"x" * 1024  # 1 KB
    file_data = io.BytesIO(small_data)
    is_valid, error, metadata = validator.validate_upload(file_data, "test.jpg", "admin")

    assert is_valid
    assert error is None
    assert metadata["size_bytes"] == 1024

    # Large image - should fail (max 10 MB for images)
    large_data = b"x" * (11 * 1024 * 1024)  # 11 MB
    file_data = io.BytesIO(large_data)
    is_valid, error, metadata = validator.validate_upload(file_data, "large.jpg", "admin")

    assert not is_valid
    assert "too large" in error.lower()


def test_validate_svg_security(mock_config):
    """Test SVG security check (XSS risk)."""
    validator = FileValidator(mock_config)

    # SVG disabled by default
    svg_data = b'<svg></svg>'
    file_data = io.BytesIO(svg_data)
    is_valid, error, metadata = validator.validate_upload(file_data, "image.svg", "admin")

    assert not is_valid
    assert "svg" in error.lower()
    assert "xss" in error.lower() or "disabled" in error.lower()

    # Enable SVG
    mock_config.file_storage.allowed_types.images.allow_svg = True
    is_valid, error, metadata = validator.validate_upload(file_data, "image.svg", "admin")

    assert is_valid or "mime" in error.lower()  # May fail MIME check


def test_validate_category_disabled(mock_config):
    """Test validation when category is disabled."""
    validator = FileValidator(mock_config)

    # Disable images
    mock_config.file_storage.allowed_types.images.enabled = False

    jpg_data = b"\xFF\xD8\xFF"  # JPEG header
    file_data = io.BytesIO(jpg_data)
    is_valid, error, metadata = validator.validate_upload(file_data, "test.jpg", "admin")

    assert not is_valid
    assert "not allowed" in error.lower() or "disabled" in error.lower()


def test_validate_extension_not_in_formats(mock_config):
    """Test validation when extension not in allowed formats."""
    validator = FileValidator(mock_config)

    # BMP not in allowed formats
    bmp_data = b"BM"  # BMP header
    file_data = io.BytesIO(bmp_data)
    is_valid, error, metadata = validator.validate_upload(file_data, "image.bmp", "admin")

    assert not is_valid
    assert "not allowed" in error.lower()


def test_calculate_checksum(mock_config):
    """Test checksum calculation."""
    validator = FileValidator(mock_config)

    data = b"test file content"
    file_data = io.BytesIO(data)

    checksum = validator.calculate_checksum(file_data)

    assert checksum.startswith("sha256:")
    assert len(checksum) > 10  # sha256: + hex digest


def test_validate_archive_safe(mock_config):
    """Test archive safety checks (basic)."""
    validator = FileValidator(mock_config)

    # Not a ZIP file
    fake_zip = b"not a zip file"
    file_data = io.BytesIO(fake_zip)
    is_safe, error = validator._is_archive_safe(file_data, "zip")

    assert not is_safe
    assert "invalid" in error.lower() or "zip" in error.lower()


def test_validate_path_traversal_in_filename(mock_config):
    """Test path traversal prevention."""
    validator = FileValidator(mock_config)

    malicious_names = [
        "../../../etc/passwd",
        "..\\..\\windows\\system32\\config",
        "test/../../secret.txt",
        "./../file.jpg",
    ]

    for name in malicious_names:
        jpg_data = b"\xFF\xD8\xFF"
        file_data = io.BytesIO(jpg_data)
        is_valid, error, metadata = validator.validate_upload(file_data, name, "admin")

        assert not is_valid
        assert "filename" in error.lower() or "invalid" in error.lower()


def test_validate_multiple_extensions(mock_config):
    """Test handling of multiple extensions (e.g., .tar.gz)."""
    validator = FileValidator(mock_config)

    # .tar.gz should be recognized as archive
    category = validator._get_file_category("backup.tar.gz")
    assert category == FileTypeCategory.ARCHIVES


def test_validate_case_insensitive_extension(mock_config):
    """Test case-insensitive extension handling."""
    validator = FileValidator(mock_config)

    # Uppercase extensions should work
    category = validator._get_file_category("IMAGE.JPG")
    assert category == FileTypeCategory.IMAGES

    category = validator._get_file_category("document.PDF")
    assert category == FileTypeCategory.DOCUMENTS

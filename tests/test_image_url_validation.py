"""
Tests for image URL validation and safety.

This module tests:
1. ImageURLValidator validates image URLs correctly
2. SSRF protection works for image URLs
3. Image extension validation
4. Content-Type verification (mocked)
5. Variable placeholder detection and extraction
"""

import pytest
from pyquizhub.core.engine.url_validator import (
    ImageURLValidator,
    URLValidator,
    ALLOWED_IMAGE_EXTENSIONS,
    ALLOWED_IMAGE_MIME_TYPES
)


class TestImageURLExtensionValidation:
    """Test image extension validation."""

    def test_valid_image_extensions(self):
        """Test URLs with valid image extensions pass validation."""
        valid_urls = [
            "https://example.com/image.jpg",
            "https://example.com/image.jpeg",
            "https://example.com/image.png",
            "https://example.com/image.gif",
            "https://example.com/image.webp",
            "https://example.com/image.svg",
            "https://example.com/image.bmp",
            "https://example.com/image.ico",
            "https://example.com/path/to/image.PNG",  # Case insensitive
        ]

        for url in valid_urls:
            # Should not raise exception
            ImageURLValidator.validate_image_extension(url)

    def test_invalid_image_extensions(self):
        """Test URLs without image extensions fail validation."""
        invalid_urls = [
            "https://example.com/document.pdf",
            "https://example.com/video.mp4",
            "https://example.com/script.js",
            "https://example.com/style.css",
            "https://example.com/data.json",
        ]

        for url in invalid_urls:
            with pytest.raises(ValueError, match="must have image extension"):
                ImageURLValidator.validate_image_extension(url)

    def test_cdn_urls_with_query_params(self):
        """Test CDN URLs with image format in query params."""
        cdn_urls = [
            "https://cdn.example.com/image?format=png",
            "https://cloudinary.com/image/upload/img?format=jpeg",
            "https://imgix.net/photo?fm=webp",
        ]

        for url in cdn_urls:
            # Should pass - has image format in query params
            ImageURLValidator.validate_image_extension(url)


class TestSSRFProtectionForImages:
    """Test SSRF protection for image URLs."""

    def test_rejects_localhost(self):
        """Test image validator rejects localhost URLs."""
        localhost_urls = [
            "http://localhost/image.png",
            "http://127.0.0.1/image.jpg",
            "http://[::1]/image.png",
        ]

        for url in localhost_urls:
            with pytest.raises(ValueError):
                ImageURLValidator.validate_image_url(url, allow_http=True)

    def test_rejects_private_ips(self):
        """Test image validator rejects private IP addresses."""
        private_urls = [
            "http://192.168.1.1/image.png",
            "http://10.0.0.1/image.jpg",
            "http://172.16.0.1/image.png",
        ]

        for url in private_urls:
            with pytest.raises(ValueError):
                ImageURLValidator.validate_image_url(url, allow_http=True)

    def test_rejects_internal_domains(self):
        """Test image validator rejects internal domain TLDs."""
        internal_urls = [
            "https://server.local/image.png",
            "https://app.internal/image.jpg",
            "https://admin.corp/image.png",
        ]

        for url in internal_urls:
            with pytest.raises(ValueError):
                ImageURLValidator.validate_image_url(url)

    def test_accepts_public_domains(self):
        """Test image validator accepts public domain URLs."""
        public_urls = [
            "https://example.com/image.png",
            "https://cdn.example.org/photo.jpg",
            "https://images.example.net/picture.webp",
        ]

        for url in public_urls:
            # Should not raise exception (extension and SSRF checks pass)
            ImageURLValidator.validate_image_url(url, verify_content=False)


class TestImageURLFormat:
    """Test comprehensive image URL validation."""

    def test_https_only_by_default(self):
        """Test HTTPS required by default."""
        http_url = "http://example.com/image.png"

        with pytest.raises(ValueError, match="HTTPS"):
            ImageURLValidator.validate_image_url(http_url)

    def test_allows_http_when_specified(self):
        """Test HTTP allowed when explicitly enabled."""
        http_url = "http://example.com/image.png"

        # Should not raise exception
        ImageURLValidator.validate_image_url(
            http_url,
            allow_http=True,
            verify_content=False
        )

    def test_requires_hostname(self):
        """Test URL must have hostname."""
        invalid_urls = [
            "file:///path/to/image.png",
            "/path/to/image.png",
            "image.png",
        ]

        for url in invalid_urls:
            with pytest.raises(ValueError):
                ImageURLValidator.validate_image_url(url, allow_http=True)

    def test_rejects_embedded_credentials(self):
        """Test URLs with embedded credentials are rejected."""
        urls_with_creds = [
            "https://user:pass@example.com/image.png",
            "https://admin@example.com/image.jpg",
        ]

        for url in urls_with_creds:
            with pytest.raises(ValueError):
                ImageURLValidator.validate_image_url(url)


class TestVariablePlaceholderDetection:
    """Test variable placeholder detection in image URLs."""

    def test_has_variable_placeholders(self):
        """Test detection of variable placeholders in URLs."""
        urls_with_vars = [
            "https://example.com/{variables.image_id}.png",
            "https://cdn.example.com/image?format={variables.format}",
            "https://example.com/{api.dog_api.message}",
            "https://example.com/{variables.category}/{variables.id}.jpg",
        ]

        for url in urls_with_vars:
            assert ImageURLValidator.has_variable_placeholders(url)

    def test_no_variable_placeholders(self):
        """Test URLs without variable placeholders."""
        urls_without_vars = [
            "https://example.com/image.png",
            "https://example.com/path/to/image.jpg",
            "https://example.com/image?id=123",
        ]

        for url in urls_without_vars:
            assert not ImageURLValidator.has_variable_placeholders(url)

    def test_extract_variable_names(self):
        """Test extraction of variable names from URL templates."""
        test_cases = [
            (
                "https://example.com/{variables.image_id}.png",
                ["variables.image_id"]
            ),
            (
                "https://cdn.example.com/{variables.category}/{variables.id}.jpg",
                ["variables.category", "variables.id"]
            ),
            (
                "https://example.com/{api.dog_api.message}",
                ["api.dog_api.message"]
            ),
            (
                "https://example.com/image.png",
                []
            ),
        ]

        for url, expected_vars in test_cases:
            actual_vars = ImageURLValidator.extract_variable_names(url)
            assert actual_vars == expected_vars


class TestEdgeCases:
    """Test edge cases in image URL validation."""

    def test_empty_url(self):
        """Test empty URL is rejected."""
        with pytest.raises(ValueError):
            ImageURLValidator.validate_image_url("")

    def test_none_url(self):
        """Test None URL is rejected."""
        with pytest.raises((ValueError, AttributeError)):
            ImageURLValidator.validate_image_url(None)

    def test_url_too_long(self):
        """Test excessively long URL is rejected."""
        long_url = "https://example.com/" + "a" * 3000 + ".png"

        with pytest.raises(ValueError, match="too long"):
            ImageURLValidator.validate_image_url(long_url)

    def test_mixed_case_extension(self):
        """Test mixed case extensions are handled."""
        urls = [
            "https://example.com/image.PNG",
            "https://example.com/image.JpEg",
            "https://example.com/image.WebP",
        ]

        for url in urls:
            # Should not raise exception
            ImageURLValidator.validate_image_extension(url)

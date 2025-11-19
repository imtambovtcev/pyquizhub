"""
Tests for image URL content verification with HTTP mocking.

This module tests the verify_image_content functionality by mocking
HTTP requests to check Content-Type headers and file sizes.
"""

import pytest
from unittest.mock import Mock, patch
from pyquizhub.core.engine.url_validator import ImageURLValidator


class TestImageContentVerification:
    """Test image content verification with mocked HTTP requests."""

    @patch('pyquizhub.core.engine.url_validator.requests.head')
    def test_verify_valid_png_image(self, mock_head):
        """Test successful verification of PNG image."""
        # Mock successful response with PNG content type
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {
            'Content-Type': 'image/png',
            'Content-Length': '1048576'  # 1 MB
        }
        mock_head.return_value = mock_response

        # Should not raise exception
        result = ImageURLValidator.verify_image_content('https://example.com/image.png')
        assert result is True

        # Verify HEAD request was made with correct parameters
        mock_head.assert_called_once()
        args, kwargs = mock_head.call_args
        assert args[0] == 'https://example.com/image.png'
        assert kwargs['timeout'] == 5
        assert kwargs['allow_redirects'] is True

    @patch('pyquizhub.core.engine.url_validator.requests.head')
    def test_verify_valid_jpeg_image(self, mock_head):
        """Test successful verification of JPEG image."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {
            'Content-Type': 'image/jpeg',
            'Content-Length': '524288'  # 512 KB
        }
        mock_head.return_value = mock_response

        result = ImageURLValidator.verify_image_content('https://example.com/photo.jpg')
        assert result is True

    @patch('pyquizhub.core.engine.url_validator.requests.head')
    def test_verify_webp_image(self, mock_head):
        """Test successful verification of WebP image."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {
            'Content-Type': 'image/webp',
            'Content-Length': '409600'  # 400 KB
        }
        mock_head.return_value = mock_response

        result = ImageURLValidator.verify_image_content('https://example.com/image.webp')
        assert result is True

    @patch('pyquizhub.core.engine.url_validator.requests.head')
    def test_verify_svg_image(self, mock_head):
        """Test successful verification of SVG image."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {
            'Content-Type': 'image/svg+xml',
            'Content-Length': '2048'
        }
        mock_head.return_value = mock_response

        result = ImageURLValidator.verify_image_content('https://example.com/icon.svg')
        assert result is True

    @patch('pyquizhub.core.engine.url_validator.requests.head')
    def test_verify_content_type_with_charset(self, mock_head):
        """Test Content-Type parsing when charset is included."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {
            'Content-Type': 'image/png; charset=utf-8',
            'Content-Length': '1024'
        }
        mock_head.return_value = mock_response

        # Should parse out charset and accept image/png
        result = ImageURLValidator.verify_image_content('https://example.com/image.png')
        assert result is True

    @patch('pyquizhub.core.engine.url_validator.requests.head')
    def test_reject_non_image_content_type(self, mock_head):
        """Test rejection when Content-Type is not an image."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {
            'Content-Type': 'text/html',
            'Content-Length': '1024'
        }
        mock_head.return_value = mock_response

        with pytest.raises(ValueError, match="does not point to image"):
            ImageURLValidator.verify_image_content('https://example.com/page.html')

    @patch('pyquizhub.core.engine.url_validator.requests.head')
    def test_reject_pdf_content_type(self, mock_head):
        """Test rejection when Content-Type is PDF."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {
            'Content-Type': 'application/pdf',
            'Content-Length': '1024'
        }
        mock_head.return_value = mock_response

        with pytest.raises(ValueError, match="does not point to image"):
            ImageURLValidator.verify_image_content('https://example.com/document.pdf')

    @patch('pyquizhub.core.engine.url_validator.requests.head')
    def test_reject_json_content_type(self, mock_head):
        """Test rejection when Content-Type is JSON."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {
            'Content-Type': 'application/json',
            'Content-Length': '512'
        }
        mock_head.return_value = mock_response

        with pytest.raises(ValueError, match="does not point to image"):
            ImageURLValidator.verify_image_content('https://example.com/data.json')

    @patch('pyquizhub.core.engine.url_validator.requests.head')
    def test_reject_image_too_large(self, mock_head):
        """Test rejection when image exceeds size limit."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {
            'Content-Type': 'image/png',
            'Content-Length': str(15 * 1024 * 1024)  # 15 MB (default max is 10 MB)
        }
        mock_head.return_value = mock_response

        with pytest.raises(ValueError, match="Image too large"):
            ImageURLValidator.verify_image_content('https://example.com/huge.png')

    @patch('pyquizhub.core.engine.url_validator.requests.head')
    def test_custom_size_limit(self, mock_head):
        """Test custom maximum file size limit."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {
            'Content-Type': 'image/jpeg',
            'Content-Length': str(3 * 1024 * 1024)  # 3 MB
        }
        mock_head.return_value = mock_response

        # 3 MB should be rejected with 2 MB limit
        with pytest.raises(ValueError, match="Image too large"):
            ImageURLValidator.verify_image_content(
                'https://example.com/large.jpg',
                max_size_mb=2.0
            )

    @patch('pyquizhub.core.engine.url_validator.requests.head')
    def test_accept_within_custom_size_limit(self, mock_head):
        """Test acceptance when within custom size limit."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {
            'Content-Type': 'image/jpeg',
            'Content-Length': str(3 * 1024 * 1024)  # 3 MB
        }
        mock_head.return_value = mock_response

        # 3 MB should be accepted with 5 MB limit
        result = ImageURLValidator.verify_image_content(
            'https://example.com/medium.jpg',
            max_size_mb=5.0
        )
        assert result is True

    @patch('pyquizhub.core.engine.url_validator.requests.head')
    def test_missing_content_length_header(self, mock_head):
        """Test that missing Content-Length header is tolerated."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {
            'Content-Type': 'image/png'
            # No Content-Length header
        }
        mock_head.return_value = mock_response

        # Should still pass (just can't check size)
        result = ImageURLValidator.verify_image_content('https://example.com/image.png')
        assert result is True

    @patch('pyquizhub.core.engine.url_validator.requests.head')
    def test_invalid_content_length_header(self, mock_head):
        """Test handling of invalid Content-Length header."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {
            'Content-Type': 'image/png',
            'Content-Length': 'invalid-number'
        }
        mock_head.return_value = mock_response

        # Should still pass (logs warning but doesn't fail)
        result = ImageURLValidator.verify_image_content('https://example.com/image.png')
        assert result is True

    @patch('pyquizhub.core.engine.url_validator.requests.head')
    def test_404_error_status(self, mock_head):
        """Test rejection when URL returns 404."""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.headers = {}
        mock_head.return_value = mock_response

        with pytest.raises(ValueError, match="returned error status: 404"):
            ImageURLValidator.verify_image_content('https://example.com/missing.png')

    @patch('pyquizhub.core.engine.url_validator.requests.head')
    def test_500_error_status(self, mock_head):
        """Test rejection when URL returns 500."""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.headers = {}
        mock_head.return_value = mock_response

        with pytest.raises(ValueError, match="returned error status: 500"):
            ImageURLValidator.verify_image_content('https://example.com/error.png')

    @patch('pyquizhub.core.engine.url_validator.requests.head')
    def test_timeout_exception(self, mock_head):
        """Test handling of request timeout."""
        import requests
        mock_head.side_effect = requests.exceptions.Timeout()

        with pytest.raises(ValueError, match="timed out after 5s"):
            ImageURLValidator.verify_image_content('https://example.com/slow.png')

    @patch('pyquizhub.core.engine.url_validator.requests.head')
    def test_custom_timeout(self, mock_head):
        """Test custom timeout parameter."""
        import requests
        mock_head.side_effect = requests.exceptions.Timeout()

        with pytest.raises(ValueError, match="timed out after 10s"):
            ImageURLValidator.verify_image_content(
                'https://example.com/slow.png',
                timeout=10
            )

    @patch('pyquizhub.core.engine.url_validator.requests.head')
    def test_connection_error(self, mock_head):
        """Test handling of connection error."""
        import requests
        mock_head.side_effect = requests.exceptions.ConnectionError()

        with pytest.raises(ValueError, match="Failed to connect"):
            ImageURLValidator.verify_image_content('https://unreachable.example.com/image.png')

    @patch('pyquizhub.core.engine.url_validator.requests.head')
    def test_request_exception(self, mock_head):
        """Test handling of generic request exception."""
        import requests
        mock_head.side_effect = requests.exceptions.RequestException("Network error")

        with pytest.raises(ValueError, match="Failed to verify image URL"):
            ImageURLValidator.verify_image_content('https://example.com/image.png')

    @patch('pyquizhub.core.engine.url_validator.requests.head')
    def test_redirects_followed(self, mock_head):
        """Test that redirects are followed."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {
            'Content-Type': 'image/jpeg',
            'Content-Length': '1024'
        }
        mock_head.return_value = mock_response

        ImageURLValidator.verify_image_content('https://example.com/redirect')

        # Verify allow_redirects was True
        args, kwargs = mock_head.call_args
        assert kwargs['allow_redirects'] is True

    @patch('pyquizhub.core.engine.url_validator.requests.head')
    def test_user_agent_header(self, mock_head):
        """Test that User-Agent header is set."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {
            'Content-Type': 'image/png',
            'Content-Length': '1024'
        }
        mock_head.return_value = mock_response

        ImageURLValidator.verify_image_content('https://example.com/image.png')

        # Verify User-Agent header was set
        args, kwargs = mock_head.call_args
        assert 'headers' in kwargs
        assert 'User-Agent' in kwargs['headers']
        assert 'PyQuizHub' in kwargs['headers']['User-Agent']


class TestValidateImageURLWithVerification:
    """Test the full validate_image_url with content verification enabled."""

    @patch('pyquizhub.core.engine.url_validator.requests.head')
    def test_full_validation_with_verification(self, mock_head):
        """Test complete validation flow with content verification."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {
            'Content-Type': 'image/png',
            'Content-Length': '1024'
        }
        mock_head.return_value = mock_response

        # Should pass all checks: URL format, SSRF, extension, and content
        ImageURLValidator.validate_image_url(
            'https://example.com/test.png',
            verify_content=True
        )

        # Verify HEAD request was made
        mock_head.assert_called_once()

    @patch('pyquizhub.core.engine.url_validator.requests.head')
    def test_validation_without_verification(self, mock_head):
        """Test validation flow without content verification."""
        # Should not make HTTP request when verify_content=False
        ImageURLValidator.validate_image_url(
            'https://example.com/test.png',
            verify_content=False
        )

        # Verify NO HEAD request was made
        mock_head.assert_not_called()

    @patch('pyquizhub.core.engine.url_validator.requests.head')
    def test_validation_fails_on_wrong_content_type(self, mock_head):
        """Test that validation fails when content type is wrong."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {
            'Content-Type': 'text/html',  # Wrong type
            'Content-Length': '1024'
        }
        mock_head.return_value = mock_response

        with pytest.raises(ValueError, match="does not point to image"):
            ImageURLValidator.validate_image_url(
                'https://example.com/fake.png',  # Has .png extension but wrong content
                verify_content=True
            )

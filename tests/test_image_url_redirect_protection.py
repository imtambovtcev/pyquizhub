"""Tests for image URL redirect protection."""
from unittest.mock import Mock, patch
import pytest

from pyquizhub.core.engine.url_validator import ImageURLValidator


class TestImageURLRedirectProtection:
    """Test redirect protection in image URL validation."""

    def test_redirect_to_non_whitelisted_domain_blocked(self):
        """Test that redirect from whitelisted to non-whitelisted domain is blocked."""
        # Simulate a redirect from imgur.com to evil.com
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.url = "https://evil.com/malicious.png"  # Final URL after redirect
        mock_response.history = [Mock()]  # Indicates there was a redirect
        mock_response.headers = {
            'Content-Type': 'image/png',
            'Content-Length': '1024'
        }

        with patch('requests.head', return_value=mock_response):
            with pytest.raises(ValueError, match="does not match allowed patterns"):
                # Try to verify an imgur URL with pattern restrictions
                # But it redirects to evil.com which doesn't match patterns
                ImageURLValidator.verify_image_content(
                    "https://i.imgur.com/abc123.png",
                    allowed_patterns=[r'^https://i\.imgur\.com/']
                )

    def test_redirect_to_whitelisted_domain_allowed(self):
        """Test that redirect between whitelisted domains is allowed."""
        # Simulate redirect from imgur.com to i.imgur.com (both whitelisted)
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.url = "https://i.imgur.com/real123.png"  # Final URL
        mock_response.history = [Mock()]  # Indicates there was a redirect
        mock_response.headers = {
            'Content-Type': 'image/png',
            'Content-Length': '1024'
        }

        with patch('requests.head', return_value=mock_response):
            # Should succeed - both URLs match the pattern
            result = ImageURLValidator.verify_image_content(
                "https://imgur.com/abc123",
                allowed_patterns=[r'^https://.*\.imgur\.com/']
            )
            assert result is True

    def test_redirect_to_homepage_blocked(self):
        """Test that redirect to domain homepage (no image extension) is blocked."""
        # Simulate redirect from i.imgur.com/abc123.png to imgur.com (homepage)
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.url = "https://imgur.com/"  # Redirected to homepage
        mock_response.history = [Mock()]  # Indicates there was a redirect
        mock_response.headers = {
            'Content-Type': 'text/html',
            'Content-Length': '5000'
        }

        with patch('requests.head', return_value=mock_response):
            with pytest.raises(ValueError, match="does not have image extension"):
                ImageURLValidator.verify_image_content(
                    "https://i.imgur.com/nonexistent.png"
                )

    def test_redirect_to_private_ip_blocked(self):
        """Test that redirect to private IP address is blocked (SSRF protection)."""
        # Simulate redirect from public URL to localhost
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.url = "http://127.0.0.1/secret.png"  # SSRF attempt
        mock_response.history = [Mock()]
        mock_response.headers = {
            'Content-Type': 'image/png',
            'Content-Length': '1024'
        }

        with patch('requests.head', return_value=mock_response):
            with pytest.raises(ValueError, match="IP-based URLs not allowed"):
                ImageURLValidator.verify_image_content(
                    "https://i.imgur.com/redirect.png"
                )

    def test_no_redirect_passes_validation(self):
        """Test that URLs without redirects pass validation normally."""
        # No redirect - direct response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.url = "https://i.imgur.com/abc123.png"  # Same as requested
        mock_response.history = []  # No redirects
        mock_response.headers = {
            'Content-Type': 'image/png',
            'Content-Length': '1024'
        }

        with patch('requests.head', return_value=mock_response):
            result = ImageURLValidator.verify_image_content(
                "https://i.imgur.com/abc123.png",
                allowed_patterns=[r'^https://i\.imgur\.com/']
            )
            assert result is True

    def test_redirect_without_pattern_restrictions_checks_ssrf_only(self):
        """Test that redirects without pattern restrictions still check SSRF."""
        # Redirect to private IP without pattern restrictions
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.url = "http://192.168.1.1/image.png"  # Private IP
        mock_response.history = [Mock()]
        mock_response.headers = {
            'Content-Type': 'image/png',
            'Content-Length': '1024'
        }

        with patch('requests.head', return_value=mock_response):
            with pytest.raises(ValueError, match="IP-based URLs not allowed"):
                # No pattern restrictions, but SSRF check should still catch it
                ImageURLValidator.verify_image_content(
                    "https://example.com/redirect.png"
                )

    def test_multiple_redirects_validates_final_url(self):
        """Test that multiple redirects are followed and final URL is validated."""
        # Chain of redirects: imgur.com -> i.imgur.com -> evil.com
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.url = "https://evil.com/final.png"  # Final destination
        mock_response.history = [Mock(), Mock()]  # Multiple redirects
        mock_response.headers = {
            'Content-Type': 'image/png',
            'Content-Length': '1024'
        }

        with patch('requests.head', return_value=mock_response):
            with pytest.raises(ValueError, match="does not match allowed patterns"):
                ImageURLValidator.verify_image_content(
                    "https://i.imgur.com/start.png",
                    allowed_patterns=[r'^https://.*\.imgur\.com/']
                )

"""
URL validation for SSRF protection and image URL validation.

This module provides comprehensive URL validation to prevent:
- SSRF attacks against internal services
- DNS rebinding attacks
- Cloud metadata service access
- Private network access
- Redirect-based bypasses

Also provides image-specific validation:
- Content-Type verification
- Image extension validation
- File size limits
"""

from __future__ import annotations

import socket
import ipaddress
import re
from urllib.parse import urlparse, parse_qs
import requests
from pyquizhub.logging.setup import get_logger

logger = get_logger(__name__)

# Allowed image extensions
ALLOWED_IMAGE_EXTENSIONS = {
    '.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg', '.bmp', '.ico', '.tif', '.tiff'
}

# Allowed image MIME types
ALLOWED_IMAGE_MIME_TYPES = {
    'image/jpeg', 'image/png', 'image/gif', 'image/webp',
    'image/svg+xml', 'image/bmp', 'image/x-icon', 'image/vnd.microsoft.icon',
    'image/tiff'
}

# Allowed document extensions
ALLOWED_DOCUMENT_EXTENSIONS = {
    '.pdf', '.doc', '.docx', '.txt', '.rtf', '.odt',
    '.xls', '.xlsx', '.ods', '.ppt', '.pptx', '.odp',
    '.md', '.html', '.htm'
}

# Allowed document MIME types
ALLOWED_DOCUMENT_MIME_TYPES = {
    'application/pdf',
    'application/msword',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'text/plain',
    'application/rtf',
    'application/vnd.oasis.opendocument.text',
    'application/vnd.ms-excel',
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    'application/vnd.oasis.opendocument.spreadsheet',
    'application/vnd.ms-powerpoint',
    'application/vnd.openxmlformats-officedocument.presentationml.presentation',
    'application/vnd.oasis.opendocument.presentation',
    'text/markdown',
    'text/html',
    'text/html; charset=iso-8859-1'
}

# Allowed audio extensions
ALLOWED_AUDIO_EXTENSIONS = {
    '.mp3', '.wav', '.ogg', '.m4a', '.flac', '.aac', '.wma', '.opus'
}

# Allowed audio MIME types
ALLOWED_AUDIO_MIME_TYPES = {
    'audio/mpeg', 'audio/wav', 'audio/ogg', 'audio/mp4',
    'audio/flac', 'audio/aac', 'audio/x-ms-wma', 'audio/opus'
}

# Allowed video extensions
ALLOWED_VIDEO_EXTENSIONS = {
    '.mp4', '.webm', '.ogg', '.mov', '.avi', '.mkv', '.flv', '.wmv'
}

# Allowed video MIME types
ALLOWED_VIDEO_MIME_TYPES = {
    'video/mp4', 'video/webm', 'video/ogg', 'video/quicktime',
    'video/x-msvideo', 'video/x-matroska', 'video/x-flv', 'video/x-ms-wmv'
}

# Generic file extensions (for "file" type - catch-all)
ALLOWED_FILE_EXTENSIONS = {
    # Include all of the above
    *ALLOWED_IMAGE_EXTENSIONS,
    *ALLOWED_DOCUMENT_EXTENSIONS,
    *ALLOWED_AUDIO_EXTENSIONS,
    *ALLOWED_VIDEO_EXTENSIONS,
    # Additional generic file types
    '.zip', '.tar', '.gz', '.7z', '.rar',
    '.json', '.xml', '.csv', '.yml', '.yaml',
    '.md', '.html', '.css', '.js'
}

# Generic file MIME types
ALLOWED_FILE_MIME_TYPES = {
    *ALLOWED_IMAGE_MIME_TYPES,
    *ALLOWED_DOCUMENT_MIME_TYPES,
    *ALLOWED_AUDIO_MIME_TYPES,
    *ALLOWED_VIDEO_MIME_TYPES,
    # Additional generic MIME types
    'application/zip',
    'application/x-tar',
    'application/gzip',
    'application/x-7z-compressed',
    'application/x-rar-compressed',
    'application/json',
    'application/xml',
    'text/xml',
    'text/csv',
    'text/yaml',
    'text/markdown',
    'text/html',
    'text/css',
    'application/javascript'
}

# Default allowed image URL patterns for RESTRICTED tier
# These are safe, public image hosting services and CDNs
# RESTRICTED tier is limited to these services to prevent resource abuse
DEFAULT_ALLOWED_IMAGE_URL_PATTERNS = [
    # CDN services
    r'^https://.*\.cloudinary\.com/',
    r'^https://.*\.imgix\.net/',
    r'^https://.*\.cloudfront\.net/',
    r'^https://.*\.fastly\.net/',
    r'^https://cdn\.jsdelivr\.net/',

    # Image hosting services
    r'^https://i\.imgur\.com/',
    r'^https://imgur\.com/.*\.(jpg|jpeg|png|gif|webp)$',
    r'^https://.*\.unsplash\.com/',
    r'^https://images\.unsplash\.com/',

    # Placeholder services (for development/testing)
    r'^https://via\.placeholder\.com/',
    r'^https://placehold\.co/',
    r'^https://picsum\.photos/',
    r'^https://dummyimage\.com/',

    # HTTPBin (testing only)
    r'^https://httpbin\.org/image',

    # Well-known domains with specific image paths (more restrictive)
    # GitHub user content
    r'^https://raw\.githubusercontent\.com/.*\.(jpg|jpeg|png|gif|webp|svg)(\?.*)?$',
    r'^https://user-images\.githubusercontent\.com/.*\.(jpg|jpeg|png|gif|webp|svg)(\?.*)?$',

    # Wikipedia/Wikimedia
    r'^https://upload\.wikimedia\.org/.*\.(jpg|jpeg|png|gif|webp|svg)(\?.*)?$',
]


class URLValidator:
    """
    Validates URLs against SSRF attack patterns.

    Implements multiple layers of protection:
    1. Scheme validation (HTTPS only)
    2. IP-based URL rejection
    3. Localhost detection
    4. Internal TLD detection
    5. DNS resolution validation
    6. Private IP range checking
    """

    # Blocked URL schemes
    BLOCKED_SCHEMES = [
        "file", "ftp", "ftps", "gopher", "dict", "jar", "tftp",
        "ldap", "ldaps", "imap", "imaps", "smtp", "smtps",
        "telnet", "ssh", "sftp", "rsync", "git", "svn",
    ]

    # Localhost variations (including tricks)
    LOCALHOST_PATTERNS = [
        "localhost",
        "127.0.0.1",
        "::1",
        "0.0.0.0",
        "0177.0.0.1",  # Octal
        "0x7f.0.0.1",  # Hex
        "0x7f.1",      # Short hex
        "2130706433",  # Decimal
        "017700000001",  # Octal full
        "[::1]",       # IPv6
        "[0:0:0:0:0:0:0:1]",  # IPv6 full
    ]

    # Internal TLDs
    INTERNAL_TLDS = [
        ".local", ".internal", ".lan", ".corp", ".private",
        ".intranet", ".home", ".localdomain"
    ]

    # Cloud metadata endpoints
    CLOUD_METADATA_IPS = [
        "169.254.169.254",  # AWS, Azure, GCP
        "fd00:ec2::254",    # AWS IPv6
    ]

    @staticmethod
    def validate_url(url: str, allow_http: bool = False) -> str:
        """
        Validate URL for SSRF attacks.

        Args:
            url: URL to validate
            allow_http: If True, allow HTTP in addition to HTTPS (NOT RECOMMENDED)

        Returns:
            Validated URL

        Raises:
            ValueError: If URL is potentially malicious
        """
        if not isinstance(url, str):
            raise ValueError(f"URL must be string, got {type(url).__name__}")

        if not url:
            raise ValueError("URL cannot be empty")

        # Check length (prevent DoS)
        if len(url) > 2048:
            raise ValueError(f"URL too long: {len(url)} characters (max 2048)")

        # Parse URL
        try:
            parsed = urlparse(url)
        except Exception as e:
            raise ValueError(f"Invalid URL format: {e}")

        # Check scheme
        allowed_schemes = ["https"]
        if allow_http:
            allowed_schemes.append("http")

        if parsed.scheme.lower() not in allowed_schemes:
            raise ValueError(
                f"Only HTTPS URLs allowed, got: {parsed.scheme}"
            )

        # Check for blocked schemes (defense in depth)
        if parsed.scheme.lower() in URLValidator.BLOCKED_SCHEMES:
            raise ValueError(f"Blocked URL scheme: {parsed.scheme}")

        # Check hostname exists
        if not parsed.hostname:
            raise ValueError("URL must have a hostname")

        hostname = parsed.hostname.lower()

        # Reject IP-based URLs (both IPv4 and IPv6)
        URLValidator._reject_ip_urls(hostname)

        # Reject localhost variations
        URLValidator._reject_localhost(hostname)

        # Reject internal TLDs
        URLValidator._reject_internal_tlds(hostname)

        # Check for authentication in URL
        if parsed.username or parsed.password:
            raise ValueError("URLs with embedded credentials not allowed")

        # Check for @-based SSRF tricks
        if "@" in url:
            raise ValueError("URLs with embedded credentials not allowed")

        # Check for unicode/IDN tricks
        URLValidator._check_unicode_tricks(hostname)

        # Check for suspicious patterns in path/query
        URLValidator._check_suspicious_patterns(parsed)

        logger.debug(f"URL validated: {hostname}")
        return url

    @staticmethod
    def _reject_ip_urls(hostname: str) -> None:
        """Reject URLs with IP addresses instead of hostnames."""
        # First check for hex/octal/decimal formats BEFORE IPv4Address
        # These can slip through IPv4Address parsing

        # Check for pure decimal IPv4 (e.g., 2130706433)
        if hostname.isdigit():
            raise ValueError(
                f"IP-based URLs not allowed (decimal IP): {hostname}")

        # Check for hex IPv4 (e.g., 0x7f000001, 0x7f.0.0.1)
        if re.match(r'^0x[0-9a-fA-F.]+', hostname):
            raise ValueError(f"IP-based URLs not allowed (hex IP): {hostname}")

        # Check for octal IPv4 (e.g., 0177.0.0.1, 0177.1)
        if re.match(r'^0[0-7.]+', hostname) and not hostname == "0":
            raise ValueError(
                f"IP-based URLs not allowed (octal IP): {hostname}")

        # Check for IPv4 addresses (dotted decimal)
        try:
            ipaddress.IPv4Address(hostname)
            raise ValueError(f"IP-based URLs not allowed: {hostname}")
        except ipaddress.AddressValueError:
            pass  # Not IPv4, continue

        # Check for IPv6 (with or without brackets)
        hostname_clean = hostname.strip("[]")
        try:
            ipaddress.IPv6Address(hostname_clean)
            raise ValueError(f"IP-based URLs not allowed (IPv6): {hostname}")
        except ipaddress.AddressValueError:
            pass  # Not IPv6, continue

    @staticmethod
    def _reject_localhost(hostname: str) -> None:
        """Reject localhost variations."""
        if hostname in URLValidator.LOCALHOST_PATTERNS:
            raise ValueError(f"Localhost URLs not allowed: {hostname}")

        # Check for variations with different formats
        if "localhost" in hostname:
            raise ValueError(f"Localhost URLs not allowed: {hostname}")

        # Check for 127.x.x.x pattern
        if hostname.startswith("127."):
            raise ValueError(f"Loopback addresses not allowed: {hostname}")

    @staticmethod
    def _reject_internal_tlds(hostname: str) -> None:
        """Reject internal TLDs."""
        for tld in URLValidator.INTERNAL_TLDS:
            if hostname.endswith(tld):
                raise ValueError(f"Internal TLD not allowed: {hostname}")

    @staticmethod
    def _check_unicode_tricks(hostname: str) -> None:
        """Check for unicode/IDN tricks."""
        # Check for unicode characters that could be used for homograph attacks
        if any(ord(char) > 127 for char in hostname):
            # Contains non-ASCII - could be IDN
            # We could allow IDN but it's risky - reject for safety
            raise ValueError(
                f"Non-ASCII characters not allowed in hostname: {hostname}"
            )

        # Check for confusable characters
        confusables = ["xn--", "ţ", "į", "ł", "þ"]
        for conf in confusables:
            if conf in hostname:
                raise ValueError(
                    f"Potentially confusable characters detected: {hostname}"
                )

    @staticmethod
    def _check_suspicious_patterns(parsed) -> None:
        """Check for suspicious patterns in URL components."""
        # Check for template variables in base URL/path
        # Template variables should ONLY be in query params or body, not in URL path
        # This prevents SSRF via variable injection into the domain/path
        full_base_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
        template_patterns = ["{", "}", "$"]
        for pattern in template_patterns:
            if pattern in full_base_url:
                raise ValueError(
                    f"Template variables not allowed in base URL. "
                    f"Only use templates in query parameters or request body."
                )

        # Check path for path traversal
        if parsed.path and (".." in parsed.path or "//" in parsed.path):
            logger.warning(f"Suspicious path detected: {parsed.path}")

        # Check query string for suspicious patterns
        if parsed.query:
            # Check for common SSRF payloads in query params
            suspicious_query_patterns = [
                "localhost", "127.0.0.1", "0.0.0.0",
                "169.254.169.254",  # Cloud metadata
                "metadata", "internal", "admin",
            ]

            query_lower = parsed.query.lower()
            for pattern in suspicious_query_patterns:
                if pattern in query_lower:
                    logger.warning(
                        f"Suspicious query parameter: {pattern} in {
                            parsed.query}")


class DNSValidator:
    """Validates DNS resolution to prevent DNS rebinding attacks."""

    @staticmethod
    def resolve_and_validate(
        hostname: str,
        check_ipv6: bool = True
    ) -> tuple[str, bool]:
        """
        Resolve hostname and validate IP is not private.

        Args:
            hostname: Hostname to resolve
            check_ipv6: If True, also check IPv6 addresses

        Returns:
            Tuple of (resolved_ip, is_safe)

        Raises:
            ValueError: If DNS resolution fails or resolves to private IP
        """
        try:
            # Resolve IPv4
            resolved_ipv4 = socket.gethostbyname(hostname)

            logger.debug(f"Resolved {hostname} to IPv4: {resolved_ipv4}")

            # Validate IPv4 is not private
            DNSValidator._validate_ip_is_public(resolved_ipv4, hostname)

            # Check IPv6 if requested
            if check_ipv6:
                DNSValidator._check_ipv6(hostname)

            return resolved_ipv4, True

        except socket.gaierror as e:
            raise ValueError(f"Failed to resolve hostname {hostname}: {e}")

    @staticmethod
    def _validate_ip_is_public(ip: str, hostname: str) -> None:
        """Validate that IP is public (not private/internal)."""
        try:
            ip_obj = ipaddress.ip_address(ip)

            # Check if private
            if ip_obj.is_private:
                raise ValueError(
                    f"Hostname {hostname} resolves to private IP: {ip}"
                )

            # Check if loopback
            if ip_obj.is_loopback:
                raise ValueError(
                    f"Hostname {hostname} resolves to loopback IP: {ip}"
                )

            # Check if link-local
            if ip_obj.is_link_local:
                raise ValueError(
                    f"Hostname {hostname} resolves to link-local IP: {ip}"
                )

            # Check if reserved
            if ip_obj.is_reserved:
                raise ValueError(
                    f"Hostname {hostname} resolves to reserved IP: {ip}"
                )

            # Check if multicast
            if ip_obj.is_multicast:
                raise ValueError(
                    f"Hostname {hostname} resolves to multicast IP: {ip}"
                )

            # Additional check for cloud metadata
            if ip == "169.254.169.254":
                raise ValueError(
                    f"Hostname {hostname} resolves to cloud metadata service"
                )

        except ipaddress.AddressValueError as e:
            raise ValueError(f"Invalid IP address {ip}: {e}")

    @staticmethod
    def _check_ipv6(hostname: str) -> None:
        """Check IPv6 resolution for private addresses."""
        try:
            ipv6_info = socket.getaddrinfo(
                hostname, None, socket.AF_INET6
            )

            for info in ipv6_info:
                ipv6_addr = info[4][0]
                ip_obj = ipaddress.ip_address(ipv6_addr)

                logger.debug(f"Resolved {hostname} to IPv6: {ipv6_addr}")

                if ip_obj.is_private or ip_obj.is_loopback or ip_obj.is_link_local:
                    raise ValueError(
                        f"Hostname {hostname} has private IPv6: {ipv6_addr}"
                    )

        except socket.gaierror:
            # No IPv6, that's fine
            logger.debug(f"No IPv6 for {hostname}")
            pass

    @staticmethod
    def check_redirect_target(redirect_url: str) -> None:
        """
        Validate redirect target URL.

        This prevents bypass via redirect chains:
        https://safe.com/redirect -> http://localhost/admin

        Args:
            redirect_url: Target of HTTP redirect

        Raises:
            ValueError: If redirect target is not safe
        """
        logger.warning(f"Redirect detected to: {redirect_url}")

        # Apply all the same validations as original URL
        URLValidator.validate_url(redirect_url)

        # Check hostname resolution
        parsed = urlparse(redirect_url)
        if parsed.hostname:
            DNSValidator.resolve_and_validate(parsed.hostname)


class APIAllowlistManager:
    """Manages allowed external API domains."""

    def __init__(self):
        # Global platform-approved APIs
        # These are considered safe for all quiz creators
        self.global_allowlist = [
            # Weather APIs
            "api.openweathermap.org",
            "api.open-meteo.com",
            "api.weatherapi.com",
            "wttr.in",

            # Geographic/Country data
            "restcountries.com",
            "api.geonames.org",

            # Developer tools (testing only - remove in production)
            "httpbin.org",
            "jsonplaceholder.typicode.com",

            # Public APIs
            "api.github.com",
            "api.agify.io",
            "api.nationalize.io",
            "api.genderize.io",

            # Joke/Fun APIs
            "official-joke-api.appspot.com",
            "v2.jokeapi.dev",
        ]

    def is_allowed(self, url: str, creator_allowlist: list = None) -> bool:
        """
        Check if URL is allowed.

        Args:
            url: Full URL to check
            creator_allowlist: Creator-specific allowed domains

        Returns:
            True if allowed, False otherwise
        """
        parsed = urlparse(url)
        hostname = parsed.hostname

        if not hostname:
            return False

        # Check global allowlist
        if self._match_domain(hostname, self.global_allowlist):
            logger.debug(f"URL allowed by global allowlist: {hostname}")
            return True

        # Check creator-specific allowlist
        if creator_allowlist:
            if self._match_domain(hostname, creator_allowlist):
                logger.debug(f"URL allowed by creator allowlist: {hostname}")
                return True

        logger.warning(f"URL not in allowlist: {hostname}")
        return False

    def _match_domain(self, hostname: str, allowlist: list) -> bool:
        """Match hostname against allowlist with wildcard support."""
        for allowed in allowlist:
            if allowed.startswith("*."):
                # Wildcard subdomain: *.example.com
                base_domain = allowed[2:]
                if hostname == base_domain or hostname.endswith(
                        "." + base_domain):
                    return True
            elif hostname == allowed:
                return True

        return False


class ImageURLValidator:
    """
    Validates image URLs with security and content checks.

    Combines SSRF protection from URLValidator with image-specific validation:
    - Extension checking
    - Content-Type verification
    - File size limits
    """

    @staticmethod
    def has_image_extension(url: str) -> bool:
        """
        Check if URL has an image extension (non-raising version).

        Args:
            url: URL to check

        Returns:
            True if URL has image extension, False otherwise
        """
        try:
            parsed = urlparse(url)
            path = parsed.path.lower()

            # Check if path ends with image extension
            has_valid_extension = any(
                path.endswith(ext) for ext in ALLOWED_IMAGE_EXTENSIONS
            )

            if has_valid_extension:
                return True

            # Check query params for CDN URLs
            query = parsed.query.lower()
            return any(ext.lstrip('.') in query for ext in ALLOWED_IMAGE_EXTENSIONS)
        except Exception:
            return False

    @staticmethod
    def validate_image_extension(url: str) -> None:
        """
        Validate URL has an image extension.

        Args:
            url: URL to check

        Raises:
            ValueError: If URL doesn't have image extension
        """
        if not ImageURLValidator.has_image_extension(url):
            raise ValueError(
                f"URL must have image extension. "
                f"Allowed: {', '.join(ALLOWED_IMAGE_EXTENSIONS)}"
            )

    @staticmethod
    def check_url_against_patterns(
        url: str,
        allowed_patterns: list[str] | None = None
    ) -> bool:
        """
        Check if URL matches any of the allowed patterns.

        This is used to restrict image URLs to approved domains/patterns
        for RESTRICTED tier users.

        Args:
            url: URL to check
            allowed_patterns: List of regex patterns. If None, uses default patterns.

        Returns:
            True if URL matches at least one pattern, False otherwise
        """
        if allowed_patterns is None:
            allowed_patterns = DEFAULT_ALLOWED_IMAGE_URL_PATTERNS

        # If no patterns specified, allow all
        if not allowed_patterns:
            return True

        # Check if URL matches any pattern
        for pattern in allowed_patterns:
            if re.match(pattern, url, re.IGNORECASE):
                logger.debug(f"URL {url} matched pattern: {pattern}")
                return True

        return False

    @staticmethod
    def validate_url_pattern_restriction(
        url: str,
        allowed_patterns: list[str] | None = None,
        error_message: str | None = None
    ) -> None:
        """
        Validate URL against allowed patterns and raise error if not matched.

        Args:
            url: URL to validate
            allowed_patterns: List of regex patterns
            error_message: Custom error message

        Raises:
            ValueError: If URL doesn't match any allowed pattern
        """
        if not ImageURLValidator.check_url_against_patterns(url, allowed_patterns):
            if error_message is None:
                error_message = (
                    f"Image URL does not match allowed patterns. "
                    f"URL: {url}\n"
                    f"Allowed services: Cloudinary, Imgix, Imgur, Unsplash, "
                    f"placeholder services, or direct HTTPS URLs to image files."
                )
            raise ValueError(error_message)

    @staticmethod
    def verify_image_content(
        url: str,
        timeout: int = 5,
        max_size_mb: float = 10.0,
        allowed_patterns: list[str] | None = None
    ) -> bool:
        """
        Verify URL points to actual image by checking Content-Type header.

        This makes a HEAD request to check headers without downloading the full image.

        Args:
            url: URL to verify
            timeout: Request timeout in seconds
            max_size_mb: Maximum allowed image size in MB
            allowed_patterns: Optional list of regex patterns for URL whitelisting.
                            If provided, both original and final (after redirect) URLs
                            must match at least one pattern.

        Returns:
            True if URL points to valid image

        Raises:
            ValueError: If verification fails or URL doesn't match allowed patterns
        """
        try:
            # Make HEAD request (doesn't download body)
            response = requests.head(
                url,
                timeout=timeout,
                allow_redirects=True,
                headers={'User-Agent': 'PyQuizHub-ImageValidator/1.0'}
            )

            # Check for redirects - ensure final URL is also safe
            if response.history:
                # There were redirects
                final_url = response.url
                if final_url != url:
                    # URL was redirected - validate final URL
                    logger.warning(
                        f"Image URL redirected from {url} to {final_url}"
                    )

                    # Re-validate final URL against SSRF checks
                    URLValidator.validate_url(final_url, allow_http=True)

                    # Check final URL has image extension
                    if not ImageURLValidator.has_image_extension(final_url):
                        raise ValueError(
                            f"Redirected URL does not have image extension: {final_url}"
                        )

                    # Check final URL against allowed patterns (if provided)
                    if allowed_patterns is not None:
                        if not ImageURLValidator.check_url_against_patterns(
                            final_url, allowed_patterns
                        ):
                            raise ValueError(
                                f"Redirected URL does not match allowed patterns: {final_url}. "
                                f"Original URL {url} redirected to non-whitelisted domain."
                            )

            # Check if request was successful
            if response.status_code >= 400:
                raise ValueError(
                    f"Image URL returned error status: {response.status_code}"
                )

            # Check Content-Type header
            content_type = response.headers.get('Content-Type', '').lower()

            # Extract MIME type (ignore charset etc.)
            mime_type = content_type.split(';')[0].strip()

            if mime_type not in ALLOWED_IMAGE_MIME_TYPES:
                raise ValueError(
                    f"URL does not point to image. Content-Type: {content_type}. "
                    f"Allowed: {', '.join(ALLOWED_IMAGE_MIME_TYPES)}"
                )

            # Check Content-Length if available
            content_length = response.headers.get('Content-Length')
            if content_length:
                try:
                    size_bytes = int(content_length)
                except ValueError:
                    logger.warning(f"Invalid Content-Length header: {content_length}")
                else:
                    # Only check size if conversion succeeded
                    size_mb = size_bytes / (1024 * 1024)

                    if size_mb > max_size_mb:
                        raise ValueError(
                            f"Image too large: {size_mb:.2f}MB (max: {max_size_mb}MB)"
                        )

            logger.debug(f"Image URL verified: {url} ({mime_type})")
            return True

        except requests.exceptions.Timeout:
            raise ValueError(f"Image URL request timed out after {timeout}s")
        except requests.exceptions.ConnectionError:
            raise ValueError("Failed to connect to image URL")
        except requests.exceptions.RequestException as e:
            raise ValueError(f"Failed to verify image URL: {e}")

    @staticmethod
    def validate_image_url(
        url: str,
        verify_content: bool = False,
        timeout: int = 5,
        allow_http: bool = False,
        allowed_patterns: list[str] | None = None
    ) -> None:
        """
        Comprehensive image URL validation with SSRF protection.

        Args:
            url: URL to validate
            verify_content: Whether to verify URL actually points to image (requires network call)
            timeout: Timeout for content verification
            allow_http: Whether to allow HTTP (default: HTTPS only)
            allowed_patterns: Optional list of regex patterns for URL whitelisting

        Raises:
            ValueError: If validation fails
        """
        # Step 1: SSRF protection (using existing URLValidator)
        URLValidator.validate_url(url, allow_http=allow_http)

        # Step 2: Check image extension
        ImageURLValidator.validate_image_extension(url)

        # Step 3: Optionally verify content (including redirect checking)
        if verify_content:
            ImageURLValidator.verify_image_content(
                url, timeout, allowed_patterns=allowed_patterns
            )

    @staticmethod
    def has_variable_placeholders(url: str) -> bool:
        """
        Check if URL contains variable placeholders like {variables.name}.

        Args:
            url: URL to check

        Returns:
            True if URL contains variable placeholders
        """
        # Pattern to match {variables.varname} or {api.id.field}
        pattern = r'\{(variables|api)\.[a-zA-Z_][a-zA-Z0-9_]*(\.[a-zA-Z_][a-zA-Z0-9_]*)*\}'
        return bool(re.search(pattern, url))

    @staticmethod
    def extract_variable_names(url: str) -> list[str]:
        """
        Extract variable names from URL template.

        Args:
            url: URL template with variable placeholders

        Returns:
            List of variable names (e.g., ['variables.img_url', 'variables.format'])
        """
        # Pattern to match {variables.varname} or {api.id.field}
        pattern = r'\{((variables|api)\.[a-zA-Z_][a-zA-Z0-9_]*(\.[a-zA-Z_][a-zA-Z0-9_]*)*)\}'
        matches = re.findall(pattern, url)
        return [match[0] for match in matches]


class AttachmentURLValidator:
    """
    Validates attachment URLs for all file types with security and content checks.

    Supports: image, video, audio, document, file
    """

    # Map attachment types to their allowed extensions and MIME types
    TYPE_CONFIGS = {
        'image': {
            'extensions': ALLOWED_IMAGE_EXTENSIONS,
            'mime_types': ALLOWED_IMAGE_MIME_TYPES
        },
        'video': {
            'extensions': ALLOWED_VIDEO_EXTENSIONS,
            'mime_types': ALLOWED_VIDEO_MIME_TYPES
        },
        'audio': {
            'extensions': ALLOWED_AUDIO_EXTENSIONS,
            'mime_types': ALLOWED_AUDIO_MIME_TYPES
        },
        'document': {
            'extensions': ALLOWED_DOCUMENT_EXTENSIONS,
            'mime_types': ALLOWED_DOCUMENT_MIME_TYPES
        },
        'file': {
            'extensions': ALLOWED_FILE_EXTENSIONS,
            'mime_types': ALLOWED_FILE_MIME_TYPES
        }
    }

    @staticmethod
    def has_valid_extension(url: str, attachment_type: str) -> bool:
        """
        Check if URL has a valid extension for the attachment type.

        Args:
            url: URL to check
            attachment_type: Type of attachment (image, video, audio, document, file)

        Returns:
            True if URL has valid extension, False otherwise
        """
        if attachment_type not in AttachmentURLValidator.TYPE_CONFIGS:
            return False

        try:
            parsed = urlparse(url)
            path = parsed.path.lower()

            allowed_extensions = AttachmentURLValidator.TYPE_CONFIGS[attachment_type]['extensions']

            # Check if path ends with allowed extension
            has_valid_extension = any(
                path.endswith(ext) for ext in allowed_extensions
            )

            if has_valid_extension:
                return True

            # Check query params for CDN URLs
            query = parsed.query.lower()
            return any(ext.lstrip('.') in query for ext in allowed_extensions)
        except Exception:
            return False

    @staticmethod
    def validate_extension(url: str, attachment_type: str) -> None:
        """
        Validate URL has valid extension for attachment type.

        Args:
            url: URL to check
            attachment_type: Type of attachment

        Raises:
            ValueError: If URL doesn't have valid extension
        """
        if not AttachmentURLValidator.has_valid_extension(url, attachment_type):
            allowed_extensions = AttachmentURLValidator.TYPE_CONFIGS[attachment_type]['extensions']
            raise ValueError(
                f"URL must have {attachment_type} extension. "
                f"Allowed: {', '.join(sorted(allowed_extensions))}"
            )

    @staticmethod
    def validate_url(
        url: str,
        attachment_type: str,
        verify_content: bool = False,
        timeout: int = 5,
        allow_http: bool = False
    ) -> None:
        """
        Comprehensive attachment URL validation with SSRF protection.

        Args:
            url: URL to validate
            attachment_type: Type of attachment (image, video, audio, document, file)
            verify_content: Whether to verify URL actually points to correct file type
            timeout: Timeout for content verification
            allow_http: Whether to allow HTTP (default: HTTPS only)

        Raises:
            ValueError: If validation fails
        """
        # Step 1: SSRF protection
        URLValidator.validate_url(url, allow_http=allow_http)

        # Step 2: Check extension
        AttachmentURLValidator.validate_extension(url, attachment_type)

        # Step 3: Optionally verify content
        if verify_content:
            AttachmentURLValidator._verify_content(url, attachment_type, timeout)

    @staticmethod
    def _verify_content(url: str, attachment_type: str, timeout: int) -> bool:
        """
        Verify URL points to correct file type by checking Content-Type header.

        Args:
            url: URL to verify
            attachment_type: Expected file type
            timeout: Request timeout in seconds

        Returns:
            True if URL points to valid file

        Raises:
            ValueError: If verification fails
        """
        try:
            response = requests.head(
                url,
                timeout=timeout,
                allow_redirects=True,
                headers={'User-Agent': 'PyQuizHub-AttachmentValidator/1.0'}
            )

            # Check for redirects - ensure final URL is also safe
            if response.history:
                final_url = response.url
                if final_url != url:
                    logger.warning(
                        f"Attachment URL redirected from {url} to {final_url}"
                    )

                    # Re-validate final URL
                    URLValidator.validate_url(final_url, allow_http=True)

                    # Check final URL has valid extension
                    if not AttachmentURLValidator.has_valid_extension(final_url, attachment_type):
                        raise ValueError(
                            f"Redirected URL does not have {attachment_type} extension: {final_url}"
                        )

            # Check if request was successful
            if response.status_code >= 400:
                raise ValueError(
                    f"Attachment URL returned error status: {response.status_code}"
                )

            # Check Content-Type header
            content_type = response.headers.get('Content-Type', '').lower()
            mime_type = content_type.split(';')[0].strip()

            allowed_mime_types = AttachmentURLValidator.TYPE_CONFIGS[attachment_type]['mime_types']

            if mime_type not in allowed_mime_types:
                raise ValueError(
                    f"URL does not point to {attachment_type}. Content-Type: {content_type}. "
                    f"Allowed: {', '.join(sorted(allowed_mime_types))}"
                )

            logger.debug(f"Attachment URL verified: {url} ({mime_type})")
            return True

        except requests.exceptions.Timeout:
            raise ValueError(f"Attachment URL request timed out after {timeout}s")
        except requests.exceptions.ConnectionError:
            raise ValueError("Failed to connect to attachment URL")
        except requests.exceptions.RequestException as e:
            raise ValueError(f"Failed to verify attachment URL: {e}")

    @staticmethod
    def has_variable_placeholders(url: str) -> bool:
        """Check if URL contains variable placeholders."""
        # Reuse ImageURLValidator's implementation
        return ImageURLValidator.has_variable_placeholders(url)

    @staticmethod
    def extract_variable_names(url: str) -> list[str]:
        """Extract variable names from URL template."""
        # Reuse ImageURLValidator's implementation
        return ImageURLValidator.extract_variable_names(url)

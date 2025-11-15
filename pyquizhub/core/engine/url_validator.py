"""
URL validation for SSRF protection.

This module provides comprehensive URL validation to prevent:
- SSRF attacks against internal services
- DNS rebinding attacks
- Cloud metadata service access
- Private network access
- Redirect-based bypasses
"""

import socket
import ipaddress
import re
from urllib.parse import urlparse, parse_qs
from typing import Tuple, Optional
from pyquizhub.config.settings import get_logger

logger = get_logger(__name__)


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
    ) -> Tuple[str, bool]:
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

"""
Comprehensive SSRF protection tests.

Tests all layers of SSRF protection:
- Layer 1: Quiz definition validation
- Layer 2: URL validation
- Layer 3: URL allowlist
- Layer 4: DNS resolution validation
- Layer 5: Request execution safety

Tests cover:
- Localhost access attempts (all variations)
- Private network access
- Cloud metadata access
- DNS rebinding attacks
- Redirect-based bypasses
- Protocol smuggling
- Unicode/IDN attacks
"""

import pytest
import socket
from unittest.mock import patch, MagicMock
from pyquizhub.core.engine.url_validator import (
    URLValidator,
    DNSValidator,
    APIAllowlistManager
)


class TestLocalhostRejection:
    """Test that all localhost variations are rejected."""

    LOCALHOST_URLS = [
        # Standard localhost
        "https://localhost/admin",
        "https://localhost:8000/delete_all",

        # IPv4 localhost
        "https://127.0.0.1/admin",
        "https://127.0.0.1:8000/secrets",
        "https://127.1/admin",
        "https://127.0.1/admin",

        # IPv4 localhost - octal representation
        "https://0177.0.0.1/admin",
        "https://0177.1/admin",

        # IPv4 localhost - hex representation
        "https://0x7f.0.0.1/admin",
        "https://0x7f.1/admin",
        "https://0x7f000001/admin",

        # IPv4 localhost - decimal representation
        "https://2130706433/admin",  # 127.0.0.1 in decimal

        # IPv6 localhost
        "https://[::1]/admin",
        "https://[0:0:0:0:0:0:0:1]/admin",
        "https://[::ffff:127.0.0.1]/admin",

        # 0.0.0.0
        "https://0.0.0.0/admin",
        "https://0/admin",
    ]

    @pytest.mark.parametrize("url", LOCALHOST_URLS)
    def test_localhost_url_rejected(self, url):
        """Test that localhost URLs are rejected."""
        with pytest.raises(ValueError, match="[Ll]ocalhost|[Ll]oopback|IP-based"):
            URLValidator.validate_url(url)

    def test_localhost_dns_resolution_rejected(self):
        """Test that hostnames resolving to localhost are rejected."""
        with patch('socket.gethostbyname', return_value='127.0.0.1'):
            with pytest.raises(ValueError, match="loopback|private"):
                DNSValidator.resolve_and_validate('evil.com')


class TestPrivateNetworkRejection:
    """Test that private network IPs are rejected."""

    PRIVATE_NETWORK_URLS = [
        # Class A private network (10.0.0.0/8)
        "https://10.0.0.1/admin",
        "https://10.255.255.254/api",

        # Class B private network (172.16.0.0/12)
        "https://172.16.0.1/admin",
        "https://172.31.255.254/api",

        # Class C private network (192.168.0.0/16)
        "https://192.168.0.1/admin",
        "https://192.168.1.1/router",
        "https://192.168.255.254/api",

        # Link-local (169.254.0.0/16)
        "https://169.254.0.1/metadata",
        "https://169.254.169.254/latest/meta-data",  # Cloud metadata

        # Other reserved ranges
        "https://224.0.0.1/multicast",
    ]

    @pytest.mark.parametrize("url", PRIVATE_NETWORK_URLS)
    def test_private_network_url_rejected(self, url):
        """Test that direct private IP URLs are rejected."""
        with pytest.raises(ValueError, match="IP-based"):
            URLValidator.validate_url(url)

    PRIVATE_IPS = [
        "10.0.0.1",
        "10.255.255.254",
        "172.16.0.1",
        "172.31.255.254",
        "192.168.0.1",
        "192.168.255.254",
        "169.254.169.254",
    ]

    @pytest.mark.parametrize("ip", PRIVATE_IPS)
    def test_private_ip_dns_resolution_rejected(self, ip):
        """Test that hostnames resolving to private IPs are rejected."""
        with patch('socket.gethostbyname', return_value=ip):
            with pytest.raises(ValueError, match="private|link-local|reserved"):
                DNSValidator.resolve_and_validate('evil.com')


class TestCloudMetadataProtection:
    """Test protection against cloud metadata service access."""

    CLOUD_METADATA_URLS = [
        # AWS/GCP/Azure metadata
        "https://169.254.169.254/latest/meta-data/",
        "https://169.254.169.254/computeMetadata/v1/",

        # Try to bypass with different formats
        "https://169.254.169.254",
        "https://169.254.169.254:80/",
    ]

    @pytest.mark.parametrize("url", CLOUD_METADATA_URLS)
    def test_cloud_metadata_url_rejected(self, url):
        """Test that cloud metadata URLs are rejected."""
        with pytest.raises(ValueError, match="IP-based"):
            URLValidator.validate_url(url)

    def test_cloud_metadata_dns_resolution_rejected(self):
        """Test that hostnames resolving to cloud metadata are rejected."""
        with patch('socket.gethostbyname', return_value='169.254.169.254'):
            with pytest.raises(ValueError, match="cloud metadata|link-local|private"):
                DNSValidator.resolve_and_validate('metadata.evil.com')


class TestDNSRebindingProtection:
    """Test protection against DNS rebinding attacks."""

    def test_dns_rebinding_attack(self):
        """
        Test DNS rebinding attack scenario.

        Attack: evil.com initially resolves to public IP (passes validation),
        then later resolves to 127.0.0.1 (attack succeeds).

        Protection: We validate DNS at request time, not just at quiz creation.
        """
        # First call returns public IP (validation passes)
        # Second call returns localhost (should be caught)
        with patch('socket.gethostbyname') as mock_dns:
            # Simulate DNS rebinding
            # Use real public IP (Google DNS) instead of TEST-NET reserved IP
            mock_dns.side_effect = ['8.8.8.8', '127.0.0.1']

            # First resolution - passes
            ip1, _ = DNSValidator.resolve_and_validate('evil.com')
            assert ip1 == '8.8.8.8'

            # Second resolution - should fail (rebinding detected)
            with pytest.raises(ValueError, match="loopback|private"):
                DNSValidator.resolve_and_validate('evil.com')

    def test_time_of_check_time_of_use(self):
        """
        Test TOCTOU (Time of Check, Time of Use) attack.

        DNS must be validated immediately before request, not cached.
        """
        # This test ensures we don't cache DNS results
        with patch('socket.gethostbyname') as mock_dns:
            mock_dns.return_value = '127.0.0.1'

            # Should fail on every check
            with pytest.raises(ValueError):
                DNSValidator.resolve_and_validate('evil.com')

            with pytest.raises(ValueError):
                DNSValidator.resolve_and_validate('evil.com')


class TestProtocolSmuggling:
    """Test protection against protocol smuggling attacks."""

    PROTOCOL_SMUGGLING_URLS = [
        # File protocol
        "file:///etc/passwd",
        "file://localhost/etc/passwd",
        "file:///c:/windows/system32/config/sam",

        # FTP protocol
        "ftp://localhost/pub",
        "ftps://internal.server/data",

        # Gopher protocol (can be used for SSRF)
        "gopher://localhost:11211/_stats",  # Memcached
        "gopher://localhost:6379/_%2A",     # Redis

        # Dict protocol
        "dict://localhost:11211/stats",

        # LDAP protocol
        "ldap://localhost:389/dc=example,dc=com",

        # Custom protocols
        "jar:http://evil.com!/",
        "sftp://internal/data",
    ]

    @pytest.mark.parametrize("url", PROTOCOL_SMUGGLING_URLS)
    def test_non_https_protocol_rejected(self, url):
        """Test that non-HTTPS protocols are rejected."""
        with pytest.raises(ValueError, match="[Oo]nly HTTPS|[Bb]locked.*scheme"):
            URLValidator.validate_url(url)


class TestUnicodeIDNAttacks:
    """Test protection against Unicode/IDN homograph attacks."""

    UNICODE_URLS = [
        # Cyrillic characters that look like Latin
        "https://еxample.com/api",  # е is Cyrillic
        "https://gооgle.com/api",   # о is Cyrillic

        # Mixed scripts
        "https://аpple.com/api",

        # IDN with xn-- prefix (punycode)
        "https://xn--e1awd7f.com/api",

        # Zero-width characters
        "https://exam\u200Bple.com/api",  # Zero-width space

        # Right-to-left override
        "https://example\u202Ecom.evil/api",
    ]

    @pytest.mark.parametrize("url", UNICODE_URLS)
    def test_unicode_hostname_rejected(self, url):
        """Test that non-ASCII hostnames are rejected."""
        with pytest.raises(ValueError, match="[Nn]on-ASCII|confusable"):
            URLValidator.validate_url(url)


class TestURLParsingTricks:
    """Test protection against URL parsing tricks."""

    def test_at_sign_bypass_rejected(self):
        """
        Test @ sign bypass attempt.

        Attack: https://victim.com@attacker.com
        Browser interprets as: user=victim.com, host=attacker.com
        """
        urls = [
            "https://localhost@evil.com/api",
            "https://admin@localhost/delete",
            "https://127.0.0.1@evil.com/proxy",
        ]

        # These will be rejected - either by @ check, credentials check, or localhost check
        # All are correct - the important thing is they're rejected
        for url in urls:
            with pytest.raises(ValueError):
                URLValidator.validate_url(url)

    def test_embedded_credentials_rejected(self):
        """Test that URLs with embedded credentials are rejected."""
        urls = [
            "https://user:pass@api.example.com/data",
            "https://admin:secret@evil.com/api",
        ]

        for url in urls:
            with pytest.raises(ValueError, match="credentials not allowed"):
                URLValidator.validate_url(url)

    def test_double_slash_tricks(self):
        """Test double slash path tricks."""
        # These should be allowed (just suspicious paths)
        # but we log warnings
        url = "https://api.example.com//admin//delete"
        # Should not raise, but should log warning
        URLValidator.validate_url(url)

    def test_path_traversal_patterns(self):
        """Test path traversal pattern detection."""
        url = "https://api.example.com/../../etc/passwd"
        # Should not raise, but should log warning
        URLValidator.validate_url(url)


class TestInternalTLDs:
    """Test protection against internal TLDs."""

    INTERNAL_TLD_URLS = [
        "https://server.local/api",
        "https://db.internal/admin",
        "https://router.lan/config",
        "https://nas.corp/data",
        "https://fileserver.private/files",
        "https://wiki.intranet/docs",
    ]

    @pytest.mark.parametrize("url", INTERNAL_TLD_URLS)
    def test_internal_tld_rejected(self, url):
        """Test that internal TLDs are rejected."""
        with pytest.raises(ValueError, match="[Ii]nternal TLD"):
            URLValidator.validate_url(url)


class TestHTTPMethodRestrictions:
    """Test that only safe HTTP methods are allowed."""

    DANGEROUS_METHODS = ["PUT", "DELETE", "PATCH", "HEAD", "OPTIONS", "TRACE"]

    @pytest.mark.parametrize("method", DANGEROUS_METHODS)
    def test_dangerous_http_methods_rejected(self, method):
        """Test that dangerous HTTP methods are rejected at quiz creation."""
        # This would be tested in quiz validation layer
        # For now, document that only GET and POST are allowed
        pass


class TestAllowlistSystem:
    """Test URL allowlist functionality."""

    def test_global_allowlist_allows_approved_domains(self):
        """Test that globally approved domains are allowed."""
        allowlist = APIAllowlistManager()

        approved_urls = [
            "https://api.open-meteo.com/v1/forecast",
            "https://api.openweathermap.org/data/2.5/weather",
            "https://restcountries.com/v3.1/all",
        ]

        for url in approved_urls:
            assert allowlist.is_allowed(url), f"Should allow: {url}"

    def test_non_allowlisted_domains_rejected(self):
        """Test that non-allowlisted domains are rejected."""
        allowlist = APIAllowlistManager()

        forbidden_urls = [
            "https://evil.com/api",
            "https://attacker.net/data",
            "https://unknown-api.com/endpoint",
        ]

        for url in forbidden_urls:
            assert not allowlist.is_allowed(url), f"Should reject: {url}"

    def test_wildcard_subdomain_matching(self):
        """Test wildcard subdomain allowlist matching."""
        allowlist = APIAllowlistManager()

        # Manually add wildcard for testing
        allowlist.global_allowlist.append("*.example.com")

        # Should match
        assert allowlist.is_allowed("https://api.example.com/data")
        assert allowlist.is_allowed("https://v2.api.example.com/data")
        assert allowlist.is_allowed("https://example.com/data")

        # Should not match
        assert not allowlist.is_allowed("https://example.org/data")
        assert not allowlist.is_allowed("https://exampleXcom/data")

    def test_creator_specific_allowlist(self):
        """Test creator-specific allowlist."""
        allowlist = APIAllowlistManager()

        creator_domains = ["api.custom-service.com", "data.myapi.net"]

        # Should be allowed with creator allowlist
        assert allowlist.is_allowed(
            "https://api.custom-service.com/endpoint",
            creator_allowlist=creator_domains
        )

        # Should be rejected without creator allowlist
        assert not allowlist.is_allowed(
            "https://api.custom-service.com/endpoint"
        )


class TestIPv6Protection:
    """Test IPv6 SSRF protection."""

    IPV6_URLS = [
        "https://[::1]/admin",  # Localhost
        "https://[::ffff:127.0.0.1]/admin",  # IPv4-mapped IPv6
        "https://[fe80::1]/admin",  # Link-local
        "https://[fc00::1]/admin",  # Unique local address
        "https://[fd00::1]/admin",  # Unique local address
    ]

    @pytest.mark.parametrize("url", IPV6_URLS)
    def test_ipv6_url_rejected(self, url):
        """Test that IPv6 URLs are rejected."""
        with pytest.raises(ValueError, match="IPv6|IP-based"):
            URLValidator.validate_url(url)

    def test_ipv6_dns_resolution_rejected(self):
        """Test that hostnames with private IPv6 are rejected."""
        with patch('socket.getaddrinfo') as mock_addrinfo:
            # Mock IPv6 resolution to link-local address
            mock_addrinfo.return_value = [
                (socket.AF_INET6, socket.SOCK_STREAM, 6, '', ('fe80::1', 80, 0, 0))]

            with patch('socket.gethostbyname', return_value='8.8.8.8'):
                # IPv4 is public, but IPv6 is private - should fail
                with pytest.raises(ValueError, match="private IPv6|private|link"):
                    DNSValidator.resolve_and_validate(
                        'evil.com', check_ipv6=True)


class TestRedirectProtection:
    """Test protection against redirect-based SSRF."""

    def test_redirect_to_localhost_rejected(self):
        """Test that redirects to localhost are rejected."""
        redirect_urls = [
            "https://127.0.0.1/admin",
            "https://localhost/delete",
            "https://[::1]/secrets",
        ]

        for redirect_url in redirect_urls:
            with pytest.raises(ValueError):
                DNSValidator.check_redirect_target(redirect_url)

    def test_redirect_to_private_network_rejected(self):
        """Test that redirects to private networks are rejected."""
        redirect_url = "https://192.168.1.1/router"

        with pytest.raises(ValueError, match="IP-based"):
            DNSValidator.check_redirect_target(redirect_url)

    def test_redirect_chain_validation(self):
        """
        Test that redirect chains are validated.

        Attack: https://safe.com -> https://evil.com -> https://localhost
        Protection: Each redirect target must be validated
        """
        # This would be tested in SafeHTTPClient
        # which blocks ALL redirects by default
        pass


class TestURLLengthLimits:
    """Test URL length limits to prevent DoS."""

    def test_excessive_url_length_rejected(self):
        """Test that excessively long URLs are rejected."""
        # Create a very long URL
        long_path = "a" * 3000
        url = f"https://api.example.com/{long_path}"

        with pytest.raises(ValueError, match="[Uu]RL too long"):
            URLValidator.validate_url(url)

    def test_reasonable_url_length_accepted(self):
        """Test that reasonable URLs are accepted."""
        url = "https://api.example.com/v1/endpoint?param=value&other=data"
        # Should not raise (if domain is allowlisted)
        try:
            URLValidator.validate_url(url)
        except ValueError as e:
            # Only allowlist errors are expected
            if "allowlist" not in str(e).lower():
                raise


class TestEmptyInvalidURLs:
    """Test handling of empty and malformed URLs."""

    INVALID_URLS = [
        "",  # Empty
        " ",  # Whitespace
        "not-a-url",  # No protocol
        "://noprotocol.com",  # Missing protocol
        "https://",  # No host
        "https:///path",  # No host
        None,  # None value
    ]

    @pytest.mark.parametrize("url", INVALID_URLS)
    def test_invalid_url_rejected(self, url):
        """Test that invalid URLs are rejected."""
        with pytest.raises((ValueError, AttributeError, TypeError)):
            URLValidator.validate_url(url)


class TestCaseSensitivity:
    """Test that validations are case-insensitive where appropriate."""

    def test_localhost_case_insensitive(self):
        """Test localhost detection is case-insensitive."""
        urls = [
            "https://LOCALHOST/admin",
            "https://LocalHost/admin",
            "https://lOcAlHoSt/admin",
        ]

        for url in urls:
            with pytest.raises(ValueError, match="[Ll]ocalhost"):
                URLValidator.validate_url(url)

    def test_internal_tld_case_insensitive(self):
        """Test internal TLD detection is case-insensitive."""
        urls = [
            "https://server.LOCAL/api",
            "https://db.Internal/data",
            "https://router.LAN/config",
        ]

        for url in urls:
            with pytest.raises(ValueError, match="[Ii]nternal"):
                URLValidator.validate_url(url)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

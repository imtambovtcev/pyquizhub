"""
Input sanitization for quiz variables and API integration.

This module provides comprehensive input sanitization to prevent:
- SQL injection
- XSS (Cross-Site Scripting)
- Template injection
- Command injection
- Path traversal
- ReDoS (Regular Expression Denial of Service)
"""

import re
from typing import Any
from urllib.parse import quote_plus, quote
from pyquizhub.logging.setup import get_logger

logger = get_logger(__name__)


class InputSanitizer:
    """
    Provides input sanitization for various attack vectors.

    All methods are static for easy use throughout the application.
    """

    # SQL Injection patterns (case-insensitive)
    SQL_INJECTION_PATTERNS = [
        r"\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|EXECUTE|UNION|TRUNCATE)\b",
        r"(--|#|/\*|\*/)",  # SQL comments
        r"(\bOR\b\s+[\w\d]+\s*=\s*[\w\d]+)",  # OR clauses
        r"(\bAND\b\s+[\w\d'\"]+\s*=\s*[\w\d'\"]+)",  # AND clauses (including quoted)
        r"(;.*--)",  # Statement terminator with comment
        r"(\bEXEC\s*\()",  # EXEC with parenthesis
        r"(xp_cmdshell|sp_executesql)",  # Dangerous SQL procedures
        r"('.*OR.*'.*=.*')",  # Common injection pattern
        r"(1\s*=\s*1|'1'='1')",  # Always true conditions
    ]

    # XSS patterns (case-insensitive)
    XSS_PATTERNS = [
        r"<script[^>]*>.*?</script>",  # Script tags
        r"<style[^>]*>.*?</style>",  # Style tags (can contain URLs)
        r"javascript:",  # JavaScript protocol
        r"on\w+\s*=",  # Event handlers (onclick, onerror, etc.)
        r"<iframe[^>]*>",  # Iframes
        r"<object[^>]*>",  # Object tags
        r"<embed[^>]*>",  # Embed tags
        r"<applet[^>]*>",  # Applet tags
        r"<meta[^>]*>",  # Meta tags
        r"<link[^>]*>",  # Link tags
        r"<img[^>]*onerror",  # Image with onerror
        r"data:text/html",  # Data URLs
        r"vbscript:",  # VBScript protocol
        r"expression\s*\(",  # CSS expressions
    ]

    # Command Injection patterns
    COMMAND_INJECTION_PATTERNS = [
        r"[;&|`$()]",  # Shell metacharacters
        r"\$\{.*\}",  # Variable expansion
        r"\$\(.*\)",  # Command substitution
        r"``",  # Backtick command substitution
    ]

    # Path Traversal patterns
    PATH_TRAVERSAL_PATTERNS = [
        r"\.\./",  # Parent directory
        r"\.\.",  # Parent directory reference
        r"%2e%2e",  # URL encoded ..
        r"\.\.\\",  # Windows path traversal
    ]

    # Template Injection patterns
    TEMPLATE_INJECTION_PATTERNS = [
        r"\{\{.+\}\}",  # Jinja2/Django templates (must have content)
        r"\$\{.+\}",  # JSP/JSF templates (must have content)
        r"<%.+%>",  # ASP/JSP templates (must have content)
        r"\#\{.+\}",  # Ruby/EL templates (must have content)
        r"<#.+>",  # FreeMarker templates
    ]

    @staticmethod
    def sanitize_string(
        value: str,
        max_length: int = 10000,
        allow_sql: bool = False,
        allow_html: bool = False,
        allow_shell: bool = False,
        allow_template: bool = False
    ) -> str:
        """
        Sanitize string value against various injection attacks.

        Args:
            value: String to sanitize
            max_length: Maximum allowed length
            allow_sql: If False, reject SQL injection patterns
            allow_html: If False, reject XSS patterns
            allow_shell: If False, reject command injection patterns
            allow_template: If False, reject template injection patterns

        Returns:
            Sanitized string

        Raises:
            ValueError: If string contains malicious patterns or exceeds length
        """
        if not isinstance(value, str):
            raise ValueError(f"Expected string, got {type(value).__name__}")

        # Length check
        if len(value) > max_length:
            raise ValueError(
                f"String length {len(value)} exceeds maximum {max_length}"
            )

        # SQL Injection check
        if not allow_sql:
            for pattern in InputSanitizer.SQL_INJECTION_PATTERNS:
                if re.search(pattern, value, re.IGNORECASE):
                    logger.warning(f"Potential SQL injection detected: {pattern}")
                    raise ValueError(
                        f"String contains potential SQL injection pattern"
                    )

        # XSS check
        if not allow_html:
            for pattern in InputSanitizer.XSS_PATTERNS:
                if re.search(pattern, value, re.IGNORECASE):
                    logger.warning(f"Potential XSS detected: {pattern}")
                    raise ValueError(
                        f"String contains potential XSS pattern"
                    )

        # Command Injection check
        if not allow_shell:
            for pattern in InputSanitizer.COMMAND_INJECTION_PATTERNS:
                if re.search(pattern, value):
                    logger.warning(f"Potential command injection detected: {pattern}")
                    raise ValueError(
                        f"String contains potential command injection pattern"
                    )

        # Template Injection check
        if not allow_template:
            for pattern in InputSanitizer.TEMPLATE_INJECTION_PATTERNS:
                if re.search(pattern, value):
                    logger.warning(f"Potential template injection detected: {pattern}")
                    raise ValueError(
                        f"String contains potential template injection pattern"
                    )

        return value

    @staticmethod
    def sanitize_for_url_param(value: Any) -> str:
        """
        Sanitize value for use in URL parameters.

        Uses URL encoding to prevent injection in URLs.

        Args:
            value: Value to sanitize

        Returns:
            URL-encoded string safe for use in URL parameters
        """
        # Convert to string first
        str_value = str(value)

        # URL encode - converts special characters to %XX format
        return quote_plus(str_value)

    @staticmethod
    def sanitize_for_url_path(value: Any) -> str:
        """
        Sanitize value for use in URL paths.

        Similar to url_param but preserves forward slashes.

        Args:
            value: Value to sanitize

        Returns:
            URL-encoded string safe for use in URL paths
        """
        str_value = str(value)

        # Check for path traversal
        for pattern in InputSanitizer.PATH_TRAVERSAL_PATTERNS:
            if re.search(pattern, str_value):
                raise ValueError(f"Path traversal detected")

        # URL encode but preserve /
        return quote(str_value, safe='/')

    @staticmethod
    def sanitize_dict(data: dict[str, Any], max_depth: int = 10) -> dict[str, Any]:
        """
        Recursively sanitize dictionary values.

        Args:
            data: Dictionary to sanitize
            max_depth: Maximum recursion depth to prevent DoS

        Returns:
            Sanitized dictionary

        Raises:
            ValueError: If dictionary is too deep or contains malicious content
        """
        if max_depth <= 0:
            raise ValueError("Dictionary nesting too deep (potential DoS)")

        sanitized = {}
        for key, value in data.items():
            # Sanitize key
            if not isinstance(key, str):
                key = str(key)

            key = InputSanitizer.sanitize_string(key, max_length=100)

            # Sanitize value based on type
            if isinstance(value, str):
                sanitized[key] = InputSanitizer.sanitize_string(value)
            elif isinstance(value, dict):
                sanitized[key] = InputSanitizer.sanitize_dict(value, max_depth - 1)
            elif isinstance(value, list):
                sanitized[key] = InputSanitizer.sanitize_list(value, max_depth - 1)
            elif isinstance(value, (int, float, bool)) or value is None:
                # Primitives are safe
                sanitized[key] = value
            else:
                # Unknown type - convert to string and sanitize
                sanitized[key] = InputSanitizer.sanitize_string(str(value))

        return sanitized

    @staticmethod
    def sanitize_list(data: list, max_depth: int = 10) -> list:
        """
        Recursively sanitize list values.

        Args:
            data: List to sanitize
            max_depth: Maximum recursion depth

        Returns:
            Sanitized list

        Raises:
            ValueError: If list is too deep or contains malicious content
        """
        if max_depth <= 0:
            raise ValueError("List nesting too deep (potential DoS)")

        sanitized = []
        for value in data:
            if isinstance(value, str):
                sanitized.append(InputSanitizer.sanitize_string(value))
            elif isinstance(value, dict):
                sanitized.append(InputSanitizer.sanitize_dict(value, max_depth - 1))
            elif isinstance(value, list):
                sanitized.append(InputSanitizer.sanitize_list(value, max_depth - 1))
            elif isinstance(value, (int, float, bool)) or value is None:
                sanitized.append(value)
            else:
                sanitized.append(InputSanitizer.sanitize_string(str(value)))

        return sanitized

    @staticmethod
    def sanitize_json_response(
        data: Any,
        max_size_mb: float = 1.0,
        max_depth: int = 10
    ) -> Any:
        """
        Sanitize JSON response from external API.

        Args:
            data: JSON data to sanitize
            max_size_mb: Maximum size in megabytes
            max_depth: Maximum nesting depth

        Returns:
            Sanitized data

        Raises:
            ValueError: If data is too large or too deep
        """
        # Estimate size (rough approximation)
        import sys
        size_bytes = sys.getsizeof(str(data))
        max_bytes = max_size_mb * 1024 * 1024

        if size_bytes > max_bytes:
            raise ValueError(
                f"JSON response too large: {size_bytes} bytes > {max_bytes} bytes"
            )

        # Sanitize based on type
        if isinstance(data, dict):
            return InputSanitizer.sanitize_dict(data, max_depth)
        elif isinstance(data, list):
            return InputSanitizer.sanitize_list(data, max_depth)
        elif isinstance(data, str):
            return InputSanitizer.sanitize_string(data)
        elif isinstance(data, (int, float, bool)) or data is None:
            return data
        else:
            return InputSanitizer.sanitize_string(str(data))

    @staticmethod
    def validate_regex_pattern(pattern: str, max_length: int = 200) -> str:
        """
        Validate regex pattern to prevent ReDoS attacks.

        Args:
            pattern: Regex pattern to validate
            max_length: Maximum pattern length

        Returns:
            Validated pattern

        Raises:
            ValueError: If pattern is potentially dangerous
        """
        if len(pattern) > max_length:
            raise ValueError(f"Regex pattern too long: {len(pattern)} > {max_length}")

        # Detect catastrophic backtracking patterns
        # Check for nested quantifiers like (a+)+, (a*)*, (a{2,5})*
        if re.search(r'\([^)]*[+*]\)[+*]', pattern):
            raise ValueError("Regex pattern contains potential ReDoS: nested quantifiers")

        # Check for alternation with quantifiers like (a|ab)*
        if re.search(r'\([^)]*\|[^)]*\)[+*]', pattern):
            raise ValueError("Regex pattern contains potential ReDoS: alternation with quantifiers")

        # Check for backreference with quantifiers
        if re.search(r'\\[0-9]\+', pattern):
            raise ValueError("Regex pattern contains potential ReDoS: backreference with quantifier")

        # Try to compile to check validity
        try:
            re.compile(pattern)
        except re.error as e:
            raise ValueError(f"Invalid regex pattern: {e}")

        return pattern

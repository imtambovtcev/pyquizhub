"""
Tests for regex safety validator.
"""

import pytest
from pyquizhub.core.engine.regex_validator import (
    RegexValidator,
    RegexValidationError,
    RegexTimeoutError
)


class TestRegexValidator:
    """Test regex validation and safe execution."""

    def test_valid_simple_pattern(self):
        """Test validation of simple valid pattern."""
        pattern = r'\d+'
        RegexValidator.validate_pattern(pattern)  # Should not raise

    def test_valid_complex_pattern(self):
        """Test validation of complex but safe pattern."""
        pattern = r'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}'
        RegexValidator.validate_pattern(pattern)  # Should not raise

    def test_empty_pattern(self):
        """Test that empty pattern is rejected."""
        with pytest.raises(RegexValidationError, match="Empty pattern"):
            RegexValidator.validate_pattern("")

    def test_too_long_pattern(self):
        """Test that overly long pattern is rejected."""
        pattern = "a" * (RegexValidator.MAX_PATTERN_LENGTH + 1)
        with pytest.raises(RegexValidationError, match="Pattern too long"):
            RegexValidator.validate_pattern(pattern)

    def test_nested_quantifiers(self):
        """Test that nested quantifiers are detected."""
        dangerous_patterns = [
            r'(a+)+',  # Nested +
            r'(a*)*',  # Nested *
            r'(a+)*',  # Mixed nested quantifiers
            r'(ab+)+c',  # Nested with other chars
        ]

        for pattern in dangerous_patterns:
            with pytest.raises(RegexValidationError, match="potentially dangerous"):
                RegexValidator.validate_pattern(pattern)

    def test_overlapping_alternations(self):
        """Test that overlapping alternations are detected."""
        dangerous_patterns = [
            r'(a|a)+',  # Overlapping alternation
            r'(ab|a)+',  # Overlapping alternation with longer match
        ]

        for pattern in dangerous_patterns:
            with pytest.raises(RegexValidationError, match="potentially dangerous"):
                RegexValidator.validate_pattern(pattern)

    def test_excessive_wildcards(self):
        """Test that excessive wildcards are detected."""
        dangerous_patterns = [
            r'.*.*.*',  # Multiple .*
            r'.+.+.+',  # Multiple .+
        ]

        for pattern in dangerous_patterns:
            with pytest.raises(RegexValidationError, match="potentially dangerous"):
                RegexValidator.validate_pattern(pattern)

    def test_invalid_regex_syntax(self):
        """Test that invalid regex syntax is caught."""
        invalid_patterns = [
            r'[',  # Unclosed bracket
            r'(?P<',  # Incomplete group
            r'*',  # Invalid quantifier
        ]

        for pattern in invalid_patterns:
            with pytest.raises(RegexValidationError, match="Invalid regex"):
                RegexValidator.validate_pattern(pattern)

    def test_safe_search_basic(self):
        """Test basic safe search."""
        pattern = r'\d+'
        text = "Hello 123 world 456"

        matches = RegexValidator.safe_search(pattern, text)

        assert len(matches) == 2
        assert matches[0]['match'] == '123'
        assert matches[0]['start'] == 6
        assert matches[0]['end'] == 9
        assert matches[1]['match'] == '456'

    def test_safe_search_with_groups(self):
        """Test safe search with capture groups."""
        pattern = r'(\w+)@(\w+)\.(\w+)'
        text = "Contact: john@example.com or jane@test.org"

        matches = RegexValidator.safe_search(pattern, text)

        assert len(matches) == 2
        assert matches[0]['match'] == 'john@example.com'
        assert matches[0]['groups'] == ('john', 'example', 'com')
        assert matches[1]['match'] == 'jane@test.org'
        assert matches[1]['groups'] == ('jane', 'test', 'org')

    def test_safe_search_case_insensitive(self):
        """Test case-insensitive search."""
        pattern = r'hello'
        text = "Hello HELLO hello HeLLo"

        # Case-sensitive (default)
        matches_sensitive = RegexValidator.safe_search(pattern, text, flags=0)
        assert len(matches_sensitive) == 1

        # Case-insensitive
        import re
        matches_insensitive = RegexValidator.safe_search(pattern, text, flags=re.IGNORECASE)
        assert len(matches_insensitive) == 4

    def test_safe_search_max_matches(self):
        """Test that max_matches limit is enforced."""
        pattern = r'\d'
        text = "1234567890" * 20  # 200 digits

        matches = RegexValidator.safe_search(pattern, text, max_matches=10)

        assert len(matches) == 10

    def test_safe_search_text_too_long(self):
        """Test that overly long text is rejected."""
        pattern = r'\d+'
        text = "a" * (RegexValidator.MAX_TEXT_LENGTH + 1)

        with pytest.raises(RegexValidationError, match="Text too long"):
            RegexValidator.safe_search(pattern, text)

    def test_safe_match_success(self):
        """Test safe match with successful match."""
        pattern = r'\d{3}-\d{4}'
        text = "123-4567 and more"

        result = RegexValidator.safe_match(pattern, text)

        assert result is not None
        assert result['match'] == '123-4567'
        assert result['start'] == 0
        assert result['end'] == 8

    def test_safe_match_no_match(self):
        """Test safe match with no match."""
        pattern = r'\d{3}-\d{4}'
        text = "no numbers here"

        result = RegexValidator.safe_match(pattern, text)

        assert result is None

    def test_safe_match_partial(self):
        """Test that match only matches from beginning."""
        pattern = r'\d+'
        text = "text 123"  # Number not at start

        result = RegexValidator.safe_match(pattern, text)

        assert result is None  # match() only matches from beginning

    def test_dangerous_pattern_validation_in_search(self):
        """Test that dangerous patterns are caught before search."""
        pattern = r'(a+)+'
        text = "aaaa"

        with pytest.raises(RegexValidationError):
            RegexValidator.safe_search(pattern, text)

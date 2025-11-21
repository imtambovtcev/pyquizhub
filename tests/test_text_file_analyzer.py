"""
Tests for text file analyzer.
"""

import pytest
import io
from pyquizhub.core.engine.text_file_analyzer import TextFileAnalyzer
from pyquizhub.core.engine.regex_validator import RegexValidationError


class TestTextFileAnalyzer:
    """Test text file reading and analysis."""

    def test_read_utf8_file(self):
        """Test reading UTF-8 encoded file."""
        content = "Hello, world!\nThis is a test."
        file_data = io.BytesIO(content.encode('utf-8'))

        text = TextFileAnalyzer.read_text_file(file_data)

        assert text == content

    def test_read_latin1_file(self):
        """Test reading Latin-1 encoded file."""
        content = "Café résumé"
        file_data = io.BytesIO(content.encode('latin-1'))

        text = TextFileAnalyzer.read_text_file(file_data)

        assert text == content

    def test_file_too_large(self):
        """Test that overly large files are rejected."""
        max_size = 1000
        content = "a" * (max_size + 1)
        file_data = io.BytesIO(content.encode('utf-8'))

        with pytest.raises(ValueError, match="File too large"):
            TextFileAnalyzer.read_text_file(file_data, max_size=max_size)

    def test_invalid_encoding(self):
        """Test that binary files decode with latin-1 as fallback."""
        # Create sequence that's invalid UTF-8 but valid Latin-1
        file_data = io.BytesIO(b'\xff\xfe\xfd')

        # Should succeed with latin-1 fallback
        text = TextFileAnalyzer.read_text_file(file_data)
        assert text is not None

    def test_count_lines(self):
        """Test line counting."""
        text = "line1\nline2\nline3"
        assert TextFileAnalyzer.count_lines(text) == 3

        text_with_trailing = "line1\nline2\n"
        # Trailing \n counts as empty line
        assert TextFileAnalyzer.count_lines(text_with_trailing) == 3

        text_no_trailing = "line1\nline2"
        assert TextFileAnalyzer.count_lines(text_no_trailing) == 2

        empty = ""
        assert TextFileAnalyzer.count_lines(empty) == 0

    def test_count_words(self):
        """Test word counting."""
        text = "Hello world this is a test"
        assert TextFileAnalyzer.count_words(text) == 6

        text_with_newlines = "Hello\nworld\ntest"
        assert TextFileAnalyzer.count_words(text_with_newlines) == 3

        empty = ""
        assert TextFileAnalyzer.count_words(empty) == 0

    def test_count_characters(self):
        """Test character counting."""
        text = "Hello"
        assert TextFileAnalyzer.count_characters(text) == 5

        text_with_spaces = "Hello world"
        assert TextFileAnalyzer.count_characters(text_with_spaces) == 11

    def test_search_text_case_sensitive(self):
        """Test case-sensitive text search."""
        text = "Hello hello HELLO"
        pattern = r'hello'

        results = TextFileAnalyzer.search_text(
            text, pattern, case_sensitive=True)

        assert results['count'] == 1
        assert results['matches'][0]['match'] == 'hello'
        assert results['case_sensitive'] is True

    def test_search_text_case_insensitive(self):
        """Test case-insensitive text search."""
        text = "Hello hello HELLO"
        pattern = r'hello'

        results = TextFileAnalyzer.search_text(
            text, pattern, case_sensitive=False)

        assert results['count'] == 3
        assert results['case_sensitive'] is False

    def test_search_text_with_groups(self):
        """Test text search with capture groups."""
        text = "Email: john@example.com, Contact: jane@test.org"
        pattern = r'(\w+)@(\w+\.\w+)'

        results = TextFileAnalyzer.search_text(text, pattern)

        assert results['count'] == 2
        assert results['matches'][0]['groups'] == ('john', 'example.com')
        assert results['matches'][1]['groups'] == ('jane', 'test.org')

    def test_search_text_max_matches(self):
        """Test that max_matches limit works."""
        text = "1 2 3 4 5 6 7 8 9 10"
        pattern = r'\d+'

        results = TextFileAnalyzer.search_text(text, pattern, max_matches=5)

        assert results['count'] == 5
        assert results['truncated'] is True

    def test_search_text_dangerous_pattern(self):
        """Test that dangerous regex patterns are rejected."""
        text = "test text"
        pattern = r'(a+)+'  # Dangerous nested quantifier

        with pytest.raises(RegexValidationError):
            TextFileAnalyzer.search_text(text, pattern)

    def test_analyze_file_without_search(self):
        """Test file analysis without regex search."""
        content = "Hello world!\nThis is line 2.\nLine 3 here."
        file_data = io.BytesIO(content.encode('utf-8'))

        results = TextFileAnalyzer.analyze_file(file_data)

        assert results['line_count'] == 3
        assert results['word_count'] == 9
        assert results['char_count'] == len(content)
        assert results['text_sample'] == content
        assert results['truncated_sample'] is False
        assert 'search_results' not in results

    def test_analyze_file_with_search(self):
        """Test file analysis with regex search."""
        content = "Email: test@example.com\nContact: admin@test.org"
        file_data = io.BytesIO(content.encode('utf-8'))

        results = TextFileAnalyzer.analyze_file(
            file_data,
            pattern=r'\w+@\w+\.\w+'
        )

        assert results['line_count'] == 2
        assert 'search_results' in results
        assert results['search_results']['count'] == 2

    def test_analyze_file_long_text_sample(self):
        """Test that long text is sampled."""
        content = "a" * 1000
        file_data = io.BytesIO(content.encode('utf-8'))

        results = TextFileAnalyzer.analyze_file(file_data)

        assert results['text_sample'] == "a" * 500
        assert results['truncated_sample'] is True

    def test_analyze_file_special_characters(self):
        """Test file with special characters."""
        content = "Special: @#$%^&*(){}[]|\\:;\"'<>,.?/~`"
        file_data = io.BytesIO(content.encode('utf-8'))

        results = TextFileAnalyzer.analyze_file(file_data)

        assert results['char_count'] == len(content)
        assert '@' in results['text_sample']

    def test_search_multiline(self):
        """Test searching across multiple lines."""
        content = "Line 1\nLine 2\nLine 3"
        file_data = io.BytesIO(content.encode('utf-8'))
        pattern = r'Line \d'

        results = TextFileAnalyzer.analyze_file(file_data, pattern=pattern)

        assert results['search_results']['count'] == 3

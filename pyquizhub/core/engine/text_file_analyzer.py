"""
Text File Analyzer for PyQuizHub.

This module provides safe text file reading and regex-based searching
for quiz file upload analysis.
"""

from __future__ import annotations

from typing import BinaryIO, Any
from pyquizhub.core.engine.regex_validator import RegexValidator, RegexValidationError
from pyquizhub.logging.setup import get_logger

logger = get_logger(__name__)


class TextFileAnalyzer:
    """Analyzes text files with safe regex searching."""

    # Maximum file size for text analysis (10 MB)
    MAX_FILE_SIZE = 10 * 1024 * 1024

    # Supported text encodings to try
    ENCODINGS = ['utf-8', 'utf-16', 'latin-1', 'cp1252']

    @classmethod
    def read_text_file(
        cls,
        file_data: BinaryIO,
        max_size: int | None = None
    ) -> str:
        """
        Safely read a text file with encoding detection.

        Args:
            file_data: Binary file object
            max_size: Optional maximum file size (defaults to MAX_FILE_SIZE)

        Returns:
            Decoded text content

        Raises:
            ValueError: If file is too large or cannot be decoded
        """
        max_size = max_size or cls.MAX_FILE_SIZE

        # Read file content
        content = file_data.read(max_size + 1)

        if len(content) > max_size:
            raise ValueError(f"File too large: max {max_size} bytes")

        # Try different encodings
        for encoding in cls.ENCODINGS:
            try:
                text = content.decode(encoding)
                logger.info(f"Successfully decoded file with {encoding}")
                return text
            except UnicodeDecodeError:
                continue

        raise ValueError("Could not decode file with any supported encoding")

    @classmethod
    def search_text(
        cls,
        text: str,
        pattern: str,
        case_sensitive: bool = True,
        max_matches: int = 100
    ) -> dict[str, Any]:
        """
        Search for a regex pattern in text.

        Args:
            text: Text to search in
            pattern: Regex pattern to search for
            case_sensitive: Whether search is case-sensitive
            max_matches: Maximum number of matches to return

        Returns:
            Dictionary with search results:
            {
                'matches': [list of match dicts],
                'count': total number of matches,
                'pattern': the pattern used,
                'truncated': whether results were truncated
            }

        Raises:
            RegexValidationError: If pattern is unsafe
        """
        flags = 0 if case_sensitive else 2  # re.IGNORECASE = 2

        try:
            matches = RegexValidator.safe_search(
                pattern=pattern,
                text=text,
                flags=flags,
                max_matches=max_matches
            )

            return {
                'matches': matches,
                'count': len(matches),
                'pattern': pattern,
                'truncated': len(matches) >= max_matches,
                'case_sensitive': case_sensitive
            }

        except RegexValidationError as e:
            logger.error(f"Regex validation failed: {e}")
            raise

    @classmethod
    def count_lines(cls, text: str) -> int:
        """Count number of lines in text."""
        return text.count('\n') + 1 if text else 0

    @classmethod
    def count_words(cls, text: str) -> int:
        """Count number of words in text."""
        return len(text.split())

    @classmethod
    def count_characters(cls, text: str) -> int:
        """Count number of characters in text."""
        return len(text)

    @classmethod
    def analyze_file(
        cls,
        file_data: BinaryIO,
        pattern: str | None = None,
        case_sensitive: bool = True,
        max_matches: int = 100
    ) -> dict[str, Any]:
        """
        Analyze a text file with optional regex search.

        Args:
            file_data: Binary file object
            pattern: Optional regex pattern to search for
            case_sensitive: Whether search is case-sensitive
            max_matches: Maximum number of matches to return

        Returns:
            Analysis results dictionary with:
            - line_count: number of lines
            - word_count: number of words
            - char_count: number of characters
            - search_results: search results if pattern provided
            - text_sample: first 500 chars of text

        Raises:
            ValueError: If file cannot be read
            RegexValidationError: If pattern is unsafe
        """
        # Read text file
        text = cls.read_text_file(file_data)

        # Basic stats
        result = {
            'line_count': cls.count_lines(text),
            'word_count': cls.count_words(text),
            'char_count': cls.count_characters(text),
            'text_sample': text[:500] if len(text) > 500 else text,
            'truncated_sample': len(text) > 500
        }

        # Perform search if pattern provided
        if pattern:
            search_results = cls.search_text(
                text=text,
                pattern=pattern,
                case_sensitive=case_sensitive,
                max_matches=max_matches
            )
            result['search_results'] = search_results

        return result

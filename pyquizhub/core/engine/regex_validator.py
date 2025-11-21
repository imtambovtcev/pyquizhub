"""
Regex Safety Validator for PyQuizHub.

This module provides safe regex validation to prevent ReDoS (Regular Expression
Denial of Service) attacks and resource exhaustion.
"""

from __future__ import annotations

import re
import signal
from typing import Any
from pyquizhub.logging.setup import get_logger

logger = get_logger(__name__)


class RegexValidationError(Exception):
    """Raised when regex validation fails."""
    pass


class RegexTimeoutError(Exception):
    """Raised when regex execution times out."""
    pass


class RegexValidator:
    """Validates and executes regex patterns safely."""

    # Maximum allowed pattern length
    MAX_PATTERN_LENGTH = 500

    # Maximum allowed text length for search
    MAX_TEXT_LENGTH = 1_000_000  # 1 MB

    # Maximum execution time in seconds
    MAX_EXECUTION_TIME = 2

    # Dangerous patterns that indicate potential ReDoS
    REDOS_PATTERNS = [
        # Nested quantifiers (e.g., (a+)+, (a*)*, (a+)*)
        r'\([^)]*[+*]\)[+*{]',
        # Overlapping alternations (e.g., (a|a)+, (ab|a)+)
        r'\([^)]*\|[^)]*\)[+*{]',
        # Excessive backtracking potential
        r'(\.\*){3,}',  # Multiple .* in sequence
        r'(\.\+){3,}',  # Multiple .+ in sequence
    ]

    @classmethod
    def validate_pattern(cls, pattern: str) -> None:
        """
        Validate a regex pattern for safety.

        Args:
            pattern: The regex pattern to validate

        Raises:
            RegexValidationError: If pattern is unsafe
        """
        if not pattern:
            raise RegexValidationError("Empty pattern not allowed")

        if len(pattern) > cls.MAX_PATTERN_LENGTH:
            raise RegexValidationError(
                f"Pattern too long: {len(pattern)} chars (max {cls.MAX_PATTERN_LENGTH})"
            )

        # Check for dangerous patterns
        for dangerous in cls.REDOS_PATTERNS:
            if re.search(dangerous, pattern):
                raise RegexValidationError(
                    f"Pattern contains potentially dangerous construct: {dangerous}"
                )

        # Try to compile the pattern
        try:
            re.compile(pattern)
        except re.error as e:
            raise RegexValidationError(f"Invalid regex pattern: {e}")

        logger.debug(f"Regex pattern validated successfully: {pattern}")

    @classmethod
    def _timeout_handler(cls, signum, frame):
        """Signal handler for timeout."""
        raise RegexTimeoutError("Regex execution timed out")

    @classmethod
    def safe_search(
        cls,
        pattern: str,
        text: str,
        flags: int = 0,
        max_matches: int = 100
    ) -> list[dict[str, Any]]:
        """
        Safely search for a pattern in text with timeout protection.

        Args:
            pattern: Regex pattern to search for
            text: Text to search in
            flags: Optional regex flags (re.IGNORECASE, etc.)
            max_matches: Maximum number of matches to return

        Returns:
            List of match dictionaries with 'match', 'start', 'end', 'groups'

        Raises:
            RegexValidationError: If pattern is unsafe
            RegexTimeoutError: If execution times out
        """
        # Validate pattern first
        cls.validate_pattern(pattern)

        # Check text length
        if len(text) > cls.MAX_TEXT_LENGTH:
            raise RegexValidationError(
                f"Text too long: {len(text)} chars (max {cls.MAX_TEXT_LENGTH})"
            )

        # Compile pattern
        try:
            compiled = re.compile(pattern, flags)
        except re.error as e:
            raise RegexValidationError(f"Failed to compile pattern: {e}")

        # Set up timeout (Unix-only, for other systems we skip timeout)
        try:
            signal.signal(signal.SIGALRM, cls._timeout_handler)
            signal.alarm(cls.MAX_EXECUTION_TIME)
            timeout_set = True
        except (AttributeError, ValueError):
            # Windows or other systems without signal.SIGALRM
            timeout_set = False
            logger.warning("Regex timeout protection not available on this system")

        try:
            matches = []
            for i, match in enumerate(compiled.finditer(text)):
                if i >= max_matches:
                    logger.warning(f"Reached max matches limit: {max_matches}")
                    break

                matches.append({
                    'match': match.group(0),
                    'start': match.start(),
                    'end': match.end(),
                    'groups': match.groups()
                })

            return matches

        except RegexTimeoutError:
            logger.error(f"Regex execution timed out for pattern: {pattern}")
            raise
        except Exception as e:
            logger.error(f"Regex search failed: {e}")
            raise RegexValidationError(f"Regex search failed: {e}")
        finally:
            if timeout_set:
                signal.alarm(0)  # Disable alarm

    @classmethod
    def safe_match(
        cls,
        pattern: str,
        text: str,
        flags: int = 0
    ) -> dict[str, Any] | None:
        """
        Safely match a pattern against text (from beginning).

        Args:
            pattern: Regex pattern to match
            text: Text to match against
            flags: Optional regex flags

        Returns:
            Match dictionary or None if no match
        """
        cls.validate_pattern(pattern)

        if len(text) > cls.MAX_TEXT_LENGTH:
            raise RegexValidationError(
                f"Text too long: {len(text)} chars (max {cls.MAX_TEXT_LENGTH})"
            )

        try:
            compiled = re.compile(pattern, flags)
        except re.error as e:
            raise RegexValidationError(f"Failed to compile pattern: {e}")

        # Set up timeout
        try:
            signal.signal(signal.SIGALRM, cls._timeout_handler)
            signal.alarm(cls.MAX_EXECUTION_TIME)
            timeout_set = True
        except (AttributeError, ValueError):
            timeout_set = False
            logger.warning("Regex timeout protection not available on this system")

        try:
            match = compiled.match(text)
            if match:
                return {
                    'match': match.group(0),
                    'start': match.start(),
                    'end': match.end(),
                    'groups': match.groups()
                }
            return None
        except RegexTimeoutError:
            logger.error(f"Regex execution timed out for pattern: {pattern}")
            raise
        except Exception as e:
            logger.error(f"Regex match failed: {e}")
            raise RegexValidationError(f"Regex match failed: {e}")
        finally:
            if timeout_set:
                signal.alarm(0)

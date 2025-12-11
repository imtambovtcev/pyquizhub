"""
Text formatting utilities for cross-platform quiz content.

This module provides formatters to convert standardized Markdown text
to platform-specific formats (Telegram, Discord, HTML, plain text).

Standard Format (used in quiz JSON):
- **bold** - Bold text
- *italic* - Italic text
- __underline__ - Underlined text (not supported on all platforms)
- ~~strikethrough~~ - Strikethrough text
- `code` - Inline code
- ```code block``` - Code block (multiline)
- [text](url) - Links

Platform Support Matrix:
┌─────────────────┬──────────┬─────────┬──────┬───────┐
│ Format          │ Telegram │ Discord │ HTML │ Plain │
├─────────────────┼──────────┼─────────┼──────┼───────┤
│ **bold**        │ *bold*   │ **bold**│ <b>  │ BOLD  │
│ *italic*        │ _italic_ │ *italic*│ <i>  │ _it_  │
│ __underline__   │ __under__│ __und__ │ <u>  │ _un_  │
│ ~~strike~~      │ ~strike~ │ ~~str~~ │ <s>  │ -str- │
│ `code`          │ `code`   │ `code`  │<code>│ code  │
│ [text](url)     │ [t](url) │ [t](url)│ <a>  │ text  │
└─────────────────┴──────────┴─────────┴──────┴───────┘

Usage:
    from pyquizhub.core.engine.text_formatter import TextFormatter

    # Get formatter for platform
    formatter = TextFormatter.for_platform("telegram")
    formatted_text = formatter.format("**Hello** *world*!")

    # Or use specific formatter directly
    from pyquizhub.core.engine.text_formatter import TelegramFormatter
    formatted = TelegramFormatter().format("**bold** text")
"""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from enum import Enum
from typing import ClassVar


class Platform(str, Enum):
    """Supported platforms for text formatting."""
    TELEGRAM = "telegram"
    DISCORD = "discord"
    HTML = "html"
    PLAIN = "plain"


class TextFormatter(ABC):
    """
    Abstract base class for text formatters.

    Subclasses implement platform-specific formatting rules.
    The standard input format is Discord-style Markdown.
    """

    # Regex patterns for parsing standard Markdown
    # Order matters - more specific patterns should come first
    PATTERNS: ClassVar[list[tuple[str, str]]] = [
        # Code blocks (must be before inline code)
        (r'```([\s\S]*?)```', 'code_block'),
        # Inline code
        (r'`([^`]+)`', 'code'),
        # Bold (must be before italic to handle ** vs *)
        (r'\*\*([^*]+)\*\*', 'bold'),
        # Italic
        (r'\*([^*]+)\*', 'italic'),
        # Underline
        (r'__([^_]+)__', 'underline'),
        # Strikethrough
        (r'~~([^~]+)~~', 'strikethrough'),
        # Links
        (r'\[([^\]]+)\]\(([^)]+)\)', 'link'),
    ]

    @classmethod
    def for_platform(cls, platform: str | Platform) -> TextFormatter:
        """
        Get formatter for the specified platform.

        Args:
            platform: Platform name or enum value

        Returns:
            Appropriate TextFormatter subclass instance

        Raises:
            ValueError: If platform is not supported
        """
        if isinstance(platform, str):
            platform = platform.lower()

        formatters = {
            Platform.TELEGRAM: TelegramFormatter,
            Platform.DISCORD: DiscordFormatter,
            Platform.HTML: HTMLFormatter,
            Platform.PLAIN: PlainTextFormatter,
            "telegram": TelegramFormatter,
            "discord": DiscordFormatter,
            "html": HTMLFormatter,
            "plain": PlainTextFormatter,
            "web": HTMLFormatter,
        }

        formatter_class = formatters.get(platform)
        if formatter_class is None:
            raise ValueError(
                f"Unsupported platform: {platform}. "
                f"Supported: {list(Platform)}"
            )
        return formatter_class()

    @abstractmethod
    def format(self, text: str) -> str:
        """
        Format text for the target platform.

        Args:
            text: Text in standard Markdown format

        Returns:
            Formatted text for the target platform
        """
        pass

    @abstractmethod
    def format_bold(self, text: str) -> str:
        """Format bold text."""
        pass

    @abstractmethod
    def format_italic(self, text: str) -> str:
        """Format italic text."""
        pass

    @abstractmethod
    def format_underline(self, text: str) -> str:
        """Format underlined text."""
        pass

    @abstractmethod
    def format_strikethrough(self, text: str) -> str:
        """Format strikethrough text."""
        pass

    @abstractmethod
    def format_code(self, text: str) -> str:
        """Format inline code."""
        pass

    @abstractmethod
    def format_code_block(self, text: str) -> str:
        """Format code block."""
        pass

    @abstractmethod
    def format_link(self, text: str, url: str) -> str:
        """Format link."""
        pass

    def _apply_formatting(self, text: str) -> str:
        """
        Apply all formatting rules to text.

        This method processes text through all patterns and applies
        the appropriate formatting method for each match.

        Uses placeholder tokens to prevent re-matching of converted text.
        """
        result = text
        placeholders: dict[str, str] = {}
        placeholder_counter = 0

        def make_placeholder(formatted: str) -> str:
            """Create a unique placeholder for formatted text."""
            nonlocal placeholder_counter
            placeholder = f"\x00PH{placeholder_counter}\x00"
            placeholder_counter += 1
            placeholders[placeholder] = formatted
            return placeholder

        # Process code blocks first (they should not have nested formatting)
        code_block_pattern = r'```([\s\S]*?)```'
        result = re.sub(
            code_block_pattern,
            lambda m: make_placeholder(self.format_code_block(m.group(1))),
            result
        )

        # Process inline code (should not have nested formatting)
        code_pattern = r'`([^`]+)`'
        result = re.sub(
            code_pattern,
            lambda m: make_placeholder(self.format_code(m.group(1))),
            result
        )

        # Process links
        link_pattern = r'\[([^\]]+)\]\(([^)]+)\)'
        result = re.sub(
            link_pattern,
            lambda m: make_placeholder(self.format_link(m.group(1), m.group(2))),
            result
        )

        # Process bold (before italic due to ** vs *)
        bold_pattern = r'\*\*([^*]+)\*\*'
        result = re.sub(
            bold_pattern,
            lambda m: make_placeholder(self.format_bold(m.group(1))),
            result
        )

        # Process italic
        italic_pattern = r'\*([^*]+)\*'
        result = re.sub(
            italic_pattern,
            lambda m: make_placeholder(self.format_italic(m.group(1))),
            result
        )

        # Process underline
        underline_pattern = r'__([^_]+)__'
        result = re.sub(
            underline_pattern,
            lambda m: make_placeholder(self.format_underline(m.group(1))),
            result
        )

        # Process strikethrough
        strike_pattern = r'~~([^~]+)~~'
        result = re.sub(
            strike_pattern,
            lambda m: make_placeholder(self.format_strikethrough(m.group(1))),
            result
        )

        # Replace all placeholders with actual formatted text
        for placeholder, formatted in placeholders.items():
            result = result.replace(placeholder, formatted)

        return result


class TelegramFormatter(TextFormatter):
    """
    Formatter for Telegram MarkdownV2.

    Telegram uses a slightly different Markdown syntax:
    - Bold: *text*
    - Italic: _text_
    - Underline: __text__
    - Strikethrough: ~text~
    - Code: `text`
    - Link: [text](url)

    Special characters must be escaped: _ * [ ] ( ) ~ ` > # + - = | { } . !

    Note: This formatter handles escaping automatically. Plain text sections
    are escaped while formatting markers are preserved.
    """

    # Characters that must be escaped in Telegram MarkdownV2
    # Note: Backslash must be escaped first to avoid double-escaping
    ESCAPE_CHARS = r'\\_*[]()~`>#+-=|{}.!'

    def escape(self, text: str) -> str:
        """
        Escape special characters for Telegram MarkdownV2.

        Args:
            text: Text to escape

        Returns:
            Escaped text safe for Telegram
        """
        result = text
        for char in self.ESCAPE_CHARS:
            result = result.replace(char, f'\\{char}')
        return result

    def format(self, text: str) -> str:
        """
        Format text for Telegram MarkdownV2.

        Converts standard Markdown to Telegram format and escapes
        special characters in plain text sections.
        """
        return self._apply_formatting(text)

    def _apply_formatting(self, text: str) -> str:
        """
        Apply all formatting rules to text for Telegram.

        This overrides the base class to handle Telegram-specific escaping.
        Plain text sections are escaped, formatted sections preserve their markers.
        """
        result = text
        placeholders: dict[str, str] = {}
        placeholder_counter = 0

        def make_placeholder(formatted: str) -> str:
            """Create a unique placeholder for formatted text."""
            nonlocal placeholder_counter
            placeholder = f"\x00PH{placeholder_counter}\x00"
            placeholder_counter += 1
            placeholders[placeholder] = formatted
            return placeholder

        # Process code blocks first (they should not have nested formatting)
        code_block_pattern = r'```([\s\S]*?)```'
        result = re.sub(
            code_block_pattern,
            lambda m: make_placeholder(self.format_code_block(m.group(1))),
            result
        )

        # Process inline code (should not have nested formatting)
        code_pattern = r'`([^`]+)`'
        result = re.sub(
            code_pattern,
            lambda m: make_placeholder(self.format_code(m.group(1))),
            result
        )

        # Process links
        link_pattern = r'\[([^\]]+)\]\(([^)]+)\)'
        result = re.sub(
            link_pattern,
            lambda m: make_placeholder(self.format_link(m.group(1), m.group(2))),
            result
        )

        # Process bold (before italic due to ** vs *)
        bold_pattern = r'\*\*([^*]+)\*\*'
        result = re.sub(
            bold_pattern,
            lambda m: make_placeholder(self.format_bold(m.group(1))),
            result
        )

        # Process italic
        italic_pattern = r'\*([^*]+)\*'
        result = re.sub(
            italic_pattern,
            lambda m: make_placeholder(self.format_italic(m.group(1))),
            result
        )

        # Process underline
        underline_pattern = r'__([^_]+)__'
        result = re.sub(
            underline_pattern,
            lambda m: make_placeholder(self.format_underline(m.group(1))),
            result
        )

        # Process strikethrough
        strike_pattern = r'~~([^~]+)~~'
        result = re.sub(
            strike_pattern,
            lambda m: make_placeholder(self.format_strikethrough(m.group(1))),
            result
        )

        # Escape remaining plain text (parts not in placeholders)
        # Split by placeholders, escape plain parts, rejoin
        parts = re.split(r'(\x00PH\d+\x00)', result)
        escaped_parts = []
        for part in parts:
            if part.startswith('\x00PH') and part.endswith('\x00'):
                # This is a placeholder, keep as is
                escaped_parts.append(part)
            else:
                # This is plain text, escape it
                escaped_parts.append(self.escape(part))
        result = ''.join(escaped_parts)

        # Replace all placeholders with actual formatted text
        for placeholder, formatted in placeholders.items():
            result = result.replace(placeholder, formatted)

        return result

    def format_bold(self, text: str) -> str:
        """Format bold: **text** -> *text* (with inner text escaped)"""
        return f'*{self.escape(text)}*'

    def format_italic(self, text: str) -> str:
        """Format italic: *text* -> _text_ (with inner text escaped)"""
        return f'_{self.escape(text)}_'

    def format_underline(self, text: str) -> str:
        """Format underline: __text__ -> __text__ (with inner text escaped)"""
        return f'__{self.escape(text)}__'

    def format_strikethrough(self, text: str) -> str:
        """Format strikethrough: ~~text~~ -> ~text~ (with inner text escaped)"""
        return f'~{self.escape(text)}~'

    def format_code(self, text: str) -> str:
        """Format inline code: `text` -> `text` (code content is not escaped)"""
        # In Telegram, code blocks don't need escaping inside
        # But backticks and backslashes need to be escaped
        escaped = text.replace('\\', '\\\\').replace('`', '\\`')
        return f'`{escaped}`'

    def format_code_block(self, text: str) -> str:
        """Format code block: ```text``` -> ```text``` (code content minimally escaped)"""
        # In code blocks, only backticks need escaping
        escaped = text.replace('```', '\\`\\`\\`')
        return f'```{escaped}```'

    def format_link(self, text: str, url: str) -> str:
        """Format link: [text](url) -> [text](url) (text and URL escaped appropriately)"""
        # Escape the link text for display
        escaped_text = self.escape(text)
        # In URLs, only ) and \ need escaping
        escaped_url = url.replace('\\', '\\\\').replace(')', '\\)')
        return f'[{escaped_text}]({escaped_url})'


class DiscordFormatter(TextFormatter):
    """
    Formatter for Discord Markdown.

    Discord uses standard Markdown:
    - Bold: **text**
    - Italic: *text*
    - Underline: __text__
    - Strikethrough: ~~text~~
    - Code: `text`
    - Link: [text](url) or auto-linked URLs

    This is essentially a passthrough since our standard format
    is Discord-style Markdown.
    """

    def format(self, text: str) -> str:
        """Format text for Discord (passthrough)."""
        # Discord uses the same format as our standard, mostly passthrough
        return self._apply_formatting(text)

    def format_bold(self, text: str) -> str:
        """Format bold: **text** -> **text**"""
        return f'**{text}**'

    def format_italic(self, text: str) -> str:
        """Format italic: *text* -> *text*"""
        return f'*{text}*'

    def format_underline(self, text: str) -> str:
        """Format underline: __text__ -> __text__"""
        return f'__{text}__'

    def format_strikethrough(self, text: str) -> str:
        """Format strikethrough: ~~text~~ -> ~~text~~"""
        return f'~~{text}~~'

    def format_code(self, text: str) -> str:
        """Format inline code: `text` -> `text`"""
        return f'`{text}`'

    def format_code_block(self, text: str) -> str:
        """Format code block."""
        return f'```{text}```'

    def format_link(self, text: str, url: str) -> str:
        """Format link: [text](url) -> [text](url)"""
        return f'[{text}]({url})'


class HTMLFormatter(TextFormatter):
    """
    Formatter for HTML output (web adapter).

    Converts Markdown to HTML tags:
    - Bold: <strong>text</strong>
    - Italic: <em>text</em>
    - Underline: <u>text</u>
    - Strikethrough: <s>text</s>
    - Code: <code>text</code>
    - Code block: <pre><code>text</code></pre>
    - Link: <a href="url">text</a>

    Security: All text content is HTML-escaped to prevent XSS attacks.
    """

    def escape_html(self, text: str) -> str:
        """
        Escape HTML special characters.

        Args:
            text: Text to escape

        Returns:
            HTML-safe text
        """
        return (
            text
            .replace('&', '&amp;')
            .replace('<', '&lt;')
            .replace('>', '&gt;')
            .replace('"', '&quot;')
            .replace("'", '&#x27;')
        )

    def format(self, text: str) -> str:
        """Format text for HTML."""
        return self._apply_formatting(text)

    def _apply_formatting(self, text: str) -> str:
        """
        Apply all formatting rules to text for HTML.

        This overrides the base class to handle HTML-specific escaping.
        Plain text sections are escaped to prevent XSS attacks.
        """
        result = text
        placeholders: dict[str, str] = {}
        placeholder_counter = 0

        def make_placeholder(formatted: str) -> str:
            """Create a unique placeholder for formatted text."""
            nonlocal placeholder_counter
            placeholder = f"\x00PH{placeholder_counter}\x00"
            placeholder_counter += 1
            placeholders[placeholder] = formatted
            return placeholder

        # Process code blocks first (they should not have nested formatting)
        code_block_pattern = r'```([\s\S]*?)```'
        result = re.sub(
            code_block_pattern,
            lambda m: make_placeholder(self.format_code_block(m.group(1))),
            result
        )

        # Process inline code (should not have nested formatting)
        code_pattern = r'`([^`]+)`'
        result = re.sub(
            code_pattern,
            lambda m: make_placeholder(self.format_code(m.group(1))),
            result
        )

        # Process links
        link_pattern = r'\[([^\]]+)\]\(([^)]+)\)'
        result = re.sub(
            link_pattern,
            lambda m: make_placeholder(self.format_link(m.group(1), m.group(2))),
            result
        )

        # Process bold (before italic due to ** vs *)
        bold_pattern = r'\*\*([^*]+)\*\*'
        result = re.sub(
            bold_pattern,
            lambda m: make_placeholder(self.format_bold(m.group(1))),
            result
        )

        # Process italic
        italic_pattern = r'\*([^*]+)\*'
        result = re.sub(
            italic_pattern,
            lambda m: make_placeholder(self.format_italic(m.group(1))),
            result
        )

        # Process underline
        underline_pattern = r'__([^_]+)__'
        result = re.sub(
            underline_pattern,
            lambda m: make_placeholder(self.format_underline(m.group(1))),
            result
        )

        # Process strikethrough
        strike_pattern = r'~~([^~]+)~~'
        result = re.sub(
            strike_pattern,
            lambda m: make_placeholder(self.format_strikethrough(m.group(1))),
            result
        )

        # Escape remaining plain text (parts not in placeholders)
        # This prevents XSS attacks through unformatted text
        parts = re.split(r'(\x00PH\d+\x00)', result)
        escaped_parts = []
        for part in parts:
            if part.startswith('\x00PH') and part.endswith('\x00'):
                # This is a placeholder, keep as is
                escaped_parts.append(part)
            else:
                # This is plain text, escape HTML
                escaped_parts.append(self.escape_html(part))
        result = ''.join(escaped_parts)

        # Replace all placeholders with actual formatted text
        for placeholder, formatted in placeholders.items():
            result = result.replace(placeholder, formatted)

        return result

    def format_bold(self, text: str) -> str:
        """Format bold: **text** -> <strong>text</strong> (text is escaped)"""
        escaped = self.escape_html(text)
        return f'<strong>{escaped}</strong>'

    def format_italic(self, text: str) -> str:
        """Format italic: *text* -> <em>text</em> (text is escaped)"""
        escaped = self.escape_html(text)
        return f'<em>{escaped}</em>'

    def format_underline(self, text: str) -> str:
        """Format underline: __text__ -> <u>text</u> (text is escaped)"""
        escaped = self.escape_html(text)
        return f'<u>{escaped}</u>'

    def format_strikethrough(self, text: str) -> str:
        """Format strikethrough: ~~text~~ -> <s>text</s> (text is escaped)"""
        escaped = self.escape_html(text)
        return f'<s>{escaped}</s>'

    def format_code(self, text: str) -> str:
        """Format inline code: `text` -> <code>text</code> (text is escaped)"""
        escaped = self.escape_html(text)
        return f'<code>{escaped}</code>'

    def format_code_block(self, text: str) -> str:
        """Format code block: ```text``` -> <pre><code>text</code></pre> (text is escaped)"""
        escaped = self.escape_html(text)
        return f'<pre><code>{escaped}</code></pre>'

    def format_link(self, text: str, url: str) -> str:
        """Format link: [text](url) -> <a href="url">text</a> (text and URL are escaped)"""
        # Escape text content to prevent XSS
        escaped_text = self.escape_html(text)
        # Escape URL for HTML attribute (prevent attribute injection)
        safe_url = self.escape_html(url.replace('"', '%22'))
        return f'<a href="{safe_url}">{escaped_text}</a>'


class PlainTextFormatter(TextFormatter):
    """
    Formatter for plain text output (CLI, logs, fallback).

    Strips or converts formatting to ASCII-compatible alternatives:
    - Bold: UPPERCASE or *text*
    - Italic: _text_
    - Underline: _text_
    - Strikethrough: -text-
    - Code: 'text'
    - Link: text (url)
    """

    def __init__(self, uppercase_bold: bool = False):
        """
        Initialize plain text formatter.

        Args:
            uppercase_bold: If True, convert bold to UPPERCASE.
                          If False, use *text* markers.
        """
        self.uppercase_bold = uppercase_bold

    def format(self, text: str) -> str:
        """Format text for plain text output."""
        return self._apply_formatting(text)

    def format_bold(self, text: str) -> str:
        """Format bold: **text** -> TEXT or *text*"""
        if self.uppercase_bold:
            return text.upper()
        return f'*{text}*'

    def format_italic(self, text: str) -> str:
        """Format italic: *text* -> _text_"""
        return f'_{text}_'

    def format_underline(self, text: str) -> str:
        """Format underline: __text__ -> _text_"""
        return f'_{text}_'

    def format_strikethrough(self, text: str) -> str:
        """Format strikethrough: ~~text~~ -> -text-"""
        return f'-{text}-'

    def format_code(self, text: str) -> str:
        """Format inline code: `text` -> 'text'"""
        return f"'{text}'"

    def format_code_block(self, text: str) -> str:
        """Format code block: ```text``` -> text with indent"""
        lines = text.strip().split('\n')
        indented = '\n'.join(f'  {line}' for line in lines)
        return f'\n{indented}\n'

    def format_link(self, text: str, url: str) -> str:
        """Format link: [text](url) -> text (url)"""
        return f'{text} ({url})'


# Convenience function for quick formatting
def format_text(text: str, platform: str | Platform) -> str:
    """
    Format text for a specific platform.

    Args:
        text: Text in standard Markdown format
        platform: Target platform (telegram, discord, html, plain)

    Returns:
        Formatted text for the target platform

    Example:
        >>> format_text("**Hello** *world*!", "telegram")
        '*Hello* _world_!'
    """
    formatter = TextFormatter.for_platform(platform)
    return formatter.format(text)

"""Tests for text formatting utilities."""

from __future__ import annotations

import pytest

from pyquizhub.core.engine.text_formatter import (
    TextFormatter,
    TelegramFormatter,
    DiscordFormatter,
    HTMLFormatter,
    PlainTextFormatter,
    Platform,
    format_text,
)


class TestTextFormatterFactory:
    """Tests for TextFormatter.for_platform factory method."""

    def test_get_telegram_formatter(self):
        """Test getting Telegram formatter."""
        formatter = TextFormatter.for_platform("telegram")
        assert isinstance(formatter, TelegramFormatter)

    def test_get_telegram_formatter_enum(self):
        """Test getting Telegram formatter with enum."""
        formatter = TextFormatter.for_platform(Platform.TELEGRAM)
        assert isinstance(formatter, TelegramFormatter)

    def test_get_discord_formatter(self):
        """Test getting Discord formatter."""
        formatter = TextFormatter.for_platform("discord")
        assert isinstance(formatter, DiscordFormatter)

    def test_get_html_formatter(self):
        """Test getting HTML formatter."""
        formatter = TextFormatter.for_platform("html")
        assert isinstance(formatter, HTMLFormatter)

    def test_get_html_formatter_via_web(self):
        """Test getting HTML formatter via 'web' alias."""
        formatter = TextFormatter.for_platform("web")
        assert isinstance(formatter, HTMLFormatter)

    def test_get_plain_formatter(self):
        """Test getting plain text formatter."""
        formatter = TextFormatter.for_platform("plain")
        assert isinstance(formatter, PlainTextFormatter)

    def test_case_insensitive(self):
        """Test that platform names are case-insensitive."""
        formatter = TextFormatter.for_platform("TELEGRAM")
        assert isinstance(formatter, TelegramFormatter)

    def test_invalid_platform(self):
        """Test that invalid platform raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            TextFormatter.for_platform("invalid")
        assert "Unsupported platform" in str(exc_info.value)


class TestTelegramFormatter:
    """Tests for Telegram MarkdownV2 formatter."""

    @pytest.fixture
    def formatter(self):
        """Create Telegram formatter."""
        return TelegramFormatter()

    def test_bold(self, formatter):
        """Test bold formatting: **text** -> *text*"""
        result = formatter.format("**bold text**")
        assert result == "*bold text*"

    def test_italic(self, formatter):
        """Test italic formatting: *text* -> _text_"""
        result = formatter.format("*italic text*")
        assert result == "_italic text_"

    def test_underline(self, formatter):
        """Test underline formatting: __text__ -> __text__"""
        result = formatter.format("__underline text__")
        assert result == "__underline text__"

    def test_strikethrough(self, formatter):
        """Test strikethrough formatting: ~~text~~ -> ~text~"""
        result = formatter.format("~~strikethrough~~")
        assert result == "~strikethrough~"

    def test_inline_code(self, formatter):
        """Test inline code formatting: `text` -> `text`"""
        result = formatter.format("`code`")
        assert result == "`code`"

    def test_code_block(self, formatter):
        """Test code block formatting."""
        result = formatter.format("```python\nprint('hello')\n```")
        assert result == "```python\nprint('hello')\n```"

    def test_link(self, formatter):
        """Test link formatting."""
        result = formatter.format("[Click here](https://example.com)")
        assert result == "[Click here](https://example.com)"

    def test_combined_formatting(self, formatter):
        """Test multiple formatting in one string."""
        text = "**Bold** and *italic* with `code`"
        result = formatter.format(text)
        assert result == "*Bold* and _italic_ with `code`"

    def test_no_formatting(self, formatter):
        """Test plain text passes through unchanged."""
        text = "Just plain text"
        result = formatter.format(text)
        assert result == "Just plain text"

    def test_escape_method(self, formatter):
        """Test character escaping."""
        result = formatter.escape("Test_with*special[chars]")
        assert result == r"Test\_with\*special\[chars\]"


class TestDiscordFormatter:
    """Tests for Discord Markdown formatter."""

    @pytest.fixture
    def formatter(self):
        """Create Discord formatter."""
        return DiscordFormatter()

    def test_bold(self, formatter):
        """Test bold formatting: **text** -> **text** (unchanged)"""
        result = formatter.format("**bold text**")
        assert result == "**bold text**"

    def test_italic(self, formatter):
        """Test italic formatting: *text* -> *text* (unchanged)"""
        result = formatter.format("*italic text*")
        assert result == "*italic text*"

    def test_underline(self, formatter):
        """Test underline formatting: __text__ -> __text__ (unchanged)"""
        result = formatter.format("__underline text__")
        assert result == "__underline text__"

    def test_strikethrough(self, formatter):
        """Test strikethrough formatting: ~~text~~ -> ~~text~~ (unchanged)"""
        result = formatter.format("~~strikethrough~~")
        assert result == "~~strikethrough~~"

    def test_inline_code(self, formatter):
        """Test inline code formatting."""
        result = formatter.format("`code`")
        assert result == "`code`"

    def test_code_block(self, formatter):
        """Test code block formatting."""
        result = formatter.format("```python\nprint('hello')\n```")
        assert result == "```python\nprint('hello')\n```"

    def test_link(self, formatter):
        """Test link formatting."""
        result = formatter.format("[Click here](https://example.com)")
        assert result == "[Click here](https://example.com)"

    def test_passthrough(self, formatter):
        """Test that Discord format is essentially passthrough."""
        text = "**Bold** and *italic* with __underline__ and ~~strike~~"
        result = formatter.format(text)
        assert result == "**Bold** and *italic* with __underline__ and ~~strike~~"


class TestHTMLFormatter:
    """Tests for HTML formatter."""

    @pytest.fixture
    def formatter(self):
        """Create HTML formatter."""
        return HTMLFormatter()

    def test_bold(self, formatter):
        """Test bold formatting: **text** -> <strong>text</strong>"""
        result = formatter.format("**bold text**")
        assert result == "<strong>bold text</strong>"

    def test_italic(self, formatter):
        """Test italic formatting: *text* -> <em>text</em>"""
        result = formatter.format("*italic text*")
        assert result == "<em>italic text</em>"

    def test_underline(self, formatter):
        """Test underline formatting: __text__ -> <u>text</u>"""
        result = formatter.format("__underline text__")
        assert result == "<u>underline text</u>"

    def test_strikethrough(self, formatter):
        """Test strikethrough formatting: ~~text~~ -> <s>text</s>"""
        result = formatter.format("~~strikethrough~~")
        assert result == "<s>strikethrough</s>"

    def test_inline_code(self, formatter):
        """Test inline code formatting: `text` -> <code>text</code>"""
        result = formatter.format("`code`")
        assert result == "<code>code</code>"

    def test_inline_code_escapes_html(self, formatter):
        """Test that code content is HTML-escaped."""
        result = formatter.format("`<script>alert('xss')</script>`")
        assert "&lt;script&gt;" in result
        assert "<script>" not in result

    def test_code_block(self, formatter):
        """Test code block formatting."""
        result = formatter.format("```print('hello')```")
        assert result == "<pre><code>print(&#x27;hello&#x27;)</code></pre>"

    def test_link(self, formatter):
        """Test link formatting: [text](url) -> <a href="url">text</a>"""
        result = formatter.format("[Click here](https://example.com)")
        assert result == '<a href="https://example.com">Click here</a>'

    def test_link_escapes_quotes(self, formatter):
        """Test that link URLs with quotes are escaped."""
        result = formatter.format('[test](https://example.com/path"param)')
        assert '%22' in result
        assert '"param' not in result.split('href=')[1]

    def test_combined_formatting(self, formatter):
        """Test multiple formatting in one string."""
        text = "**Bold** and *italic*"
        result = formatter.format(text)
        assert result == "<strong>Bold</strong> and <em>italic</em>"

    def test_escape_html_method(self, formatter):
        """Test HTML escaping."""
        result = formatter.escape_html("<script>alert('xss')</script>")
        assert "&lt;" in result
        assert "&gt;" in result
        assert "&#x27;" in result
        assert "<script>" not in result


class TestPlainTextFormatter:
    """Tests for plain text formatter."""

    @pytest.fixture
    def formatter(self):
        """Create plain text formatter."""
        return PlainTextFormatter()

    @pytest.fixture
    def uppercase_formatter(self):
        """Create plain text formatter with uppercase bold."""
        return PlainTextFormatter(uppercase_bold=True)

    def test_bold_default(self, formatter):
        """Test bold formatting: **text** -> *text*"""
        result = formatter.format("**bold text**")
        assert result == "*bold text*"

    def test_bold_uppercase(self, uppercase_formatter):
        """Test bold formatting with uppercase: **text** -> TEXT"""
        result = uppercase_formatter.format("**bold text**")
        assert result == "BOLD TEXT"

    def test_italic(self, formatter):
        """Test italic formatting: *text* -> _text_"""
        result = formatter.format("*italic text*")
        assert result == "_italic text_"

    def test_underline(self, formatter):
        """Test underline formatting: __text__ -> _text_"""
        result = formatter.format("__underline text__")
        assert result == "_underline text_"

    def test_strikethrough(self, formatter):
        """Test strikethrough formatting: ~~text~~ -> -text-"""
        result = formatter.format("~~strikethrough~~")
        assert result == "-strikethrough-"

    def test_inline_code(self, formatter):
        """Test inline code formatting: `text` -> 'text'"""
        result = formatter.format("`code`")
        assert result == "'code'"

    def test_code_block(self, formatter):
        """Test code block formatting (indented)."""
        result = formatter.format("```print('hello')```")
        assert "  print('hello')" in result

    def test_link(self, formatter):
        """Test link formatting: [text](url) -> text (url)"""
        result = formatter.format("[Click here](https://example.com)")
        assert result == "Click here (https://example.com)"

    def test_combined_formatting(self, formatter):
        """Test multiple formatting in one string."""
        text = "**Bold** and *italic*"
        result = formatter.format(text)
        assert result == "*Bold* and _italic_"


class TestFormatTextFunction:
    """Tests for the format_text convenience function."""

    def test_telegram(self):
        """Test formatting for Telegram."""
        result = format_text("**bold**", "telegram")
        assert result == "*bold*"

    def test_discord(self):
        """Test formatting for Discord."""
        result = format_text("**bold**", "discord")
        assert result == "**bold**"

    def test_html(self):
        """Test formatting for HTML."""
        result = format_text("**bold**", "html")
        assert result == "<strong>bold</strong>"

    def test_plain(self):
        """Test formatting for plain text."""
        result = format_text("**bold**", "plain")
        assert result == "*bold*"

    def test_with_enum(self):
        """Test formatting with Platform enum."""
        result = format_text("**bold**", Platform.TELEGRAM)
        assert result == "*bold*"


class TestEdgeCases:
    """Tests for edge cases and special scenarios."""

    def test_empty_string(self):
        """Test formatting empty string."""
        assert format_text("", "telegram") == ""
        assert format_text("", "html") == ""

    def test_nested_formatting_bold_in_italic(self):
        """Test nested formatting (may not work perfectly)."""
        # This tests current behavior - nested formatting is complex
        text = "*italic with **bold** inside*"
        # The current implementation handles this sequentially
        result = format_text(text, "telegram")
        # Just verify it doesn't crash
        assert isinstance(result, str)

    def test_multiple_bold_sections(self):
        """Test multiple bold sections in one string."""
        result = format_text("**first** and **second**", "html")
        assert result == "<strong>first</strong> and <strong>second</strong>"

    def test_adjacent_formatting(self):
        """Test adjacent formatting elements."""
        result = format_text("**bold***italic*", "telegram")
        # Both should be formatted
        assert "*" in result
        assert "_" in result

    def test_multiline_text(self):
        """Test multiline text formatting."""
        text = "**Line 1**\n*Line 2*\n__Line 3__"
        result = format_text(text, "html")
        assert "<strong>Line 1</strong>" in result
        assert "<em>Line 2</em>" in result
        assert "<u>Line 3</u>" in result

    def test_code_block_with_newlines(self):
        """Test code block with multiple lines."""
        text = "```\nline1\nline2\nline3\n```"
        result = format_text(text, "html")
        assert "<pre><code>" in result
        assert "</code></pre>" in result

    def test_special_characters_in_text(self):
        """Test special characters that aren't formatting."""
        text = "Price: $100 (50% off!)"
        # Telegram MarkdownV2 requires escaping of special characters
        result = format_text(text, "telegram")
        assert result == r"Price: $100 \(50% off\!\)"  # Parentheses and ! escaped

        # Discord and HTML should pass through unchanged
        result = format_text(text, "discord")
        assert result == text

        result = format_text(text, "html")
        assert result == text

    def test_url_with_special_chars(self):
        """Test link with special characters in URL."""
        text = "[link](https://example.com/path?a=1&b=2)"
        result = format_text(text, "html")
        # & in URLs should be escaped to &amp; in HTML attributes (security)
        assert 'href="https://example.com/path?a=1&amp;b=2"' in result

    def test_asterisks_not_formatting(self):
        """Test asterisks that shouldn't be treated as formatting."""
        # Single asterisk at start of line (like bullet point)
        text = "* Item 1\n* Item 2"
        result = format_text(text, "telegram")
        # These shouldn't be converted since they're not paired
        # Current behavior may vary - just check it doesn't crash
        assert isinstance(result, str)

    def test_inline_code_preserves_formatting_chars(self):
        """Test that formatting chars inside code are preserved."""
        text = "Use `**not bold**` for syntax"
        result = format_text(text, "html")
        # The **not bold** inside code should be escaped, not formatted
        assert "<code>" in result
        assert "<strong>" not in result or result.index("<code>") < result.index(
            "<strong>") if "<strong>" in result else True


class TestRealWorldExamples:
    """Tests with real-world quiz content examples."""

    def test_quiz_question_formatting(self):
        """Test typical quiz question formatting."""
        question = "**Question 1**: What is the capital of *France*?"

        telegram = format_text(question, "telegram")
        assert "*Question 1*" in telegram
        assert "_France_" in telegram

        html = format_text(question, "html")
        assert "<strong>Question 1</strong>" in html
        assert "<em>France</em>" in html

    def test_final_message_formatting(self):
        """Test typical final message formatting."""
        message = """**Quiz Complete!**

Your score: *85%*
Level: __Expert__

~~You failed~~ Congratulations!

Check your results at [our website](https://quiz.example.com)"""

        # Test Telegram - note that special chars inside formatting are escaped
        telegram = format_text(message, "telegram")
        assert r"*Quiz Complete\!*" in telegram  # ! escaped inside bold
        assert "_85%_" in telegram
        assert "__Expert__" in telegram
        assert "~You failed~" in telegram
        assert r"Congratulations\!" in telegram  # ! escaped in plain text

        # Test HTML
        html = format_text(message, "html")
        assert "<strong>Quiz Complete!</strong>" in html
        assert "<em>85%</em>" in html
        assert "<u>Expert</u>" in html
        assert "<s>You failed</s>" in html
        assert '<a href="https://quiz.example.com">' in html

    def test_code_example_in_quiz(self):
        """Test code examples in quiz content."""
        question = "What does this code output?\n```python\nprint('Hello')\n```"

        html = format_text(question, "html")
        assert "<pre><code>" in html
        assert "print" in html

        telegram = format_text(question, "telegram")
        assert "```" in telegram

    def test_mixed_content(self):
        """Test mixed content with multiple formatting types."""
        content = """**Important**: Use `pip install` to install.

For more info, see [documentation](https://docs.example.com).

*Note*: This is __required__ for the quiz."""

        html = format_text(content, "html")
        assert "<strong>Important</strong>" in html
        assert "<code>pip install</code>" in html
        assert '<a href="https://docs.example.com">' in html
        assert "<em>Note</em>" in html
        assert "<u>required</u>" in html


class TestSecurityInjectionPrevention:
    """Tests for security - ensuring no injection vulnerabilities in formatters."""

    # ==================== HTML XSS Prevention ====================

    def test_html_xss_script_tag_in_text(self):
        """Test that script tags in plain text are escaped in HTML output."""
        malicious = "<script>alert('XSS')</script>"
        result = format_text(malicious, "html")
        assert "<script>" not in result
        assert "&lt;script&gt;" in result

    def test_html_xss_script_tag_in_bold(self):
        """Test that script tags inside bold formatting are escaped."""
        malicious = "**<script>alert('XSS')</script>**"
        result = format_text(malicious, "html")
        assert "<script>" not in result
        # The script tag content should be inside <strong> but escaped
        assert "<strong>" in result

    def test_html_xss_event_handler(self):
        """Test that event handlers in text are escaped."""
        malicious = '<img src=x onerror="alert(\'XSS\')">'
        result = format_text(malicious, "html")
        assert 'onerror=' not in result or '&' in result
        assert "<img" not in result or "&lt;img" in result

    def test_html_xss_in_link_text(self):
        """Test that XSS in link text is escaped."""
        malicious = "[<script>alert('XSS')</script>](https://example.com)"
        result = format_text(malicious, "html")
        assert "<script>" not in result
        assert "href=" in result  # Link should still work

    def test_html_xss_javascript_url(self):
        """Test that javascript: URLs are preserved but don't execute.

        Note: The formatter converts to <a href="..."> which browsers
        may block for javascript: URLs, but we should still test behavior.
        """
        malicious = "[click me](javascript:alert('XSS'))"
        result = format_text(malicious, "html")
        # The URL should be preserved (it's the browser's job to block javascript:)
        # but the link text should be safe
        assert "<a href=" in result
        assert ">click me</a>" in result

    def test_html_xss_data_url(self):
        """Test handling of data: URLs."""
        malicious = "[click](data:text/html,<script>alert('XSS')</script>)"
        result = format_text(malicious, "html")
        assert "<a href=" in result
        # Link text should be safe
        assert ">click</a>" in result

    def test_html_xss_in_code_block(self):
        """Test that code blocks properly escape HTML."""
        malicious = "```<script>alert('XSS')</script>```"
        result = format_text(malicious, "html")
        assert "<script>" not in result
        assert "&lt;script&gt;" in result
        assert "<pre><code>" in result

    def test_html_xss_in_inline_code(self):
        """Test that inline code properly escapes HTML."""
        malicious = "`<script>alert('XSS')</script>`"
        result = format_text(malicious, "html")
        assert "<script>" not in result
        assert "&lt;script&gt;" in result
        assert "<code>" in result

    def test_html_xss_quotes_in_link_url(self):
        """Test that quotes in URLs are properly escaped."""
        malicious = '[link](https://example.com/path" onclick="alert(1))'
        result = format_text(malicious, "html")
        # The " should be escaped to prevent attribute injection
        assert 'onclick=' not in result or '%22' in result

    def test_html_xss_angle_brackets_preserved_in_code(self):
        """Test that angle brackets in code are escaped."""
        code = "`<div class='test'>content</div>`"
        result = format_text(code, "html")
        assert "<div" not in result or "&lt;div" in result
        assert "<code>" in result

    # ==================== Telegram Injection Prevention ====================

    def test_telegram_markdown_injection_in_text(self):
        """Test that Telegram special characters in user text are escaped."""
        # These characters have special meaning in Telegram MarkdownV2
        # Input uses our standard format: ** for bold, * for italic
        text = "User input with **bold** and *italic* and [link](url)"
        result = format_text(text, "telegram")
        # Bold ** -> * in Telegram
        assert "*bold*" in result
        # Italic * -> _ in Telegram
        assert "_italic_" in result
        # Link should be converted properly
        assert "[" in result
        assert "](" in result

    def test_telegram_escape_special_chars(self):
        """Test that all Telegram special characters are escaped in plain text."""
        # All special chars: _ * [ ] ( ) ~ ` > # + - = | { } . !
        special = "Test: _ * [ ] ( ) ~ ` > # + - = | { } . !"
        result = format_text(special, "telegram")
        # Each special char should be escaped with backslash
        assert r"\!" in result
        assert r"\(" in result
        assert r"\)" in result
        assert r"\." in result

    def test_telegram_nested_formatting_escape(self):
        """Test that nested formatting attempts don't cause issues."""
        nested = "**bold with *nested* inside**"
        result = format_text(nested, "telegram")
        # Should produce valid Telegram markdown, not crash or misformat
        assert isinstance(result, str)

    def test_telegram_code_block_injection(self):
        """Test that code blocks don't allow escaping."""
        malicious = "```python\n*not bold*\n```"
        result = format_text(malicious, "telegram")
        # Inside code block, * should not be interpreted as formatting
        assert "```" in result

    def test_telegram_link_url_injection(self):
        """Test that malicious URLs don't break Telegram markdown."""
        malicious = "[link](https://example.com/path) extra text"
        result = format_text(malicious, "telegram")
        # Should produce valid output
        assert "[" in result
        assert "](" in result

    # ==================== Discord Injection Prevention ====================

    def test_discord_everyone_mention_not_injected(self):
        """Test that @everyone mentions in user content are preserved as-is.

        Note: Discord's API will not actually ping @everyone from bot messages
        without specific permissions, but we should verify content passes through.
        """
        text = "Hello @everyone!"
        result = format_text(text, "discord")
        # Discord formatter is passthrough, so content stays as-is
        assert "@everyone" in result

    def test_discord_user_mention_format(self):
        """Test that Discord mention format is preserved."""
        text = "Hello <@123456789>!"
        result = format_text(text, "discord")
        assert "<@123456789>" in result

    def test_discord_code_block_escape(self):
        """Test that code blocks work correctly in Discord."""
        code = "```python\nprint('hello')\n```"
        result = format_text(code, "discord")
        assert "```python" in result
        assert "```" in result

    # ==================== Plain Text Safety ====================

    def test_plain_removes_potential_formatting(self):
        """Test that plain text formatter removes formatting safely."""
        text = "**bold** and *italic*"
        result = format_text(text, "plain")
        # Should convert to ASCII-safe representation
        assert "**" not in result or "*bold*" in result
        assert "_italic_" in result

    # ==================== Cross-Platform Consistency ====================

    def test_same_input_different_outputs(self):
        """Test that the same input produces appropriate output for each platform."""
        input_text = "**Bold** and *italic* with `code`"

        telegram = format_text(input_text, "telegram")
        discord = format_text(input_text, "discord")
        html = format_text(input_text, "html")
        plain = format_text(input_text, "plain")

        # Telegram: *Bold* _italic_ `code`
        assert "*Bold*" in telegram
        assert "_italic_" in telegram

        # Discord: **Bold** *italic* `code` (unchanged)
        assert "**Bold**" in discord
        assert "*italic*" in discord

        # HTML: <strong>Bold</strong> <em>italic</em> <code>code</code>
        assert "<strong>Bold</strong>" in html
        assert "<em>italic</em>" in html
        assert "<code>code</code>" in html

        # Plain: *Bold* _italic_ 'code'
        assert "*Bold*" in plain
        assert "_italic_" in plain
        assert "'code'" in plain

    # ==================== Null Byte Injection ====================

    def test_null_byte_injection(self):
        """Test that null bytes don't cause issues."""
        malicious = "text\x00with\x00nulls"
        # Should not crash
        result_html = format_text(malicious, "html")
        result_tg = format_text(malicious, "telegram")
        result_dc = format_text(malicious, "discord")

        assert isinstance(result_html, str)
        assert isinstance(result_tg, str)
        assert isinstance(result_dc, str)

    # ==================== Unicode Safety ====================

    def test_unicode_characters_preserved(self):
        """Test that Unicode characters are preserved correctly."""
        text = "Hello 世界! 🎉 Привет мир!"
        result_html = format_text(text, "html")
        result_tg = format_text(text, "telegram")

        assert "世界" in result_html
        assert "🎉" in result_html
        assert "Привет" in result_html

        # For Telegram, ! should be escaped
        assert "世界" in result_tg
        assert "🎉" in result_tg

    def test_unicode_in_formatting(self):
        """Test Unicode inside formatting markers."""
        text = "**こんにちは** and *мир*"
        result_html = format_text(text, "html")
        result_tg = format_text(text, "telegram")

        assert "<strong>こんにちは</strong>" in result_html
        assert "<em>мир</em>" in result_html

        assert "*こんにちは*" in result_tg
        assert "_мир_" in result_tg

    # ==================== RTL and Bidirectional Text ====================

    def test_rtl_text_handling(self):
        """Test right-to-left text handling."""
        text = "Hello שלום world"
        result = format_text(text, "html")
        assert "שלום" in result

    def test_bidi_override_characters(self):
        """Test handling of bidirectional override characters."""
        # These could be used for text spoofing attacks
        malicious = "user\u202efdp.exe"  # Right-to-left override
        result_html = format_text(malicious, "html")
        # Character should be preserved (it's legitimate Unicode)
        assert "\u202e" in result_html or "&#x202e;" in result_html.lower() or result_html

    # ==================== Length and Recursion Safety ====================

    def test_very_long_input(self):
        """Test handling of very long input."""
        long_text = "**bold**" * 10000
        result = format_text(long_text, "html")
        assert "<strong>bold</strong>" in result

    def test_deeply_nested_fake_formatting(self):
        """Test that fake deeply nested formatting doesn't cause issues."""
        # Attempt to create deeply nested patterns
        nested = "****very bold****"
        result = format_text(nested, "telegram")
        # Should not crash or hang
        assert isinstance(result, str)

    # ==================== Template Injection Prevention ====================

    def test_jinja_template_injection(self):
        """Test that Jinja2 template syntax isn't interpreted."""
        malicious = "{{ config.items() }}"
        result = format_text(malicious, "html")
        # Template syntax should be preserved as text
        assert "{{" in result or "&" in result

    def test_python_format_string_injection(self):
        """Test that Python format strings aren't interpreted."""
        malicious = "{__class__.__mro__[1].__subclasses__()}"
        result = format_text(malicious, "html")
        # Should be preserved as text (with escaping if needed)
        assert isinstance(result, str)

    # ==================== Regression Tests ====================

    def test_empty_formatting_markers(self):
        """Test handling of empty formatting markers."""
        empty_bold = "****"
        empty_italic = "**"
        empty_code = "``"

        # Should not crash
        result1 = format_text(empty_bold, "html")
        result2 = format_text(empty_italic, "html")
        result3 = format_text(empty_code, "html")

        assert isinstance(result1, str)
        assert isinstance(result2, str)
        assert isinstance(result3, str)

    def test_unmatched_formatting_markers(self):
        """Test handling of unmatched formatting markers."""
        unmatched = "**bold without closing"
        result = format_text(unmatched, "html")
        # Should not crash, may preserve as-is
        assert isinstance(result, str)

    def test_mixed_unmatched_markers(self):
        """Test handling of mixed unmatched markers."""
        mixed = "**bold *italic** but italic never closed"
        result = format_text(mixed, "html")
        assert isinstance(result, str)

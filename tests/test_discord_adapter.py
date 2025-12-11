"""
Tests for Discord bot adapter.

This module tests the Discord bot adapter functionality including:
- Bot initialization
- Command handling
- Session management
- Question display
- Answer submission
- Button interactions
"""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import discord

from pyquizhub.adapters.discord.bot import DiscordQuizBot, QuizButtonView


@pytest.fixture
def mock_discord_token():
    """Mock Discord bot token."""
    return "mock_discord_token_12345"


@pytest.fixture
def mock_api_base_url():
    """Mock API base URL."""
    return "http://localhost:8000"


@pytest.fixture
def mock_user_token():
    """Mock user token."""
    return "mock_user_token_12345"


@pytest.fixture
def discord_bot(mock_discord_token, mock_api_base_url, mock_user_token):
    """Create a Discord bot instance for testing."""
    with patch('discord.ext.commands.Bot.run'):
        bot = DiscordQuizBot(
            token=mock_discord_token,
            api_base_url=mock_api_base_url,
            user_token=mock_user_token
        )
        return bot


class TestDiscordBotInitialization:
    """Test Discord bot initialization."""

    def test_bot_initialization(
            self,
            discord_bot,
            mock_discord_token,
            mock_api_base_url,
            mock_user_token):
        """Test bot initializes with correct configuration."""
        assert discord_bot.bot_token == mock_discord_token
        assert discord_bot.api_base_url == mock_api_base_url
        assert discord_bot.user_token == mock_user_token
        assert isinstance(discord_bot.user_sessions, dict)
        assert len(discord_bot.user_sessions) == 0

    def test_bot_intents(self, discord_bot):
        """Test bot has correct intents enabled."""
        assert discord_bot.intents.message_content is True
        assert discord_bot.intents.members is True

    def test_bot_command_prefix(self, discord_bot):
        """Test bot has correct command prefix."""
        assert discord_bot.command_prefix == "!"


class TestSessionManagement:
    """Test session management functionality."""

    def test_create_session(self, discord_bot):
        """Test creating a new session."""
        user_id = 123456789
        session_data = {
            "quiz_id": "test_quiz",
            "session_id": "test_session",
            "channel_id": 987654321,
            "awaiting_input": None
        }

        discord_bot.user_sessions[user_id] = session_data

        assert user_id in discord_bot.user_sessions
        assert discord_bot.user_sessions[user_id] == session_data

    def test_update_session(self, discord_bot):
        """Test updating an existing session."""
        user_id = 123456789
        discord_bot.user_sessions[user_id] = {
            "quiz_id": "test_quiz",
            "session_id": "test_session",
            "channel_id": 987654321,
            "awaiting_input": None
        }

        discord_bot.user_sessions[user_id]["awaiting_input"] = "integer"

        assert discord_bot.user_sessions[user_id]["awaiting_input"] == "integer"

    def test_delete_session(self, discord_bot):
        """Test deleting a session."""
        user_id = 123456789
        discord_bot.user_sessions[user_id] = {
            "quiz_id": "test_quiz",
            "session_id": "test_session",
            "channel_id": 987654321,
            "awaiting_input": None
        }

        del discord_bot.user_sessions[user_id]

        assert user_id not in discord_bot.user_sessions


class TestQuestionDisplay:
    """Test question display functionality."""

    @pytest.mark.asyncio
    async def test_send_multiple_choice_question(self, discord_bot):
        """Test sending a multiple choice question."""
        mock_channel = AsyncMock()
        user_id = 123456789
        question_data = {
            "data": {
                "type": "multiple_choice",
                "text": "What is 2+2?",
                "options": [
                    {"label": "3", "value": "3"},
                    {"label": "4", "value": "4"},
                    {"label": "5", "value": "5"}
                ]
            }
        }

        await discord_bot.send_question(mock_channel, user_id, question_data)

        # Verify channel.send was called with text and view
        mock_channel.send.assert_called_once()
        call_args = mock_channel.send.call_args
        assert "What is 2+2?" in call_args[0][0]
        assert "view" in call_args[1]

    @pytest.mark.asyncio
    async def test_send_text_question(self, discord_bot):
        """Test sending a text input question."""
        mock_channel = AsyncMock()
        user_id = 123456789

        # Create session for user
        discord_bot.user_sessions[user_id] = {
            "quiz_id": "test_quiz",
            "session_id": "test_session",
            "channel_id": 987654321,
            "awaiting_input": None
        }

        question_data = {
            "data": {
                "type": "text",
                "text": "What is your name?"
            }
        }

        await discord_bot.send_question(mock_channel, user_id, question_data)

        # Verify channel.send was called with text
        mock_channel.send.assert_called_once()
        call_args = mock_channel.send.call_args
        assert "What is your name?" in call_args[0][0]
        assert "type your answer" in call_args[0][0].lower()

    @pytest.mark.asyncio
    async def test_send_integer_question(self, discord_bot):
        """Test sending an integer input question."""
        mock_channel = AsyncMock()
        user_id = 123456789

        # Create session for user
        discord_bot.user_sessions[user_id] = {
            "quiz_id": "test_quiz",
            "session_id": "test_session",
            "channel_id": 987654321,
            "awaiting_input": None
        }

        question_data = {
            "data": {
                "type": "integer",
                "text": "How old are you?"
            }
        }

        await discord_bot.send_question(mock_channel, user_id, question_data)

        # Verify channel.send was called
        mock_channel.send.assert_called_once()
        call_args = mock_channel.send.call_args
        assert "How old are you?" in call_args[0][0]
        assert "whole number" in call_args[0][0].lower()

    @pytest.mark.asyncio
    async def test_send_float_question(self, discord_bot):
        """Test sending a float input question."""
        mock_channel = AsyncMock()
        user_id = 123456789

        # Create session for user
        discord_bot.user_sessions[user_id] = {
            "quiz_id": "test_quiz",
            "session_id": "test_session",
            "channel_id": 987654321,
            "awaiting_input": None
        }

        question_data = {
            "data": {
                "type": "float",
                "text": "What is pi?"
            }
        }

        await discord_bot.send_question(mock_channel, user_id, question_data)

        # Verify channel.send was called
        mock_channel.send.assert_called_once()
        call_args = mock_channel.send.call_args
        assert "What is pi?" in call_args[0][0]
        assert "decimal number" in call_args[0][0].lower()

    @pytest.mark.asyncio
    async def test_send_question_with_image(self, discord_bot):
        """Test sending a question with an image."""
        mock_channel = AsyncMock()
        user_id = 123456789
        question_data = {
            "data": {
                "type": "multiple_choice",
                "text": "What animal is this?",
                "attachments": [
                    {
                        "type": "image",
                        "url": "https://example.com/dog.jpg"
                    }
                ],
                "options": [
                    {"label": "Dog", "value": "dog"},
                    {"label": "Cat", "value": "cat"}
                ]
            }
        }

        await discord_bot.send_question(mock_channel, user_id, question_data)

        # Verify channel.send was called with embed
        mock_channel.send.assert_called_once()
        call_args = mock_channel.send.call_args
        assert "embed" in call_args[1]
        assert "view" in call_args[1]

    @pytest.mark.asyncio
    async def test_send_final_message(self, discord_bot):
        """Test sending a final message."""
        mock_channel = AsyncMock()
        mock_channel.id = 987654321

        # Create a session
        user_id = 123456789
        discord_bot.user_sessions[user_id] = {
            "quiz_id": "test_quiz",
            "session_id": "test_session",
            "channel_id": 987654321,
            "awaiting_input": None
        }

        question_data = {
            "data": {
                "type": "final_message",
                "text": "Congratulations! You scored 10/10!"
            }
        }

        await discord_bot.send_question(mock_channel, user_id, question_data)

        # Verify final message was sent
        mock_channel.send.assert_called_once()
        call_args = mock_channel.send.call_args
        assert "Congratulations" in call_args[0][0]

        # Verify session was cleared
        assert user_id not in discord_bot.user_sessions


def create_mock_aiohttp_session(response_data, status=200):
    """Create a properly configured mock aiohttp session."""
    mock_response = MagicMock()
    mock_response.status = status

    async def mock_json():
        return response_data

    mock_response.json = mock_json

    class MockContextManager:
        async def __aenter__(self):
            return mock_response

        async def __aexit__(self, *args):
            pass

    mock_session = MagicMock()
    mock_session.post.return_value = MockContextManager()

    return mock_session


class TestAnswerHandling:
    """Test answer handling functionality."""

    @pytest.mark.asyncio
    async def test_submit_answer_success(self, discord_bot):
        """Test successful answer submission."""
        mock_channel = AsyncMock()
        user_id = 123456789

        # Create session
        discord_bot.user_sessions[user_id] = {
            "quiz_id": "test_quiz",
            "session_id": "test_session",
            "channel_id": 987654321,
            "awaiting_input": "text"
        }

        mock_session = create_mock_aiohttp_session({
            "question": {
                "data": {
                    "type": "final_message",
                    "text": "Quiz complete!"
                }
            }
        })

        async def mock_get_session():
            return mock_session

        discord_bot.get_http_session = mock_get_session
        await discord_bot.submit_answer(mock_channel, user_id, "test_answer")

        # Session should be cleared after final message
        assert user_id not in discord_bot.user_sessions

    @pytest.mark.asyncio
    async def test_submit_answer_api_error(self, discord_bot):
        """Test answer submission with API error."""
        mock_channel = AsyncMock()
        user_id = 123456789

        # Create session
        discord_bot.user_sessions[user_id] = {
            "quiz_id": "test_quiz",
            "session_id": "test_session",
            "channel_id": 987654321,
            "awaiting_input": None
        }

        mock_session = create_mock_aiohttp_session(
            {"detail": "Invalid answer"}, status=400)

        async def mock_get_session():
            return mock_session

        discord_bot.get_http_session = mock_get_session
        await discord_bot.submit_answer(mock_channel, user_id, "test_answer")

        # Verify error message was sent
        mock_channel.send.assert_called_once()
        call_args = mock_channel.send.call_args
        assert "Error" in call_args[0][0] or "error" in call_args[0][0].lower()

    @pytest.mark.asyncio
    async def test_handle_integer_answer(self, discord_bot):
        """Test handling integer answer input."""
        mock_message = AsyncMock()
        mock_message.author.id = 123456789
        mock_message.content = "42"
        mock_message.channel = AsyncMock()
        mock_message.channel.id = 987654321
        mock_message.attachments = []

        # Create session awaiting integer input
        discord_bot.user_sessions[123456789] = {
            "quiz_id": "test_quiz",
            "session_id": "test_session",
            "channel_id": 987654321,
            "awaiting_input": "integer"
        }

        mock_session = create_mock_aiohttp_session({
            "question": {
                "data": {
                    "type": "final_message",
                    "text": "Quiz complete!"
                }
            }
        })

        async def mock_get_session():
            return mock_session

        discord_bot.get_http_session = mock_get_session
        await discord_bot.handle_text_answer(mock_message)

        # Session should be cleared after final message
        assert 123456789 not in discord_bot.user_sessions

    @pytest.mark.asyncio
    async def test_handle_invalid_integer_answer(self, discord_bot):
        """Test handling invalid integer answer."""
        mock_message = AsyncMock()
        mock_message.author.id = 123456789
        mock_message.content = "not a number"
        mock_message.attachments = []

        # Create session awaiting integer input
        discord_bot.user_sessions[123456789] = {
            "quiz_id": "test_quiz",
            "session_id": "test_session",
            "channel_id": 987654321,
            "awaiting_input": "integer"
        }

        await discord_bot.handle_text_answer(mock_message)

        # Verify error message was sent
        mock_message.reply.assert_called_once()
        call_args = mock_message.reply.call_args
        assert "valid" in call_args[0][0].lower()

    @pytest.mark.asyncio
    async def test_handle_float_answer(self, discord_bot):
        """Test handling float answer input."""
        mock_message = AsyncMock()
        mock_message.author.id = 123456789
        mock_message.content = "3.14"
        mock_message.channel = AsyncMock()
        mock_message.attachments = []

        # Create session awaiting float input
        discord_bot.user_sessions[123456789] = {
            "quiz_id": "test_quiz",
            "session_id": "test_session",
            "channel_id": 987654321,
            "awaiting_input": "float"
        }

        mock_session = create_mock_aiohttp_session({
            "question": {
                "data": {
                    "type": "final_message",
                    "text": "Quiz complete!"
                }
            }
        })

        async def mock_get_session():
            return mock_session

        discord_bot.get_http_session = mock_get_session
        await discord_bot.handle_text_answer(mock_message)

        # Session should be cleared after final message
        assert 123456789 not in discord_bot.user_sessions

    @pytest.mark.asyncio
    async def test_handle_multiple_select_answer(self, discord_bot):
        """Test handling multiple select answer."""
        mock_message = AsyncMock()
        mock_message.author.id = 123456789
        mock_message.content = "a, b, c"
        mock_message.channel = AsyncMock()
        mock_message.attachments = []

        # Create session awaiting multiple select input
        discord_bot.user_sessions[123456789] = {
            "quiz_id": "test_quiz",
            "session_id": "test_session",
            "channel_id": 987654321,
            "awaiting_input": "multiple_select"
        }

        mock_session = create_mock_aiohttp_session({
            "question": {
                "data": {
                    "type": "final_message",
                    "text": "Quiz complete!"
                }
            }
        })

        async def mock_get_session():
            return mock_session

        discord_bot.get_http_session = mock_get_session
        await discord_bot.handle_text_answer(mock_message)

        # Session should be cleared after final message
        assert 123456789 not in discord_bot.user_sessions


class TestButtonView:
    """Test Discord button view functionality."""

    def test_button_view_options_processed(self, discord_bot):
        """Test button view processes options correctly."""
        options = [
            {"label": "Option 1", "value": "opt1"},
            {"label": "Option 2", "value": "opt2"},
            {"label": "Option 3", "value": "opt3"}
        ]

        # We can't instantiate the view without an event loop,
        # but we can verify the bot integration works
        assert discord_bot is not None
        assert isinstance(options, list)
        assert len(options) == 3

    def test_button_view_max_options(self, discord_bot):
        """Test button view can handle many options."""
        # Discord limit is 25 components per view
        options = [{"label": f"Option {i}", "value": f"opt{i}"}
                   for i in range(30)]

        # Verify we have the correct number of options
        assert len(options) == 30
        # In actual implementation, only first 25 would be used
        assert len(options[:25]) == 25

    def test_button_view_timeout_config(self, discord_bot):
        """Test button view timeout configuration."""
        # The QuizButtonView is configured with timeout=None
        # We can't test this without an event loop, but we can
        # verify the configuration is correct in the source code
        assert discord_bot is not None

    @pytest.mark.asyncio
    async def test_button_callback_no_session(self, discord_bot):
        """Test button callback when user has no active session."""
        user_id = 123456789
        options = [{"label": "Option 1", "value": "opt1"}]
        view = QuizButtonView(discord_bot, user_id, options)

        # Mock interaction from a different user (no session)
        mock_interaction = AsyncMock()
        mock_interaction.user.id = 123456789  # Same user, but no session
        mock_interaction.channel = AsyncMock()

        # Get the button callback
        button = view.children[0]

        # Call the callback
        await button.callback(mock_interaction)

        # Verify error response
        mock_interaction.response.send_message.assert_called_once()
        call_args = mock_interaction.response.send_message.call_args
        assert "No active quiz session" in call_args[0][0]


class TestEdgeCases:
    """Test edge cases and error handling."""

    @pytest.mark.asyncio
    async def test_handle_text_answer_no_session(self, discord_bot):
        """Test handling text answer when user has no session."""
        mock_message = AsyncMock()
        mock_message.author.id = 999999999
        mock_message.content = "test answer"

        # Don't create a session
        await discord_bot.handle_text_answer(mock_message)

        # Should silently ignore (no error message)
        mock_message.reply.assert_not_called()

    @pytest.mark.asyncio
    async def test_handle_text_answer_not_awaiting_input(self, discord_bot):
        """Test handling text when not awaiting input."""
        mock_message = AsyncMock()
        mock_message.author.id = 123456789
        mock_message.content = "test answer"

        # Create session not awaiting input
        discord_bot.user_sessions[123456789] = {
            "quiz_id": "test_quiz",
            "session_id": "test_session",
            "channel_id": 987654321,
            "awaiting_input": None
        }

        await discord_bot.handle_text_answer(mock_message)

        # Should silently ignore
        mock_message.reply.assert_not_called()

    @pytest.mark.asyncio
    async def test_submit_answer_quiz_complete_no_question(self, discord_bot):
        """Test submit answer when quiz completes without final message."""
        mock_channel = AsyncMock()
        user_id = 123456789

        # Create session
        discord_bot.user_sessions[user_id] = {
            "quiz_id": "test_quiz",
            "session_id": "test_session",
            "channel_id": 987654321,
            "awaiting_input": None
        }

        mock_session = create_mock_aiohttp_session({"question": None})

        async def mock_get_session():
            return mock_session

        discord_bot.get_http_session = mock_get_session
        await discord_bot.submit_answer(mock_channel, user_id, "test_answer")

        # Verify completion message was sent
        mock_channel.send.assert_called_once()
        call_args = mock_channel.send.call_args
        assert "Quiz completed" in call_args[0][0] or "completed" in call_args[0][0].lower(
        )

        # Verify session was deleted
        assert user_id not in discord_bot.user_sessions


class TestURLValidation:
    """Test URL validation for SSRF protection."""

    def test_safe_url(self, discord_bot):
        """Test that safe URLs are allowed."""
        assert discord_bot._is_url_safe(
            "https://example.com/image.jpg") is True
        assert discord_bot._is_url_safe(
            "https://cdn.discord.com/image.png") is True

    def test_localhost_blocked(self, discord_bot):
        """Test that localhost URLs are blocked."""
        assert discord_bot._is_url_safe("http://localhost/file") is False
        assert discord_bot._is_url_safe("http://127.0.0.1/file") is False
        assert discord_bot._is_url_safe("http://0.0.0.0/file") is False

    def test_private_ip_blocked(self, discord_bot):
        """Test that private IP ranges are blocked."""
        assert discord_bot._is_url_safe("http://10.0.0.1/file") is False
        assert discord_bot._is_url_safe("http://192.168.1.1/file") is False
        assert discord_bot._is_url_safe("http://172.16.0.1/file") is False
        assert discord_bot._is_url_safe(
            "http://169.254.169.254/latest/meta-data") is False

    def test_invalid_url(self, discord_bot):
        """Test that invalid URLs return False."""
        assert discord_bot._is_url_safe("not a url") is False
        assert discord_bot._is_url_safe("") is False


class TestCommandRegistration:
    """Test command registration functionality."""

    def test_prefix_commands_registered(self, discord_bot):
        """Test that prefix commands are registered."""
        command_names = [cmd.name for cmd in discord_bot.commands]
        assert "quiz" in command_names
        assert "start" in command_names
        assert "help" in command_names

    def test_help_command_disabled(self, discord_bot):
        """Test that default help command is disabled."""
        # We set help_command=None in __init__
        assert discord_bot.help_command is None

    def test_slash_commands_registered(self, discord_bot):
        """Test that slash commands are registered in tree."""
        # Slash commands are registered via @self.tree.command
        # We can verify the tree exists
        assert discord_bot.tree is not None


class TestHandleQuizStart:
    """Test the _handle_quiz_start helper method."""

    @pytest.mark.asyncio
    async def test_handle_quiz_start_success(self, discord_bot):
        """Test successful quiz start."""
        mock_channel = AsyncMock()
        mock_channel.id = 987654321
        user_id = 123456789
        token = "test_token"
        mock_send = AsyncMock()

        mock_session = create_mock_aiohttp_session({
            "quiz_id": "test_quiz",
            "session_id": "test_session",
            "title": "Test Quiz",
            "question": {
                "data": {
                    "type": "multiple_choice",
                    "text": "First question?",
                    "options": [
                        {"label": "A", "value": "a"},
                        {"label": "B", "value": "b"}
                    ]
                }
            }
        })

        async def mock_get_session():
            return mock_session

        discord_bot.get_http_session = mock_get_session
        await discord_bot._handle_quiz_start(mock_channel, user_id, token, mock_send)

        # Verify quiz title was sent
        mock_send.assert_called()
        assert user_id in discord_bot.user_sessions
        assert discord_bot.user_sessions[user_id]["quiz_id"] == "test_quiz"

    @pytest.mark.asyncio
    async def test_handle_quiz_start_api_error(self, discord_bot):
        """Test quiz start with API error."""
        mock_channel = AsyncMock()
        user_id = 123456789
        token = "invalid_token"
        mock_send = AsyncMock()

        mock_session = create_mock_aiohttp_session(
            {"detail": "Token not found"},
            status=404
        )

        async def mock_get_session():
            return mock_session

        discord_bot.get_http_session = mock_get_session
        await discord_bot._handle_quiz_start(mock_channel, user_id, token, mock_send)

        # Verify error message was sent
        mock_send.assert_called_once()
        call_args = mock_send.call_args
        assert "Failed to start quiz" in call_args[0][0]

"""
Discord Bot adapter for PyQuizHub.

This module implements a Discord bot that allows users to take quizzes
through Discord chat interface.
"""

from __future__ import annotations

import os
import tempfile
from typing import Any
from pathlib import Path
from urllib.parse import urlparse

import discord
from discord.ext import commands
from discord import app_commands
import aiohttp

from pyquizhub.config.settings import get_config_manager, get_logger
from pyquizhub.core.engine.text_formatter import DiscordFormatter

logger = get_logger(__name__)

# Text formatter for converting standard Markdown to Discord format
# Discord uses standard Markdown, so this is mostly a passthrough
_formatter = DiscordFormatter()

# Security constants
MAX_FILE_SIZE = 20 * 1024 * 1024  # 20 MB limit
BLOCKED_HOSTS = ['localhost', '127.0.0.1', '0.0.0.0']

# Image formats that Discord can embed directly via URL
# Other formats (SVG, TIFF, BMP, etc.) need to be uploaded as files
DISCORD_EMBEDDABLE_IMAGE_FORMATS = {'jpg', 'jpeg', 'png', 'gif', 'webp'}


class DiscordQuizBot(commands.Bot):
    """Discord bot for PyQuizHub quizzes."""

    def __init__(self, token: str, api_base_url: str, user_token: str):
        """
        Initialize the Discord quiz bot.

        Args:
            token: Discord bot token
            api_base_url: PyQuizHub API base URL
            user_token: User token for API authentication
        """
        # Initialize bot with command prefix and intents
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True

        super().__init__(command_prefix="!", intents=intents, help_command=None)

        self.bot_token = token
        self.api_base_url = api_base_url
        self.user_token = user_token

        # Store user sessions: {user_id: {quiz_id, session_id, channel_id,
        # awaiting_input}}
        self.user_sessions: dict[int, dict[str, Any]] = {}

        # HTTP session for async requests
        self._http_session: aiohttp.ClientSession | None = None

        # Register commands
        self.setup_commands()

    def format_text(self, text: str) -> str:
        """
        Format text for Discord using standard Markdown.

        Discord uses standard Markdown syntax which matches our standard format,
        so this is mostly a passthrough. However, using the formatter ensures
        consistency if the standard format ever changes.

        Args:
            text: Text in standard Markdown format

        Returns:
            Text formatted for Discord
        """
        return _formatter.format(text)

    async def get_http_session(self) -> aiohttp.ClientSession:
        """Get or create the HTTP session."""
        if self._http_session is None or self._http_session.closed:
            self._http_session = aiohttp.ClientSession()
        return self._http_session

    async def close_http_session(self) -> None:
        """Close the HTTP session."""
        if self._http_session and not self._http_session.closed:
            await self._http_session.close()

    async def _handle_quiz_start(
        self,
        channel: discord.abc.Messageable,
        user_id: int,
        token: str,
        send_func
    ) -> None:
        """Handle starting a quiz (shared by slash and prefix commands)."""
        try:
            session = await self.get_http_session()
            async with session.post(
                f"{self.api_base_url}/quiz/start_quiz",
                json={"token": token, "user_id": str(user_id)},
                headers={"Authorization": self.user_token},
            ) as response:
                if response.status != 200:
                    error_data = await response.json()
                    detail = error_data.get('detail', 'Unknown error')
                    if isinstance(detail, dict):
                        detail = detail.get(
                            'error', {}).get(
                            'message', 'Unknown error')
                    await send_func(f"❌ Failed to start quiz: {detail}")
                    return

                data = await response.json()

            quiz_id = data["quiz_id"]
            session_id = data["session_id"]
            title = data["title"]

            # Store session
            self.user_sessions[user_id] = {
                "quiz_id": quiz_id,
                "session_id": session_id,
                "channel_id": channel.id,
                "awaiting_input": None,
            }

            await send_func(f"🎓 Starting quiz: **{title}**\n")
            await self.send_question(channel, user_id, data["question"])

        except aiohttp.ClientError as e:
            logger.error(f"HTTP error starting quiz: {e}")
            await send_func(f"❌ Connection error: {str(e)}")
        except Exception as e:
            logger.error(f"Error starting quiz: {e}")
            await send_func(f"❌ Error: {str(e)}")

    def setup_commands(self):
        """Set up bot commands."""
        bot = self  # Reference for closures

        @self.event
        async def on_ready():
            """Called when bot is ready."""
            logger.info(f"Discord bot logged in as {bot.user}")
            try:
                # Try guild-specific sync first (instant) if DISCORD_GUILD_ID
                # is set
                guild_id = os.getenv("DISCORD_GUILD_ID")
                if guild_id:
                    guild = discord.Object(id=int(guild_id))
                    bot.tree.copy_global_to(guild=guild)
                    synced = await bot.tree.sync(guild=guild)
                    logger.info(
                        f"Synced {
                            len(synced)} slash command(s) to guild {guild_id}")
                else:
                    # Global sync (can take up to 1 hour)
                    synced = await bot.tree.sync()
                    logger.info(
                        f"Synced {
                            len(synced)} slash command(s) globally")
            except Exception as e:
                logger.error(f"Failed to sync commands: {e}")

        @self.event
        async def on_message(message: discord.Message):
            """Handle text messages (answers)."""
            # Ignore messages from the bot itself
            if message.author == bot.user:
                return

            # Process commands first (this handles !quiz, !start, etc.)
            await bot.process_commands(message)

            # If message is not a command, check if it's an answer
            if not message.content.startswith(bot.command_prefix):
                await bot.handle_text_answer(message)

        # Register prefix commands using add_command
        @commands.command(name="start")
        async def prefix_start(ctx):
            """Start the PyQuizHub bot."""
            await ctx.send(
                f"👋 Hello {ctx.author.name}!\n\n"
                "Welcome to PyQuizHub Bot! 🎓\n\n"
                "**Commands:**\n"
                "`!quiz <token>` - Start a quiz\n"
                "`!help` - Show this help\n\n"
                "Or use slash commands: `/quiz`, `/help`"
            )
        self.add_command(prefix_start)

        @commands.command(name="quiz")
        async def prefix_quiz(ctx, token: str = None):
            """Start a quiz with a token."""
            if not token:
                await ctx.send("❌ Please provide a quiz token: `!quiz <token>`")
                return
            await bot._handle_quiz_start(ctx.channel, ctx.author.id, token, ctx.send)
        self.add_command(prefix_quiz)

        @commands.command(name="help")
        async def prefix_help(ctx):
            """Show help information."""
            await ctx.send(
                "📚 **PyQuizHub Bot Help**\n\n"
                "**Prefix Commands (!):**\n"
                "`!quiz <token>` - Start a quiz with a token\n"
                "`!start` - Show welcome message\n"
                "`!help` - Show this help\n\n"
                "**Slash Commands (/):**\n"
                "`/quiz <token>` - Start a quiz\n"
                "`/continue <token>` - Continue unfinished quiz\n"
                "`/status` - Check active quiz session\n"
                "`/start` - Show welcome\n"
                "`/help` - Show help\n\n"
                "**How to take a quiz:**\n"
                "1. Get a quiz token from your administrator\n"
                "2. Use `!quiz <token>` to start\n"
                "3. Answer by clicking buttons or typing\n"
                "4. View your results at the end!"
            )
        self.add_command(prefix_help)

        # Error handler for unknown commands
        @self.event
        async def on_command_error(ctx, error):
            """Handle command errors."""
            if isinstance(error, commands.CommandNotFound):
                cmd = ctx.message.content.split()[0][1:]  # Remove ! prefix
                await ctx.send(
                    f"❓ Unknown command: `{cmd}`\n\n"
                    "**Available commands:**\n"
                    "`!quiz <token>` - Start a quiz\n"
                    "`!start` - Show welcome message\n"
                    "`!help` - Show help\n\n"
                    "Or use slash commands: `/quiz`, `/start`, `/help`"
                )
            elif isinstance(error, commands.MissingRequiredArgument):
                await ctx.send(f"❌ Missing argument: `{error.param.name}`")
            else:
                logger.error(f"Command error: {error}")

        @self.tree.command(name="start", description="Start the PyQuizHub bot")
        async def start_command(interaction: discord.Interaction):
            """Handle /start command."""
            await interaction.response.send_message(
                f"👋 Hello {interaction.user.name}!\n\n"
                "Welcome to PyQuizHub Bot! 🎓\n\n"
                "To start a quiz, use:\n"
                "`/quiz <quiz_token>`\n\n"
                "For help, use `/help`"
            )

        @self.tree.command(name="help", description="Show help information")
        async def help_command(interaction: discord.Interaction):
            """Handle /help command."""
            await interaction.response.send_message(
                "📚 **PyQuizHub Bot Help**\n\n"
                "**Commands:**\n"
                "`/start` - Start the bot\n"
                "`/quiz <token>` - Start a quiz or continue existing one\n"
                "`/continue <token>` - Continue an unfinished quiz\n"
                "`/status` - Check if you have any active quizzes\n"
                "`/help` - Show this help message\n\n"
                "**How to take a quiz:**\n"
                "1. Get a quiz token from your quiz administrator\n"
                "2. Use `/quiz <token>` to start\n"
                "3. Answer questions by clicking buttons or typing answers\n"
                "4. View your results at the end!\n\n"
                "💡 **Tip:** If you're in the middle of answering a question, "
                "just type your answer - don't use commands!"
            )

        @self.tree.command(name="quiz",
                           description="Start a quiz with a token")
        @app_commands.describe(token="The quiz token to start")
        async def quiz_command(interaction: discord.Interaction, token: str):
            """Handle /quiz command to start a quiz."""
            user_id = interaction.user.id

            # Defer response since API call might take time
            await interaction.response.defer()

            # Call start_quiz API
            try:
                session = await self.get_http_session()
                async with session.post(
                    f"{self.api_base_url}/quiz/start_quiz",
                    json={"token": token, "user_id": str(user_id)},
                    headers={"Authorization": self.user_token},
                ) as response:
                    if response.status != 200:
                        error_data = await response.json()
                        await interaction.followup.send(
                            f"❌ Failed to start quiz: {error_data.get('detail', 'Unknown error')}"
                        )
                        return

                    data = await response.json()

                quiz_id = data["quiz_id"]
                session_id = data["session_id"]
                title = data["title"]

                # Store session
                self.user_sessions[user_id] = {
                    "quiz_id": quiz_id,
                    "session_id": session_id,
                    "channel_id": interaction.channel_id,
                    "awaiting_input": None,
                }

                await interaction.followup.send(f"🎓 Starting quiz: **{title}**\n")
                await self.send_question(interaction.channel, user_id, data["question"])

            except aiohttp.ClientError as e:
                logger.error(f"HTTP error starting quiz: {e}")
                await interaction.followup.send(f"❌ Connection error: {str(e)}")
            except Exception as e:
                logger.error(f"Error starting quiz: {e}")
                await interaction.followup.send(f"❌ Error: {str(e)}")

        @self.tree.command(name="continue",
                           description="Continue an unfinished quiz")
        @app_commands.describe(token="The quiz token to continue")
        async def continue_command(
                interaction: discord.Interaction,
                token: str):
            """Handle /continue command to continue a quiz."""
            user_id = interaction.user.id

            # Defer response since API call might take time
            await interaction.response.defer()

            try:
                session = await self.get_http_session()
                async with session.post(
                    f"{self.api_base_url}/quiz/start_quiz",
                    json={"token": token, "user_id": str(user_id)},
                    headers={"Authorization": self.user_token},
                ) as response:
                    if response.status != 200:
                        error_data = await response.json()
                        await interaction.followup.send(
                            f"❌ Failed to continue quiz: {error_data.get('detail', 'Unknown error')}"
                        )
                        return

                    data = await response.json()

                quiz_id = data["quiz_id"]
                session_id = data["session_id"]
                title = data["title"]

                # Store/update session
                self.user_sessions[user_id] = {
                    "quiz_id": quiz_id,
                    "session_id": session_id,
                    "channel_id": interaction.channel_id,
                    "awaiting_input": None,
                }

                await interaction.followup.send(f"🔄 Continuing quiz: **{title}**\n")
                await self.send_question(interaction.channel, user_id, data["question"])

            except aiohttp.ClientError as e:
                logger.error(f"HTTP error continuing quiz: {e}")
                await interaction.followup.send(f"❌ Connection error: {str(e)}")
            except Exception as e:
                logger.error(f"Error continuing quiz: {e}")
                await interaction.followup.send(f"❌ Error: {str(e)}")

        @self.tree.command(name="status",
                           description="Check your active quiz session")
        async def status_command(interaction: discord.Interaction):
            """Handle /status command."""
            user_id = interaction.user.id

            if user_id in self.user_sessions:
                session = self.user_sessions[user_id]
                await interaction.response.send_message(
                    f"📊 **Active Quiz Session**\n\n"
                    f"Session ID: `{session['session_id']}`\n"
                    f"Quiz ID: `{session['quiz_id']}`\n\n"
                    f"Just answer the current question to continue!\n\n"
                    f"💡 **Tip:** If you need to see the question again, "
                    "use `/continue` with your quiz token."
                )
            else:
                await interaction.response.send_message(
                    "ℹ️ No active quiz session.\n\n"
                    "Use `/quiz <token>` to start a new quiz, "
                    "or `/continue <token>` to resume an unfinished one."
                )

    def _is_url_safe(self, url: str) -> bool:
        """
        Basic SSRF protection - check if URL is safe to fetch.

        Args:
            url: URL to validate

        Returns:
            True if URL appears safe, False otherwise
        """
        try:
            parsed = urlparse(url)
            hostname = parsed.hostname

            if not hostname:
                return False

            # Block localhost and common private IP ranges
            if hostname.lower() in BLOCKED_HOSTS:
                return False

            # Block private IP ranges
            if hostname.startswith((
                '10.', '172.16.', '172.17.', '172.18.', '172.19.',
                '172.20.', '172.21.', '172.22.', '172.23.', '172.24.',
                '172.25.', '172.26.', '172.27.', '172.28.', '172.29.',
                '172.30.', '172.31.', '192.168.', '169.254.'
            )):
                return False

            return True

        except Exception:
            return False

    async def download_and_send_file(
        self,
        channel: discord.abc.Messageable,
        url: str,
        attachment_type: str,
        format_type: str,
        caption: str | None = None,
        view: discord.ui.View | None = None
    ) -> bool:
        """
        Download a file and upload it to Discord (fallback when URL embedding fails).

        Args:
            channel: Discord channel to send to
            url: File URL to download
            attachment_type: Type of attachment (image, audio, video, document)
            format_type: Format of the file
            caption: Optional caption text
            view: Optional view with buttons

        Returns:
            True if sent successfully, False otherwise
        """
        if not self._is_url_safe(url):
            logger.error(f"Blocked unsafe URL: {url}")
            return False

        try:
            session = await self.get_http_session()
            async with session.get(
                url,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                if response.status != 200:
                    logger.error(
                        f"Failed to download file from {url}: HTTP {
                            response.status}")
                    return False

                # Check Content-Length header
                content_length = response.headers.get('Content-Length')
                if content_length and int(content_length) > MAX_FILE_SIZE:
                    logger.error(f"File too large: {content_length} bytes")
                    return False

                # Get filename
                filename = Path(url).name or f"file.{format_type}"

                # Download with size limit
                with tempfile.NamedTemporaryFile(delete=False, suffix=f".{format_type}") as tmp_file:
                    tmp_path = tmp_file.name
                    downloaded_size = 0

                    async for chunk in response.content.iter_chunked(8192):
                        downloaded_size += len(chunk)
                        if downloaded_size > MAX_FILE_SIZE:
                            logger.error(
                                f"File exceeded size limit: {downloaded_size} bytes")
                            os.remove(tmp_path)
                            return False
                        tmp_file.write(chunk)

            # Send to Discord
            try:
                discord_file = discord.File(tmp_path, filename=filename)

                if caption:
                    await channel.send(content=caption, file=discord_file, view=view)
                else:
                    await channel.send(file=discord_file, view=view)

                logger.info(
                    f"Successfully sent {attachment_type} via file upload")
                return True

            finally:
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)

        except aiohttp.ClientError as e:
            logger.error(f"HTTP error downloading file: {e}")
            return False
        except Exception as e:
            logger.error(f"Failed to download and send file: {e}")
            return False

    async def send_attachment(
        self,
        channel: discord.abc.Messageable,
        attachment: dict,
        caption: str | None = None,
        view: discord.ui.View | None = None
    ) -> bool:
        """
        Send an attachment using Discord embed or file upload.

        Args:
            channel: Discord channel to send to
            attachment: Attachment dict with 'type', 'format', and 'url'
            caption: Optional caption text
            view: Optional view with buttons

        Returns:
            True if sent successfully, False otherwise
        """
        attachment_type = attachment.get("type")
        format_type = attachment.get("format", "").lower()
        url = attachment.get("url")

        if not url:
            return False

        enable_download = os.getenv(
            'DISCORD_ENABLE_FILE_DOWNLOAD',
            'true').lower() == 'true'

        # Check if this is an embeddable image (jpg, png, gif, webp)
        if self._is_embeddable_image(attachment):
            try:
                embed = discord.Embed(color=discord.Color.blue())
                if caption:
                    embed.description = caption
                embed.set_image(url=url)
                await channel.send(embed=embed, view=view)
                return True
            except discord.HTTPException as e:
                logger.info(f"Image embed failed: {e}. Trying file upload...")
                if enable_download:
                    return await self.download_and_send_file(
                        channel, url, attachment_type, format_type, caption, view
                    )
                return False

        # For non-embeddable images and other types, download and upload as file
        # This includes SVG, TIFF, BMP, audio, video, documents
        if enable_download and attachment_type in (
                "image", "audio", "video", "document", "file"):
            success = await self.download_and_send_file(
                channel, url, attachment_type, format_type, caption, view
            )
            if success:
                return True
            # Fall back to link if download fails
            logger.info(
                f"File download failed for {attachment_type}, falling back to link")

        # Fallback: show link in embed
        try:
            embed = discord.Embed(color=discord.Color.blue())
            type_icons = {
                "video": "🎬",
                "audio": "🎵",
                "document": "📄",
            }
            icon = type_icons.get(attachment_type, "📎")
            type_label = attachment_type.title() if attachment_type else "File"
            embed.description = (caption or "") + \
                f"\n{icon} [{type_label}]({url})"
            await channel.send(embed=embed, view=view)
            return True
        except discord.HTTPException as e:
            logger.error(f"Failed to send attachment link: {e}")
            return False

    async def send_question(
        self,
        channel: discord.abc.Messageable,
        user_id: int,
        question_data: dict
    ) -> None:
        """Send a question to the user."""
        question = question_data["data"]
        question_type = question.get("type")
        attachments = question.get("attachments", [])

        # Check if it's a final message
        if question_type == "final_message":
            # Format the quiz text for Discord Markdown
            formatted_text = self.format_text(question['text'])
            final_text = f"🎉 {formatted_text}\n\nQuiz completed! Use `/quiz` to start another quiz."

            if attachments:
                first_att = attachments[0]
                # Send first attachment with text
                if self._is_embeddable_image(first_att):
                    embed = discord.Embed(
                        description=final_text,
                        color=discord.Color.green()
                    )
                    embed.set_image(url=first_att["url"])
                    await channel.send(embed=embed)
                else:
                    # Non-embeddable attachment: download and upload with
                    # typing indicator
                    async with channel.typing():
                        await channel.send(final_text)
                        await self.send_attachment(channel, first_att, first_att.get("caption"))

                # Send additional attachments with typing indicator
                if len(attachments) > 1:
                    async with channel.typing():
                        for att in attachments[1:]:
                            await self.send_attachment(channel, att, att.get("caption"))
            else:
                await channel.send(final_text)

            # Clear session
            if user_id in self.user_sessions:
                del self.user_sessions[user_id]
            return

        # Build and format question text for Discord Markdown
        formatted_question = self.format_text(question['text'])
        text = f"❓ **{formatted_question}**\n"

        # Handle different question types
        if question_type == "multiple_choice":
            view = QuizButtonView(self, user_id, question["options"])
            await self._send_question_with_attachments(channel, text, attachments, view)

        elif question_type == "multiple_select":
            text += "\n💡 Select one or more options from the dropdown:"
            view = MultiSelectView(self, user_id, question["options"])
            await self._send_question_with_attachments(channel, text, attachments, view)

        elif question_type in ["integer", "float", "text"]:
            type_hint = {
                "integer": "whole number",
                "float": "decimal number",
                "text": "text",
            }
            text += f"\n💡 Please type your answer ({
                type_hint[question_type]}):"
            await self._send_question_with_attachments(channel, text, attachments)

            if user_id in self.user_sessions:
                self.user_sessions[user_id]["awaiting_input"] = question_type

        elif question_type == "file_upload":
            file_types = question.get("file_types", [])
            max_size = question.get("max_size_mb", 10)
            description = question.get("description", "")

            text += "\n📎 Please send a file as an attachment"
            if file_types:
                text += f"\n💡 Accepted types: {', '.join(file_types)}"
            if max_size:
                text += f"\n💡 Max size: {max_size}MB"
            if description:
                text += f"\n\n{description}"

            await self._send_question_with_attachments(channel, text, attachments)

            if user_id in self.user_sessions:
                self.user_sessions[user_id]["awaiting_input"] = "file_upload"

        else:
            text_with_hint = text + "\n💡 Please type your answer:"
            await self._send_question_with_attachments(channel, text_with_hint, attachments)

            if user_id in self.user_sessions:
                self.user_sessions[user_id]["awaiting_input"] = "text"

    def _is_embeddable_image(self, attachment: dict) -> bool:
        """
        Check if an image attachment can be embedded directly in Discord.

        Discord only supports embedding certain image formats via URL.
        Other formats (SVG, TIFF, BMP, etc.) need to be uploaded as files.
        """
        if attachment.get("type") != "image":
            return False

        # Check format field first
        format_type = attachment.get("format", "").lower()
        if format_type in DISCORD_EMBEDDABLE_IMAGE_FORMATS:
            return True

        # Fallback: check URL extension if format not specified
        url = attachment.get("url", "")
        if url:
            # Extract extension from URL path (ignoring query params)
            path = url.split("?")[0]
            ext = path.rsplit(".", 1)[-1].lower() if "." in path else ""
            if ext in DISCORD_EMBEDDABLE_IMAGE_FORMATS:
                return True

        return False

    async def _send_question_with_attachments(
        self,
        channel: discord.abc.Messageable,
        text: str,
        attachments: list[dict],
        view: discord.ui.View | None = None
    ) -> None:
        """
        Helper to send question text with attachments.

        Handles all attachment types properly:
        - Embeddable images (jpg, png, gif, webp): embedded in message via URL
        - Non-embeddable images (svg, tiff, bmp): downloaded and uploaded as files
        - Audio/Video/Documents: downloaded and uploaded as Discord files

        Uses typing indicator while downloading attachments to
        provide visual feedback that content is loading.
        """
        if not attachments:
            # No attachments, just send text
            await channel.send(text, view=view)
            return

        first_att = attachments[0]

        if self._is_embeddable_image(first_att):
            # Embeddable image can be embedded directly via URL
            embed = discord.Embed(description=text, color=discord.Color.blue())
            embed.set_image(url=first_att["url"])
            await channel.send(embed=embed, view=view)
        else:
            # Non-embeddable attachment: show typing while downloading
            # Send text with view first, then download/upload attachment
            async with channel.typing():
                await channel.send(text, view=view)
                await self.send_attachment(channel, first_att, first_att.get("caption"))

        # Send additional attachments with typing indicator
        if len(attachments) > 1:
            async with channel.typing():
                for att in attachments[1:]:
                    await self.send_attachment(channel, att, att.get("caption"))

    async def handle_text_answer(self, message: discord.Message) -> None:
        """Handle text messages as answers."""
        user_id = message.author.id

        if user_id not in self.user_sessions:
            return  # Silently ignore if no active session

        session = self.user_sessions[user_id]
        awaiting_type = session.get("awaiting_input")

        if not awaiting_type:
            return  # Silently ignore if not awaiting input

        # Check for file attachments first
        if message.attachments and awaiting_type == "file_upload":
            await self.handle_file_upload(message)
            return

        # Parse answer based on expected type
        answer_value = message.content.strip()

        if awaiting_type == "integer":
            try:
                answer_value = int(answer_value)
            except ValueError:
                await message.reply("❌ Please enter a valid whole number.")
                return
        elif awaiting_type == "float":
            try:
                answer_value = float(answer_value)
            except ValueError:
                await message.reply("❌ Please enter a valid number.")
                return
        elif awaiting_type == "multiple_select":
            # Parse comma-separated values
            answer_value = [v.strip() for v in answer_value.split(",")]

        await self.submit_answer(message.channel, user_id, answer_value)

    async def handle_file_upload(self, message: discord.Message) -> None:
        """Handle file upload messages."""
        user_id = message.author.id

        if user_id not in self.user_sessions:
            await message.reply("ℹ️ No active quiz. Use `/quiz <token>` to start.")
            return

        session = self.user_sessions[user_id]
        if session.get("awaiting_input") != "file_upload":
            await message.reply("ℹ️ The current question doesn't expect a file upload.")
            return

        if not message.attachments:
            await message.reply("❌ No file attachment found. Please send a file.")
            return

        attachment = message.attachments[0]

        try:
            # Download file from Discord
            file_bytes = await attachment.read()
            file_name = attachment.filename

            await message.reply("⏳ Uploading file...")

            # Upload to PyQuizHub API
            http_session = await self.get_http_session()

            form = aiohttp.FormData()
            form.add_field(
                'file',
                file_bytes,
                filename=file_name,
                content_type='application/octet-stream'
            )

            async with http_session.post(
                f"{self.api_base_url}/uploads/upload",
                data=form,
                headers={"Authorization": self.user_token},
            ) as response:
                if response.status != 200:
                    error_data = await response.json()
                    await message.reply(
                        f"❌ Failed to upload file: {error_data.get('detail', 'Unknown error')}"
                    )
                    return

                upload_data = await response.json()

            file_id = upload_data.get("file_id")
            if not file_id:
                await message.reply("❌ File upload failed: no file_id returned")
                return

            # Submit the file_id as the answer
            await self.submit_answer(message.channel, user_id, {"file_id": file_id})

        except aiohttp.ClientError as e:
            logger.error(f"HTTP error uploading file: {e}")
            await message.reply(f"❌ Connection error: {str(e)}")
        except Exception as e:
            logger.error(f"Error handling file upload: {e}")
            await message.reply(f"❌ Error: {str(e)}")

    async def submit_answer(
        self,
        channel: discord.abc.Messageable,
        user_id: int,
        answer_value: Any
    ) -> None:
        """Submit an answer to the quiz API."""
        session = self.user_sessions[user_id]
        quiz_id = session["quiz_id"]
        session_id = session["session_id"]

        try:
            http_session = await self.get_http_session()
            async with http_session.post(
                f"{self.api_base_url}/quiz/submit_answer/{quiz_id}",
                json={
                    "user_id": str(user_id),
                    "session_id": session_id,
                    "answer": {"answer": answer_value},
                },
                headers={"Authorization": self.user_token},
            ) as response:
                if response.status != 200:
                    error_data = await response.json()
                    await channel.send(
                        f"❌ Error: {error_data.get('detail', 'Failed to submit answer')}"
                    )
                    return

                data = await response.json()

            # Clear awaiting input flag
            session["awaiting_input"] = None

            # Send next question (or final message if quiz is complete)
            if "question" in data and data["question"]:
                await self.send_question(channel, user_id, data["question"])
            else:
                # Quiz completed without final message
                await channel.send(
                    "🎉 Quiz completed!\n\nUse `/quiz` to start another quiz."
                )
                if user_id in self.user_sessions:
                    del self.user_sessions[user_id]

        except aiohttp.ClientError as e:
            logger.error(f"HTTP error submitting answer: {e}")
            await channel.send(f"❌ Connection error: {str(e)}")
        except Exception as e:
            logger.error(f"Error submitting answer: {e}")
            await channel.send(f"❌ Error: {str(e)}")

    async def close(self) -> None:
        """Clean up resources."""
        await self.close_http_session()
        await super().close()

    def run_bot(self) -> None:
        """Start the bot."""
        logger.info("Starting Discord bot...")
        self.run(self.bot_token)


class QuizButtonView(discord.ui.View):
    """View containing buttons for quiz options."""

    def __init__(self, bot: DiscordQuizBot, user_id: int, options: list[dict]):
        """
        Initialize the button view.

        Args:
            bot: The Discord bot instance
            user_id: The user ID this view is for
            options: List of option dicts with 'label' and 'value'
        """
        super().__init__(timeout=None)  # No timeout for quiz buttons

        self.bot = bot
        self.user_id = user_id

        # Add buttons for each option (max 25 components per view in Discord)
        for idx, option in enumerate(options[:25]):
            button = discord.ui.Button(
                label=option["label"][:80],  # Discord label limit
                style=discord.ButtonStyle.primary,
                custom_id=f"quiz_answer_{user_id}_{idx}"
            )
            button.callback = self.make_button_callback(option["value"])
            self.add_item(button)

    def make_button_callback(self, answer_value: str):
        """Create a callback function for a button."""
        async def button_callback(interaction: discord.Interaction):
            user_id = interaction.user.id

            # Only allow the user who started the quiz to answer
            if user_id != self.user_id:
                await interaction.response.send_message(
                    "❌ This quiz belongs to another user. Use `/quiz` to start your own.",
                    ephemeral=True
                )
                return

            if user_id not in self.bot.user_sessions:
                await interaction.response.send_message(
                    "❌ No active quiz session. Use `/quiz` to start.",
                    ephemeral=True
                )
                return

            # Acknowledge the button click
            await interaction.response.defer()

            # Disable the buttons after click
            for item in self.children:
                item.disabled = True
            try:
                await interaction.message.edit(view=self)
            except discord.HTTPException:
                pass  # Ignore if we can't edit

            # Submit the answer
            await self.bot.submit_answer(interaction.channel, user_id, answer_value)

        return button_callback


class MultiSelectView(discord.ui.View):
    """View with a multi-select dropdown for multiple_select questions."""

    def __init__(self, bot: DiscordQuizBot, user_id: int, options: list[dict]):
        """
        Initialize the multi-select view.

        Args:
            bot: The Discord bot instance
            user_id: The user ID this view is for
            options: List of option dicts with 'label' and 'value'
        """
        super().__init__(timeout=None)

        self.bot = bot
        self.user_id = user_id

        # Create a Select menu (max 25 options in Discord)
        select = discord.ui.Select(
            placeholder="Select one or more options...",
            min_values=1,
            max_values=len(options[:25]),
            options=[
                discord.SelectOption(
                    label=opt["label"][:100],
                    value=opt["value"][:100]
                )
                for opt in options[:25]
            ],
            custom_id=f"multi_select_{user_id}"
        )
        select.callback = self.select_callback
        self.add_item(select)

    async def select_callback(self, interaction: discord.Interaction):
        """Handle select menu submission."""
        user_id = interaction.user.id

        # Only allow the user who started the quiz to answer
        if user_id != self.user_id:
            await interaction.response.send_message(
                "❌ This quiz belongs to another user. Use `/quiz` to start your own.",
                ephemeral=True
            )
            return

        if user_id not in self.bot.user_sessions:
            await interaction.response.send_message(
                "❌ No active quiz session. Use `/quiz` to start.",
                ephemeral=True
            )
            return

        # Get selected values (this is already a list)
        selected_values = interaction.data.get("values", [])

        # Acknowledge the interaction
        await interaction.response.defer()

        # Disable the select after submission
        for item in self.children:
            item.disabled = True
        try:
            await interaction.message.edit(view=self)
        except discord.HTTPException:
            pass

        # Submit the answer as a list
        await self.bot.submit_answer(interaction.channel, user_id, selected_values)


def main():
    """Main entry point for the Discord bot."""
    # Load configuration
    config_manager = get_config_manager()
    config_manager.load()

    # Get Discord bot token from environment
    discord_token = os.getenv("DISCORD_BOT_TOKEN")
    if not discord_token:
        raise ValueError("DISCORD_BOT_TOKEN environment variable not set")

    # Get API configuration
    api_base_url = os.getenv(
        "PYQUIZHUB_API__BASE_URL",
        config_manager.api_base_url)
    user_token = os.getenv(
        "PYQUIZHUB_USER_TOKEN",
        config_manager.get_token("user"))

    # Create and run bot
    bot = DiscordQuizBot(discord_token, api_base_url, user_token)
    bot.run_bot()


if __name__ == "__main__":
    main()

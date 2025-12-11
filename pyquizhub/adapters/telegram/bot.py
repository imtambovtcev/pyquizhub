"""
Telegram Bot adapter for PyQuizHub.

This module implements a Telegram bot that allows users to take quizzes
through Telegram chat interface.
"""

from __future__ import annotations

import os
import logging
from typing import Any

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
import requests

from pyquizhub.config.settings import get_config_manager, get_logger

logger = get_logger(__name__)


class TelegramQuizBot:
    """Telegram bot for PyQuizHub quizzes."""

    def __init__(self, token: str, api_base_url: str, user_token: str):
        """
        Initialize the Telegram quiz bot.

        Args:
            token: Telegram bot token
            api_base_url: PyQuizHub API base URL
            user_token: User token for API authentication
        """
        self.token = token
        self.api_base_url = api_base_url
        self.user_token = user_token
        self.application = Application.builder().token(token).build()

        # Register handlers
        self.application.add_handler(
            CommandHandler(
                "start", self.start_command))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CommandHandler("quiz", self.quiz_command))
        self.application.add_handler(
            CommandHandler(
                "continue",
                self.continue_command))
        self.application.add_handler(
            CommandHandler(
                "status",
                self.status_command))
        self.application.add_handler(
            CallbackQueryHandler(
                self.button_callback))
        self.application.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, self.text_message)
        )
        self.application.add_handler(
            MessageHandler(
                filters.PHOTO | filters.Document.ALL,
                self.file_message))

        # Store user sessions: {user_id: {quiz_id, session_id, quiz_token,
        # awaiting_input}}
        self.user_sessions: dict[int, dict[str, Any]] = {}

    async def start_command(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Handle /start command."""
        user = update.effective_user
        await update.message.reply_text(
            f"👋 Hello {user.first_name}!\n\n"
            "Welcome to PyQuizHub Bot! 🎓\n\n"
            "To start a quiz, use:\n"
            "/quiz <quiz_token>\n\n"
            "For help, use /help"
        )

    async def help_command(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Handle /help command."""
        await update.message.reply_text(
            "📚 PyQuizHub Bot Help\n\n"
            "Commands:\n"
            "/start - Start the bot\n"
            "/quiz <token> - Start a quiz or continue existing one\n"
            "/continue <token> - Continue an unfinished quiz\n"
            "/status - Check if you have any active quizzes\n"
            "/help - Show this help message\n\n"
            "How to take a quiz:\n"
            "1. Get a quiz token from your quiz administrator\n"
            "2. Use /quiz <token> to start\n"
            "3. Answer questions by clicking buttons or typing answers\n"
            "4. View your results at the end!\n\n"
            "💡 Tip: If you're in the middle of answering a question, just type your answer - don't use commands!"
        )

    async def quiz_command(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Handle /quiz command to start a quiz (or continue if active session exists)."""
        if not context.args:
            await update.message.reply_text(
                "❌ Please provide a quiz token:\n" "/quiz <quiz_token>"
            )
            return

        quiz_token = context.args[0]
        user_id = update.effective_user.id

        # Call start_quiz API - it will automatically resume if there's an
        # active session
        try:
            response = requests.post(
                f"{self.api_base_url}/quiz/start_quiz",
                json={"token": quiz_token, "user_id": str(user_id)},
                headers={"Authorization": self.user_token},
            )

            if response.status_code != 200:
                await update.message.reply_text(
                    f"❌ Failed to start quiz: {response.json().get('detail', 'Unknown error')}"
                )
                return

            data = response.json()
            quiz_id = data["quiz_id"]
            session_id = data["session_id"]
            title = data["title"]

            # Store session
            self.user_sessions[user_id] = {
                "quiz_id": quiz_id,
                "session_id": session_id,
                "awaiting_input": None,
            }

            await update.message.reply_text(f"🎓 Starting quiz: {title}\n\n")
            await self.send_question(update, data["question"])

        except Exception as e:
            logger.error(f"Error starting quiz: {e}")
            await update.message.reply_text(f"❌ Error: {str(e)}")

    async def continue_command(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Handle /continue command to continue an unfinished quiz and resend current question."""
        if not context.args:
            await update.message.reply_text(
                "❌ Please provide a quiz token:\n" "/continue <quiz_token>"
            )
            return

        quiz_token = context.args[0]
        user_id = update.effective_user.id

        # Call start_quiz API to get current question (will resume if active session exists)
        # This is safe - the API returns the already-prepared question from saved state
        # No API calls or score updates are re-executed
        try:
            response = requests.post(
                f"{self.api_base_url}/quiz/start_quiz",
                json={"token": quiz_token, "user_id": str(user_id)},
                headers={"Authorization": self.user_token},
            )

            if response.status_code != 200:
                await update.message.reply_text(
                    f"❌ Failed to continue quiz: {response.json().get('detail', 'Unknown error')}"
                )
                return

            data = response.json()
            quiz_id = data["quiz_id"]
            session_id = data["session_id"]
            title = data["title"]

            # Store/update session
            self.user_sessions[user_id] = {
                "quiz_id": quiz_id,
                "session_id": session_id,
                "awaiting_input": None,
            }

            # If already had a session, just resend the question
            await update.message.reply_text(f"🔄 Continuing quiz: {title}\n\n")
            await self.send_question(update, data["question"])

        except Exception as e:
            logger.error(f"Error continuing quiz: {e}")
            await update.message.reply_text(f"❌ Error: {str(e)}")

    async def status_command(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Handle /status command to check active quizzes and optionally resend question."""
        user_id = update.effective_user.id

        # Check in-memory session
        if user_id in self.user_sessions:
            session = self.user_sessions[user_id]
            await update.message.reply_text(
                f"📊 Active Quiz Session\n\n"
                f"Session ID: {session['session_id']}\n"
                f"Quiz ID: {session['quiz_id']}\n\n"
                f"Just answer the current question to continue!\n\n"
                f"💡 Tip: If you need to see the question again, use /continue with your quiz token."
            )
        else:
            await update.message.reply_text(
                "ℹ️ No active quiz session.\n\n"
                "Use /quiz <token> to start a new quiz, or /continue <token> to resume an unfinished one."
            )

    async def download_and_send_file(
            self,
            update: Update,
            url: str,
            attachment_type: str,
            format_type: str,
            caption: str | None = None,
            reply_markup=None) -> bool:
        """
        Download a file and upload it to Telegram (fallback when URL sending fails).

        SECURITY NOTE: This method is only safe for URLs from TRUSTED SOURCES (e.g., pre-validated quiz JSON).
        DO NOT use this with user-generated URLs without additional validation:
        - Check for SSRF (localhost, private IPs, cloud metadata)
        - Limit file sizes
        - Validate content types
        - Implement rate limiting

        Args:
            update: Telegram update object
            url: File URL to download
            attachment_type: Type of attachment (image, audio, video, document, file)
            format_type: Format of the file
            caption: Optional caption text
            reply_markup: Optional reply markup for buttons

        Returns:
            True if sent successfully, False otherwise
        """
        import aiohttp
        import tempfile
        import os
        from pathlib import Path
        from urllib.parse import urlparse

        # SECURITY: Basic SSRF protection - block private IPs and localhost
        try:
            parsed = urlparse(url)
            hostname = parsed.hostname

            if not hostname:
                logger.error(f"Invalid URL: no hostname")
                return False

            # Block localhost and common private IP ranges
            blocked_hosts = ['localhost', '127.0.0.1', '0.0.0.0']
            if hostname.lower() in blocked_hosts:
                logger.error(f"Blocked localhost/loopback URL: {url}")
                return False

            # Block private IP ranges (basic check)
            if hostname.startswith(
                ('10.',
                 '172.16.',
                 '172.17.',
                 '172.18.',
                 '172.19.',
                 '172.20.',
                 '172.21.',
                 '172.22.',
                 '172.23.',
                 '172.24.',
                 '172.25.',
                 '172.26.',
                 '172.27.',
                 '172.28.',
                 '172.29.',
                 '172.30.',
                 '172.31.',
                 '192.168.',
                 '169.254.')):
                logger.error(f"Blocked private IP URL: {url}")
                return False

        except Exception as e:
            logger.error(f"Failed to parse URL {url}: {e}")
            return False

        # SECURITY: File size limits (adjust based on your needs)
        MAX_FILE_SIZE = 20 * 1024 * 1024  # 20 MB limit

        try:
            # Download the file with size limits
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as response:
                    if response.status != 200:
                        logger.error(
                            f"Failed to download file from {url}: HTTP {
                                response.status}")
                        return False

                    # Check Content-Length header if available
                    content_length = response.headers.get('Content-Length')
                    if content_length and int(content_length) > MAX_FILE_SIZE:
                        logger.error(
                            f"File too large: {content_length} bytes (max {MAX_FILE_SIZE})")
                        return False

                    # Get filename from URL or use format
                    filename = Path(url).name or f"file.{format_type}"

                    # Create temporary file
                    with tempfile.NamedTemporaryFile(delete=False, suffix=f".{format_type}") as tmp_file:
                        tmp_path = tmp_file.name

                        # Read content with size limit
                        downloaded_size = 0
                        async for chunk in response.content.iter_chunked(8192):
                            downloaded_size += len(chunk)
                            if downloaded_size > MAX_FILE_SIZE:
                                logger.error(
                                    f"File exceeded size limit during download: {downloaded_size} bytes")
                                if os.path.exists(tmp_path):
                                    os.remove(tmp_path)
                                return False
                            tmp_file.write(chunk)

            # Send the file to Telegram
            try:
                with open(tmp_path, 'rb') as file:
                    if attachment_type == "image":
                        if format_type == "gif":
                            await update.effective_message.reply_animation(
                                animation=file,
                                caption=caption,
                                reply_markup=reply_markup,
                                filename=filename
                            )
                        elif format_type in ["jpeg", "jpg", "png", "webp"]:
                            await update.effective_message.reply_photo(
                                photo=file,
                                caption=caption,
                                reply_markup=reply_markup,
                                filename=filename
                            )
                        else:
                            await update.effective_message.reply_document(
                                document=file,
                                caption=caption,
                                reply_markup=reply_markup,
                                filename=filename
                            )
                    elif attachment_type == "audio":
                        await update.effective_message.reply_audio(
                            audio=file,
                            caption=caption,
                            reply_markup=reply_markup,
                            filename=filename
                        )
                    elif attachment_type == "video":
                        await update.effective_message.reply_video(
                            video=file,
                            caption=caption,
                            reply_markup=reply_markup,
                            filename=filename
                        )
                    else:  # document or file
                        await update.effective_message.reply_document(
                            document=file,
                            caption=caption,
                            reply_markup=reply_markup,
                            filename=filename
                        )

                logger.info(
                    f"Successfully sent {attachment_type} (format: {format_type}) via file upload")
                return True

            finally:
                # Clean up temp file
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)

        except Exception as e:
            logger.error(f"Failed to download and send file: {e}")
            return False

    async def send_attachment(
            self,
            update: Update,
            attachment: dict,
            caption: str | None = None,
            reply_markup=None) -> bool:
        """
        Send an attachment using the appropriate Telegram method based on attachment type and format.

        Args:
            update: Telegram update object
            attachment: Attachment dict with 'type', 'format', and 'url'
            caption: Optional caption text
            reply_markup: Optional reply markup for buttons

        Returns:
            True if sent successfully, False otherwise
        """
        attachment_type = attachment.get("type")
        format_type = attachment.get("format", "").lower()
        url = attachment.get("url")

        if not url:
            return False

        try:
            # Try sending by URL first
            if attachment_type == "image":
                if format_type == "gif":
                    await update.effective_message.reply_animation(
                        animation=url,
                        caption=caption,
                        reply_markup=reply_markup
                    )
                elif format_type in ["jpeg", "jpg", "png", "webp"]:
                    await update.effective_message.reply_photo(
                        photo=url,
                        caption=caption,
                        reply_markup=reply_markup
                    )
                else:
                    await update.effective_message.reply_document(
                        document=url,
                        caption=caption,
                        reply_markup=reply_markup
                    )

            elif attachment_type == "audio":
                await update.effective_message.reply_audio(
                    audio=url,
                    caption=caption,
                    reply_markup=reply_markup
                )

            elif attachment_type == "video":
                await update.effective_message.reply_video(
                    video=url,
                    caption=caption,
                    reply_markup=reply_markup
                )

            elif attachment_type in ["document", "file"]:
                await update.effective_message.reply_document(
                    document=url,
                    caption=caption,
                    reply_markup=reply_markup
                )

            else:
                logger.warning(f"Unknown attachment type: {attachment_type}")
                return False

            return True

        except Exception as e:
            # If URL sending failed, try downloading and uploading the file (if
            # enabled)
            import os
            enable_download = os.getenv(
                'TELEGRAM_ENABLE_FILE_DOWNLOAD',
                'false').lower() == 'true'

            if enable_download:
                logger.info(
                    f"URL sending failed for {attachment_type} (format: {format_type}): {e}. Trying file upload...")
                return await self.download_and_send_file(update, url, attachment_type, format_type, caption, reply_markup)
            else:
                logger.warning(
                    f"URL sending failed for {attachment_type} (format: {format_type}): {e}. File download is disabled. Enable with TELEGRAM_ENABLE_FILE_DOWNLOAD=true")
                return False

    def _build_multi_select_keyboard(
        self, options: list[dict], selected: list[str]
    ) -> list[list[InlineKeyboardButton]]:
        """Build keyboard for multiple_select with checkmarks for selected items."""
        keyboard = []
        for option in options:
            value = option["value"]
            label = option["label"]
            # Add checkmark if selected
            display = f"✅ {label}" if value in selected else f"⬜ {label}"
            keyboard.append([
                InlineKeyboardButton(display, callback_data=f"ms_toggle:{value}")
            ])
        # Add submit button
        keyboard.append([
            InlineKeyboardButton("✅ Submit Selection", callback_data="ms_submit")
        ])
        return keyboard

    async def send_question(self, update: Update, question_data: dict) -> None:
        """Send a question to the user."""
        question = question_data["data"]
        question_type = question.get("type")
        attachments = question.get("attachments", [])

        # Check if it's a final message
        if question_type == "final_message":
            # Send final message with attachments if present
            final_text = f"🎉 {
                question['text']}\n\nQuiz completed! Use /quiz to start another quiz."

            if attachments:
                # Send first attachment with caption, then remaining
                # attachments
                sent = await self.send_attachment(update, attachments[0], final_text)
                if not sent:
                    # Fallback to text only if first attachment fails
                    await update.effective_message.reply_text(final_text)

                # Send additional attachments if present
                for attachment in attachments[1:]:
                    caption = attachment.get("caption", "")
                    await self.send_attachment(update, attachment, caption)
            else:
                await update.effective_message.reply_text(final_text)

            # Clear session
            user_id = update.effective_user.id
            if user_id in self.user_sessions:
                del self.user_sessions[user_id]
            return

        # Send question text
        text = f"❓ {question['text']}\n"

        # Handle different question types
        if question_type == "multiple_choice":
            # Create inline keyboard with options
            keyboard = []
            for option in question["options"]:
                keyboard.append(
                    [
                        InlineKeyboardButton(
                            option["label"], callback_data=option["value"]
                        )
                    ]
                )
            reply_markup = InlineKeyboardMarkup(keyboard)

            # Send with attachments if available
            if attachments:
                sent = await self.send_attachment(update, attachments[0], text, reply_markup)
                if not sent:
                    # Fallback to text only
                    await update.effective_message.reply_text(text, reply_markup=reply_markup)

                # Send additional attachments without buttons
                for attachment in attachments[1:]:
                    caption = attachment.get("caption", "")
                    await self.send_attachment(update, attachment, caption)
            else:
                await update.effective_message.reply_text(text, reply_markup=reply_markup)

        elif question_type == "multiple_select":
            text += "\n💡 Tap options to select/deselect, then tap ✅ Submit:"
            # Initialize empty selections for this user
            user_id = update.effective_user.id
            if user_id in self.user_sessions:
                self.user_sessions[user_id]["multi_select_choices"] = []
                self.user_sessions[user_id]["multi_select_options"] = question["options"]
                self.user_sessions[user_id]["awaiting_input"] = "multiple_select"

            # Build keyboard with unchecked options
            keyboard = self._build_multi_select_keyboard(question["options"], [])
            reply_markup = InlineKeyboardMarkup(keyboard)

            # Send with attachments if available
            if attachments:
                sent = await self.send_attachment(update, attachments[0], text, reply_markup)
                if not sent:
                    await update.effective_message.reply_text(text, reply_markup=reply_markup)

                for attachment in attachments[1:]:
                    caption = attachment.get("caption", "")
                    await self.send_attachment(update, attachment, caption)
            else:
                await update.effective_message.reply_text(text, reply_markup=reply_markup)

        elif question_type in ["integer", "float", "text"]:
            type_hint = {
                "integer": "whole number",
                "float": "decimal number",
                "text": "text",
            }
            text += f"\n💡 Please type your answer ({
                type_hint[question_type]}):"

            # Send with attachments if available
            if attachments:
                sent = await self.send_attachment(update, attachments[0], text)
                if not sent:
                    # Fallback to text only
                    await update.effective_message.reply_text(text)

                # Send additional attachments
                for attachment in attachments[1:]:
                    caption = attachment.get("caption", "")
                    await self.send_attachment(update, attachment, caption)
            else:
                await update.effective_message.reply_text(text)

            # Mark that we're awaiting text input
            user_id = update.effective_user.id
            if user_id in self.user_sessions:
                self.user_sessions[user_id]["awaiting_input"] = question_type

        elif question_type == "file_upload":
            file_types = question.get("file_types", [])
            max_size = question.get("max_size_mb", 10)
            description = question.get("description", "")

            text += f"\n📎 Please send a file"
            if file_types:
                text += f"\n💡 Accepted types: {', '.join(file_types)}"
            if max_size:
                text += f"\n💡 Max size: {max_size}MB"
            if description:
                text += f"\n\n{description}"

            # Send with attachments if available
            if attachments:
                sent = await self.send_attachment(update, attachments[0], text)
                if not sent:
                    # Fallback to text only
                    await update.effective_message.reply_text(text)

                # Send additional attachments
                for attachment in attachments[1:]:
                    caption = attachment.get("caption", "")
                    await self.send_attachment(update, attachment, caption)
            else:
                await update.effective_message.reply_text(text)

            # Mark that we're awaiting file upload
            user_id = update.effective_user.id
            if user_id in self.user_sessions:
                self.user_sessions[user_id]["awaiting_input"] = "file_upload"

        else:
            text_with_hint = text + "\n💡 Please type your answer:"

            # Send with attachments if available
            if attachments:
                sent = await self.send_attachment(update, attachments[0], text_with_hint)
                if not sent:
                    # Fallback to text only
                    await update.effective_message.reply_text(text_with_hint)

                # Send additional attachments
                for attachment in attachments[1:]:
                    caption = attachment.get("caption", "")
                    await self.send_attachment(update, attachment, caption)
            else:
                await update.effective_message.reply_text(text_with_hint)

            user_id = update.effective_user.id
            if user_id in self.user_sessions:
                self.user_sessions[user_id]["awaiting_input"] = "text"

    async def button_callback(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Handle button clicks."""
        query = update.callback_query
        user_id = update.effective_user.id

        if user_id not in self.user_sessions:
            await query.answer()
            await query.edit_message_text("❌ No active quiz session. Use /quiz to start.")
            return

        session = self.user_sessions[user_id]
        callback_data = query.data

        # Handle multiple_select toggle buttons
        if callback_data.startswith("ms_toggle:"):
            value = callback_data.split(":", 1)[1]
            choices = session.get("multi_select_choices", [])

            # Toggle the selection
            if value in choices:
                choices.remove(value)
            else:
                choices.append(value)
            session["multi_select_choices"] = choices

            # Update the keyboard to show new state
            options = session.get("multi_select_options", [])
            keyboard = self._build_multi_select_keyboard(options, choices)
            reply_markup = InlineKeyboardMarkup(keyboard)

            await query.answer()
            try:
                await query.edit_message_reply_markup(reply_markup=reply_markup)
            except Exception:
                pass  # Ignore if message can't be edited
            return

        # Handle multiple_select submit button
        if callback_data == "ms_submit":
            choices = session.get("multi_select_choices", [])
            if not choices:
                await query.answer("Please select at least one option!", show_alert=True)
                return

            await query.answer()
            # Clear the multi-select state
            session.pop("multi_select_choices", None)
            session.pop("multi_select_options", None)
            # Submit the selections as a list
            await self.submit_answer(update, user_id, choices)
            return

        # Regular button click (multiple_choice)
        await query.answer()
        await self.submit_answer(update, user_id, callback_data)

    async def file_message(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Handle file messages (photo or document uploads)."""
        user_id = update.effective_user.id

        if user_id not in self.user_sessions:
            await update.message.reply_text(
                "ℹ️ No active quiz. Use /quiz <token> to start a quiz."
            )
            return

        session = self.user_sessions[user_id]
        awaiting_type = session.get("awaiting_input")

        if awaiting_type != "file_upload":
            await update.message.reply_text(
                "ℹ️ The current question doesn't expect a file upload."
            )
            return

        # Download the file from Telegram
        try:
            if update.message.photo:
                # Get the largest photo
                file = await update.message.photo[-1].get_file()
                file_name = f"photo_{file.file_unique_id}.jpg"
            elif update.message.document:
                file = await update.message.document.get_file()
                file_name = update.message.document.file_name
            else:
                await update.message.reply_text("❌ Unsupported file type.")
                return

            # Download file to bytes
            import io
            file_bytes = io.BytesIO()
            await file.download_to_memory(file_bytes)
            file_bytes.seek(0)

            # Upload to PyQuizHub API
            await update.message.reply_text("⏳ Uploading file...")

            upload_response = requests.post(
                f"{self.api_base_url}/uploads/upload",
                files={"file": (file_name, file_bytes, "application/octet-stream")},
                headers={"Authorization": self.user_token},
            )

            if upload_response.status_code != 200:
                await update.message.reply_text(
                    f"❌ Failed to upload file: {upload_response.json().get('detail', 'Unknown error')}"
                )
                return

            upload_data = upload_response.json()
            file_id = upload_data.get("file_id")

            if not file_id:
                await update.message.reply_text("❌ File upload failed: no file_id returned")
                return

            # Submit the file_id as the answer
            await self.submit_answer(update, user_id, {"file_id": file_id})

        except Exception as e:
            logger.error(f"Error handling file upload: {e}")
            await update.message.reply_text(f"❌ Error: {str(e)}")

    async def text_message(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Handle text messages (answers)."""
        user_id = update.effective_user.id

        if user_id not in self.user_sessions:
            await update.message.reply_text(
                "ℹ️ No active quiz. Use /quiz <token> to start a quiz."
            )
            return

        session = self.user_sessions[user_id]
        awaiting_type = session.get("awaiting_input")

        if not awaiting_type:
            await update.message.reply_text(
                "ℹ️ Please use the buttons to answer the current question."
            )
            return

        # Parse answer based on expected type
        answer_value = update.message.text.strip()

        if awaiting_type == "integer":
            try:
                answer_value = int(answer_value)
            except ValueError:
                await update.message.reply_text("❌ Please enter a valid whole number.")
                return
        elif awaiting_type == "float":
            try:
                answer_value = float(answer_value)
            except ValueError:
                await update.message.reply_text("❌ Please enter a valid number.")
                return
        elif awaiting_type == "multiple_select":
            # Parse comma-separated values
            answer_value = [v.strip() for v in answer_value.split(",")]

        await self.submit_answer(update, user_id, answer_value)

    async def submit_answer(
        self, update: Update, user_id: int, answer_value: Any
    ) -> None:
        """Submit an answer to the quiz API."""
        session = self.user_sessions[user_id]
        quiz_id = session["quiz_id"]
        session_id = session["session_id"]

        try:
            response = requests.post(
                f"{self.api_base_url}/quiz/submit_answer/{quiz_id}",
                json={
                    "user_id": str(user_id),
                    "session_id": session_id,
                    "answer": {"answer": answer_value},
                },
                headers={"Authorization": self.user_token},
            )

            if response.status_code != 200:
                await update.effective_message.reply_text(
                    f"❌ Error: {response.json().get('detail', 'Failed to submit answer')}"
                )
                return

            data = response.json()

            # Clear awaiting input flag
            session["awaiting_input"] = None

            # Send next question (or final message if quiz is complete)
            if "question" in data and data["question"]:
                await self.send_question(update, data["question"])
            else:
                # Quiz completed without final message
                await update.effective_message.reply_text(
                    "🎉 Quiz completed!\n\nUse /quiz to start another quiz."
                )
                if user_id in self.user_sessions:
                    del self.user_sessions[user_id]

        except Exception as e:
            logger.error(f"Error submitting answer: {e}")
            await update.effective_message.reply_text(f"❌ Error: {str(e)}")

    def run(self) -> None:
        """Start the bot."""
        logger.info("Starting Telegram bot...")
        self.application.run_polling(allowed_updates=Update.ALL_TYPES)


def main():
    """Main entry point for the Telegram bot."""
    # Load configuration
    config_manager = get_config_manager()
    config_manager.load()

    # Get Telegram bot token from environment
    telegram_token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not telegram_token:
        raise ValueError("TELEGRAM_BOT_TOKEN environment variable not set")

    # Get API configuration
    api_base_url = config_manager.api_base_url
    user_token = config_manager.get_token("user")

    # Create and run bot
    bot = TelegramQuizBot(telegram_token, api_base_url, user_token)
    bot.run()


if __name__ == "__main__":
    main()

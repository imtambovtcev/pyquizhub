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
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CommandHandler("quiz", self.quiz_command))
        self.application.add_handler(CallbackQueryHandler(self.button_callback))
        self.application.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, self.text_message)
        )

        # Store user sessions: {user_id: {quiz_id, session_id, awaiting_input}}
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
            "/quiz <token> - Start a quiz with the given token\n"
            "/help - Show this help message\n\n"
            "How to take a quiz:\n"
            "1. Get a quiz token from your quiz administrator\n"
            "2. Use /quiz <token> to start\n"
            "3. Answer questions by clicking buttons or typing answers\n"
            "4. View your results at the end!"
        )

    async def quiz_command(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Handle /quiz command to start a quiz."""
        if not context.args:
            await update.message.reply_text(
                "❌ Please provide a quiz token:\n" "/quiz <quiz_token>"
            )
            return

        quiz_token = context.args[0]
        user_id = update.effective_user.id

        # Call PyQuizHub API to start quiz
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

    async def send_question(self, update: Update, question_data: dict) -> None:
        """Send a question to the user."""
        question = question_data["data"]
        question_type = question.get("type")

        # Check if it's a final message
        if question_type == "final_message":
            await update.effective_message.reply_text(
                f"🎉 {question['text']}\n\n" "Quiz completed! Use /quiz to start another quiz."
            )
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
            await update.effective_message.reply_text(text, reply_markup=reply_markup)

        elif question_type == "multiple_select":
            text += "\n💡 Select multiple options (comma-separated) or click buttons:\n"
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
            await update.effective_message.reply_text(text, reply_markup=reply_markup)
            # Mark that we're awaiting text input
            user_id = update.effective_user.id
            if user_id in self.user_sessions:
                self.user_sessions[user_id]["awaiting_input"] = "multiple_select"

        elif question_type in ["integer", "float", "text"]:
            type_hint = {
                "integer": "whole number",
                "float": "decimal number",
                "text": "text",
            }
            text += f"\n💡 Please type your answer ({type_hint[question_type]}):"
            await update.effective_message.reply_text(text)
            # Mark that we're awaiting text input
            user_id = update.effective_user.id
            if user_id in self.user_sessions:
                self.user_sessions[user_id]["awaiting_input"] = question_type

        else:
            await update.effective_message.reply_text(
                text + "\n💡 Please type your answer:"
            )
            user_id = update.effective_user.id
            if user_id in self.user_sessions:
                self.user_sessions[user_id]["awaiting_input"] = "text"

    async def button_callback(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Handle button clicks."""
        query = update.callback_query
        await query.answer()

        user_id = update.effective_user.id
        if user_id not in self.user_sessions:
            await query.edit_message_text("❌ No active quiz session. Use /quiz to start.")
            return

        answer_value = query.data
        await self.submit_answer(update, user_id, answer_value)

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

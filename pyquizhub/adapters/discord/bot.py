"""
Discord Bot adapter for PyQuizHub.

This module implements a Discord bot that allows users to take quizzes
through Discord chat interface.
"""

from __future__ import annotations

import os
import logging
from typing import Any

import discord
from discord.ext import commands
from discord import app_commands
import requests

from pyquizhub.config.settings import get_config_manager, get_logger

logger = get_logger(__name__)


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

        super().__init__(command_prefix="!", intents=intents)

        self.token = token
        self.api_base_url = api_base_url
        self.user_token = user_token

        # Store user sessions: {user_id: {quiz_id, session_id, channel_id, awaiting_input}}
        self.user_sessions: dict[int, dict[str, Any]] = {}

        # Register commands
        self.setup_commands()

    def setup_commands(self):
        """Set up bot commands."""

        @self.event
        async def on_ready():
            """Called when bot is ready."""
            logger.info(f"Discord bot logged in as {self.user}")
            try:
                synced = await self.tree.sync()
                logger.info(f"Synced {len(synced)} slash command(s)")
            except Exception as e:
                logger.error(f"Failed to sync commands: {e}")

        @self.event
        async def on_message(message: discord.Message):
            """Handle text messages (answers)."""
            # Ignore messages from the bot itself
            if message.author == self.user:
                return

            # Process commands first
            await self.process_commands(message)

            # If message is not a command, check if it's an answer
            if not message.content.startswith(self.command_prefix):
                await self.handle_text_answer(message)

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
                "💡 **Tip:** If you're in the middle of answering a question, just type your answer - don't use commands!"
            )

        @self.tree.command(name="quiz", description="Start a quiz with a token")
        @app_commands.describe(token="The quiz token to start")
        async def quiz_command(interaction: discord.Interaction, token: str):
            """Handle /quiz command to start a quiz."""
            user_id = interaction.user.id

            # Defer response since API call might take time
            await interaction.response.defer()

            # Call start_quiz API
            try:
                response = requests.post(
                    f"{self.api_base_url}/quiz/start_quiz",
                    json={"token": token, "user_id": str(user_id)},
                    headers={"Authorization": self.user_token},
                )

                if response.status_code != 200:
                    await interaction.followup.send(
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
                    "channel_id": interaction.channel_id,
                    "awaiting_input": None,
                }

                await interaction.followup.send(f"🎓 Starting quiz: **{title}**\n")
                await self.send_question(interaction.channel, data["question"])

            except Exception as e:
                logger.error(f"Error starting quiz: {e}")
                await interaction.followup.send(f"❌ Error: {str(e)}")

        @self.tree.command(name="continue", description="Continue an unfinished quiz")
        @app_commands.describe(token="The quiz token to continue")
        async def continue_command(interaction: discord.Interaction, token: str):
            """Handle /continue command to continue a quiz."""
            user_id = interaction.user.id

            # Defer response since API call might take time
            await interaction.response.defer()

            try:
                response = requests.post(
                    f"{self.api_base_url}/quiz/start_quiz",
                    json={"token": token, "user_id": str(user_id)},
                    headers={"Authorization": self.user_token},
                )

                if response.status_code != 200:
                    await interaction.followup.send(
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
                    "channel_id": interaction.channel_id,
                    "awaiting_input": None,
                }

                await interaction.followup.send(f"🔄 Continuing quiz: **{title}**\n")
                await self.send_question(interaction.channel, data["question"])

            except Exception as e:
                logger.error(f"Error continuing quiz: {e}")
                await interaction.followup.send(f"❌ Error: {str(e)}")

        @self.tree.command(name="status", description="Check your active quiz session")
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
                    f"💡 **Tip:** If you need to see the question again, use `/continue` with your quiz token."
                )
            else:
                await interaction.response.send_message(
                    "ℹ️ No active quiz session.\n\n"
                    "Use `/quiz <token>` to start a new quiz, or `/continue <token>` to resume an unfinished one."
                )

    async def send_question(self, channel: discord.abc.Messageable, question_data: dict) -> None:
        """Send a question to the user."""
        question = question_data["data"]
        question_type = question.get("type")
        image_url = question.get("image_url")

        # Check if it's a final message
        if question_type == "final_message":
            final_text = f"🎉 {question['text']}\n\nQuiz completed! Use `/quiz` to start another quiz."

            if image_url:
                embed = discord.Embed(description=final_text, color=discord.Color.green())
                embed.set_image(url=image_url)
                await channel.send(embed=embed)
            else:
                await channel.send(final_text)

            # Clear session for all users in this channel
            users_to_clear = [uid for uid, sess in self.user_sessions.items()
                            if sess.get("channel_id") == channel.id]
            for uid in users_to_clear:
                del self.user_sessions[uid]
            return

        # Send question text
        text = f"❓ **{question['text']}**\n"

        # Handle different question types
        if question_type == "multiple_choice":
            # Create buttons for options
            view = QuizButtonView(self, question["options"])

            if image_url:
                embed = discord.Embed(description=text, color=discord.Color.blue())
                embed.set_image(url=image_url)
                await channel.send(embed=embed, view=view)
            else:
                await channel.send(text, view=view)

        elif question_type == "multiple_select":
            text += "\n💡 Select multiple options (comma-separated) or click buttons:\n"
            view = QuizButtonView(self, question["options"])

            if image_url:
                embed = discord.Embed(description=text, color=discord.Color.blue())
                embed.set_image(url=image_url)
                await channel.send(embed=embed, view=view)
            else:
                await channel.send(text, view=view)

            # Mark awaiting input for all users in this channel
            for uid, sess in self.user_sessions.items():
                if sess.get("channel_id") == channel.id:
                    sess["awaiting_input"] = "multiple_select"

        elif question_type in ["integer", "float", "text"]:
            type_hint = {
                "integer": "whole number",
                "float": "decimal number",
                "text": "text",
            }
            text += f"\n💡 Please type your answer ({type_hint[question_type]}):"

            if image_url:
                embed = discord.Embed(description=text, color=discord.Color.blue())
                embed.set_image(url=image_url)
                await channel.send(embed=embed)
            else:
                await channel.send(text)

            # Mark awaiting input
            for uid, sess in self.user_sessions.items():
                if sess.get("channel_id") == channel.id:
                    sess["awaiting_input"] = question_type

        else:
            text_with_hint = text + "\n💡 Please type your answer:"

            if image_url:
                embed = discord.Embed(description=text_with_hint, color=discord.Color.blue())
                embed.set_image(url=image_url)
                await channel.send(embed=embed)
            else:
                await channel.send(text_with_hint)

            # Mark awaiting input
            for uid, sess in self.user_sessions.items():
                if sess.get("channel_id") == channel.id:
                    sess["awaiting_input"] = "text"

    async def handle_text_answer(self, message: discord.Message) -> None:
        """Handle text messages as answers."""
        user_id = message.author.id

        if user_id not in self.user_sessions:
            return  # Silently ignore if no active session

        session = self.user_sessions[user_id]
        awaiting_type = session.get("awaiting_input")

        if not awaiting_type:
            return  # Silently ignore if not awaiting input

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

    async def submit_answer(
        self, channel: discord.abc.Messageable, user_id: int, answer_value: Any
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
                await channel.send(
                    f"❌ Error: {response.json().get('detail', 'Failed to submit answer')}"
                )
                return

            data = response.json()

            # Clear awaiting input flag
            session["awaiting_input"] = None

            # Send next question (or final message if quiz is complete)
            if "question" in data and data["question"]:
                await self.send_question(channel, data["question"])
            else:
                # Quiz completed without final message
                await channel.send(
                    "🎉 Quiz completed!\n\nUse `/quiz` to start another quiz."
                )
                if user_id in self.user_sessions:
                    del self.user_sessions[user_id]

        except Exception as e:
            logger.error(f"Error submitting answer: {e}")
            await channel.send(f"❌ Error: {str(e)}")

    def run_bot(self) -> None:
        """Start the bot."""
        logger.info("Starting Discord bot...")
        self.run(self.token)


class QuizButtonView(discord.ui.View):
    """View containing buttons for quiz options."""

    def __init__(self, bot: DiscordQuizBot, options: list[dict]):
        """
        Initialize the button view.

        Args:
            bot: The Discord bot instance
            options: List of option dicts with 'label' and 'value'
        """
        super().__init__(timeout=None)  # No timeout for quiz buttons

        self.bot = bot

        # Add buttons for each option (max 25 components per view in Discord)
        for idx, option in enumerate(options[:25]):
            button = discord.ui.Button(
                label=option["label"],
                style=discord.ButtonStyle.primary,
                custom_id=f"quiz_answer_{idx}"
            )
            button.callback = self.make_button_callback(option["value"])
            self.add_item(button)

    def make_button_callback(self, answer_value: str):
        """Create a callback function for a button."""
        async def button_callback(interaction: discord.Interaction):
            user_id = interaction.user.id

            if user_id not in self.bot.user_sessions:
                await interaction.response.send_message(
                    "❌ No active quiz session. Use `/quiz` to start.",
                    ephemeral=True
                )
                return

            # Acknowledge the button click
            await interaction.response.defer()

            # Submit the answer
            await self.bot.submit_answer(interaction.channel, user_id, answer_value)

        return button_callback


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
    api_base_url = config_manager.api_base_url
    user_token = config_manager.get_token("user")

    # Create and run bot
    bot = DiscordQuizBot(discord_token, api_base_url, user_token)
    bot.run_bot()


if __name__ == "__main__":
    main()

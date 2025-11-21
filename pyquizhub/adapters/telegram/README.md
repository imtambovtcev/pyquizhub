# Telegram Bot Adapter

A Telegram bot interface for PyQuizHub that allows users to take quizzes through Telegram.

## Features

- 🤖 Interactive quiz taking through Telegram chat
- 📱 Support for multiple question types:
  - Multiple choice (inline buttons)
  - Multiple select (buttons or comma-separated text)
  - Integer/Float input (text messages)
  - Text input (text messages)
- 🎯 Real-time quiz progress
- 📊 Final results display
- 🔒 Secure API integration with user token authentication

## Setup

### 1. Create a Telegram Bot

1. Talk to [@BotFather](https://t.me/botfather) on Telegram
2. Send `/newbot` and follow the instructions
3. Copy the bot token you receive

### 2. Set Environment Variables

```bash
export TELEGRAM_BOT_TOKEN="your-bot-token-here"
export PYQUIZHUB_USER_TOKEN="your-user-token-here"
```

### 3. Start the Bot

```bash
python -m pyquizhub.adapters.telegram.bot
```

Or with poetry:

```bash
poetry run python -m pyquizhub.adapters.telegram.bot
```

## Usage

### User Commands

- `/start` - Start the bot and see welcome message
- `/help` - Show help information
- `/quiz <token>` - Start a quiz with the given token

### Taking a Quiz

1. Get a quiz token from your quiz administrator
2. Start the quiz: `/quiz <your-token>`
3. Answer questions:
   - For multiple choice: Click the inline buttons
   - For text/number input: Type your answer
   - For multiple select: Click buttons or type comma-separated values
4. View your results when the quiz completes!

## Example Session

```
User: /start
Bot: 👋 Hello John!
     Welcome to PyQuizHub Bot! 🎓
     To start a quiz, use: /quiz <quiz_token>

User: /quiz ABC123
Bot: 🎓 Starting quiz: Python Basics

Bot: ❓ What is 2 + 2?
     [1] [2] [3] [4]

User: *clicks [4]*

Bot: ❓ What is your name?
     💡 Please type your answer (text):

User: John

Bot: 🎉 Quiz Completed!
     📊 Your Results:
     Score: 10/10
     Quiz completed! Use /quiz to start another quiz.
```

## Architecture

The Telegram adapter:
1. Receives user commands and messages through Telegram
2. Calls the PyQuizHub API to start quizzes and submit answers
3. Formats API responses as Telegram messages with appropriate buttons
4. Manages user sessions to track quiz progress

## Configuration

The bot uses the following configuration from `config.yaml`:

- `api.base_url`: PyQuizHub API endpoint (default: http://127.0.0.1:8000)
- `security.user_token_env`: Environment variable for user token

## Error Handling

- Invalid quiz tokens show error messages
- Connection errors to the API are caught and reported
- Invalid answer formats (e.g., text instead of number) show helpful hints
- Session management prevents confusion between multiple quizzes

## Development

### Running Tests

```bash
pytest tests/test_adapters/test_telegram.py
```

### Manual Testing

1. Set up environment variables
2. Run the bot
3. Open Telegram and search for your bot
4. Test with /start, /help, and /quiz commands

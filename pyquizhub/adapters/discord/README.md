# Discord Bot Adapter for PyQuizHub

This adapter allows users to take PyQuizHub quizzes through Discord using a Discord bot with slash commands and interactive buttons.

## Features

- **Slash Commands**: Modern Discord slash commands (`/quiz`, `/help`, `/status`, etc.)
- **Interactive Buttons**: Click buttons to answer multiple choice questions
- **Text Input**: Type answers for integer, float, and text questions
- **Image Support**: Display images in quiz questions using Discord embeds
- **Session Management**: Track active quiz sessions per user
- **Error Handling**: Graceful fallback if images fail to load

## Setup Instructions

### 1. Create a Discord Application and Bot

1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Click "New Application"
3. Give it a name (e.g., "PyQuizHub Bot")
4. Go to the "Bot" section in the left sidebar
5. Click "Add Bot"
6. **Important**: Enable "MESSAGE CONTENT INTENT" under "Privileged Gateway Intents"
7. Copy the bot token (you'll need this for the `.env` file)

### 2. Configure Bot Permissions

In the "OAuth2" > "URL Generator" section:

**Scopes:**
- `bot`
- `applications.commands`

**Bot Permissions:**
- Send Messages
- Read Messages/View Channels
- Use Slash Commands
- Embed Links
- Attach Files (for image support)

Copy the generated URL and use it to invite the bot to your Discord server.

### 3. Configure Environment Variables

Add to your `.env` file:

```bash
DISCORD_BOT_TOKEN=your-discord-bot-token-here
PYQUIZHUB_API__BASE_URL=http://localhost:8000  # Or your API URL
PYQUIZHUB_USER_TOKEN=your-secure-user-token-here
```

### 4. Run the Bot

**Using Docker Compose:**

```bash
docker compose up discord-bot
```

**Using Poetry (local development):**

```bash
micromamba activate pyquizhub
poetry run python -m pyquizhub.adapters.discord.bot
```

**Direct Python:**

```bash
python -m pyquizhub.adapters.discord.bot
```

## Usage

### Commands

- `/start` - Welcome message and introduction
- `/help` - Show help information
- `/quiz <token>` - Start a quiz with the provided token
- `/continue <token>` - Continue an unfinished quiz
- `/status` - Check your active quiz session

### Taking a Quiz

1. Get a quiz token from your quiz administrator
2. Use `/quiz <token>` in Discord
3. Answer questions by:
   - **Multiple Choice**: Click the buttons
   - **Integer/Float/Text**: Type your answer in chat
   - **Multiple Select**: Type comma-separated values or click buttons
4. View your results when the quiz completes!

## Supported Question Types

- **multiple_choice**: Displays buttons for each option
- **multiple_select**: Displays buttons + accepts comma-separated text input
- **integer**: Text input, validates as whole number
- **float**: Text input, validates as decimal number
- **text**: Free text input
- **final_message**: Displays quiz completion message

## Image Support

The Discord adapter displays images using Discord embeds:

- Images appear above question text
- Buttons appear below the embed
- Automatic fallback to text-only if image URL fails
- Supports all image question types (fixed URLs, variables, API-fetched)

## Architecture

### Session Management

- Sessions stored in-memory per user ID
- Each session tracks:
  - `quiz_id`: Current quiz identifier
  - `session_id`: API session identifier
  - `channel_id`: Discord channel for responses
  - `awaiting_input`: Expected input type (integer/float/text/etc.)

### Button Handling

Uses Discord's `discord.ui.View` and `discord.ui.Button`:
- Each option gets its own button
- Buttons have no timeout (quiz can be paused)
- Button clicks submit answers directly to the API

### Error Handling

- Invalid bot token → Logs error and exits
- API errors → Sends error message to user
- Invalid answers → Prompts user to retry
- Image load failures → Falls back to text-only

## Troubleshooting

### Bot doesn't respond to commands

1. Check that "MESSAGE CONTENT INTENT" is enabled in Discord Developer Portal
2. Verify bot token is correct in `.env`
3. Ensure bot has proper permissions in your server
4. Check bot logs for errors

### Slash commands not appearing

1. Wait a few minutes after starting the bot (Discord syncs commands)
2. Check bot logs for "Synced X slash command(s)" message
3. Try kicking and re-inviting the bot
4. In development, commands sync to all servers; in production, consider guild-specific commands for faster sync

### Images not displaying

1. Verify image URLs are publicly accessible
2. Check that bot has "Embed Links" permission
3. Test with a known-good image URL
4. Check API logs for image validation errors

### "No active quiz session" errors

1. User must start quiz with `/quiz <token>` first
2. Sessions are in-memory and reset when bot restarts
3. Each user has their own session (can't share)

## Development

### Adding New Commands

1. Define command in `setup_commands()` method
2. Use `@self.tree.command()` decorator
3. Add description for slash command
4. Implement async handler

### Modifying Question Display

Edit `send_question()` method to customize:
- Text formatting
- Embed styling
- Button layout
- Image handling

### Testing Locally

```bash
# Set environment variables
export DISCORD_BOT_TOKEN=your-token
export PYQUIZHUB_API__BASE_URL=http://localhost:8000
export PYQUIZHUB_USER_TOKEN=your-user-token

# Run bot
poetry run python -m pyquizhub.adapters.discord.bot
```

## Comparison with Telegram Adapter

| Feature | Discord | Telegram |
|---------|---------|----------|
| Commands | Slash commands (`/quiz`) | Text commands (`/quiz`) |
| Buttons | Discord UI Buttons | Inline Keyboard Buttons |
| Images | Embeds with set_image | reply_photo with caption |
| Sessions | Per user ID | Per user ID |
| Input | Slash args + text messages | Command args + text messages |
| API | discord.py | python-telegram-bot |

## Dependencies

- `discord.py ^2.4.0`
- `requests` - for API calls
- PyQuizHub core modules

## License

Same as PyQuizHub main project.

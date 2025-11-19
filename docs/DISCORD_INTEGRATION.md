# Discord Bot Integration for PyQuizHub

This document describes the complete Discord bot adapter integration for PyQuizHub.

## Overview

The Discord bot adapter allows users to take PyQuizHub quizzes directly through Discord using modern slash commands and interactive button components. It provides feature parity with the Telegram bot adapter while leveraging Discord-specific features like embeds and button views.

## Implementation Summary

### Files Created

1. **[pyquizhub/adapters/discord/bot.py](../pyquizhub/adapters/discord/bot.py)** (483 lines)
   - Main Discord bot implementation
   - Slash command handlers
   - Button interaction system
   - Session management
   - Question display with image support
   - Answer validation and submission

2. **[pyquizhub/adapters/discord/__init__.py](../pyquizhub/adapters/discord/__init__.py)**
   - Package initialization

3. **[pyquizhub/adapters/discord/README.md](../pyquizhub/adapters/discord/README.md)** (300+ lines)
   - Complete setup guide
   - Usage instructions
   - Troubleshooting tips
   - Architecture documentation

4. **[tests/test_discord_adapter.py](../tests/test_discord_adapter.py)** (550+ lines)
   - 25 comprehensive unit tests
   - Tests for initialization, session management, question display, answer handling
   - Edge case and error handling tests
   - All tests passing ✅

### Files Modified

1. **[pyproject.toml](../pyproject.toml)**
   - Added `discord-py = "^2.4.0"` dependency
   - Added `pytest-asyncio = "^1.3.0"` dev dependency

2. **[docker-compose.yml](../docker-compose.yml)**
   - Added `discord-bot` service
   - Configuration mirrors `telegram-bot` service

3. **[.env.example](../.env.example)**
   - Added Discord bot configuration section
   - Step-by-step setup instructions

4. **[CLAUDE.md](../CLAUDE.md)**
   - Updated testing instructions to include Discord adapter
   - Added Discord to adapter testing checklist

5. **[README.md](../README.md)**
   - Added Discord Bot to Access Adapters list
   - Added Discord bot setup section
   - Updated services list

## Features

### Slash Commands

All bot interactions use modern Discord slash commands:

- `/start` - Welcome message and bot introduction
- `/help` - Display help information with commands list
- `/quiz <token>` - Start a quiz with the provided token
- `/continue <token>` - Resume an unfinished quiz
- `/status` - Check active quiz session

### Question Type Support

| Question Type | Discord Implementation |
|--------------|------------------------|
| `multiple_choice` | Interactive buttons for each option |
| `multiple_select` | Buttons + text input (comma-separated) |
| `integer` | Text input with validation |
| `float` | Text input with decimal validation |
| `text` | Free text input |
| `final_message` | Completion message with image support |

### Image Support

The Discord adapter displays images using Discord embeds:

- **Image Display**: Uses `embed.set_image(url)` for clean presentation
- **Fallback**: Automatic fallback to text-only if image fails to load
- **Question Images**: Images appear above question text
- **Final Message Images**: Images can appear in quiz completion messages
- **Button Integration**: Buttons appear below image embeds

### Session Management

- **Per-User Sessions**: Each user has their own independent quiz session
- **Channel Tracking**: Sessions track which channel they're in
- **State Persistence**: Tracks current question, awaiting input type
- **Automatic Cleanup**: Sessions cleared after quiz completion
- **In-Memory Storage**: Session data stored in bot memory (cleared on restart)

### Error Handling

- **Invalid Inputs**: Clear error messages for wrong data types
- **API Errors**: Graceful error display to users
- **Image Loading Failures**: Automatic fallback to text-only
- **Missing Sessions**: Helpful prompts to start a quiz
- **Network Errors**: Logged and user-friendly error messages

## Architecture

### Class Structure

```python
class DiscordQuizBot(commands.Bot):
    """Main bot class extending discord.ext.commands.Bot"""

    - __init__(token, api_base_url, user_token)
    - setup_commands()  # Register all slash commands
    - send_question(channel, question_data)
    - handle_text_answer(message)
    - submit_answer(channel, user_id, answer_value)
    - run_bot()

class QuizButtonView(discord.ui.View):
    """Button view for multiple choice questions"""

    - __init__(bot, options)
    - make_button_callback(answer_value)
```

### Data Flow

1. **User runs `/quiz <token>`**
   - Bot calls PyQuizHub API `/quiz/start_quiz`
   - Stores session data (quiz_id, session_id, channel_id)
   - Sends first question with buttons/text prompt

2. **User answers (button click or text message)**
   - Bot validates input based on question type
   - Calls PyQuizHub API `/quiz/submit_answer/{quiz_id}`
   - Receives next question or final message
   - Updates session state

3. **Quiz completes**
   - Final message displayed
   - Session deleted from memory
   - User can start new quiz

### API Integration

The Discord bot integrates with PyQuizHub API:

```python
# Start quiz
POST /quiz/start_quiz
{
    "token": "quiz_token",
    "user_id": "discord_user_id"
}

# Submit answer
POST /quiz/submit_answer/{quiz_id}
{
    "user_id": "discord_user_id",
    "session_id": "session_id",
    "answer": {"answer": answer_value}
}
```

## Testing

### Test Coverage

25 unit tests covering:

- ✅ Bot initialization (3 tests)
- ✅ Session management (3 tests)
- ✅ Question display (6 tests)
- ✅ Answer handling (6 tests)
- ✅ Button views (4 tests)
- ✅ Edge cases (3 tests)

### Running Tests

```bash
# Discord adapter tests only
pytest tests/test_discord_adapter.py -v

# All tests (739 total)
pytest
```

### Test Results

```
25 passed in 0.45s
739 passed in 5.13s (full suite)
```

## Deployment

### Docker Compose (Recommended)

```bash
# 1. Add Discord token to .env
echo "DISCORD_BOT_TOKEN=your-token-here" >> .env

# 2. Start all services
docker-compose up -d

# 3. Check logs
docker logs pyquizhub-discord-bot-1
```

### Local Development

```bash
# 1. Set environment variables
export DISCORD_BOT_TOKEN=your-token-here
export PYQUIZHUB_API__BASE_URL=http://localhost:8000
export PYQUIZHUB_USER_TOKEN=your-user-token

# 2. Run bot
poetry run python -m pyquizhub.adapters.discord.bot
```

### Production Considerations

1. **Bot Token Security**
   - Store token in environment variables
   - Never commit tokens to version control
   - Rotate tokens regularly

2. **Permissions**
   - Minimum required permissions:
     - Send Messages
     - Read Messages/View Channels
     - Use Slash Commands
     - Embed Links

3. **Intents**
   - Must enable "MESSAGE CONTENT INTENT" in Discord Developer Portal
   - Required for reading user text answers

4. **Rate Limiting**
   - Discord.py handles rate limits automatically
   - API calls are sequential per user

5. **Monitoring**
   - Check bot logs for errors
   - Monitor API response times
   - Track session creation/deletion

## Comparison with Telegram Adapter

| Feature | Discord | Telegram |
|---------|---------|----------|
| **Commands** | Slash commands (`/quiz`) | Text commands (`/quiz`) |
| **Buttons** | Discord UI Buttons | Inline Keyboard Buttons |
| **Images** | Embeds with `set_image()` | `reply_photo()` with caption |
| **Command Discovery** | Auto-complete in Discord | Manual typing |
| **Permissions** | Role-based | Admin/user distinction |
| **Session Storage** | In-memory per user ID | In-memory per user ID |
| **Input Types** | Slash args + text messages | Command args + text |
| **API Library** | discord.py 2.4.0 | python-telegram-bot 22.5 |

## Known Limitations

1. **Session Persistence**
   - Sessions stored in memory only
   - Lost on bot restart
   - Users must restart quiz if bot restarts

2. **Button Limits**
   - Discord limits 25 components per view
   - Quizzes with >25 options only show first 25

3. **Image URLs**
   - Must be publicly accessible
   - Discord may cache images
   - HTTPS recommended for security

4. **Event Loop**
   - Button views require running event loop
   - Can't be unit tested without async context
   - Integration tests recommended

## Future Enhancements

Potential improvements for future versions:

1. **Persistent Sessions**
   - Store sessions in database
   - Survive bot restarts
   - Cross-server quiz access

2. **Enhanced UI**
   - Rich embeds with colors
   - Progress indicators
   - Quiz thumbnails

3. **Leaderboards**
   - Server-wide leaderboards
   - Role-based rewards
   - Quiz statistics

4. **Voice Integration**
   - Read questions aloud in voice channels
   - Voice-based answer submission

5. **Moderation**
   - Quiz access control per server
   - Admin commands for quiz management
   - User report system

## Troubleshooting

### Bot Doesn't Respond to Commands

**Symptoms**: Slash commands don't appear or don't respond

**Solutions**:
- Check MESSAGE CONTENT INTENT is enabled in Developer Portal
- Verify bot token is correct in `.env`
- Wait a few minutes after bot start (commands sync globally)
- Check bot has proper permissions in server
- Review bot logs for errors

### Slash Commands Not Appearing

**Symptoms**: Commands don't show in Discord's command picker

**Solutions**:
- Wait 5-10 minutes for global command sync
- Check bot logs for "Synced X slash command(s)" message
- Kick and re-invite bot
- Verify bot has `applications.commands` scope

### Images Not Displaying

**Symptoms**: Questions with images show text only

**Solutions**:
- Verify image URLs are publicly accessible
- Check bot has "Embed Links" permission
- Test with known-good image URL (e.g., httpbin.org)
- Review API logs for image validation errors

### "No Active Quiz Session" Errors

**Symptoms**: User gets error when trying to answer

**Solutions**:
- User must start quiz with `/quiz <token>` first
- Sessions reset when bot restarts
- Each user needs their own session (can't share)
- Check user ID matches session user ID

## Conclusion

The Discord bot adapter provides a fully-featured quiz experience within Discord, matching the functionality of the Telegram adapter while leveraging Discord-specific features. With 25 passing tests, comprehensive documentation, and Docker deployment support, it's production-ready and easy to deploy.

For questions or issues, see:
- [Discord Bot README](../pyquizhub/adapters/discord/README.md)
- [PyQuizHub Main Documentation](../README.md)
- [Test Suite](../tests/test_discord_adapter.py)

# PyQuizHub
![logo](image/README/logo.png)
PyQuizHub is a flexible quiz management system with a modular architecture that consists of:

* Core Engine - Handles quiz logic and data management 
* Storage Backends - Supports multiple storage options
* Access Adapters - Provides different access levels and interaction methods

## Features

### Access Levels
- **Admin**
  - Full system access and configuration
  - User management
  - Storage management
  - Full quiz access

- **Creator**
  - Create new quizzes
  - Edit own quizzes
  - View quiz results
  - Generate access tokens

- **User**
  - Take quizzes with valid token
  - View own results
  - Track progress

### Access Adapters
- **Web Interface** - Interactive HTML/JavaScript quiz interface
- **CLI** - Command-line quiz interface
- **Telegram Bot** - Take quizzes via Telegram with inline keyboards
- **Discord Bot** - Take quizzes via Discord with slash commands and buttons

### System Requirements

- Python 3.12+
- PostgreSQL (optional)
- Redis (optional)

## Installation

### Prerequisites
- Python 3.12+
- Poetry (for dependency management)
- PostgreSQL (optional, for production deployment)

### Local Development Setup

1. Clone the repository:
```bash
git clone <repository-url>
cd pyquizhub
```

2. Install dependencies using Poetry:
```bash
poetry install
```

3. (Optional) Configure environment:
```bash
# Copy example environment file
cp .env.example .env

# Edit .env if you need custom settings
# For local development, the defaults in config.yaml work fine
```

4. Run the application:
```bash
# Start API server
poetry run uvicorn pyquizhub.main:app --reload

# Or start web interface (in another terminal)
poetry run python -m pyquizhub.adapters.web.server
```

## Configuration

PyQuizHub uses a layered configuration approach:

1. **Base configuration** (`config.yaml`): Default settings for all environments
2. **Environment variables** (`.env` file or system env): Override specific settings

### Configuration Priority (highest to lowest)
1. Environment variables (`PYQUIZHUB_*`)
2. `.env` file (if present)
3. `config.yaml` file (defaults)

### Environment Variables

All configuration can be overridden using environment variables with the `PYQUIZHUB_` prefix:

- `PYQUIZHUB_STORAGE__TYPE`: Storage type (`file` or `sql`)
- `PYQUIZHUB_STORAGE__SQL__CONNECTION_STRING`: Database connection string
- `PYQUIZHUB_STORAGE__FILE__BASE_DIR`: Directory for file storage
- `PYQUIZHUB_API__BASE_URL`: API base URL
- `PYQUIZHUB_API__HOST`: Server host (default: `0.0.0.0`)
- `PYQUIZHUB_API__PORT`: Server port (default: `8000`)
- `PYQUIZHUB_ADMIN_TOKEN`: Admin authentication token
- `PYQUIZHUB_CREATOR_TOKEN`: Creator authentication token
- `PYQUIZHUB_USER_TOKEN`: User authentication token

**Note:** Use `__` (double underscore) to access nested configuration keys.

### Quick Start Examples

**Local development (file storage, no auth):**
```bash
# No .env needed - uses defaults from config.yaml
poetry run uvicorn pyquizhub.main:app --reload
```

**Local development (PostgreSQL):**
```bash
# Create .env file:
echo 'PYQUIZHUB_STORAGE__TYPE=sql' > .env
echo 'PYQUIZHUB_STORAGE__SQL__CONNECTION_STRING=postgresql://user:pass@localhost/pyquizhub' >> .env

poetry run uvicorn pyquizhub.main:app --reload
```

**Production (with authentication):**
```bash
# Generate secure tokens
python -c "import secrets; print('Admin:', secrets.token_urlsafe(32))"
python -c "import secrets; print('Creator:', secrets.token_urlsafe(32))"
python -c "import secrets; print('User:', secrets.token_urlsafe(32))"

# Add to .env file
PYQUIZHUB_ADMIN_TOKEN=<generated-admin-token>
PYQUIZHUB_CREATOR_TOKEN=<generated-creator-token>
PYQUIZHUB_USER_TOKEN=<generated-user-token>
```

## Deployment Options

### Docker Deployment

The easiest way to deploy PyQuizHub with PostgreSQL:

1. Copy and configure environment:
```bash
cp .env.example .env
# Edit .env with your settings (see comments in file)
```

2. Generate secure tokens for production:
```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
# Add generated tokens to .env file
```

3. Start services:
```bash
docker-compose up -d
```

Services:
- API: `http://localhost:8000`
- Web Interface: `http://localhost:8080`
- Admin Web: `http://localhost:8081`
- PostgreSQL: `localhost:5433` (mapped from container port 5432)
- Telegram Bot: (if `TELEGRAM_BOT_TOKEN` configured)
- Discord Bot: (if `DISCORD_BOT_TOKEN` configured)

4. Stop services:
```bash
docker-compose down
```

### Bot Adapters Setup

#### Telegram Bot

1. Create a bot with [@BotFather](https://t.me/BotFather) on Telegram
2. Copy the bot token
3. Add to `.env`:
```bash
TELEGRAM_BOT_TOKEN=your-telegram-bot-token-here
```
4. Start the bot:
```bash
# With Docker Compose
docker-compose up telegram-bot

# Or locally
poetry run python -m pyquizhub.adapters.telegram.bot
```

#### Discord Bot

1. Create a Discord application at [Discord Developer Portal](https://discord.com/developers/applications)
2. Create a bot in the "Bot" section
3. Enable "MESSAGE CONTENT INTENT" under Privileged Gateway Intents
4. Copy the bot token
5. Add to `.env`:
```bash
DISCORD_BOT_TOKEN=your-discord-bot-token-here
```
6. Invite bot to your server using OAuth2 URL generator:
   - Scopes: `bot`, `applications.commands`
   - Bot Permissions: Send Messages, Read Messages/View Channels, Use Slash Commands, Embed Links
7. Start the bot:
```bash
# With Docker Compose
docker-compose up discord-bot

# Or locally
poetry run python -m pyquizhub.adapters.discord.bot
```

For detailed setup instructions, see:
- [Telegram Bot README](pyquizhub/adapters/telegram/README.md)
- [Discord Bot README](pyquizhub/adapters/discord/README.md)

### Manual Docker Build

```bash
# Build image
docker build -t pyquizhub .

# Run with environment variables
docker run -p 8000:8000 \
  -e PYQUIZHUB_STORAGE__TYPE=file \
  -e PYQUIZHUB_STORAGE__FILE__BASE_DIR=/app/data \
  pyquizhub
```

## Documentation

The documentation is built using Sphinx:

```bash
poetry run sphinx-build -b html docs/ docs/_build/html
```

For detailed documentation, see:
- [Getting Started](docs/getting_started.rst)
- [Architecture Overview](docs/architecture.rst)
- [Quiz Format Guide](docs/quiz_format.rst)
- [Deployment Guide](docs/deployment.rst)

## Testing

Run tests with:
```bash
poetry run pytest
```

## Security Considerations

- Use strong authentication tokens
- Enable HTTPS in production
- Implement proper database security:
  - Regular backups
  - Connection encryption
  - Proper user permissions
- Enable rate limiting
- Follow security best practices

## License

This project is licensed under the MIT License.
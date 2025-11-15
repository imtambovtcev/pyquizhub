# PyQuizHub

![logo](image/README/logo.png)

**PyQuizHub v2.0** - A powerful, flexible quiz management system with advanced features including API integrations, typed variables, and comprehensive security.

## Overview

PyQuizHub is a modular quiz management system designed for creating interactive, dynamic quizzes with real-time API integrations. It supports multiple access levels, comprehensive validation, and flexible deployment options.

### Key Features

- **🔄 API Integrations** - Fetch real-time data from external APIs (weather, jokes, facts, etc.)
- **📊 Typed Variable System** - Strongly-typed variables with automatic validation and constraints
- **🔒 Security First** - SSRF protection, input sanitization, permission tiers, and safe expression evaluation
- **🎯 Multiple Question Types** - Multiple choice, multiple select, integer, float, text, and final messages
- **🌐 Admin Web Interface** - User-friendly web UI for quiz management and monitoring
- **🐳 Docker Ready** - Easy deployment with Docker Compose
- **✅ Comprehensive Testing** - 618+ tests covering all features and security scenarios

## Quick Start

### Using Docker (Recommended)

1. **Clone and configure**:
```bash
git clone <repository-url>
cd pyquizhub
cp .env.example .env
```

2. **Set admin token** in `.env`:
```bash
PYQUIZHUB_ADMIN_TOKEN=your-secret-admin-token-here
PYQUIZHUB_USER_TOKEN=your-secure-user-token-here
```

3. **Start services**:
```bash
docker compose up -d
```

4. **Access services**:
- **API**: http://localhost:8000
- **Web Interface**: http://localhost:8080
- **Admin Web**: http://localhost:8081
- **PostgreSQL**: localhost:5433

### Local Development

1. **Install dependencies**:
```bash
poetry install
```

2. **Run API server**:
```bash
poetry run uvicorn pyquizhub.main:app --reload
```

3. **Run web interface** (separate terminal):
```bash
poetry run python -m pyquizhub.adapters.web.server
```

4. **Run tests**:
```bash
poetry run pytest
```

## Architecture

PyQuizHub follows a modular, layered architecture:

```
┌─────────────────────────────────────────┐
│           Access Layer                  │
│  (Admin Web, User Web, CLI, API)        │
├─────────────────────────────────────────┤
│          Business Logic                 │
│  (Quiz Engine, Validators, Security)    │
├─────────────────────────────────────────┤
│         Storage Layer                   │
│    (File Storage, SQL Storage)          │
└─────────────────────────────────────────┘
```

### Core Components

- **Quiz Engine** - Processes quiz logic, API integrations, and state management
- **Variable System** - Typed variables with constraints, tags, and permission-based mutability
- **Security Layer** - SSRF protection, input sanitization, permission enforcement
- **API Integration** - Supports GET/POST, static/dynamic URLs, multiple timing options
- **Storage Backends** - File-based or PostgreSQL with consistent interface
- **Admin Web** - Flask-based management interface
- **User Web** - Interactive quiz-taking interface

## Access Levels

### Admin
- Full system access and configuration
- User and quiz management
- View all results and sessions
- Generate access tokens
- Access to admin web interface

### Creator
- Create and edit own quizzes
- View quiz results for own quizzes
- Generate quiz access tokens
- Limited permissions for API integrations

### User
- Take quizzes with valid token
- View own results
- Track progress across sessions

## System Requirements

- **Python**: 3.10+ (3.12 recommended)
- **Database**: PostgreSQL 15+ (optional, file storage available)
- **Docker**: 20.10+ and Docker Compose 2.0+ (for containerized deployment)
- **Poetry**: 1.5+ (for local development)

## Configuration

PyQuizHub uses a layered configuration approach:

1. **Base configuration** (`config.yaml`) - Default settings
2. **Environment variables** (`.env` file or system) - Override settings

### Key Environment Variables

```bash
# API Configuration
PYQUIZHUB_API__HOST=0.0.0.0
PYQUIZHUB_API__PORT=8000

# Authentication
PYQUIZHUB_ADMIN_TOKEN=your-admin-token
PYQUIZHUB_USER_TOKEN=your-user-token

# Storage (file or sql)
PYQUIZHUB_STORAGE__TYPE=file
PYQUIZHUB_STORAGE__FILE__BASE_DIR=/app/data

# OR PostgreSQL
PYQUIZHUB_STORAGE__TYPE=sql
PYQUIZHUB_STORAGE__SQL__CONNECTION_STRING=postgresql://user:pass@localhost/pyquizhub
```

**Note:** Use `__` (double underscore) to access nested configuration keys.

## Quiz JSON Format

PyQuizHub v2.0 uses a typed variable system for flexible, validated quizzes.

### Basic Structure

```json
{
  "metadata": {
    "title": "My Quiz",
    "description": "A sample quiz",
    "author": "Admin",
    "version": "2.0"
  },
  "variables": {
    "score": {
      "type": "integer",
      "mutable_by": ["engine"],
      "tags": ["score", "public"],
      "description": "User's total score"
    }
  },
  "questions": [
    {
      "id": 1,
      "data": {
        "text": "What is 2 + 2?",
        "type": "integer"
      },
      "score_updates": [
        {
          "condition": "answer == 4",
          "update": {
            "score": "score + 1"
          }
        }
      ]
    }
  ],
  "transitions": {
    "1": [
      {"expression": "true", "next_question_id": null}
    ]
  }
}
```

### API Integration Example

```json
{
  "api_integrations": [
    {
      "id": "weather_api",
      "timing": "before_question",
      "question_id": 1,
      "method": "GET",
      "url": "https://api.weatherapi.com/v1/current.json?q=London",
      "auth": {"type": "none"},
      "extract_response": {
        "variables": {
          "temperature": {
            "path": "current.temp_c",
            "type": "float"
          }
        }
      }
    }
  ]
}
```

## Testing

PyQuizHub has comprehensive test coverage (618+ tests):

```bash
# Run all tests
poetry run pytest

# Run with coverage
poetry run pytest --cov=pyquizhub --cov-report=html

# Run specific test category
poetry run pytest tests/test_security/
poetry run pytest tests/test_joke_quiz_api_timing.py
```

### Test Categories

- **Unit Tests** - Core engine, validators, variable system
- **Integration Tests** - API endpoints, storage backends
- **Security Tests** - SSRF, injection, malicious payloads
- **Flow Tests** - Complete quiz workflows for each quiz type
- **API Timing Tests** - Static vs dynamic API integration patterns

## Documentation

Comprehensive documentation is available in the [`docs/`](docs/) directory:

- [Quiz JSON Format Guide](docs/quiz_json_format_guide.md) - Complete quiz format reference
- [API Integration Guide](docs/api_integration.md) - External API integration patterns
- [Security Redesign](docs/SECURITY_REDESIGN.md) - Security architecture and features
- [Variable System](docs/VARIABLE_SYSTEM_EXAMPLE.md) - Typed variable system examples
- [Configuration Guide](docs/configuration.md) - Deployment and configuration options

### Admin Web Interface

See [admin_web/README.md](admin_web/README.md) for admin interface documentation.

## Security

PyQuizHub v2.0 includes comprehensive security features:

- **SSRF Protection** - URL validation, allowlist/blocklist, localhost blocking
- **Input Sanitization** - All user inputs are validated and sanitized
- **Permission System** - Tiered permissions (RESTRICTED, STANDARD, ADVANCED, ADMIN)
- **Safe Expression Evaluation** - Sandboxed expression execution
- **Rate Limiting** - Configurable rate limits for API calls
- **Authentication** - Token-based auth for all access levels

For detailed security information, see [docs/SECURITY_REDESIGN.md](docs/SECURITY_REDESIGN.md).

## Deployment

### Docker Compose (Production)

```bash
# 1. Configure environment
cp .env.example .env
# Edit .env with production settings

# 2. Generate secure tokens
python -c "import secrets; print(secrets.token_urlsafe(32))"

# 3. Start services
docker compose up -d

# 4. View logs
docker compose logs -f

# 5. Stop services
docker compose down
```

### Services

- **api** - FastAPI backend (port 8000)
- **web** - User quiz interface (port 8080)
- **admin-web** - Admin management interface (port 8081)
- **db** - PostgreSQL database (port 5433)

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Guidelines

- Run tests before committing: `poetry run pytest`
- Follow PEP 8 style guidelines
- Add tests for new features
- Update documentation

## Version History

See [CHANGELOG.md](CHANGELOG.md) for version history and release notes.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

- **Issues**: [GitHub Issues](https://github.com/yourusername/pyquizhub/issues)
- **Documentation**: [docs/](docs/)
- **Examples**: [tests/test_quiz_jsons/](tests/test_quiz_jsons/)

## Acknowledgments

- Built with FastAPI, Flask, PostgreSQL, and Python
- Tested with pytest and comprehensive test coverage
- Designed for security, flexibility, and ease of use

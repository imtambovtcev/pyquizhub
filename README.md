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

### System Requirements

- Python 3.10+
- PostgreSQL (optional)
- Redis (optional)

## Installation

1. Using Poetry:
```bash
poetry install
```

2. Set required environment variables:
```bash
PYQUIZHUB_STORAGE=sql  # or filesystem
PYQUIZHUB_DB_URL=postgresql://user:pass@localhost/pyquizhub
PYQUIZHUB_SECRET_KEY=your-secret-key
PYQUIZHUB_LOG_LEVEL=INFO
```

## Deployment Options

### Local Development
```bash
poetry run uvicorn pyquizhub.main:app --reload
```

### Docker Deployment
```bash
# Build image
docker build -t pyquizhub .

# Run with docker-compose
docker-compose up
```

Example docker-compose.yml:
```yaml
version: '3.8'
services:
  web:
    image: pyquizhub
    ports:
      - "8080:8080"
    environment:
      - PYQUIZHUB_STORAGE=sql
      - PYQUIZHUB_DB_URL=postgresql://user:pass@db/pyquizhub
    depends_on:
      - db
  db:
    image: postgres:15
    environment:
      - POSTGRES_DB=pyquizhub
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=pass
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
# Contributing to PyQuizHub

Thank you for your interest in contributing to PyQuizHub! This guide will help you get started.

## Code of Conduct

Please be respectful and constructive in all interactions. We aim to maintain a welcoming and inclusive environment.

## Getting Started

### Prerequisites

- Python 3.10+ (3.12 recommended)
- Poetry 1.5+
- Docker and Docker Compose (for containerized development)
- Git
- PostgreSQL (optional, for database testing)

### Setting Up Development Environment

1. **Fork and clone the repository**:
```bash
git clone https://github.com/yourusername/pyquizhub.git
cd pyquizhub
```

2. **Install dependencies**:
```bash
poetry install
```

3. **Set up environment**:
```bash
cp .env.example .env
# Edit .env if needed for local development
```

4. **Run tests to verify setup**:
```bash
poetry run pytest
```

5. **Start development server**:
```bash
# API server
poetry run uvicorn pyquizhub.main:app --reload

# Web interface (in another terminal)
poetry run python -m pyquizhub.adapters.web.server

# Admin web (in another terminal)
cd admin_web
python app.py
```

## Development Workflow

### 1. Create a Feature Branch

```bash
git checkout -b feature/your-feature-name
# or
git checkout -b fix/bug-description
# or
git checkout -b docs/documentation-update
```

### 2. Make Your Changes

- Write clean, readable code
- Follow PEP 8 style guidelines
- Add docstrings to functions and classes
- Keep commits atomic and focused

### 3. Add Tests

**All new features must include tests!**

```bash
# Create test file
touch tests/test_your_feature.py

# Write tests
poetry run pytest tests/test_your_feature.py -v
```

See [TESTING.md](TESTING.md) for testing guidelines.

### 4. Run Tests and Linting

```bash
# Run all tests
poetry run pytest

# Run with coverage
poetry run pytest --cov=pyquizhub

# Check code style (if configured)
poetry run black pyquizhub/
poetry run isort pyquizhub/
poetry run flake8 pyquizhub/
```

### 5. Update Documentation

- Update relevant `.md` files in `docs/`
- Add docstrings to new functions/classes
- Update README if adding major features
- Update CHANGELOG.md

### 6. Commit Your Changes

```bash
git add .
git commit -m "feat: add new feature description"
# or
git commit -m "fix: resolve bug description"
# or
git commit -m "docs: update documentation"
```

#### Commit Message Format

We follow conventional commits:

- `feat:` - New feature
- `fix:` - Bug fix
- `docs:` - Documentation changes
- `style:` - Code style changes (formatting, etc.)
- `refactor:` - Code refactoring
- `test:` - Adding or updating tests
- `chore:` - Maintenance tasks

Examples:
```
feat: add dynamic API timing support for quizzes
fix: correct validation error for array variables
docs: update API integration guide with examples
test: add comprehensive SSRF protection tests
refactor: simplify variable constraint application logic
```

### 7. Push and Create Pull Request

```bash
git push origin feature/your-feature-name
```

Then create a pull request on GitHub with:
- Clear title describing the change
- Description of what was changed and why
- Reference to related issues (if any)
- Screenshots (for UI changes)
- Test results

## Code Style Guidelines

### Python Code

- **PEP 8**: Follow Python style guidelines
- **Type Hints**: Use type hints for function parameters and return values
- **Docstrings**: Add docstrings to all public functions and classes

Example:
```python
def validate_quiz(
    quiz_data: dict,
    creator_tier: CreatorPermissionTier = CreatorPermissionTier.RESTRICTED
) -> dict:
    """
    Validate the JSON structure and contents of a quiz.

    Args:
        quiz_data: The quiz data to validate
        creator_tier: The permission tier of the quiz creator

    Returns:
        dict: Validation results containing errors, warnings, and permission_errors

    Examples:
        >>> result = validate_quiz(quiz_data)
        >>> if result["errors"]:
        ...     print("Validation failed:", result["errors"])
    """
```

### File Structure

- Keep files focused and single-purpose
- Use clear, descriptive file names
- Group related functionality in modules

### Import Organization

```python
# Standard library imports
import json
from typing import Dict, Any

# Third-party imports
import requests
from fastapi import FastAPI

# Local application imports
from pyquizhub.core.engine import QuizEngine
from pyquizhub.config import settings
```

## Testing Guidelines

### Test Requirements

- **All new features must have tests**
- **All bug fixes must have regression tests**
- Aim for >90% code coverage for new code
- Tests should be fast and independent

### Test Structure

```python
import pytest
from starlette.testclient import TestClient

class TestNewFeature:
    """Tests for the new feature."""

    @pytest.fixture(scope="class")
    def setup(self, api_client, admin_headers):
        """Set up test data."""
        # Create test data
        return test_data

    def test_feature_basic_functionality(self, api_client, user_headers, setup):
        """Test that feature works in basic case."""
        # Arrange
        request_data = {...}

        # Act
        response = api_client.post("/endpoint", json=request_data, headers=user_headers)

        # Assert
        assert response.status_code == 200
        assert response.json()["result"] == expected_value

    def test_feature_error_handling(self, api_client, user_headers, setup):
        """Test that feature handles errors correctly."""
        # Test error cases
```

### Running Tests

```bash
# All tests
poetry run pytest

# Specific test file
poetry run pytest tests/test_your_feature.py

# Specific test
poetry run pytest tests/test_your_feature.py::test_specific_function

# With coverage
poetry run pytest --cov=pyquizhub --cov-report=html
```

## Security Considerations

### When Adding Features

- **Validate all inputs** - Never trust user input
- **Use parameterized queries** - Prevent SQL injection
- **Sanitize outputs** - Prevent XSS attacks
- **Check permissions** - Enforce access controls
- **Rate limit API calls** - Prevent abuse
- **Avoid SSRF vulnerabilities** - Validate URLs carefully

### Security Testing

Add security tests for new features:

```python
def test_feature_prevents_injection():
    """Test that feature prevents injection attacks."""
    malicious_input = "'; DROP TABLE users; --"
    response = api_client.post("/endpoint", json={"data": malicious_input})
    # Verify injection is prevented
```

## Documentation Guidelines

### Code Documentation

- Add docstrings to all public functions and classes
- Include parameter descriptions and return values
- Provide usage examples for complex functions
- Document any side effects or state changes

### Markdown Documentation

- Use clear, concise language
- Include code examples
- Add screenshots for UI features
- Keep documentation up to date

### API Documentation

- Document all API endpoints
- Include request/response examples
- Specify error responses
- Note authentication requirements

## Pull Request Process

### Before Submitting

- [ ] All tests pass locally
- [ ] Code follows style guidelines
- [ ] Documentation is updated
- [ ] Commit messages are clear
- [ ] No commented-out code or debug statements
- [ ] CHANGELOG.md is updated (for significant changes)

### PR Review Process

1. **Automated Checks**: GitHub Actions will run tests
2. **Code Review**: Maintainers will review your code
3. **Feedback**: Address any requested changes
4. **Approval**: PR will be merged after approval

### What Reviewers Look For

- Code quality and readability
- Test coverage
- Documentation completeness
- Security considerations
- Performance implications
- Backward compatibility

## Types of Contributions

### Bug Fixes

1. Create an issue describing the bug
2. Include steps to reproduce
3. Fix the bug and add regression test
4. Submit PR referencing the issue

### New Features

1. Discuss feature in an issue first
2. Get feedback on approach
3. Implement feature with tests
4. Update documentation
5. Submit PR

### Documentation

- Fix typos or unclear sections
- Add examples or tutorials
- Improve API documentation
- Update outdated information

### Tests

- Add missing test coverage
- Improve existing tests
- Add edge case testing
- Add security tests

## Project Structure

```
pyquizhub/
├── pyquizhub/           # Main application code
│   ├── core/            # Core business logic
│   │   ├── engine/      # Quiz engine and logic
│   │   ├── storage/     # Storage backends
│   │   └── security/    # Security features
│   ├── adapters/        # Access interfaces
│   │   ├── api/         # FastAPI endpoints
│   │   ├── web/         # User web interface
│   │   └── cli/         # Command-line interface
│   ├── config/          # Configuration management
│   └── models.py        # Pydantic models
├── admin_web/           # Admin web interface
├── tests/               # Test suite
├── docs/                # Documentation
└── README.md            # Main documentation
```

## Key Areas for Contribution

### High Priority

- **Security improvements** - SSRF protection, input validation
- **Performance optimization** - Query optimization, caching
- **Test coverage** - Add missing tests
- **Documentation** - Improve guides and examples
- **Bug fixes** - Fix reported issues

### Feature Ideas

- Visual quiz editor in admin web
- Quiz analytics and insights
- Export/import functionality
- Quiz templates and themes
- Multi-language support
- Webhook integrations
- Quiz scheduling

## Community

### Communication

- **GitHub Issues**: Bug reports and feature requests
- **Pull Requests**: Code contributions and discussions
- **Discussions**: General questions and ideas

### Getting Help

- Check existing documentation first
- Search for existing issues
- Create a new issue if needed
- Be specific and provide context

## License

By contributing, you agree that your contributions will be licensed under the same license as the project (MIT License).

## Recognition

Contributors will be recognized in:
- README.md (for significant contributions)
- CHANGELOG.md (for each release)
- GitHub contributors list

Thank you for contributing to PyQuizHub! 🎉

# Changelog

All notable changes to PyQuizHub will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.0.0] - 2025-01-15

### Major Rewrite - Variable System & Security

This release represents a complete architectural redesign focusing on security, flexibility, and type safety.

### Added

#### Variable System
- **Typed Variables** - Strongly-typed variable system replacing the old scores system
  - Variable types: `integer`, `float`, `boolean`, `string`, `array`
  - Automatic type validation and conversion
  - Constraint system (min/max values, string length, array size)
  - Variable tags (`score`, `leaderboard`, `user_input`, `api_data`, etc.)
  - Mutable-by permissions (`user`, `api`, `engine`)
  - Auto-applied default constraints based on type and tags

#### API Integration
- **Comprehensive API Integration System**
  - Multiple API timing options: `on_quiz_start`, `before_question`, `after_answer`, `on_quiz_end`
  - Static and dynamic URL support with variable substitution
  - Support for GET, POST, PUT, PATCH, DELETE methods
  - Response extraction with JSONPath-like syntax
  - Authentication support (none, fixed, dynamic)
  - Request body templates for POST/PUT requests

#### Security Features
- **SSRF Protection**
  - URL validation and sanitization
  - Allowlist/blocklist for domains
  - Localhost and private IP blocking
  - Configurable rate limiting
  - Permission tiers (RESTRICTED, STANDARD, ADVANCED, ADMIN)

- **Input Sanitization**
  - All user inputs validated and sanitized
  - HTML escaping for string variables
  - SQL injection prevention
  - Path traversal protection

- **Safe Expression Evaluation**
  - Sandboxed expression execution
  - Whitelist of allowed operations
  - Protection against code injection
  - Variable access control

#### Admin Web Interface
- **Flask-based Admin Web UI**
  - Quiz management (create, edit, delete, validate)
  - User management and monitoring
  - Token generation and management
  - Results viewing and export
  - Active session monitoring
  - JSON quiz validation with error reporting
  - Visual quiz editor (planned)

#### Testing
- **Comprehensive Test Suite (618+ tests)**
  - Unit tests for all core components
  - Integration tests for API endpoints
  - Security tests (SSRF, injection, malicious payloads)
  - Quiz flow tests for all quiz types
  - API timing tests (static vs dynamic)
  - Permission validation tests
  - Variable system tests

#### Question Types
- **Final Message Type** - Display final messages without requiring user input
  - Useful for quiz completion messages
  - Supports variable substitution
  - Can include quiz results and feedback

#### Documentation
- Comprehensive quiz JSON format guide
- API integration documentation
- Security architecture documentation
- Variable system examples
- Admin web interface guide
- Testing documentation

### Changed

#### Breaking Changes
- **Variable System** - Replaced `scores` with typed `variables`
  - Migration path: Convert score definitions to integer variables with `["engine"]` mutable_by
  - Old format still supported with deprecation warning

- **API Response Format** - Results now use `variables` instead of `scores`
  - Affects `/quiz/start_quiz` and `/quiz/submit_answer` endpoints
  - Results endpoint returns `variables` object

- **Quiz JSON Schema** - Updated to v2.0 format
  - `scores` → `variables` (with type definitions)
  - Required fields: `type`, `mutable_by` for each variable
  - Optional fields: `tags`, `description`, `constraints`, `default`

#### Improvements
- **Enhanced Validation** - More comprehensive quiz JSON validation
  - Type checking for all variable definitions
  - Expression validation with type awareness
  - API integration structure validation
  - Permission tier validation

- **Better Error Messages** - Detailed validation errors with context
  - Specific error messages for each validation failure
  - Warning system for non-critical issues
  - Permission errors separated from validation errors

- **Performance** - Optimized quiz engine and storage operations
  - Lazy loading of API integrations
  - Efficient variable store implementation
  - Optimized database queries

### Fixed

- **Admin API Validation** - Fixed missing `/api/validate-quiz` endpoint in admin web
  - Added proper quiz validation endpoint
  - Improved error display in frontend
  - Added permission error handling

- **API Integration Timing** - Fixed API call timing for `before_question` timing
  - APIs now correctly called before each question presentation
  - Support for looping quizzes with fresh API data

- **Joke Quiz Flow** - Fixed joke quiz variable substitution
  - Proper variable replacement in question text
  - Support for both static and dynamic joke fetching

- **Weather Quiz Scoring** - Fixed complex scoring logic with API data
  - Correct temperature comparison
  - Proper floating-point handling
  - Variable persistence across questions

### Security

- **SSRF Mitigation** - Comprehensive SSRF protection for API integrations
- **Input Validation** - All user inputs sanitized and validated
- **Permission Enforcement** - Strict permission checking for all operations
- **Safe Evaluation** - Sandboxed expression execution preventing code injection
- **Rate Limiting** - Configurable rate limits for API calls

## [1.0.0] - 2024-11-08

### Initial Release

- Basic quiz engine with score tracking
- File and SQL storage backends
- CLI adapter
- Simple web interface
- Docker deployment support
- Basic question types (multiple choice, text, integer)
- Simple transitions between questions

---

## Migration Guide

### Migrating from v1.0 to v2.0

#### 1. Update Quiz JSON Format

**Old Format (v1.0)**:
```json
{
  "scores": {
    "correct": 0,
    "total": 0
  }
}
```

**New Format (v2.0)**:
```json
{
  "variables": {
    "correct": {
      "type": "integer",
      "mutable_by": ["engine"],
      "tags": ["score", "public"],
      "description": "Number of correct answers"
    },
    "total": {
      "type": "integer",
      "mutable_by": ["engine"],
      "tags": ["score", "public"],
      "description": "Total questions answered"
    }
  }
}
```

#### 2. Update Score Updates

**Old Format**:
```json
{
  "score_updates": [
    {
      "condition": "answer == 'yes'",
      "update": {
        "correct": "correct + 1"
      }
    }
  ]
}
```

**New Format** (same, but uses typed variables):
```json
{
  "score_updates": [
    {
      "condition": "answer == 'yes'",
      "update": {
        "correct": "correct + 1"
      }
    }
  ]
}
```

#### 3. Update API Calls

If using the API programmatically, update to access `variables` instead of `scores`:

**Old**:
```python
response = client.get("/quiz/results/user_id/quiz_id")
score = response["scores"]["correct"]
```

**New**:
```python
response = client.get("/quiz/results/user_id/quiz_id")
score = response["variables"]["correct"]
```

#### 4. Environment Variables

No changes required for environment variables. All existing configuration continues to work.

## Upgrading

### Docker

```bash
# Pull latest image
docker compose pull

# Restart services
docker compose up -d
```

### Local Development

```bash
# Update dependencies
poetry update

# Run tests
poetry run pytest

# Restart services
poetry run uvicorn pyquizhub.main:app --reload
```

---

**Note**: The old `scores` format is still supported with deprecation warnings. We recommend migrating to the new `variables` format for access to new features and better type safety.

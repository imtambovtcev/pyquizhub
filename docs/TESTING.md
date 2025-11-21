# Testing Guide

PyQuizHub has comprehensive test coverage with 618+ tests covering all features, security scenarios, and edge cases.

## Quick Start

```bash
# Run all tests
poetry run pytest

# Run with verbose output
poetry run pytest -v

# Run with coverage
poetry run pytest --cov=pyquizhub --cov-report=html

# Run specific test file
poetry run pytest tests/test_security/test_ssrf_protection.py

# Run specific test class
poetry run pytest tests/test_joke_quiz_api_timing.py::TestDynamicJokeQuiz

# Run specific test
poetry run pytest tests/test_joke_quiz_api_timing.py::TestDynamicJokeQuiz::test_dynamic_api_called_before_each_question
```

## Test Organization

```
tests/
├── test_adapters/           # CLI and adapter tests
├── test_security/           # Security and vulnerability tests
├── test_storage/            # Storage backend tests
├── test_quiz_jsons/         # Sample quiz JSON files
├── test_*_flow.py          # End-to-end quiz flow tests
├── test_*_quiz_scoring.py  # Quiz-specific scoring tests
└── test_*.py               # Unit and integration tests
```

## Test Categories

### 1. Unit Tests (Core Functionality)

#### Engine Tests (`test_engine.py`)
- Quiz state management
- Question transitions
- Score/variable updates
- Expression evaluation

#### Variable System Tests (`test_variable_system.py`)
- Variable type validation
- Constraint enforcement
- Mutable-by permissions
- Variable tags and metadata
- Array handling
- Auto-constraints application

#### Validator Tests (`test_json_validator_new_format.py`)
- Quiz JSON schema validation
- Variable definition validation
- API integration validation
- Permission validation

#### Auto-Constraints Tests (`test_auto_constraints.py`)
- Default constraint application
- Type-specific constraints
- Tag-based constraints
- User input limits

### 2. Integration Tests (API Endpoints)

#### Admin API Tests (`test_admin_api.py`)
- Quiz creation and management
- Token generation
- User management
- Results retrieval
- Quiz deletion

#### Engine API Tests (`test_engine_api.py`)
- Quiz start workflow
- Answer submission
- Session management
- Result tracking

#### API Integration Tests (`test_api_integration.py`)
- External API calls
- Response extraction
- Variable population
- Error handling
- Rate limiting

### 3. Security Tests (`test_security/`)

#### SSRF Protection (`test_ssrf_protection.py`)
```python
# Tests for Server-Side Request Forgery protection
- Localhost blocking
- Private IP blocking
- Domain allowlist/blocklist
- URL validation
- Protocol validation
```

Examples:
```bash
# Run all SSRF tests
poetry run pytest tests/test_security/test_ssrf_protection.py -v

# Specific SSRF test
poetry run pytest tests/test_security/test_ssrf_protection.py::test_ssrf_localhost_blocked
```

#### Injection Protection (`test_injection_protection.py`)
```python
# Tests for various injection attacks
- SQL injection prevention
- Command injection prevention
- Expression injection prevention
- Path traversal prevention
```

#### Malicious Payloads (`test_malicious_quiz_payloads.py`)
```python
# Tests with crafted malicious quiz JSONs
- Malformed JSON handling
- Oversized payloads
- Nested structure attacks
- Type confusion attacks
```

#### Comprehensive Threats (`test_comprehensive_threats.py`)
```python
# Integration tests for combined attack vectors
- Multi-stage attacks
- Chain attacks
- Permission bypass attempts
- Data exfiltration attempts
```

### 4. Quiz Flow Tests

#### Simple Quiz Flow (`test_simple_quiz_flow.py`)
- Basic question answering
- Score updates
- Quiz completion
- Results verification

```bash
# Run simple quiz flow tests
poetry run pytest tests/test_simple_quiz_flow.py -v
```

#### Complex Quiz Flow (`test_complex_quiz_flow.py`)
- Conditional branching
- Quiz loops
- Multiple score variables
- Complex transitions

Example test:
```python
def test_complex_quiz_loop_path_no_then_yes():
    """Test loop behavior - answering no then yes causes loop back to Q1."""
    # Answer NO to apples → loops back to Q1
    # Answer YES to apples → progresses to Q2
    # Verify final scores: fruits=2, apples=1, pears=2
```

#### Joke Quiz Flow (`test_joke_quiz_flow.py`)
- API-integrated quiz execution
- Variable substitution in questions
- Dynamic content display
- Loop behavior with fresh data

#### Weather Quiz Scoring (`test_weather_quiz_scoring.py`)
- Real-time API data integration
- Floating-point calculations
- Complex scoring logic
- Temperature comparisons

### 5. API Timing Tests (`test_joke_quiz_api_timing.py`)

Tests for different API integration timing patterns:

#### Static API Timing
```python
def test_static_api_called_once_at_start():
    """API called once at quiz start, same data on loops."""
    # Start quiz → API called (count = 1)
    # Answer and loop → API NOT called (count = 1)
    # Same joke shown every time
```

#### Dynamic API Timing
```python
def test_dynamic_api_called_before_each_question():
    """API called before EACH question presentation."""
    # Start quiz → API called (count = 1), Joke #1
    # Loop to Q1 → API called (count = 2), Joke #2
    # Loop to Q1 → API called (count = 3), Joke #3
```

### 6. Storage Tests (`test_storage/`)

#### File Storage Tests (`test_file_storage.py`)
- Quiz CRUD operations
- Session management
- Results storage
- Token management

#### SQL Storage Tests (`test_sql_storage.py`)
- Database operations
- Transaction handling
- Concurrent access
- Data integrity

#### Storage Consistency (`test_storage_consistency.py`)
- Cross-backend compatibility
- Data migration
- Backup and restore

### 7. Configuration Tests (`test_config.py`)

- Environment variable parsing
- Configuration validation
- Nested key access
- Default value handling
- Override behavior

## Test Fixtures

### Common Fixtures (`conftest.py`)

```python
@pytest.fixture(scope="module")
def api_client():
    """FastAPI test client for API tests."""

@pytest.fixture(scope="module")
def admin_headers():
    """Headers with admin authentication."""

@pytest.fixture(scope="module")
def user_headers():
    """Headers with user authentication."""
```

### Quiz Fixtures

```python
@pytest.fixture
def simple_quiz():
    """Load simple quiz JSON."""
    with open("tests/test_quiz_jsons/simple_quiz.json") as f:
        return json.load(f)

@pytest.fixture
def mock_joke_api():
    """Mock joke API responses."""
    with patch('pyquizhub.core.engine.api_integration.requests.request') as mock:
        mock.return_value.status_code = 200
        mock.return_value.json.return_value = {"setup": "...", "punchline": "..."}
        yield mock
```

## Sample Quiz JSONs

Located in `tests/test_quiz_jsons/`:

### Basic Quizzes
- `simple_quiz.json` - Minimal quiz (1 question, basic scoring)
- `complex_quiz.json` - Loops and branching
- `test_quiz_integer.json` - Integer question type
- `test_quiz_float.json` - Float question type
- `test_quiz_multiple_choice.json` - Multiple choice
- `test_quiz_multiple_select.json` - Multiple select
- `test_quiz_text.json` - Text input

### API-Integrated Quizzes
- `joke_quiz_api.json` - Joke API integration (dynamic)
- `joke_quiz_static_api.json` - Joke API (static, called once)
- `joke_quiz_dynamic_api.json` - Joke API (dynamic, called per question)
- `weather_quiz.json` - Weather API integration
- `complex_weather_quiz.json` - Complex weather quiz with scoring
- `test_api_simple_static.json` - Simple static API example
- `test_api_dynamic_url.json` - Dynamic URL construction

### Test Quizzes (Variable System)
- `test_variables_all_types.json` - All variable types
- `test_variables_arrays.json` - Array variables
- `test_quiz_float.json` - Float handling
- `new_format_weather_quiz.json` - Weather quiz in new format

### Invalid Quizzes (For Validation Testing)
- `invalid_quiz_missing_keys.json` - Missing required fields
- `invalid_quiz_invalid_variable_type.json` - Invalid type
- `invalid_quiz_invalid_mutable_by.json` - Invalid mutable_by
- `invalid_quiz_multiple_leaderboard.json` - Multiple leaderboard vars
- `invalid_quiz_array_missing_item_type.json` - Array without item type
- And 15+ more invalid quiz files for edge cases

## Running Specific Test Suites

### Security Tests Only
```bash
poetry run pytest tests/test_security/ -v
```

### Flow Tests Only
```bash
poetry run pytest tests/test_*_flow.py -v
```

### API Integration Tests
```bash
poetry run pytest tests/test_api_integration.py tests/test_joke_quiz_api_timing.py -v
```

### Storage Tests
```bash
poetry run pytest tests/test_storage/ -v
```

## Coverage Reports

### Generate HTML Coverage Report
```bash
poetry run pytest --cov=pyquizhub --cov-report=html
open htmlcov/index.html  # View in browser
```

### Coverage by Module
```bash
poetry run pytest --cov=pyquizhub --cov-report=term-missing
```

### Current Coverage
- **Overall**: ~95% code coverage
- **Core Engine**: ~98%
- **Security Layer**: ~97%
- **API Integration**: ~96%
- **Validators**: ~99%

## Test Data

### Mock API Responses

```python
# Joke API Mock
{
    "id": 42,
    "type": "general",
    "setup": "Why don't scientists trust atoms?",
    "punchline": "Because they make up everything!"
}

# Weather API Mock
{
    "location": {"name": "London"},
    "current": {
        "temp_c": 15.5,
        "condition": {"text": "Partly cloudy"}
    }
}
```

## Debugging Tests

### Run with Print Statements
```bash
poetry run pytest -s tests/test_joke_quiz_flow.py
```

### Run with Debugger
```bash
poetry run pytest --pdb tests/test_joke_quiz_flow.py
```

### Show Local Variables on Failure
```bash
poetry run pytest -l tests/test_joke_quiz_flow.py
```

### Run Last Failed Tests
```bash
poetry run pytest --lf
```

## Continuous Integration

Tests run automatically on:
- Every commit (via GitHub Actions)
- Pull requests
- Scheduled nightly builds

### CI Configuration
```yaml
# .github/workflows/test.yml
- name: Run tests
  run: poetry run pytest --cov=pyquizhub --cov-report=xml

- name: Upload coverage
  uses: codecov/codecov-action@v3
```

## Writing New Tests

### Test Template

```python
import pytest
from starlette.testclient import TestClient

class TestNewFeature:
    """Tests for new feature."""

    @pytest.fixture(scope="class")
    def setup_data(self, api_client, admin_headers):
        """Set up test data."""
        # Create quiz, generate token, etc.
        return {"quiz_id": quiz_id, "token": token}

    def test_feature_basic_case(self, api_client, user_headers, setup_data):
        """Test basic functionality."""
        response = api_client.post("/endpoint", json={...}, headers=user_headers)
        assert response.status_code == 200
        assert response.json()["result"] == expected

    def test_feature_edge_case(self, api_client, user_headers, setup_data):
        """Test edge case."""
        # Test boundary conditions, error cases, etc.
```

### Best Practices

1. **Use descriptive test names** - Explain what is being tested
2. **One assertion concept per test** - Test one thing at a time
3. **Use fixtures for setup** - Keep tests clean and DRY
4. **Mock external dependencies** - Don't make real API calls
5. **Test both success and failure** - Cover happy path and error cases
6. **Use parametrize for similar tests** - Test multiple inputs efficiently
7. **Add docstrings** - Explain test purpose and expected behavior

### Example: Parametrized Test

```python
@pytest.mark.parametrize("input_value,expected", [
    (4, True),  # Correct answer
    (3, False), # Wrong answer
    (5, False), # Wrong answer
])
def test_answer_validation(api_client, user_headers, setup_data, input_value, expected):
    """Test answer validation with various inputs."""
    response = api_client.post("/quiz/submit_answer/...", json={"answer": input_value})
    assert (response.json()["correct"] == expected)
```

## Performance Testing

```bash
# Run tests with timing
poetry run pytest --durations=10

# Profile test execution
poetry run pytest --profile

# Stress tests (excluded by default)
poetry run pytest tests/test_stress.py
```

## Test Statistics

- **Total Tests**: 618
- **Test Execution Time**: ~1.8 seconds
- **Success Rate**: 100%
- **Code Coverage**: ~95%
- **Security Tests**: 200+
- **Integration Tests**: 150+
- **Unit Tests**: 268+

## Troubleshooting

### Common Issues

**Issue**: Tests fail with "FileNotFoundError"
```bash
# Solution: Run tests from project root
cd /path/to/pyquizhub
poetry run pytest
```

**Issue**: API integration tests timeout
```bash
# Solution: Check network connection or increase timeout
poetry run pytest --timeout=30
```

**Issue**: Database tests fail
```bash
# Solution: Ensure PostgreSQL is running
docker compose up -d db
poetry run pytest tests/test_storage/test_sql_storage.py
```

## Additional Resources

- [pytest Documentation](https://docs.pytest.org/)
- [Coverage.py Documentation](https://coverage.readthedocs.io/)
- [Mock Documentation](https://docs.python.org/3/library/unittest.mock.html)
- [FastAPI Testing](https://fastapi.tiangolo.com/tutorial/testing/)

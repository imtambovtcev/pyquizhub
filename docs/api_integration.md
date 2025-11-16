# External API Integration for Quizzes

## Overview

PyQuizHub now supports integration with external REST APIs, enabling quizzes to:
- Fetch real-time data (weather, stock prices, news, etc.)
- Use AI/ML services (OpenAI, Hugging Face, etc.)
- Submit answers to external systems
- Validate answers against live data
- Create dynamic, data-driven quiz experiences

## Features

### Supported Capabilities

- ✅ **HTTP Methods**: GET, POST, PUT, DELETE, PATCH
- ✅ **Authentication**: None, API Key, Bearer Token, Basic Auth, OAuth2
- ✅ **Request Timing**: Before quiz, after quiz, before question, after answer
- ✅ **Template Variables**: Inject scores, answers, timestamps into requests
- ✅ **Response Extraction**: JSONPath for extracting specific data
- ✅ **Error Handling**: Automatic retries, timeout management
- ✅ **Stateless Architecture**: All API state stored in session data
- ✅ **Token Management**: Automatic OAuth2 token refresh

### Security Considerations

⚠️ **Important**: API-enabled quizzes should be restricted to authorized quiz creators only.

- API credentials are stored in quiz definitions (should be encrypted in production)
- OAuth2 tokens are refreshed automatically and stored in session state
- Quiz creators have access to external API endpoints
- Rate limiting should be implemented for API calls

## Quiz JSON Structure

### Basic Example: Weather Quiz

```json
{
    "metadata": {
        "title": "Weather Quiz",
        "requires_api": true
    },
    "api_integrations": [
        {
            "id": "weather",
            "timing": "on_quiz_start",
            "url": "https://api.open-meteo.com/v1/forecast?latitude=52.52&longitude=13.41&current=temperature_2m",
            "method": "GET",
            "authentication": {"type": "none"},
            "response_path": "current.temperature_2m"
        }
    ],
    "questions": [
        {
            "id": 1,
            "data": {
                "text": "What is the current temperature in Berlin? (±5°C)",
                "type": "float"
            },
            "score_updates": [
                {
                    "condition": "answer >= (api.weather - 5) and answer <= (api.weather + 5)",
                    "update": {"correct_answers": "correct_answers + 1"}
                }
            ]
        }
    ]
}
```

## API Integration Configuration

### Structure

Each API integration has the following structure:

```json
{
    "id": "unique_identifier",
    "timing": "when_to_execute",
    "url": "https://api.example.com/endpoint",
    "method": "GET|POST|PUT|DELETE|PATCH",
    "authentication": { /* authentication config */ },
    "headers": { /* additional headers */ },
    "body": { /* request body template */ },
    "response_path": "path.to.data",
    "timeout": 10,
    "description": "Human-readable description"
}
```

### Timing Options

| Value | Description | Use Case |
|-------|-------------|----------|
| `on_quiz_start` | Execute when quiz starts | Fetch initial data, authenticate |
| `on_quiz_end` | Execute when quiz completes | Submit results, analytics |
| `before_question` | Execute before showing question | Fetch question-specific data |
| `after_answer` | Execute after answer submitted | Validate answer, submit data |

#### Question-Specific Timing

```json
{
    "id": "specific_api",
    "timing": "before_question",
    "question_id": 2,
    "url": "..."
}
```

This API call will only execute before question 2.

## Authentication Types

### 1. No Authentication

```json
{
    "authentication": {
        "type": "none"
    }
}
```

### 2. API Key

```json
{
    "authentication": {
        "type": "api_key",
        "key_name": "X-API-Key",
        "credential": "your-api-key-here"
    }
}
```

### 3. Bearer Token

```json
{
    "authentication": {
        "type": "bearer",
        "credential": "your-bearer-token"
    }
}
```

### 4. Basic Authentication

```json
{
    "authentication": {
        "type": "basic",
        "username": "your-username",
        "credential": "your-password"
    }
}
```

### 5. OAuth2

```json
{
    "authentication": {
        "type": "oauth2",
        "id": "oauth_service",
        "token_url": "https://oauth.example.com/token",
        "client_id": "your-client-id",
        "client_secret": "your-client-secret",
        "refresh_token": "your-refresh-token"
    }
}
```

**OAuth2 Features:**
- Automatic token refresh when expired
- Tokens stored in session state
- Refresh triggered 5 minutes before expiry

## Template Variables

### Available in URL and Body

You can use `{variable}` syntax to inject dynamic data:

```json
{
    "url": "https://api.example.com/users/{user_id}/score",
    "body": {
        "quiz_id": "{quiz_id}",
        "answer": "{answer}",
        "score": "{correct_answers}"
    }
}
```

### Context Variables by Timing

| Timing | Available Variables |
|--------|---------------------|
| `on_quiz_start` | (none - quiz just starting) |
| `before_question` | `question_id`, all score variables |
| `after_answer` | `question_id`, `answer`, all score variables |
| `on_quiz_end` | `final_scores` (all score variables) |

### Example: POST Request with Templates

```json
{
    "id": "submit_answer",
    "timing": "after_answer",
    "url": "https://api.example.com/answers",
    "method": "POST",
    "body": {
        "question": "{question_id}",
        "user_answer": "{answer}",
        "current_score": "{correct_answers}",
        "timestamp": "{timestamp}"
    }
}
```

## Accessing API Data in Conditions

API responses are accessible in score update conditions and transitions using `api.<id>` syntax:

### Simple Access

```json
{
    "condition": "answer == api.weather.temperature"
}
```

### Nested Data

```json
{
    "condition": "api.stock.current.price > 100"
}
```

### In Score Updates

```json
{
    "score_updates": [
        {
            "condition": "answer == api.trivia.correct_answer",
            "update": {
                "correct_answers": "correct_answers + 1"
            }
        }
    ]
}
```

### Question Text with API Data

```json
{
    "data": {
        "text": "The current temperature is {api.weather}°C. Is it freezing?",
        "type": "multiple_choice",
        "options": [
            {"value": "yes", "label": "Yes"},
            {"value": "no", "label": "No"}
        ]
    }
}
```

## Response Path Extraction

Use JSONPath-like syntax to extract specific data from API responses:

### Example Response

```json
{
    "data": {
        "current": {
            "temperature": 22.5,
            "humidity": 65
        }
    },
    "status": "success"
}
```

### Extraction

```json
{
    "response_path": "data.current.temperature"
}
```

Result: `22.5` (accessible as `api.weather` if id is "weather")

### Array Access

```json
{
    "response_path": "results[0].value"
}
```

## Complete Example: Multi-Step Quiz with APIs

```json
{
    "metadata": {
        "title": "Live Stock Market Quiz",
        "requires_api": true
    },
    "scores": {
        "correct_predictions": 0,
        "total_score": 0
    },
    "api_integrations": [
        {
            "id": "auth",
            "timing": "on_quiz_start",
            "url": "https://api.stockservice.com/auth",
            "method": "POST",
            "authentication": {
                "type": "basic",
                "username": "api_user",
                "credential": "api_password"
            },
            "response_path": "access_token"
        },
        {
            "id": "stock_price",
            "timing": "before_question",
            "question_id": 1,
            "url": "https://api.stockservice.com/v1/price/AAPL",
            "method": "GET",
            "authentication": {
                "type": "bearer",
                "credential": "{api.auth}"
            },
            "response_path": "price.current"
        },
        {
            "id": "submit_prediction",
            "timing": "after_answer",
            "question_id": 1,
            "url": "https://api.stockservice.com/v1/predictions",
            "method": "POST",
            "authentication": {
                "type": "bearer",
                "credential": "{api.auth}"
            },
            "body": {
                "symbol": "AAPL",
                "predicted_price": "{answer}",
                "actual_price": "{api.stock_price}",
                "timestamp": "{timestamp}"
            }
        }
    ],
    "questions": [
        {
            "id": 1,
            "data": {
                "text": "Apple (AAPL) stock is currently at ${api.stock_price}. What will it be in 1 hour? (±$5 to win)",
                "type": "float"
            },
            "score_updates": [
                {
                    "condition": "answer >= (api.stock_price - 5) and answer <= (api.stock_price + 5)",
                    "update": {
                        "correct_predictions": "correct_predictions + 1",
                        "total_score": "total_score + 10"
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

## Implementation Details

### Stateless Architecture

All API state is stored in session data:

```python
session_state = {
    "current_question_id": 1,
    "scores": {...},
    "answers": [...],
    "api_data": {
        "weather": {
            "response": 22.5,
            "timestamp": "2025-11-13T10:00:00",
            "status_code": 200,
            "success": True
        }
    },
    "api_credentials": {
        "oauth_service": {
            "token": "access_token_here",
            "expires_at": "2025-11-13T11:00:00"
        }
    }
}
```

### Session Resumption

Sessions can be resumed after any time period (seconds, days, years):

1. **Token Expiry Check**: OAuth tokens are checked and refreshed if needed
2. **State Recovery**: All API data is preserved in session
3. **Idempotency**: API calls with same inputs won't be repeated unnecessarily

### Error Handling

- **Retries**: Up to 3 automatic retries on network errors
- **Timeouts**: Configurable timeout per API call (default: 10s)
- **Graceful Degradation**: Quiz continues even if API call fails
- **Error Logging**: All API errors are logged with context

## Security Best Practices

### 1. Credential Management

❌ **Don't** store credentials in plain text:
```json
{
    "authentication": {
        "credential": "my-secret-key"
    }
}
```

✅ **Do** use environment variables or encrypted storage:
```python
# In production:
api_config["auth"]["credential"] = os.getenv("API_KEY")
```

### 2. Permission Control

Only authorized quiz creators should create API-enabled quizzes:

```python
def create_quiz(quiz_data, user):
    if quiz_data.get("metadata", {}).get("requires_api"):
        if not user.has_permission("create_api_quiz"):
            raise PermissionError("Not authorized for API quizzes")
```

### 3. Rate Limiting

Implement rate limiting for API calls:

```python
# Per-user rate limiting
# Per-API rate limiting
# Global rate limiting
```

### 4. URL Validation

Validate API URLs to prevent SSRF attacks:

```python
def validate_api_url(url):
    # Block internal IPs
    # Allow only HTTPS in production
    # Whitelist allowed domains
```

## Testing

### Unit Tests

```python
def test_api_integration():
    quiz_data = load_quiz("weather_quiz.json")
    engine = QuizEngine(quiz_data)
    
    state = engine.start_quiz()
    
    # Check API data was fetched
    assert "api_data" in state
    assert "weather" in state["api_data"]
    assert state["api_data"]["weather"]["success"]
```

### Integration Tests

Test with mock API responses:

```python
@patch('requests.get')
def test_weather_quiz_integration(mock_get):
    mock_get.return_value.json.return_value = {
        "current": {"temperature_2m": 22.5}
    }
    mock_get.return_value.status_code = 200
    
    # Run quiz test
```

## Future Enhancements

1. **GraphQL Support**: Add support for GraphQL APIs
2. **WebSocket Support**: Real-time data streaming
3. **Caching**: Response caching to reduce API calls
4. **Batching**: Batch multiple API calls
5. **Webhooks**: Send quiz events to external systems
6. **API Marketplace**: Pre-configured API integrations
7. **Testing Mode**: Mock API responses for testing

## Limitations

- Maximum 10 API calls per quiz (configurable)
- 10-second default timeout
- No support for file uploads
- No support for multipart/form-data
- OAuth2 only supports refresh token grant

## Conclusion

External API integration transforms PyQuizHub from a static quiz platform into a dynamic, data-driven experience platform. Users can create quizzes that interact with the real world, validate answers against live data, and provide personalized experiences based on external services.

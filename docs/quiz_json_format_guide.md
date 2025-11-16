# PyQuizHub Quiz JSON Format Guide

**Version:** 2.0  
**Last Updated:** November 13, 2025

---

## Table of Contents

1. [Overview](#overview)
2. [Basic Structure](#basic-structure)
3. [Top-Level Fields](#top-level-fields)
4. [Question Types](#question-types)
5. [Score Updates and Conditions](#score-updates-and-conditions)
6. [Transitions and Branching](#transitions-and-branching)
7. [API Integrations](#api-integrations)
8. [Expression Syntax](#expression-syntax)
9. [Complete Examples](#complete-examples)
10. [Validation and Best Practices](#validation-and-best-practices)

---

## Overview

PyQuizHub quizzes are defined using JSON files that describe the quiz structure, questions, scoring logic, navigation flow, and optional external API integrations. This format is flexible, supporting everything from simple linear quizzes to complex adaptive quizzes with conditional branching and real-time data fetching.

### Key Features

- **Multiple question types**: text, integer, float, multiple choice, multiple select
- **Dynamic scoring**: Conditional score updates based on answers
- **Branching logic**: Navigate to different questions based on conditions
- **API integration**: Fetch data from external REST APIs
- **Expression evaluation**: Safe evaluation of mathematical and logical expressions
- **Template variables**: Dynamic content using API data and quiz state

---

## Basic Structure

Every quiz JSON must contain four required top-level fields:

```json
{
    "metadata": { /* Quiz information */ },
    "scores": { /* Score variables */ },
    "questions": [ /* Question array */ ],
    "transitions": { /* Navigation rules */ },
    "api_integrations": [ /* Optional: API calls */ ]
}
```

---

## Top-Level Fields

### 1. `metadata` (Required)

Contains descriptive information about the quiz.

**Structure:**
```json
{
    "metadata": {
        "title": "Quiz Title",
        "description": "Brief description of the quiz",
        "author": "Author Name",
        "version": "1.0",
        "requires_api": false
    }
}
```

**Fields:**
- `title` (string): Quiz title shown to users
- `description` (string, optional): Brief description
- `author` (string, optional): Creator's name
- `version` (string, optional): Version number
- `requires_api` (boolean, optional): Set to `true` if quiz needs API calls to function

---

### 2. `scores` (Required)

Defines score variables and their initial values. These variables can be updated based on user answers.

**Structure:**
```json
{
    "scores": {
        "points": 0,
        "correct_answers": 0,
        "streak": 0
    }
}
```

**Rules:**
- All score variables must be initialized with numeric values
- Variable names must not include `answer` (reserved keyword)
- Can have multiple score variables
- Scores are updated using expressions in `score_updates`

---

### 3. `questions` (Required)

An array of question objects. Each question must have a unique ID.

**Basic Question Structure:**
```json
{
    "id": 1,
    "data": {
        "text": "Question text here",
        "type": "multiple_choice",
        "options": [ /* for choice questions */ ]
    },
    "score_updates": [
        {
            "condition": "answer == 'correct_value'",
            "update": {
                "score_name": "score_name + 1"
            }
        }
    ]
}
```

**Fields:**
- `id` (number): Unique identifier for the question
- `data` (object): Question content and configuration
- `score_updates` (array, optional): Rules for updating scores based on answers

---

### 4. `transitions` (Required)

Defines navigation rules between questions. Each question ID maps to an array of transition conditions.

**Structure:**
```json
{
    "transitions": {
        "1": [
            {
                "expression": "answer == 'yes'",
                "next_question_id": 2
            },
            {
                "expression": "true",
                "next_question_id": 3
            }
        ],
        "2": [
            {
                "expression": "true",
                "next_question_id": null
            }
        ]
    }
}
```

**Rules:**
- Key is the question ID (as string)
- Value is an array of transition objects
- Transitions are evaluated **in order**
- First matching condition is used
- `next_question_id: null` ends the quiz
- Should always have a fallback `"expression": "true"` as last transition

---

### 5. `api_integrations` (Optional)

Defines external API calls to fetch data during the quiz. New in v2.0!

**Basic Structure:**
```json
{
    "api_integrations": [
        {
            "id": "weather",
            "timing": "on_quiz_start",
            "url": "https://api.weather.com/current",
            "method": "GET",
            "authentication": {
                "type": "none"
            },
            "response_path": "temperature"
        }
    ]
}
```

See [API Integrations](#api-integrations) section for detailed documentation.

---

## Question Types

### 1. Multiple Choice (`multiple_choice`)

Single answer selection from predefined options.

```json
{
    "id": 1,
    "data": {
        "text": "What is the capital of France?",
        "type": "multiple_choice",
        "options": [
            {"value": "paris", "label": "Paris"},
            {"value": "london", "label": "London"},
            {"value": "berlin", "label": "Berlin"}
        ]
    },
    "score_updates": [
        {
            "condition": "answer == 'paris'",
            "update": {"points": "points + 1"}
        }
    ]
}
```

**Answer Type:** `string` (the selected `value`)

---

### 2. Multiple Select (`multiple_select`)

Multiple answers can be selected from options.

```json
{
    "id": 2,
    "data": {
        "text": "Select all prime numbers:",
        "type": "multiple_select",
        "options": [
            {"value": "2", "label": "2"},
            {"value": "3", "label": "3"},
            {"value": "4", "label": "4"},
            {"value": "5", "label": "5"}
        ]
    },
    "score_updates": [
        {
            "condition": "'2' in answer and '3' in answer and '5' in answer and '4' not in answer",
            "update": {"points": "points + 2"}
        }
    ]
}
```

**Answer Type:** `list` (array of selected `value`s)

---

### 3. Text Input (`text`)

Free-form text answer.

```json
{
    "id": 3,
    "data": {
        "text": "What is the largest planet?",
        "type": "text"
    },
    "score_updates": [
        {
            "condition": "answer == 'Jupiter' or answer == 'jupiter'",
            "update": {"points": "points + 1"}
        }
    ]
}
```

**Answer Type:** `string`

---

### 4. Integer Input (`integer`)

Whole number input.

```json
{
    "id": 4,
    "data": {
        "text": "How many continents are there?",
        "type": "integer",
        "min": 1,
        "max": 10
    },
    "score_updates": [
        {
            "condition": "answer == 7",
            "update": {"points": "points + 1"}
        }
    ]
}
```

**Answer Type:** `integer`  
**Optional Fields:** `min`, `max` (validation bounds)

---

### 5. Float Input (`float`)

Decimal number input.

```json
{
    "id": 5,
    "data": {
        "text": "What is the value of π (to 2 decimal places)?",
        "type": "float",
        "min": 0.0,
        "max": 10.0
    },
    "score_updates": [
        {
            "condition": "answer >= 3.13 and answer <= 3.15",
            "update": {"points": "points + 1"}
        }
    ]
}
```

**Answer Type:** `float`  
**Optional Fields:** `min`, `max` (validation bounds), `hint`

---

## Score Updates and Conditions

Score updates define how quiz variables change based on user answers.

### Basic Score Update

```json
{
    "score_updates": [
        {
            "condition": "answer == 'correct'",
            "update": {
                "score": "score + 1"
            }
        }
    ]
}
```

### Multiple Conditions

```json
{
    "score_updates": [
        {
            "condition": "answer >= 90",
            "update": {
                "grade": "grade + 100",
                "rank": "'A'"
            }
        },
        {
            "condition": "answer >= 70",
            "update": {
                "grade": "grade + 70",
                "rank": "'B'"
            }
        },
        {
            "condition": "true",
            "update": {
                "grade": "grade + 50",
                "rank": "'C'"
            }
        }
    ]
}
```

**Note:** All matching conditions are applied (not just the first one), so order your conditions carefully or use mutually exclusive conditions.

### Complex Conditions

```json
{
    "condition": "answer > 10 and score < 100",
    "update": {
        "score": "score + (answer * 2)",
        "bonus": "bonus + 5"
    }
}
```

---

## Transitions and Branching

Transitions control which question appears next based on conditions.

### Linear Flow

```json
{
    "transitions": {
        "1": [{"expression": "true", "next_question_id": 2}],
        "2": [{"expression": "true", "next_question_id": 3}],
        "3": [{"expression": "true", "next_question_id": null}]
    }
}
```

### Conditional Branching

```json
{
    "transitions": {
        "1": [
            {
                "expression": "answer == 'expert'",
                "next_question_id": 10
            },
            {
                "expression": "answer == 'beginner'",
                "next_question_id": 2
            },
            {
                "expression": "true",
                "next_question_id": 5
            }
        ]
    }
}
```

### Score-Based Branching

```json
{
    "transitions": {
        "5": [
            {
                "expression": "points >= 10",
                "next_question_id": null
            },
            {
                "expression": "points < 5",
                "next_question_id": 1
            },
            {
                "expression": "true",
                "next_question_id": 6
            }
        ]
    }
}
```

### Looping

```json
{
    "transitions": {
        "1": [
            {
                "expression": "answer == 'no'",
                "next_question_id": 1
            },
            {
                "expression": "true",
                "next_question_id": 2
            }
        ]
    }
}
```

---

## API Integrations

API integrations allow quizzes to fetch data from external REST APIs. This enables dynamic content, real-time data, and personalized quiz experiences.

### API Configuration Object

```json
{
    "id": "unique_api_id",
    "timing": "on_quiz_start",
    "question_id": 1,
    "url": "https://api.example.com/data",
    "method": "GET",
    "authentication": {
        "type": "bearer",
        "credential": "your_token_here"
    },
    "headers": {
        "Accept": "application/json"
    },
    "body": {
        "key": "value"
    },
    "response_path": "data.result",
    "timeout": 10,
    "max_retries": 3,
    "description": "Description of what this API does"
}
```

### API Timing Options

The `timing` field determines when the API call is executed:

#### 1. `on_quiz_start`
Execute when quiz begins (before first question).

```json
{
    "id": "init_data",
    "timing": "on_quiz_start",
    "url": "https://api.example.com/init"
}
```

**Use cases:** Fetch user profile, get quiz seed data, initialize session

---

#### 2. `before_question`
Execute before displaying a specific question.

```json
{
    "id": "question_data",
    "timing": "before_question",
    "question_id": 3,
    "url": "https://api.example.com/question/3"
}
```

**Use cases:** Load question-specific content, fetch hints, get dynamic question text

---

#### 3. `after_answer`
Execute after user submits answer to a specific question.

```json
{
    "id": "submit_answer",
    "timing": "after_answer",
    "question_id": 2,
    "url": "https://api.example.com/submit",
    "method": "POST",
    "body": {
        "answer": "{answer}",
        "question_id": "{question_id}"
    }
}
```

**Use cases:** Submit answers to analytics, trigger notifications, update external systems

---

#### 4. `on_quiz_end`
Execute when quiz completes.

```json
{
    "id": "final_submit",
    "timing": "on_quiz_end",
    "url": "https://api.example.com/results",
    "method": "POST",
    "body": {
        "score": "{points}",
        "user_id": "{user_id}"
    }
}
```

**Use cases:** Submit final results, send completion certificates, update leaderboards

---

### HTTP Methods

Supported methods: `GET`, `POST`, `PUT`, `DELETE`, `PATCH`

```json
{
    "method": "POST",
    "body": {
        "data": "value"
    }
}
```

---

### Authentication Types

#### 1. No Authentication

```json
{
    "authentication": {
        "type": "none"
    }
}
```

---

#### 2. API Key

```json
{
    "authentication": {
        "type": "api_key",
        "key_name": "X-API-Key",
        "credential": "your_api_key_here"
    }
}
```

The API key is added to request headers: `X-API-Key: your_api_key_here`

---

#### 3. Bearer Token

```json
{
    "authentication": {
        "type": "bearer",
        "credential": "your_bearer_token"
    }
}
```

Adds header: `Authorization: Bearer your_bearer_token`

---

#### 4. Basic Authentication

```json
{
    "authentication": {
        "type": "basic",
        "username": "user",
        "password": "pass"
    }
}
```

Encodes credentials in Base64 and adds header: `Authorization: Basic <encoded>`

---

#### 5. OAuth2 (Client Credentials)

```json
{
    "authentication": {
        "type": "oauth2",
        "token_url": "https://auth.example.com/token",
        "client_id": "your_client_id",
        "client_secret": "your_client_secret",
        "scope": "read write"
    }
}
```

Automatically handles token retrieval and refresh.

---

### Response Path Extraction

Use JSONPath-style syntax to extract specific data from API responses.

**API Response:**
```json
{
    "status": "success",
    "data": {
        "temperature": 22.5,
        "location": "Berlin"
    }
}
```

**Response Path Examples:**

```json
// Extract temperature
"response_path": "data.temperature"
// Result: 22.5

// Extract entire data object
"response_path": "data"
// Result: {"temperature": 22.5, "location": "Berlin"}

// Extract array element
"response_path": "results[0].value"
// For response: {"results": [{"value": 10}, {"value": 20}]}
// Result: 10

// No path (get entire response)
"response_path": ""
// Result: entire response object
```

---

### Template Variables

Use `{variable}` syntax in URLs and request bodies to inject dynamic values.

**Available Variables:**
- `{answer}` - User's answer to current question
- `{question_id}` - Current question ID
- `{session_id}` - Quiz session ID
- `{user_id}` - User identifier
- `{timestamp}` - Current timestamp
- `{score_name}` - Any score variable (e.g., `{points}`)
- `{api.api_id}` - Response from previous API call (e.g., `{api.weather}`)
- `{api.api_id.field}` - Nested field from API response (e.g., `{api.joke_api.setup}`)

**Example:**

```json
{
    "id": "submit",
    "timing": "after_answer",
    "question_id": 1,
    "url": "https://api.example.com/quiz/{session_id}/answer",
    "method": "POST",
    "body": {
        "question_id": "{question_id}",
        "answer": "{answer}",
        "score": "{points}",
        "timestamp": "{timestamp}",
        "previous_data": "{api.init_data}"
    }
}
```

---

### Using API Data in Questions and Conditions

Access API response data using the `api` variable in expressions:

#### In Question Text

```json
{
    "id": 1,
    "data": {
        "text": "The temperature is {api.weather}°C. Is it warm?",
        "type": "multiple_choice",
        "options": [
            {"value": "yes", "label": "Yes"},
            {"value": "no", "label": "No"}
        ]
    }
}
```

#### In Conditions

```json
{
    "score_updates": [
        {
            "condition": "answer >= (api.weather - 5) and answer <= (api.weather + 5)",
            "update": {
                "points": "points + 1"
            }
        }
    ]
}
```

#### In Transitions

```json
{
    "transitions": {
        "1": [
            {
                "expression": "api.difficulty == 'hard'",
                "next_question_id": 10
            },
            {
                "expression": "true",
                "next_question_id": 2
            }
        ]
    }
}
```

---

### Error Handling and Retries

API calls automatically retry on failure (default: 3 attempts).

**Configuration:**

```json
{
    "id": "unstable_api",
    "url": "https://api.example.com/data",
    "timeout": 15,
    "max_retries": 5
}
```

**Error Information:**

When an API call fails, error details are stored in session state:

```json
{
    "api_data": {
        "my_api": {
            "success": false,
            "error": "Connection timeout",
            "timestamp": "2025-11-13T10:30:00"
        }
    }
}
```

**Checking for Errors in Expressions:**

```json
{
    "condition": "api.weather != None",
    "update": {"points": "points + 1"}
}
```

---

## Expression Syntax

Expressions are used in conditions, score updates, and transitions. They support a safe subset of Python syntax.

### Supported Operators

#### Arithmetic
```python
+   # Addition
-   # Subtraction
*   # Multiplication
/   # Division
**  # Exponentiation
```

#### Comparison
```python
==  # Equal
!=  # Not equal
<   # Less than
<=  # Less than or equal
>   # Greater than
>=  # Greater than or equal
in  # Membership test
```

#### Logical
```python
and  # Logical AND
or   # Logical OR
```

### Variables Available in Expressions

1. **`answer`** - User's answer to current question
   - Type depends on question type (string, int, float, list)

2. **Score variables** - All variables defined in `scores`
   - Example: `points`, `correct_answers`, `streak`

3. **`api`** - API response data (when API integrations are used)
   - Access with dot notation: `api.weather`, `api.joke_api.setup`
   - Access with subscript: `api["weather"]`, `api.results[0]`

### Expression Examples

#### Simple Comparisons
```python
answer == 'yes'
answer > 10
score >= 100
```

#### Boolean Logic
```python
answer >= 70 and answer <= 90
score > 100 or attempts < 3
answer == 'expert' and points > 50
```

#### Membership Tests
```python
'2' in answer                    # Check if '2' is in answer list
'correct' in answer             # Check if string contains value
```

#### Arithmetic in Updates
```python
"points + 1"
"score + (answer * 2)"
"streak + 1 if answer == 'yes' else 0"  # Note: ternary not supported, use multiple conditions
```

#### API Data Access
```python
api.weather > 20
api.joke_api.type == 'general'
answer >= (api.weather - 5) and answer <= (api.weather + 5)
```

#### Complex Expressions
```python
answer >= 1 and answer <= 5 and score < 100
(points > 50 and level == 'hard') or attempts > 10
'correct' in answer and score > api.threshold
```

### Expression Restrictions

For security, the following are **NOT** allowed:

- Function calls (except built-ins like `len()` in specific contexts)
- Import statements
- Assignments within expressions
- Lambda functions
- List/dict comprehensions
- Attribute access on non-dict objects
- Exec/eval operations

---

## Complete Examples

### Example 1: Simple Linear Quiz

```json
{
    "metadata": {
        "title": "Basic Math Quiz",
        "description": "Test your arithmetic skills",
        "version": "1.0"
    },
    "scores": {
        "correct": 0
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
                    "update": {"correct": "correct + 1"}
                }
            ]
        },
        {
            "id": 2,
            "data": {
                "text": "What is 5 * 3?",
                "type": "integer"
            },
            "score_updates": [
                {
                    "condition": "answer == 15",
                    "update": {"correct": "correct + 1"}
                }
            ]
        }
    ],
    "transitions": {
        "1": [{"expression": "true", "next_question_id": 2}],
        "2": [{"expression": "true", "next_question_id": null}]
    }
}
```

---

### Example 2: Branching Quiz

```json
{
    "metadata": {
        "title": "Fruit Preference Quiz",
        "description": "Quiz with conditional branching",
        "version": "1.0"
    },
    "scores": {
        "fruits": 0,
        "apples": 0,
        "pears": 0
    },
    "questions": [
        {
            "id": 1,
            "data": {
                "text": "Do you like apples?",
                "type": "multiple_choice",
                "options": [
                    {"value": "yes", "label": "Yes"},
                    {"value": "no", "label": "No"}
                ]
            },
            "score_updates": [
                {
                    "condition": "answer == 'yes'",
                    "update": {
                        "fruits": "fruits + 1",
                        "apples": "apples + 2"
                    }
                },
                {
                    "condition": "answer == 'no'",
                    "update": {
                        "apples": "apples - 1"
                    }
                }
            ]
        },
        {
            "id": 2,
            "data": {
                "text": "Do you like pears?",
                "type": "multiple_choice",
                "options": [
                    {"value": "yes", "label": "Yes"},
                    {"value": "no", "label": "No"}
                ]
            },
            "score_updates": [
                {
                    "condition": "answer == 'yes'",
                    "update": {
                        "fruits": "fruits + 1",
                        "pears": "pears + 2"
                    }
                }
            ]
        }
    ],
    "transitions": {
        "1": [
            {
                "expression": "answer == 'no'",
                "next_question_id": 1
            },
            {
                "expression": "true",
                "next_question_id": 2
            }
        ],
        "2": [
            {"expression": "true", "next_question_id": null}
        ]
    }
}
```

---

### Example 3: Quiz with API Integration (Weather)

```json
{
    "metadata": {
        "title": "Weather Quiz",
        "description": "Guess the current temperature",
        "version": "1.0",
        "requires_api": true
    },
    "scores": {
        "correct_answers": 0
    },
    "api_integrations": [
        {
            "id": "weather",
            "timing": "on_quiz_start",
            "url": "https://api.open-meteo.com/v1/forecast?latitude=52.52&longitude=13.41&current=temperature_2m",
            "method": "GET",
            "authentication": {"type": "none"},
            "response_path": "current.temperature_2m",
            "description": "Fetch current temperature in Berlin"
        }
    ],
    "questions": [
        {
            "id": 1,
            "data": {
                "text": "What is the current temperature in Berlin (°C)? Guess within ±5°C!",
                "type": "float"
            },
            "score_updates": [
                {
                    "condition": "answer >= (api.weather - 5) and answer <= (api.weather + 5)",
                    "update": {"correct_answers": "correct_answers + 1"}
                }
            ]
        }
    ],
    "transitions": {
        "1": [{"expression": "true", "next_question_id": null}]
    }
}
```

---

### Example 4: Advanced API Integration (Joke Quiz)

```json
{
    "metadata": {
        "title": "AI Joke Quiz",
        "description": "Rate random jokes from an API",
        "version": "1.0",
        "requires_api": true
    },
    "scores": {
        "humor_score": 0,
        "total_ratings": 0
    },
    "api_integrations": [
        {
            "id": "joke_api",
            "timing": "before_question",
            "question_id": 1,
            "url": "https://official-joke-api.appspot.com/random_joke",
            "method": "GET",
            "authentication": {"type": "none"},
            "description": "Fetch a random joke"
        },
        {
            "id": "rating_submit",
            "timing": "after_answer",
            "question_id": 1,
            "url": "https://httpbin.org/post",
            "method": "POST",
            "authentication": {
                "type": "api_key",
                "key_name": "X-API-Key",
                "credential": "demo-key-123"
            },
            "body": {
                "joke_id": "{api.joke_api.id}",
                "rating": "{answer}",
                "timestamp": "{timestamp}"
            },
            "description": "Submit rating"
        }
    ],
    "questions": [
        {
            "id": 1,
            "data": {
                "text": "Here's a joke:\n\nSetup: {api.joke_api.setup}\nPunchline: {api.joke_api.punchline}\n\nHow funny? (1-5)",
                "type": "integer",
                "min": 1,
                "max": 5
            },
            "score_updates": [
                {
                    "condition": "answer >= 1 and answer <= 5",
                    "update": {
                        "humor_score": "humor_score + answer",
                        "total_ratings": "total_ratings + 1"
                    }
                }
            ]
        }
    ],
    "transitions": {
        "1": [{"expression": "true", "next_question_id": null}]
    }
}
```

---

## Validation and Best Practices

### Validation Rules

The quiz JSON is validated when uploaded. Common errors:

1. **Missing required fields**: Must have `metadata`, `scores`, `questions`, `transitions`
2. **Duplicate question IDs**: Each question must have a unique ID
3. **Invalid expressions**: Conditions and updates must use valid syntax
4. **Unreachable questions**: Every question should be reachable via transitions
5. **Missing transitions**: Every question must have at least one transition rule
6. **Invalid question types**: Must be one of: `text`, `integer`, `float`, `multiple_choice`, `multiple_select`
7. **Reserved variable names**: Cannot use `answer` as a score variable name

### Best Practices

#### 1. Always Include Fallback Transitions

```json
{
    "transitions": {
        "1": [
            {"expression": "score > 10", "next_question_id": 5},
            {"expression": "true", "next_question_id": 2}  // Fallback
        ]
    }
}
```

#### 2. Use Descriptive Question IDs

While numeric IDs work, consider using consistent numbering:
- Sequential for linear quizzes: `1, 2, 3, ...`
- Grouped for branching: `10, 11, 12` for beginner path, `20, 21, 22` for expert path

#### 3. Initialize All Score Variables

```json
{
    "scores": {
        "points": 0,
        "streak": 0,
        "level": 1
    }
}
```

#### 4. Test API Endpoints Before Deployment

- Verify API URLs are accessible
- Test authentication credentials
- Validate response structure matches `response_path`
- Check API rate limits

#### 5. Handle API Failures Gracefully

```json
{
    "score_updates": [
        {
            "condition": "answer == api.weather and api.weather != None",
            "update": {"points": "points + 1"}
        }
    ]
}
```

#### 6. Use Clear Question Text

- Include units for numeric questions: "What is the temperature (°C)?"
- Provide context when using API data
- Add hints for complex questions

#### 7. Document API Integrations

Use the `description` field:

```json
{
    "id": "weather",
    "description": "Fetches current temperature in Berlin from Open-Meteo API",
    "url": "https://api.open-meteo.com/..."
}
```

#### 8. Avoid Circular Loops Without Exit Conditions

```json
// BAD: Infinite loop
{
    "1": [{"expression": "true", "next_question_id": 1}]
}

// GOOD: Loop with exit condition
{
    "1": [
        {"expression": "attempts >= 3", "next_question_id": null},
        {"expression": "answer == 'no'", "next_question_id": 1},
        {"expression": "true", "next_question_id": 2}
    ]
}
```

#### 9. Version Your Quizzes

Update the version when making significant changes:

```json
{
    "metadata": {
        "version": "2.1",
        "description": "Added API integration for real-time data"
    }
}
```

#### 10. Use Mutually Exclusive Conditions in Score Updates

If you want only one condition to apply:

```json
{
    "score_updates": [
        {
            "condition": "answer >= 90",
            "update": {"grade": "'A'"}
        },
        {
            "condition": "answer >= 80 and answer < 90",
            "update": {"grade": "'B'"}
        },
        {
            "condition": "answer < 80",
            "update": {"grade": "'C'"}
        }
    ]
}
```

---

## Appendix: Quick Reference

### Question Type Summary

| Type | Answer Type | Has Options | Example Use |
|------|-------------|-------------|-------------|
| `multiple_choice` | string | Yes | Select one answer |
| `multiple_select` | list | Yes | Select multiple answers |
| `text` | string | No | Free text input |
| `integer` | int | No | Whole numbers |
| `float` | float | No | Decimal numbers |

### API Timing Summary

| Timing | When Executed | Use For |
|--------|---------------|---------|
| `on_quiz_start` | Before first question | Initialize data, fetch user profile |
| `before_question` | Before specific question | Load question content, get hints |
| `after_answer` | After specific answer | Submit analytics, trigger actions |
| `on_quiz_end` | After quiz completion | Submit results, send notifications |

### Auth Type Summary

| Type | Configuration | Header Format |
|------|---------------|---------------|
| `none` | No fields | None |
| `api_key` | `key_name`, `credential` | `{key_name}: {credential}` |
| `bearer` | `credential` | `Authorization: Bearer {credential}` |
| `basic` | `username`, `password` | `Authorization: Basic {base64}` |
| `oauth2` | `token_url`, `client_id`, `client_secret` | `Authorization: Bearer {token}` |

---

## Additional Resources

- **Example Quizzes**: `/tests/test_quiz_jsons/` directory
- **API Integration Documentation**: `/docs/api_integration.md`
- **Testing Guide**: `/docs/api_integration_testing.md`
- **Architecture Overview**: `/docs/architecture.rst`
- **Use Case Examples**: `/docs/use_case_complex_quiz.md`

---

**End of Guide**

*For questions or issues, please refer to the project documentation or submit an issue on GitHub.*

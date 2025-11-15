# Variable System with Tags - Examples

## Overview

The new variable system uses **tags** to classify variables by purpose, visibility, and safety, rather than rigid naming conventions.

## Example 1: Weather Quiz with Scores

```json
{
  "metadata": {
    "title": "Weather Prediction Quiz",
    "version": "2.0"
  },

  "variables": {
    "user_prediction": {
      "type": "float",
      "default": 0,
      "mutable_by": ["user", "engine"],
      "tags": ["score", "user_input"],
      "description": "User's temperature prediction (displayed as score)",
      "constraints": {
        "min_value": -50,
        "max_value": 50
      }
    },

    "actual_temp": {
      "type": "float",
      "default": 0,
      "mutable_by": ["api"],
      "tags": ["api_data"],
      "source_api": "weather",
      "description": "Actual temperature from API",
      "fallback": {
        "behavior": "use_default",
        "default_value": 20.0,
        "reason_message": "Weather service unavailable"
      }
    },

    "accuracy_score": {
      "type": "integer",
      "default": 0,
      "mutable_by": ["engine"],
      "tags": ["leaderboard", "computed"],
      "description": "THE primary score for leaderboard ranking (0-100)",
      "constraints": {
        "min_value": 0,
        "max_value": 100
      }
    },

    "city_choice": {
      "type": "string",
      "default": "berlin",
      "mutable_by": ["user"],
      "tags": ["user_input", "private"],
      "description": "Selected city (safe enum)",
      "constraints": {
        "enum": ["berlin", "london", "paris", "tokyo"]
      }
    },

    "user_comment": {
      "type": "string",
      "default": "",
      "mutable_by": ["user"],
      "tags": ["user_input", "private"],
      "description": "Free-text comment (NOT safe for APIs)",
      "constraints": {
        "max_length": 500
      }
    },

    "api_endpoint_base": {
      "type": "string",
      "default": "https://api.open-meteo.com/v1/forecast",
      "mutable_by": [],
      "tags": ["immutable", "safe_for_api", "private"],
      "description": "API endpoint (constant)"
    }
  },

  "api_integrations": [
    {
      "id": "weather",
      "base_url": "https://api.open-meteo.com/v1/forecast",
      "timing": "before_question",
      "question_id": 2,
      "access_level": "public_safe",
      "method": "GET",

      "query_params": {
        "latitude": {
          "berlin": "52.52",
          "london": "51.51",
          "paris": "48.85",
          "tokyo": "35.68"
        },
        "longitude": {
          "berlin": "13.41",
          "london": "-0.13",
          "paris": "2.35",
          "tokyo": "139.65"
        },
        "current": "temperature_2m"
      },

      "param_source": {
        "latitude": "variables.city_choice",
        "longitude": "variables.city_choice"
      },

      "response_mapping": {
        "current.temperature_2m": "actual_temp"
      }
    }
  ],

  "questions": [
    {
      "id": 1,
      "data": {
        "text": "Choose a city: {variables.city_choice}",
        "type": "multiple_choice",
        "options": [
          {"value": "berlin", "label": "Berlin 🇩🇪"},
          {"value": "london", "label": "London 🇬🇧"},
          {"value": "paris", "label": "Paris 🇫🇷"},
          {"value": "tokyo", "label": "Tokyo 🇯🇵"}
        ]
      },
      "variable_updates": [
        {
          "condition": "true",
          "updates": {
            "city_choice": "answer"
          }
        }
      ]
    },
    {
      "id": 2,
      "data": {
        "text": "What's the temperature in {variables.city_choice}? (in °C)",
        "type": "float"
      },
      "variable_updates": [
        {
          "condition": "true",
          "updates": {
            "user_prediction": "answer"
          }
        }
      ]
    },
    {
      "id": 3,
      "data": {
        "text": "Results:\n\nYour prediction: {variables.user_prediction}°C\nActual temp: {variables.actual_temp}°C\nAccuracy: {variables.accuracy_score}/100",
        "type": "text"
      },
      "variable_updates": [
        {
          "condition": "true",
          "updates": {
            "accuracy_score": "max(0, 100 - abs(user_prediction - actual_temp) * 10)"
          }
        }
      ]
    }
  ],

  "transitions": {
    "1": [{"expression": "true", "next_question_id": 2}],
    "2": [{"expression": "true", "next_question_id": 3}],
    "3": [{"expression": "true", "next_question_id": null}]
  }
}
```

## Tag Behavior Matrix

| Variable | Type | Tags | Safe for API? | Public? | Notes |
|----------|------|------|---------------|---------|-------|
| `user_prediction` | float | `score`, `user_input` | ✅ Yes (numeric) | ✅ Yes (score) | Secondary score for analytics |
| `actual_temp` | float | `api_data` | ✅ Yes (api_data) | ❌ No | Private by default |
| `accuracy_score` | integer | `leaderboard`, `computed` | ✅ Yes (numeric) | ✅ Yes (auto) | **PRIMARY** score for ranking |
| `city_choice` | string | `user_input`, `private` | ✅ Yes (enum) | ❌ No | Safe due to enum constraint |
| `user_comment` | string | `user_input`, `private` | ❌ **NO** (free text) | ❌ No | **Cannot** be used in APIs |
| `api_endpoint_base` | string | `immutable`, `safe_for_api` | ✅ Yes (immutable) | ❌ No | Constant literal |

**Note**: `leaderboard` tag automatically adds `score` and `public` tags. Only ONE variable per quiz can have the `leaderboard` tag.

## Example 2: Permission-Aware Quiz

```json
{
  "metadata": {
    "title": "Premium Features Quiz",
    "creator_tier": "standard"
  },

  "variables": {
    "basic_score": {
      "type": "integer",
      "default": 0,
      "mutable_by": ["engine"],
      "tags": ["score", "public"],
      "description": "Basic score (all users)"
    },

    "premium_insight": {
      "type": "string",
      "default": "Upgrade for detailed analysis",
      "mutable_by": ["api"],
      "tags": ["api_data", "public"],
      "source_api": "premium_analysis",
      "description": "Premium AI analysis",
      "fallback": {
        "behavior": "use_default",
        "default_value": "Upgrade to Premium for AI insights",
        "reason_message": "Premium feature not available"
      }
    },

    "admin_debug_info": {
      "type": "string",
      "default": "",
      "mutable_by": ["engine"],
      "tags": ["admin_only", "private"],
      "description": "Debug info (admins only)"
    }
  },

  "api_integrations": [
    {
      "id": "premium_analysis",
      "url": "https://api.example.com/ai/analyze",
      "method": "POST",
      "access_level": "premium",
      "timing": "after_question",
      "question_id": 5,
      "fallback": {
        "behavior": "degrade",
        "hide_questions": [6, 7],
        "alternative_flow": {
          "from_question": 5,
          "to_question": 8
        }
      }
    }
  ]
}
```

## Tag Auto-Application Rules

### Automatic Tags

1. **LEADERBOARD tag** → Automatically adds `SCORE` and `PUBLIC` tags
   ```json
   {
     "tags": ["leaderboard"]  // Becomes ["leaderboard", "score", "public", "safe_for_api"]
   }
   ```
   **Important**: Only ONE variable per quiz can have the `leaderboard` tag. This is the primary score used for ranking users on leaderboards.

2. **SCORE tag** → Automatically adds `PUBLIC` tag
   ```json
   {
     "tags": ["score"]  // Becomes ["score", "public", "safe_for_api"]
   }
   ```

3. **Numeric types** → Automatically adds `SAFE_FOR_API`
   ```json
   {
     "type": "float"  // Gets "safe_for_api" tag
   }
   ```

4. **String with enum** → Adds `SAFE_FOR_API` + `SANITIZED`
   ```json
   {
     "type": "string",
     "constraints": {"enum": ["a", "b"]}  // Gets "safe_for_api", "sanitized"
   }
   ```

5. **USER_INPUT tag** → Adds `UNTRUSTED`
   ```json
   {
     "tags": ["user_input"]  // Becomes ["user_input", "untrusted"]
   }
   ```

6. **API_DATA tag** → Adds `SANITIZED` + `SAFE_FOR_API`
   ```json
   {
     "tags": ["api_data"]  // Becomes ["api_data", "sanitized", "safe_for_api"]
   }
   ```

7. **source_api set** → Adds `API_DATA` tag
   ```json
   {
     "source_api": "weather"  // Gets "api_data" tag
   }
   ```

8. **No visibility tag** → Defaults to `PRIVATE`
   ```json
   {
     "tags": []  // Becomes ["private"]
   }
   ```

9. **IMMUTABLE tag** → Requires `mutable_by: []`
   ```json
   {
     "tags": ["immutable"],
     "mutable_by": []  // Must be empty
   }
   ```

## Security Validations

### Tag Conflicts (Will Raise Error)

```json
// ERROR: Can't be both PUBLIC and PRIVATE
{
  "tags": ["public", "private"]  // ❌ Invalid
}

// ERROR: Can't be SAFE_FOR_API and UNTRUSTED without sanitization
{
  "type": "string",
  "tags": ["safe_for_api", "untrusted"]  // ❌ Invalid
  // No enum constraint = no sanitization
}

// OK: Enum constraint sanitizes untrusted input
{
  "type": "string",
  "tags": ["user_input"],  // Gets "untrusted" tag
  "constraints": {"enum": ["yes", "no"]}  // Enum sanitizes → OK for API
}
```

### Score Validation

```json
// ERROR: Scores must be numeric
{
  "tags": ["score"],
  "type": "string"  // ❌ Invalid - scores must be int or float
}

// OK: Valid score
{
  "tags": ["score"],
  "type": "integer",  // ✅ Valid
  "default": 0
}
```

## Migration from Old "scores" System

### Old Format (Deprecated)
```json
{
  "scores": {
    "user_score": 0,
    "total_points": 100
  }
}
```

### New Format
```json
{
  "variables": {
    "user_score": {
      "type": "integer",
      "default": 0,
      "mutable_by": ["engine"],
      "tags": ["score"],  // Mark as score for public display
      "description": "User's earned points"
    },
    "total_points": {
      "type": "integer",
      "default": 100,
      "mutable_by": [],
      "tags": ["immutable", "public"],
      "description": "Total possible points"
    }
  }
}
```

## Query Variables by Tag

```python
# Get all public variables (for display)
public_vars = store.get_by_tag(VariableTag.PUBLIC)

# Get all scores (for analytics - includes ALL score-tagged variables)
scores = store.get_by_tag(VariableTag.SCORE)

# Get THE leaderboard score (primary score for ranking)
leaderboard_score = store.get_leaderboard_score()
# Returns: ("total_score", 100) or None

# Get variables safe for API use
safe_for_api = store.get_by_tag(VariableTag.SAFE_FOR_API)

# Get untrusted variables (need extra validation)
untrusted = store.get_by_tag(VariableTag.UNTRUSTED)
```

## LEADERBOARD vs SCORE Tags

**LEADERBOARD tag** - Use for THE primary score variable:
- ✅ Only ONE variable per quiz can have this tag
- ✅ Automatically gets `score` and `public` tags
- ✅ This is the score used for ranking users on leaderboards
- ✅ Must be numeric (int or float)
- Example: `total_points`, `final_score`, `accuracy_rating`

**SCORE tag** - Use for secondary/analytics scores:
- ✅ Multiple variables can have this tag
- ✅ Automatically gets `public` tag
- ✅ Used for analytics, detailed breakdowns, sub-scores
- ✅ Must be numeric (int or float)
- Example: `section_1_score`, `bonus_points`, `time_penalty`

```json
{
  "variables": {
    "final_score": {
      "type": "integer",
      "tags": ["leaderboard"],  // THE primary ranking score
      "description": "Total score for leaderboard ranking"
    },
    "section_a_score": {
      "type": "integer",
      "tags": ["score"],  // Secondary score for analytics
      "description": "Section A performance"
    },
    "section_b_score": {
      "type": "integer",
      "tags": ["score"],  // Secondary score for analytics
      "description": "Section B performance"
    }
  }
}
```

## Summary

**Key Benefits of Tag System:**

1. ✅ **Flexible Classification** - Variables can have multiple purposes
2. ✅ **Automatic Safety** - Tags auto-applied based on type and constraints
3. ✅ **Clear Intent** - `score` tag explicitly marks metrics
4. ✅ **Security Enforcement** - `safe_for_api` vs `untrusted` tags prevent attacks
5. ✅ **Visibility Control** - `public`, `private`, `admin_only` tags
6. ✅ **Backwards Compatible** - Old "scores" can be migrated
7. ✅ **Query by Purpose** - Easy to find all scores, all public vars, etc.

**Security Model:**

- **Numeric types** → Always safe for APIs
- **String with enum** → Safe (whitelisted values)
- **Free-text string** → **NOT safe** for APIs (injection risk)
- **API responses** → Safe (already sanitized)
- **User input** → Untrusted until validated

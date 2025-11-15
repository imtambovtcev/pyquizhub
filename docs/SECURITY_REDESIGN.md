# PyQuizHub Security Redesign: Variable System & Permission Tiers

## Overview

This document outlines a comprehensive security redesign replacing the current "scores" system with a flexible "variables" system and implementing multi-tier permission controls.

## 1. Variable System (Replacing Scores)

### Current System Problems
- Called "scores" but used for general state management
- No type safety or validation
- No distinction between safe/unsafe strings
- All variables are mutable by anyone

### New Variable System Design

#### Variable Types

```python
class VariableType(Enum):
    # Numeric types (always safe for API use)
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"

    # String types with safety levels
    STRING_SAFE = "string_safe"      # Pre-validated, can be used in API requests
    STRING_UNSAFE = "string_unsafe"  # User input, CANNOT be used in API URLs/bodies
    STRING_LITERAL = "string_literal" # Compile-time constants, always safe

    # Complex types
    OBJECT = "object"  # JSON object
    ARRAY = "array"    # JSON array
```

#### Safety Classification

**Safe Strings** - Can be used in API request construction:
- Literal strings defined in quiz JSON (`type: "string_literal"`)
- Validated enum values from multiple_choice answers
- API response values (already sanitized by InputSanitizer)
- Sanitized and validated user input (explicitly marked safe after validation)

**Unsafe Strings** - CANNOT be used in API requests:
- Free-text user input (`type: "text"` questions)
- User-provided strings that haven't been validated
- Any string containing potentially dangerous characters

#### Variable Definition Schema

```json
{
  "variables": {
    "user_prediction": {
      "type": "float",
      "default": 0,
      "mutable_by": ["user", "engine"],
      "description": "User's temperature prediction",
      "constraints": {
        "min": -50,
        "max": 50
      }
    },
    "actual_temp": {
      "type": "float",
      "default": 0,
      "mutable_by": ["api"],
      "source_api": "temp",
      "description": "Actual temperature from API"
    },
    "user_name": {
      "type": "string_unsafe",
      "default": "",
      "mutable_by": ["user"],
      "description": "User's name (cannot be used in API requests)",
      "constraints": {
        "max_length": 100,
        "pattern": "^[a-zA-Z0-9 ]+$"
      }
    },
    "city_choice": {
      "type": "string_safe",
      "default": "berlin",
      "mutable_by": ["user"],
      "description": "Selected city (safe for API use)",
      "constraints": {
        "enum": ["berlin", "london", "paris", "tokyo"]
      }
    },
    "api_endpoint": {
      "type": "string_literal",
      "default": "https://api.open-meteo.com/v1/forecast",
      "mutable_by": [],
      "description": "API endpoint (immutable)"
    }
  }
}
```

#### Mutability Control

Variables specify who can modify them:
- `["user"]` - Only user answers can modify
- `["api"]` - Only API responses can modify
- `["engine"]` - Only quiz logic can modify
- `["user", "engine"]` - Both user and engine
- `[]` - Immutable (constants)

#### Validation Rules

1. **Type Enforcement**: Variables must match declared type
2. **Constraint Checking**: Min/max, patterns, enums enforced
3. **Mutability Enforcement**: Only authorized actors can modify
4. **Safety Enforcement**: `string_unsafe` cannot be used in API construction
5. **API Source Validation**: `source_api` must reference valid API integration

## 2. Creator Permission Tiers

### Permission Levels

```python
class CreatorPermissionTier(Enum):
    # Tier 1: Restricted (default for new users)
    RESTRICTED = "restricted"
    # - Can only use pre-approved API endpoints (allowlist)
    # - Cannot use variables in API URLs
    # - Fixed authentication only (no dynamic auth)
    # - Max 5 API calls per quiz session

    # Tier 2: Standard (verified creators)
    STANDARD = "standard"
    # - Can use variables in query parameters only
    # - Can add path segments after approved base URL
    #   Example: base="api.example.com/v1" can add "/users" or "/posts"
    # - Can use custom headers (validated)
    # - Max 20 API calls per quiz session

    # Tier 3: Advanced (trusted creators)
    ADVANCED = "advanced"
    # - Can construct full URLs with variables (with validation)
    # - Can use custom authentication schemes
    # - Can use POST/PUT requests with body templates
    # - Max 50 API calls per quiz session

    # Tier 4: Admin (platform administrators)
    ADMIN = "admin"
    # - Bypass some validations (still security-checked)
    # - Unlimited API calls
    # - Can use internal APIs
```

### Permission Enforcement

#### Tier 1 (Restricted) - Example

```json
{
  "creator_tier": "restricted",
  "api_integrations": [
    {
      "id": "weather",
      "url": "https://api.open-meteo.com/v1/forecast?latitude=52.52&longitude=13.41",
      "allowed": true,  // In global allowlist
      "uses_variables": false,  // No variables = OK
      "method": "GET"
    }
  ]
}
```

#### Tier 2 (Standard) - Example

```json
{
  "creator_tier": "standard",
  "api_integrations": [
    {
      "id": "weather",
      "base_url": "https://api.open-meteo.com/v1/forecast",
      "allowed_path_template": "/{endpoint}",  // Can add /current or /hourly
      "allowed_query_params": {
        "latitude": "fixed",  // Value is fixed
        "longitude": "fixed",
        "city": "variable:city_choice"  // Can use safe variable
      },
      "method": "GET"
    }
  ]
}
```

#### Tier 3 (Advanced) - Example

```json
{
  "creator_tier": "advanced",
  "api_integrations": [
    {
      "id": "custom_api",
      "url_template": "https://api.example.com/v1/{variables.endpoint}/{variables.resource_id}",
      "method": "POST",
      "body_template": {
        "query": "{variables.user_query}",
        "options": {
          "format": "json",
          "limit": 10
        }
      },
      "headers": {
        "X-Custom-Header": "{variables.session_token}"
      }
    }
  ]
}
```

### Creator Configuration

```json
{
  "creator_id": "user_123",
  "permission_tier": "standard",
  "custom_allowlist": [
    "api.mycompany.com",
    "internal.example.org"
  ],
  "allowed_base_urls": {
    "api.mycompany.com": {
      "allowed_paths": ["/public/*", "/data/read/*"],
      "forbidden_paths": ["/admin/*", "/data/write/*"]
    }
  },
  "rate_limits": {
    "max_api_calls_per_session": 30,  // Override default tier limit
    "max_quizzes": 100
  }
}
```

## 3. User Permission System

### User Permission Levels

```python
class UserPermissionLevel(Enum):
    # Guest users (not logged in)
    GUEST = "guest"
    # - Cannot trigger API calls
    # - Quiz runs in "safe mode" with fallbacks

    # Basic users (free tier)
    BASIC = "basic"
    # - Can trigger API calls marked as "public_safe"
    # - Limited to 10 API calls per day

    # Premium users (paid)
    PREMIUM = "premium"
    # - Can trigger all API calls in quiz
    # - Normal rate limits apply

    # Restricted users (flagged for abuse)
    RESTRICTED = "restricted"
    # - API calls disabled
    # - Quiz runs with fallbacks only
```

### Quiz-Level API Access Control

```json
{
  "api_integrations": [
    {
      "id": "weather",
      "url": "https://api.open-meteo.com/v1/forecast?...",
      "access_level": "public_safe",  // Available to all users
      "fallback_behavior": "skip"  // If user lacks permission
    },
    {
      "id": "premium_data",
      "url": "https://api.example.com/premium",
      "access_level": "premium",  // Only premium users
      "fallback_behavior": "use_default"
    },
    {
      "id": "optional_enhancement",
      "url": "https://api.example.com/enhance",
      "access_level": "basic",
      "fallback_behavior": "degrade_gracefully"
    }
  ]
}
```

## 4. Safe Fallback System

### Fallback Strategies

```python
class FallbackBehavior(Enum):
    SKIP = "skip"                    # Skip API call, continue quiz
    USE_DEFAULT = "use_default"      # Use default value from variable
    DEGRADE_GRACEFULLY = "degrade"   # Continue with reduced functionality
    FAIL = "fail"                    # Block quiz execution (error message)
```

### Fallback Configuration

```json
{
  "variables": {
    "weather_temp": {
      "type": "float",
      "default": 20.0,
      "mutable_by": ["api"],
      "source_api": "weather",
      "fallback": {
        "behavior": "use_default",
        "default_value": 20.0,
        "reason_message": "Weather data unavailable, using default temperature"
      }
    },
    "premium_insight": {
      "type": "string_safe",
      "default": "",
      "mutable_by": ["api"],
      "source_api": "premium_data",
      "fallback": {
        "behavior": "degrade",
        "default_value": "Basic analysis available",
        "hide_questions": [5, 6],  // Hide premium-only questions
        "alternative_flow": {
          "from_question": 4,
          "to_question": 7  // Skip to public content
        }
      }
    }
  }
}
```

### Runtime Fallback Execution

When API call fails or user lacks permission:

```python
def execute_api_with_fallback(api_config, user_permissions, variables):
    """Execute API call with fallback handling."""

    # Check user permissions
    if not user_has_access(user_permissions, api_config["access_level"]):
        logger.info(f"User lacks permission for API {api_config['id']}")
        return handle_fallback(api_config, variables)

    # Check creator permissions
    if not creator_can_use_api(creator_tier, api_config):
        logger.warning(f"Creator lacks permission for API {api_config['id']}")
        return handle_fallback(api_config, variables)

    try:
        # Execute API call
        result = execute_api_call(api_config, variables)
        return result
    except Exception as e:
        logger.error(f"API call failed: {e}")
        return handle_fallback(api_config, variables)


def handle_fallback(api_config, variables):
    """Handle fallback behavior."""
    fallback = api_config.get("fallback", {})
    behavior = fallback.get("behavior", "fail")

    if behavior == "skip":
        return None  # Continue without this data

    elif behavior == "use_default":
        # Find target variable
        target_var = find_variable_for_api(api_config["id"], variables)
        if target_var and "default_value" in fallback:
            variables[target_var] = fallback["default_value"]
            return fallback.get("reason_message")

    elif behavior == "degrade":
        # Apply degraded mode
        if "hide_questions" in fallback:
            mark_questions_hidden(fallback["hide_questions"])
        if "alternative_flow" in fallback:
            redirect_quiz_flow(fallback["alternative_flow"])
        return fallback.get("reason_message")

    elif behavior == "fail":
        raise QuizExecutionError("Required API unavailable")
```

## 5. Migration Strategy

### Phase 1: Variable System
1. Add `variables` field to quiz schema (keep `scores` for backwards compatibility)
2. Update JSON validator to handle both formats
3. Update engine to use new variable system
4. Mark `scores` as deprecated

### Phase 2: Permission System
1. Add creator permission tiers to database
2. Add user permission levels
3. Implement permission checks in API integration
4. Add fallback handling

### Phase 3: Security Hardening
1. Enforce string safety in API construction
2. Add comprehensive permission tests
3. Update all example quizzes
4. Remove deprecated `scores` support

## 6. Security Enhancements

### String Safety Enforcement

```python
def validate_api_url_construction(url_template, variables, creator_tier):
    """Validate that API URL construction is safe."""

    # Extract variable references from template
    var_refs = extract_variable_references(url_template)

    for var_ref in var_refs:
        var_def = variables[var_ref]

        # CRITICAL: Unsafe strings cannot be used in URLs
        if var_def["type"] == "string_unsafe":
            raise SecurityError(
                f"Cannot use unsafe string variable '{var_ref}' in API URL. "
                f"User input cannot be used in request construction."
            )

        # Check creator tier permissions
        if creator_tier == "restricted":
            raise PermissionError(
                f"Tier {creator_tier} cannot use variables in URLs"
            )

        # Standard tier can only use variables in query params
        if creator_tier == "standard":
            if var_ref in extract_path_variables(url_template):
                raise PermissionError(
                    f"Tier {creator_tier} cannot use variables in URL path"
                )
```

### Validation Pipeline

```
User Input → Type Validation → Safety Classification → Permission Check → API Construction
     ↓              ↓                    ↓                    ↓                ↓
  "Berlin"      string type         string_unsafe?      user has access?   URL encode
                                         ↓                                      ↓
                                    If from enum:                         Safe to use
                                    → string_safe

                                    If free text:
                                    → string_unsafe
                                    → REJECT if used in API
```

## 7. Example Quiz with New System

```json
{
  "metadata": {
    "title": "Advanced Weather Quiz",
    "creator_tier": "standard",
    "requires_permissions": ["api_access"]
  },

  "variables": {
    "city_choice": {
      "type": "string_safe",
      "default": "berlin",
      "mutable_by": ["user"],
      "constraints": {
        "enum": ["berlin", "london", "paris", "tokyo"]
      },
      "description": "User-selected city (safe enum)"
    },

    "user_guess": {
      "type": "float",
      "default": 0,
      "mutable_by": ["user"],
      "constraints": {"min": -50, "max": 50}
    },

    "actual_temp": {
      "type": "float",
      "default": 20.0,
      "mutable_by": ["api"],
      "source_api": "weather",
      "fallback": {
        "behavior": "use_default",
        "default_value": 20.0
      }
    },

    "user_comment": {
      "type": "string_unsafe",
      "default": "",
      "mutable_by": ["user"],
      "constraints": {"max_length": 500},
      "description": "User comment (cannot be used in APIs)"
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
      },

      "fallback": {
        "behavior": "use_default",
        "message": "Weather service unavailable"
      }
    }
  ],

  "questions": [
    {
      "id": 1,
      "data": {
        "text": "Choose a city:",
        "type": "multiple_choice",
        "options": [
          {"value": "berlin", "label": "Berlin"},
          {"value": "london", "label": "London"},
          {"value": "paris", "label": "Paris"},
          {"value": "tokyo", "label": "Tokyo"}
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
    }
  ]
}
```

## 8. Testing Strategy

### Security Tests Required

1. **String Safety Tests**
   - Unsafe strings rejected in API URLs
   - Safe strings allowed
   - Type enforcement

2. **Permission Tests**
   - Each tier can only access allowed features
   - Permission escalation attempts blocked
   - Fallbacks work correctly

3. **Variable Validation Tests**
   - Type checking
   - Constraint enforcement
   - Mutability controls

4. **Integration Tests**
   - Full quiz flow with permissions
   - Fallback scenarios
   - Mixed permission levels

## 9. Database Schema Changes

### Creator Permissions Table
```sql
CREATE TABLE creator_permissions (
    creator_id VARCHAR(255) PRIMARY KEY,
    permission_tier VARCHAR(50) NOT NULL,
    custom_allowlist JSON,
    allowed_base_urls JSON,
    rate_limits JSON,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);
```

### User Permissions Table
```sql
CREATE TABLE user_permissions (
    user_id VARCHAR(255) PRIMARY KEY,
    permission_level VARCHAR(50) NOT NULL,
    api_call_quota INT DEFAULT 10,
    quota_reset_at TIMESTAMP,
    is_restricted BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);
```

## 10. API Changes

### New Endpoints

```
POST /api/v1/creator/request-tier-upgrade
  - Request permission tier upgrade

GET /api/v1/creator/permissions
  - Get current permission tier and limits

POST /api/v1/quiz/validate-permissions
  - Validate quiz against creator permissions

GET /api/v1/user/permissions
  - Get user permission level and quotas
```

---

## Summary

This redesign provides:

✅ **Type Safety**: Strong typing for all variables
✅ **String Safety**: Clear distinction between safe/unsafe strings
✅ **Permission Tiers**: Graduated access control for creators
✅ **User Controls**: Per-user API access restrictions
✅ **Graceful Degradation**: Fallback system for missing permissions
✅ **Security**: Defense in depth against injection attacks
✅ **Flexibility**: Support for complex quiz flows
✅ **Backwards Compatible**: Migration path from old system

This system balances security, flexibility, and usability while preventing abuse and protecting against attacks.

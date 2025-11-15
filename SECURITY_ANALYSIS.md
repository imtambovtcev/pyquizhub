# PyQuizHub Security Analysis & Redesign

## Executive Summary

This document analyzes the current security posture of PyQuizHub and proposes a comprehensive redesign of the variable management and API integration system to address critical security vulnerabilities.

## Current Security Issues

### 1. **Template Injection Vulnerabilities**

**Location**: `api_integration.py` lines 312-361

```python
def _render_template(self, template: str, context: Dict[str, Any]) -> str:
    result = template
    for key, value in context.items():
        placeholder = "{" + key + "}"
        if placeholder in result:
            result = result.replace(placeholder, str(value))
    return result
```

**Issues**:
- No input sanitization - user input directly interpolated into templates
- No escaping for special characters
- Potential for injection in API URLs, headers, and bodies
- `str(value)` conversion doesn't validate or sanitize

**Attack Vector Example**:
```json
{
  "answer": "'; DROP TABLE users; --",
  "api_integrations": [{
    "url": "https://api.example.com/search?q={answer}"
  }]
}
```
Results in: `https://api.example.com/search?q='; DROP TABLE users; --`

### 2. **Unrestricted Variable Access**

**Location**: `safe_evaluator.py` lines 114-122

```python
elif isinstance(node, ast.Name):
    if node.id == "true":
        return True
    if node.id == "false":
        return False
    if node.id in variables:
        return variables[node.id]
    raise ValueError(f"Unauthorized variable: {node.id}")
```

**Issues**:
- Variables dictionary contains mixed data (scores, API responses, user input)
- No distinction between trusted and untrusted data
- No type validation before evaluation
- "scores" naming is misleading - they're actually general variables

### 3. **API Response Trust Issues**

**Location**: `api_integration.py` lines 407-429

```python
def _process_response(self, response: requests.Response, api_config: Dict[str, Any]) -> Any:
    data = response.json()
    response_path = api_config.get("response_path")
    if response_path:
        data = self._extract_json_path(data, response_path)
    return data
```

**Issues**:
- No validation of API response data
- No size limits on responses
- No type checking
- Responses stored directly without sanitization
- Could contain malicious payloads (XXL JSON, recursive structures)

### 4. **Missing Input Validation**

**Issues**:
- No string length limits
- No character whitelist validation
- No numeric range validation beyond question-level constraints
- No protection against ReDoS (Regular Expression Denial of Service)

### 5. **Lack of Variable Type System**

**Current State**: Variables are untyped dictionaries
- No schema definition
- No runtime type checking
- No immutability controls
- API can overwrite any variable

---

## Proposed Solution: Secure Variable System

### New Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Quiz Definition                       │
├─────────────────────────────────────────────────────────┤
│  variables:                                             │
│    temperature:                                         │
│      type: float                                        │
│      range: [-50, 50]                                   │
│      mutable_by: ["user", "api"]                       │
│      default: 0                                         │
│                                                         │
│    user_prediction:                                     │
│      type: float                                        │
│      range: [-100, 100]                                │
│      mutable_by: ["user"]                              │
│      default: 0                                         │
│                                                         │
│    api_weather_temp:                                    │
│      type: float                                        │
│      range: [-100, 100]                                │
│      mutable_by: ["api:weather_api"]                   │
│      default: 0                                         │
│                                                         │
│    score:                                               │
│      type: integer                                      │
│      range: [0, 1000]                                  │
│      mutable_by: ["engine"]                            │
│      default: 0                                         │
└─────────────────────────────────────────────────────────┘
```

### Variable Type Specification

```python
class VariableType(Enum):
    INTEGER = "integer"
    FLOAT = "float"
    STRING = "string"
    BOOLEAN = "boolean"
    LIST = "list"
    DICT = "dict"

class VariableSource(Enum):
    USER = "user"           # User answer
    API = "api"             # API response
    ENGINE = "engine"       # Quiz engine calculation
    SYSTEM = "system"       # System-generated (session_id, timestamp)

class VariableDefinition:
    name: str
    type: VariableType
    mutable_by: List[VariableSource | str]  # ["user"] or ["api:weather_api"]
    default: Any
    constraints: VariableConstraints

class VariableConstraints:
    # For numbers
    min_value: Optional[float]
    max_value: Optional[float]

    # For strings
    max_length: Optional[int]
    allowed_chars: Optional[str]  # Regex pattern
    forbidden_patterns: List[str]  # SQL injection, XSS patterns

    # For lists
    max_items: Optional[int]
    item_type: Optional[VariableType]

    # For all types
    nullable: bool = False
```

### Security Features

1. **Type Safety**
   - Strict type checking at variable assignment
   - Type conversion with validation
   - Reject invalid types

2. **Access Control**
   - Variables have explicit `mutable_by` list
   - API responses can only write to designated variables
   - User input can only write to user-designated variables
   - Engine has its own protected variables

3. **Input Sanitization**
   - URL encoding for API parameters
   - HTML/XML escaping where appropriate
   - SQL injection pattern detection
   - XSS pattern detection

4. **Constraints Enforcement**
   - Numeric ranges enforced
   - String length limits
   - Character whitelisting
   - Pattern blacklisting

### API Integration Security

```python
class SecureAPIIntegration:
    def prepare_request_body(
        self,
        body_template: Dict[str, Any],
        variables: VariableStore
    ) -> Dict[str, Any]:
        """
        Safely prepare API request body.

        Security measures:
        1. Only allow variables marked as 'api' in mutable_by
        2. Sanitize all string values
        3. Validate against constraints
        4. URL-encode parameters
        """

    def process_response(
        self,
        response: Response,
        api_config: APIConfig,
        variables: VariableStore
    ) -> VariableStore:
        """
        Safely process API response.

        Security measures:
        1. Limit response size (max 1MB)
        2. Validate JSON structure
        3. Check response against variable constraints
        4. Only write to variables designated for this API
        5. Sanitize string values
        """
```

### Sanitization Functions

```python
class InputSanitizer:
    # SQL Injection patterns
    SQL_INJECTION_PATTERNS = [
        r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|EXECUTE)\b)",
        r"(--|\#|\/\*)",
        r"(\bOR\b.*=.*)",
        r"(\bAND\b.*=.*)",
        r"(;.*--)",
    ]

    # XSS patterns
    XSS_PATTERNS = [
        r"<script[^>]*>.*?</script>",
        r"javascript:",
        r"on\w+\s*=",
        r"<iframe",
    ]

    @staticmethod
    def sanitize_string(value: str, constraints: VariableConstraints) -> str:
        """Sanitize string input."""
        # 1. Length check
        if constraints.max_length and len(value) > constraints.max_length:
            raise ValueError(f"String exceeds max length: {len(value)} > {constraints.max_length}")

        # 2. Character whitelist
        if constraints.allowed_chars:
            if not re.match(f"^[{constraints.allowed_chars}]+$", value):
                raise ValueError(f"String contains forbidden characters")

        # 3. Pattern blacklist
        for pattern in InputSanitizer.SQL_INJECTION_PATTERNS:
            if re.search(pattern, value, re.IGNORECASE):
                raise ValueError("Potential SQL injection detected")

        for pattern in InputSanitizer.XSS_PATTERNS:
            if re.search(pattern, value, re.IGNORECASE):
                raise ValueError("Potential XSS attack detected")

        # 4. Custom forbidden patterns
        if constraints.forbidden_patterns:
            for pattern in constraints.forbidden_patterns:
                if re.search(pattern, value):
                    raise ValueError(f"Forbidden pattern detected: {pattern}")

        return value

    @staticmethod
    def url_encode_parameter(value: str) -> str:
        """URL encode for safe API parameter injection."""
        from urllib.parse import quote_plus
        return quote_plus(value)
```

---

## Implementation Plan

### Phase 1: Variable System (Priority: HIGH)

1. **Create `variable_types.py`**
   - VariableType enum
   - VariableSource enum
   - VariableDefinition class
   - VariableConstraints class

2. **Create `variable_store.py`**
   - VariableStore class (manages variable state)
   - Type validation
   - Constraint enforcement
   - Access control checks

3. **Create `input_sanitizer.py`**
   - String sanitization
   - Pattern detection (SQL injection, XSS)
   - URL encoding
   - Character whitelisting

### Phase 2: Engine Integration (Priority: HIGH)

1. **Update `engine.py`**
   - Replace "scores" dict with VariableStore
   - Update variable access in expressions
   - Add variable initialization from quiz definition

2. **Update `safe_evaluator.py`**
   - Use VariableStore instead of dict
   - Add type checking
   - Enforce access controls

3. **Update `json_validator.py`**
   - Validate variable definitions
   - Validate constraints
   - Validate mutable_by specifications

### Phase 3: API Security (Priority: CRITICAL)

1. **Update `api_integration.py`**
   - Remove unsafe template rendering
   - Add input sanitization before API calls
   - Add response validation
   - Enforce variable write permissions
   - Add size limits

2. **Add `api_security.py`**
   - Request sanitization
   - Response validation
   - Size limits
   - Timeout enforcement

### Phase 4: Testing (Priority: HIGH)

1. **Security Tests**
   - SQL injection attempts
   - XSS attempts
   - Template injection attempts
   - API response manipulation
   - Variable access violations

2. **Integration Tests**
   - Complex weather quiz with new format
   - Multiple API integrations
   - Edge cases

---

## Migration Guide

### Old Format (Insecure):
```json
{
  "scores": {
    "user_prediction": 0,
    "accuracy_score": 0
  },
  "questions": [{
    "score_updates": [{
      "condition": "true",
      "update": {
        "user_prediction": "answer"
      }
    }]
  }]
}
```

### New Format (Secure):
```json
{
  "variables": {
    "user_prediction": {
      "type": "float",
      "default": 0,
      "mutable_by": ["user"],
      "constraints": {
        "min_value": -100,
        "max_value": 100
      }
    },
    "accuracy_score": {
      "type": "integer",
      "default": 0,
      "mutable_by": ["engine"],
      "constraints": {
        "min_value": 0,
        "max_value": 100
      }
    }
  },
  "questions": [{
    "variable_updates": [{
      "condition": "true",
      "updates": {
        "user_prediction": "answer"
      }
    }]
  }]
}
```

---

## Security Checklist

- [x] Identified template injection vulnerabilities
- [x] Identified unrestricted variable access
- [x] Identified API response trust issues
- [x] Identified missing input validation
- [ ] Implement VariableStore with type safety
- [ ] Implement InputSanitizer
- [ ] Implement API request sanitization
- [ ] Implement API response validation
- [ ] Add comprehensive security tests
- [ ] Update documentation
- [ ] Migrate example quizzes

---

## Breaking Changes

1. **Quiz JSON Format**
   - `scores` → `variables`
   - `score_updates` → `variable_updates`
   - Added `type`, `mutable_by`, `constraints` to variables

2. **API Responses**
   - Must declare which variables they can write to
   - Must respect variable constraints
   - Size limits enforced

3. **User Input**
   - Must declare which variables user can write to
   - String validation enforced
   - Pattern blacklisting enforced

---

## Future Enhancements

1. **Rate Limiting**: Limit API calls per quiz session
2. **Content Security Policy**: For web-based quiz display
3. **Audit Logging**: Log all variable changes for security auditing
4. **Encryption**: Encrypt sensitive variables in session storage
5. **Variable History**: Track variable changes for rollback/audit

---

## Conclusion

The current system has critical security vulnerabilities that could lead to:
- SQL injection attacks
- XSS attacks
- API abuse
- Data tampering
- DoS attacks

The proposed variable system with type safety, access control, and input sanitization will:
- Prevent injection attacks
- Enforce data integrity
- Provide clear security boundaries
- Enable security auditing
- Improve code maintainability

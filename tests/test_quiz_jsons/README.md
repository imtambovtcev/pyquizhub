# Test Quiz JSON Files

This directory contains test quiz JSON files for validating the quiz system.

## New Format (v2.0) - Variables System

### Basic Tests
- **simple_quiz.json** - Minimal valid quiz with new variables format
- **complex_quiz.json** - Multi-question quiz (needs update to v2.0)

### Variable System Tests
- **test_variables_all_types.json** - Demonstrates all variable types (integer, float, boolean, string, array)
- **test_variables_arrays.json** - Tests homogeneous arrays with different item types
- **new_format_weather_quiz.json** - Weather prediction quiz (needs cleanup - has old fields)

### API Integration Tests (New Format)
- **test_api_simple_static.json** - Simple GET with fixed URL + extract_response (RESTRICTED tier)
- **test_api_dynamic_url.json** - Dynamic URL with url_template + prepare_request (ADVANCED tier)
- **test_api_post_body.json** - POST request with body_template (ADVANCED tier)
- **complex_weather_quiz.json** - Real-world weather API example (updated to v2.0)

### Permission Tier Tests
- **test_permission_restricted.json** - Quiz that passes RESTRICTED tier validation
- **test_permission_restricted_fail.json** - Quiz that fails RESTRICTED tier (6 APIs > limit of 5)

## Old Format (v1.0) - Scores System (Deprecated)

### Valid Old Format
- **weather_quiz.json** - Weather quiz using old scores format
- **joke_quiz_api.json** - Joke API quiz using old format

### Question Type Tests (Old Format)
- **test_quiz_multiple_choice.json** - Multiple choice question type
- **test_quiz_multiple_select.json** - Multiple select question type
- **test_quiz_text.json** - Text input question type
- **test_quiz_integer.json** - Integer input question type
- **test_quiz_float.json** - Float input question type

### Invalid Quiz Tests (Negative Testing)
- **invalid_quiz_missing_keys.json** - Missing required top-level keys
- **invalid_quiz_bad_score_update.json** - Invalid score update expression
- **invalid_quiz_bad_transition.json** - Invalid transition configuration
- **invalid_quiz_invalid_condition_expression.json** - Invalid condition expression
- **invalid_quiz_duplicate_question_ids.json** - Duplicate question IDs
- **invalid_quiz_non_iterable_questions.json** - Questions field is not a list
- **invalid_quiz_unexpected_top_level.json** - Unexpected top-level keys

### Warning Tests
- **warning_quiz_no_trivial_condition.json** - Missing trivial condition at end
- **warning_quiz_non_trivial_after_trivial.json** - Non-trivial condition after trivial

## Format Differences

### Old Format (v1.0)
```json
{
    "scores": {
        "score_name": 0
    },
    "api_integrations": [
        {
            "id": "api_id",
            "timing": "before_question",
            "question_id": 2,
            "url": "...",
            "response_path": "..."
        }
    ],
    "questions": [...],
    "transitions": {...}
}
```

### New Format (v2.0)
```json
{
    "variables": {
        "var_name": {
            "type": "integer|float|boolean|string|array",
            "array_item_type": "string",  // Required if type is array
            "mutable_by": ["user", "api", "engine"],
            "tags": ["score", "leaderboard", "user_input", ...],
            "constraints": {...}
        }
    },
    "api_integrations": [
        {
            "id": "api_id",
            "method": "GET|POST|PUT|PATCH|DELETE",
            "url": "...",  // Static URL
            "prepare_request": {  // Optional - for dynamic URLs
                "url_template": "...",
                "body_template": {...},
                "required_variables": [...]
            },
            "extract_response": {  // Required
                "variables": {
                    "var_name": {"path": "...", "type": "..."}
                }
            }
        }
    ],
    "questions": [...],
    "transitions": {...}
}
```

## Key Features to Test

### Variable System
- [x] All types: integer, float, boolean, string, array
- [x] Array with different item types
- [x] Auto-constraints application
- [x] Explicit constraints override auto-constraints
- [x] Tags: score, leaderboard, user_input, api_data, etc.
- [x] Leaderboard variable (only one per quiz)

### API Integration
- [x] Simple static URL (RESTRICTED tier)
- [x] Dynamic URL with url_template (ADVANCED tier)
- [x] POST with body_template (ADVANCED tier)
- [x] extract_response with multiple variables
- [x] Response path extraction (nested objects, arrays)

### Permission Tiers
- [x] RESTRICTED: max 5 APIs, GET only, fixed URLs
- [x] STANDARD: max 20 APIs, GET only, query param variables
- [ ] ADVANCED: max 50 APIs, all methods, url_template, body_template
- [ ] ADMIN: unlimited

## TODO - Missing Test Cases

1. **Negative Variable Tests**
   - Invalid type (object)
   - Missing required fields (type, mutable_by)
   - Invalid array_item_type
   - Multiple leaderboard variables
   - Nested arrays

2. **API Integration Edge Cases**
   - extract_response variable type mismatch
   - extract_response referencing undefined variable
   - prepare_request using unsafe variable in URL

3. **Permission Tier Edge Cases**
   - STANDARD tier with query param variables (should pass)
   - STANDARD tier with url_template (should fail)
   - POST method on RESTRICTED/STANDARD tiers (should fail)

4. **Execution Blocks** (when implemented)
   - update_variables block
   - api_call block
   - user_interaction block
   - Block ordering and timing

## Migration Guide

To migrate from v1.0 to v2.0:

1. Rename `scores` to `variables`
2. For each variable, add:
   - `type` field
   - `mutable_by` array
   - Optional: `tags`, `constraints`, `description`
3. Update API integrations:
   - Remove `timing`, `question_id`, `response_path`
   - Add `extract_response` block with variable mappings
   - For dynamic URLs: add `prepare_request` block
4. Update templates: `{scores.x}` → `{variables.x}` or `{api.x}` → `{variables.x}`

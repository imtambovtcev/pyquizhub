# PyQuizHub Security Implementation Plan

## Overview

This document outlines the step-by-step plan to implement the secure variable system for PyQuizHub, addressing critical security vulnerabilities while maintaining backward compatibility where possible.

## Files Created

### ✅ Completed
1. **SECURITY_ANALYSIS.md** - Comprehensive security analysis
2. **pyquizhub/core/engine/variable_types.py** - Variable type system with constraints
3. **pyquizhub/core/engine/input_sanitizer.py** - Input sanitization utilities

### 🔄 Next Steps

4. **pyquizhub/core/engine/variable_store.py** - Variable storage with access control
5. **pyquizhub/core/engine/api_security.py** - Secure API integration wrapper
6. **tests/test_security/** - Comprehensive security tests

## Implementation Phases

### Phase 1: Core Variable System ✅ (Partially Complete)

**Status**: Type system and sanitizer created

**Remaining Tasks**:
1. Create `variable_store.py` with:
   - VariableStore class
   - Variable access control
   - Type validation on set/get
   - Change tracking for audit

2. Update `safe_evaluator.py` to:
   - Accept VariableStore instead of dict
   - Enforce type checking
   - Validate variable access permissions

### Phase 2: Engine Integration (Next)

**Files to Modify**:
1. `engine.py`
   - Replace `scores` dict with `VariableStore`
   - Update `start_quiz()` to initialize from variable definitions
   - Update `answer_question()` to use VariableStore

2. `json_validator.py`
   - Add validation for `variables` section
   - Validate variable definitions
   - Validate constraints
   - Validate `mutable_by` specifications

3. Create migration helper:
   - `quiz_migrator.py` - Convert old format to new format

### Phase 3: API Security (Critical)

**Files to Modify**:
1. `api_integration.py`
   - Replace unsafe `_render_template()` with secure version
   - Add input sanitization before API calls
   - Add response validation and size limits
   - Enforce variable write permissions

2. Create `api_security.py`:
   - Secure template rendering
   - Request body sanitization
   - Response validation
   - Rate limiting (optional)

### Phase 4: Testing

**Test Files to Create**:
1. `tests/test_security/test_input_sanitization.py`
   - SQL injection tests
   - XSS tests
   - Command injection tests
   - Path traversal tests

2. `tests/test_security/test_variable_system.py`
   - Type validation tests
   - Constraint enforcement tests
   - Access control tests

3. `tests/test_security/test_api_security.py`
   - API request sanitization tests
   - API response validation tests
   - Size limit tests

### Phase 5: Migration & Documentation

1. Update example quizzes to new format
2. Create migration guide
3. Update API documentation
4. Add security best practices guide

## Breaking Changes

### Quiz JSON Format Changes

#### Old Format (scores-based):
```json
{
  "scores": {
    "temperature": 0,
    "score": 0
  },
  "questions": [{
    "score_updates": [{
      "condition": "true",
      "update": {
        "temperature": "answer"
      }
    }]
  }]
}
```

#### New Format (variables-based):
```json
{
  "variables": {
    "temperature": {
      "type": "float",
      "default": 0,
      "mutable_by": ["user"],
      "constraints": {
        "min_value": -100,
        "max_value": 100
      }
    },
    "score": {
      "type": "integer",
      "default": 0,
      "mutable_by": ["engine"],
      "constraints": {
        "min_value": 0,
        "max_value": 1000
      }
    }
  },
  "questions": [{
    "variable_updates": [{
      "condition": "true",
      "updates": {
        "temperature": "answer"
      }
    }]
  }]
}
```

### Backward Compatibility Strategy

**Option 1: Auto-Migration (Recommended)**
- Detect old format automatically
- Migrate on-the-fly with sensible defaults
- Log warning about deprecated format
- Preserve old format support for 1-2 versions

**Option 2: Hard Break**
- Reject old format immediately
- Require manual migration
- Provide migration script

**Decision**: Implement Option 1 for gradual migration

### Migration Helper Implementation

```python
class QuizFormatMigrator:
    """Migrates quizzes from old format to new variable system."""

    @staticmethod
    def migrate(quiz_data: dict) -> dict:
        """
        Migrate quiz from scores-based to variables-based format.

        Args:
            quiz_data: Quiz in old or new format

        Returns:
            Quiz in new format
        """
        # Check if already in new format
        if "variables" in quiz_data:
            return quiz_data

        # Check if in old format
        if "scores" not in quiz_data:
            raise ValueError("Invalid quiz format")

        logger.warning("Migrating quiz from deprecated 'scores' format to 'variables' format")

        # Convert scores to variables with default constraints
        variables = {}
        for name, default_value in quiz_data.get("scores", {}).items():
            var_type = _infer_type(default_value)
            variables[name] = {
                "type": var_type,
                "default": default_value,
                "mutable_by": ["engine", "user", "api"],  # Permissive default
                "constraints": _get_default_constraints(var_type)
            }

        # Update quiz data
        new_quiz = quiz_data.copy()
        new_quiz["variables"] = variables
        # Keep scores for backward compat (will be ignored)

        # Convert score_updates to variable_updates
        for question in new_quiz.get("questions", []):
            if "score_updates" in question:
                question["variable_updates"] = question.pop("score_updates")

        return new_quiz
```

## Security Testing Checklist

### Input Sanitization Tests
- [ ] SQL injection attempts
- [ ] XSS attempts (script tags, event handlers)
- [ ] Command injection attempts
- [ ] Path traversal attempts
- [ ] Template injection attempts
- [ ] ReDoS (catastrophic backtracking) patterns
- [ ] Unicode attacks
- [ ] Null byte injection

### Variable System Tests
- [ ] Type enforcement (integer, float, string, boolean, list, dict)
- [ ] Range constraints (min/max values)
- [ ] Length constraints (min/max length)
- [ ] Pattern matching (allowed chars, forbidden patterns)
- [ ] Access control (user, api, engine permissions)
- [ ] Null handling
- [ ] Nested structure limits (max depth)

### API Integration Tests
- [ ] URL parameter sanitization
- [ ] Request body sanitization
- [ ] Response size limits
- [ ] Response depth limits
- [ ] Response type validation
- [ ] Variable write permission enforcement
- [ ] API-specific variable isolation

### Edge Cases
- [ ] Very long strings (10MB+)
- [ ] Very deep nesting (100+ levels)
- [ ] Very large numbers (beyond float range)
- [ ] Unicode edge cases (emoji, RTL, zero-width)
- [ ] Empty values
- [ ] Concurrent modifications

## Performance Considerations

### Optimization Strategies
1. **Lazy Validation**: Only validate when value changes
2. **Compiled Patterns**: Pre-compile regex patterns
3. **Caching**: Cache validation results for immutable values
4. **Batch Operations**: Validate multiple variables in one pass

### Benchmarks to Monitor
- Variable validation time: < 1ms per variable
- Expression evaluation time: < 5ms per expression
- API sanitization overhead: < 10ms per request
- Total quiz processing time: < 100ms per answer

## Rollout Strategy

### Stage 1: Internal Testing (Week 1)
- Implement core variable system
- Run security tests
- Performance testing
- Code review

### Stage 2: Beta Testing (Week 2)
- Deploy to staging environment
- Migrate example quizzes
- Test with real workloads
- Gather feedback

### Stage 3: Gradual Production Rollout (Week 3)
- Deploy with feature flag
- Enable auto-migration
- Monitor errors and performance
- Collect metrics

### Stage 4: Full Rollout (Week 4)
- Enable for all users
- Deprecate old format
- Update documentation
- Announce changes

## Monitoring & Metrics

### Security Metrics
- Number of blocked injection attempts
- Number of validation failures
- API response rejections
- Variable access violations

### Performance Metrics
- Variable validation latency
- Expression evaluation latency
- API sanitization overhead
- Memory usage per session

### Error Metrics
- Migration failures
- Validation errors
- Type conversion errors
- Constraint violations

## Documentation Updates Needed

1. **API Documentation**
   - Update quiz JSON schema
   - Add variable system examples
   - Document security constraints
   - Add migration guide

2. **Security Guide**
   - Best practices for variable constraints
   - Common attack vectors
   - How to audit quiz definitions
   - API integration security

3. **Developer Guide**
   - How to add new variable types
   - How to customize constraints
   - How to extend sanitization
   - Testing security features

## Success Criteria

- [ ] All security tests pass
- [ ] Performance benchmarks met
- [ ] No regressions in existing functionality
- [ ] All example quizzes migrated
- [ ] Documentation updated
- [ ] Code review approved
- [ ] Security audit passed

## Risk Mitigation

### Risk: Breaking existing quizzes
**Mitigation**: Auto-migration with fallback to old behavior

### Risk: Performance degradation
**Mitigation**: Extensive benchmarking, optimization passes

### Risk: Compatibility issues
**Mitigation**: Comprehensive integration testing

### Risk: False positives in sanitization
**Mitigation**: Configurable sanitization levels, whitelist options

## Next Immediate Steps

1. ✅ Create SECURITY_ANALYSIS.md
2. ✅ Create variable_types.py
3. ✅ Create input_sanitizer.py
4. ⏭️ Create variable_store.py
5. ⏭️ Update safe_evaluator.py
6. ⏭️ Update engine.py
7. ⏭️ Update api_integration.py
8. ⏭️ Create security tests

## Timeline Estimate

- Core Implementation: 3-4 days
- Testing: 2-3 days
- Documentation: 1-2 days
- Migration: 1 day
- **Total: 7-10 days**

## Questions for Review

1. Should we support custom variable types?
2. What should be the default constraint values?
3. Should we add encryption for sensitive variables?
4. How aggressive should the sanitization be?
5. Should we log all rejected inputs for security audit?

---

**Status**: Phase 1 Partially Complete
**Next**: Implement variable_store.py and update safe_evaluator.py
**Priority**: HIGH - Critical security fixes

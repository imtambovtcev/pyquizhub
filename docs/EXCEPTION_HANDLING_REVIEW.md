# Exception Handling Review

## Overview

This document reviews broad `except Exception` handlers in the codebase and provides recommendations for more specific exception handling.

## Security Concern

Broad exception handlers can:
1. **Mask errors**: Hide bugs and security issues
2. **Leak information**: Generic error messages may expose internal details
3. **Allow undefined behavior**: Catch unexpected exceptions that should crash
4. **Hinder debugging**: Make it harder to trace actual issues

## Files with Broad Exception Handling

Total files: 29

### Critical Files (Security-Sensitive)

1. **pyquizhub/core/api/router_file_uploads.py**
   - File upload operations
   - **Risk**: High - handles user file uploads

2. **pyquizhub/core/api/router_admin.py**
   - Admin operations (quiz creation, deletion, token management)
   - **Risk**: High - privileged operations

3. **pyquizhub/core/api/router_quiz.py**
   - Quiz endpoints
   - **Risk**: Medium - main user-facing API

4. **pyquizhub/core/engine/engine.py**
   - Quiz engine logic
   - **Risk**: Medium - core business logic

5. **pyquizhub/core/engine/api_integration.py**
   - External API integration
   - **Risk**: Medium - external system integration

### Utility Files (Lower Risk)

6. **pyquizhub/core/files/file_file_storage.py**
   - File metadata storage
   - **Risk**: Low - internal storage operations

7. **pyquizhub/core/storage/sql_storage.py**
   - SQL storage operations
   - **Risk**: Low - internal database operations

8. **pyquizhub/core/engine/json_validator.py**
   - Quiz JSON validation
   - **Risk**: Low - validation (fails safely)

### Scripts and Tools (Not Critical)

- `scripts/` - Development scripts (not production code)
- `creator_web/` - Creator web interface
- `admin_web/` - Admin web interface
- `pyquizhub/adapters/` - Bot adapters

## Recommended Specific Exceptions

### File Operations
Instead of:
```python
except Exception as e:
    logger.error(f"Failed: {e}")
```

Use:
```python
except (IOError, OSError, PermissionError) as e:
    logger.error(f"File operation failed: {e}")
except json.JSONDecodeError as e:
    logger.error(f"Invalid JSON: {e}")
```

### API/HTTP Operations
```python
except httpx.HTTPError as e:
    logger.error(f"HTTP request failed: {e}")
except httpx.TimeoutException as e:
    logger.error(f"Request timed out: {e}")
```

### Database Operations
```python
except sqlalchemy.exc.SQLAlchemyError as e:
    logger.error(f"Database operation failed: {e}")
except sqlalchemy.exc.IntegrityError as e:
    logger.error(f"Data integrity constraint violation: {e}")
```

### FastAPI File Upload
```python
except (UnicodeDecodeError, ValueError) as e:
    logger.error(f"File read failed: {e}")
    raise HTTPException(status_code=400, detail="Invalid file content")
```

## When Broad Exception Handling is Acceptable

1. **Top-level error boundaries**: Main application entry points
2. **Background tasks**: Long-running tasks that shouldn't crash the app
3. **Logging wrapper**: When you want to log all errors but still re-raise
4. **Cleanup handlers**: When you MUST clean up resources regardless of error

Example of acceptable broad handler:
```python
try:
    # Complex operation
    pass
except SpecificException1 as e:
    # Handle known case
    pass
except SpecificException2 as e:
    # Handle another known case
    pass
except Exception as e:
    # Log unexpected error for investigation
    logger.exception("Unexpected error - please investigate")
    raise  # Re-raise to preserve stack trace
```

## Priority Fixes

### High Priority (Security-Critical)

1. **router_file_uploads.py**
   - Line 188: File read operation
   - Line 591: Text analysis operation
   - **Fix**: Catch specific file/IO exceptions

2. **router_admin.py**
   - Line 136: Quiz update operation
   - Line 170: Quiz deletion operation
   - Line 361: Token deletion operation
   - **Fix**: Catch SQLAlchemy/storage-specific exceptions

### Medium Priority

3. **engine.py**
   - Line 469: API call failures
   - **Fix**: Already catches specific httpx exceptions, this is catch-all for other errors
   - **Action**: Add specific exception types for common failures

4. **router_quiz.py**
   - Various quiz operation handlers
   - **Fix**: Catch storage and validation exceptions specifically

### Low Priority (Can Remain)

5. **file_file_storage.py**
   - Lines 69, 94, 125, 149, 173, 205, 234, 270
   - **Analysis**: These are internal storage operations with safe fallbacks
   - **Action**: Can remain as-is, but document why

6. **Background tasks (main.py)**
   - Line 67: File cleanup task error handler
   - **Analysis**: Acceptable - task should continue running despite errors
   - **Action**: Keep as-is (already documented in code)

## Implementation Strategy

### Phase 1: Critical Security Fixes
- Fix file upload handlers (router_file_uploads.py)
- Fix admin operation handlers (router_admin.py)
- Add tests to verify error handling

### Phase 2: Core Logic Improvements
- Fix engine error handling (engine.py)
- Fix quiz API handlers (router_quiz.py)
- Improve error messages

### Phase 3: Cleanup and Documentation
- Review all other handlers
- Add comments explaining why broad handlers are used
- Create exception handling best practices guide

## Testing Recommendations

For each fixed exception handler, add tests:

1. **Test specific exception paths**:
```python
def test_file_upload_invalid_content():
    # Upload file with invalid content
    # Should raise HTTPException with 400 status
```

2. **Test error messages don't leak info**:
```python
def test_error_message_safe():
    # Trigger error
    # Verify error message doesn't expose internal paths/details
```

3. **Test exception recovery**:
```python
def test_operation_continues_after_error():
    # Trigger non-fatal error
    # Verify system continues working
```

## References

- [Python Exception Hierarchy](https://docs.python.org/3/library/exceptions.html#exception-hierarchy)
- [FastAPI Exception Handling](https://fastapi.tiangolo.com/tutorial/handling-errors/)
- [OWASP Error Handling](https://cheatsheetseries.owasp.org/cheatsheets/Error_Handling_Cheat_Sheet.html)

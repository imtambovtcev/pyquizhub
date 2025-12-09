# File Cleanup Scheduler

The file cleanup scheduler is a background task that automatically deletes expired file metadata from storage.

## Overview

Files uploaded to PyQuizHub can have an optional expiration time (`expires_at`). The cleanup scheduler periodically scans for expired files and removes their metadata from storage.

## Configuration

### Enabling the Scheduler

**By default, the file cleanup scheduler is DISABLED.** To enable it, set the following configuration:

```python
# In your configuration or .env file
PYQUIZHUB_FILE_CLEANUP_ENABLED=true
```

### Cleanup Interval

Configure how often the cleanup runs (default: 3600 seconds = 1 hour):

```python
PYQUIZHUB_FILE_CLEANUP_INTERVAL_SECONDS=3600
```

## How It Works

1. **Startup**: When FastAPI starts (if enabled), the scheduler initializes:
   - Creates a file storage instance (FileBasedFileStorage or SQLFileStorage)
   - Spawns a background asyncio task
   - Logs: `File cleanup scheduler enabled (interval: Xs)`

2. **Periodic Cleanup**: Every `interval_seconds`:
   - Calls `cleanup_expired_files()` on the storage backend
   - Deletes all files where `expires_at < now(UTC)`
   - Logs the number of deleted files

3. **Shutdown**: When FastAPI shuts down:
   - Cancels the cleanup task gracefully
   - Waits for the task to finish
   - Logs: `Cleanup task cancelled successfully`

## Storage Backend Support

The cleanup scheduler works with both storage backends:

### File-Based Storage
- Scans all `.json` files in the metadata directory
- Checks each file's `expires_at` field
- Deletes expired metadata files

### SQL Storage
- Executes SQL query: `DELETE FROM file_metadata WHERE expires_at < now()`
- Efficient bulk deletion in single transaction

## File Expiration Rules

Files are deleted if:
- `expires_at` field is set (not `null`)
- `expires_at` is in the past (less than current UTC time)

Files are NEVER deleted if:
- `expires_at` is `null` (permanent files)
- `expires_at` is in the future
- File has no `expires_at` field

## Example Configuration

### Docker (docker-compose.yml)

```yaml
services:
  api:
    environment:
      - PYQUIZHUB_FILE_CLEANUP_ENABLED=true
      - PYQUIZHUB_FILE_CLEANUP_INTERVAL_SECONDS=1800  # 30 minutes
```

### Python (config file)

```python
from pyquizhub.config.settings import get_config_manager

config = get_config_manager()
config.file_cleanup_enabled = True
config.file_cleanup_interval_seconds = 3600  # 1 hour
```

### Environment Variables

```bash
export PYQUIZHUB_FILE_CLEANUP_ENABLED=true
export PYQUIZHUB_FILE_CLEANUP_INTERVAL_SECONDS=7200  # 2 hours
```

## Monitoring

### Logs

The scheduler produces these log messages:

**Startup (INFO)**:
```
File cleanup scheduler enabled (interval: 3600s)
```

**Disabled (DEBUG)**:
```
File cleanup scheduler disabled (set file_cleanup_enabled=true to enable)
```

**Cleanup run with deletions (INFO)**:
```
File cleanup completed: 42 expired files removed
```

**Cleanup run without deletions (DEBUG)**:
```
File cleanup completed: no expired files found
```

**Errors (ERROR)**:
```
Error in file cleanup task: <error details>
```

**Shutdown (DEBUG)**:
```
Cleanup task cancelled successfully
```

## Testing

### Manual Test

```python
from datetime import datetime, timedelta, timezone
from pyquizhub.core.files.models import FileMetadata
from pyquizhub.core.files.file_file_storage import FileBasedFileStorage

# Create storage
storage = FileBasedFileStorage("/tmp/test_storage")

# Create expired file
expired = FileMetadata.create_new(
    file_type="image",
    platform="url",
    platform_data={"url": "https://example.com/test.jpg"},
    user_id="test_user",
    expires_at=datetime.now(timezone.utc) - timedelta(hours=1)
)
storage.store_file_metadata(expired)

# Run cleanup
deleted_count = storage.cleanup_expired_files()
print(f"Deleted {deleted_count} files")  # Should print: Deleted 1 files

# Verify deleted
assert storage.get_file_metadata(expired.file_id) is None
```

### Automated Tests

See [tests/test_file_cleanup_scheduler.py](/tests/test_file_cleanup_scheduler.py) for comprehensive test suite:
- Basic cleanup functionality
- Error handling
- Cancellation behavior
- Mixed expiration times
- Large-scale performance
- Idempotency
- Different file types

## Performance Considerations

### File-Based Storage
- **O(n)** where n = number of files
- Must read every metadata file to check expiration
- Recommended interval: 1-6 hours
- Suitable for < 10,000 files

### SQL Storage
- **O(1)** with proper indexing
- Single SQL query with WHERE clause
- Recommended interval: 15 minutes - 1 hour
- Suitable for millions of files
- **Recommendation**: Add index on `expires_at` column:

```sql
CREATE INDEX idx_file_metadata_expires_at
ON file_metadata(expires_at)
WHERE expires_at IS NOT NULL;
```

## Error Handling

The cleanup task is designed to be resilient:

1. **Individual cleanup errors**: Task continues running
2. **Storage errors**: Logged with full traceback, next cycle continues
3. **Shutdown**: Task cancels gracefully without leaving orphaned processes

## Best Practices

1. **Enable in production**: Set `file_cleanup_enabled=true` in production
2. **Adjust interval**: Balance between storage efficiency and system load
   - High traffic: More frequent (15-30 minutes)
   - Low traffic: Less frequent (2-6 hours)
3. **Monitor logs**: Watch for errors or unexpected deletion counts
4. **Set appropriate expiration**: Consider quiz duration + buffer time
5. **Test before deploy**: Verify cleanup works with your storage backend

## Troubleshooting

### Scheduler not running

Check logs for:
```
File cleanup scheduler disabled (set file_cleanup_enabled=true to enable)
```

**Solution**: Set `PYQUIZHUB_FILE_CLEANUP_ENABLED=true`

### Files not being deleted

1. Check `expires_at` values are in the past
2. Verify timezone is UTC
3. Check logs for cleanup errors
4. Manually run `cleanup_expired_files()` to test

### High CPU usage

- Reduce cleanup frequency (increase interval)
- For file-based storage, consider switching to SQL
- Add SQL index on `expires_at` column

## Security Considerations

- Cleanup runs in the same process as the API
- No separate authentication required
- Cannot be triggered manually via API (security by design)
- Only deletes expired files (cannot accidentally delete active files)

## Future Enhancements

Potential improvements for future versions:

1. Metrics endpoint to monitor cleanup statistics
2. Admin API to trigger manual cleanup
3. Configurable batch size for large-scale cleanup
4. Automatic adjustment of interval based on file count
5. Cleanup of actual file data (currently only metadata)

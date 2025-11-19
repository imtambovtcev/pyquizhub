# File Attachment System Design

## Problem Statement

Users need to submit files (images, documents, audio, etc.) as quiz answers, but:

1. **Security**: Platform-specific file identifiers contain sensitive data
   - Telegram file_id → Download URL contains bot token
   - Discord attachment URLs may be temporary

2. **Privacy**: Quiz creators analyzing results shouldn't see internal file data
   - Platform identifiers are implementation details
   - File storage locations should be hidden

3. **Portability**: Files from different platforms need uniform handling
   - Telegram bot receives file_id
   - Discord bot receives attachment URLs
   - Web adapter receives uploaded files or URLs

## Solution Architecture

### Separate Storage: Files vs Variables

```
┌─────────────────────────────────────────────────────────────┐
│                    Session Storage                          │
├─────────────────────────────────────────────────────────────┤
│  session_id: "abc123"                                       │
│  quiz_id: "quiz_001"                                        │
│  user_id: "user_456"                                        │
│  variables: {                                               │
│    "score": 10,                                             │
│    "user_photo": "file://f7e3d9a1-4b2c-4e8f-9d6a-1234..."  │ ← File reference
│  }                                                           │
└─────────────────────────────────────────────────────────────┘
                              ↓
                    (file:// reference)
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                   File Metadata Storage                     │
├─────────────────────────────────────────────────────────────┤
│  file_id: "f7e3d9a1-4b2c-4e8f-9d6a-123456789abc"           │
│  file_type: "image"                                         │
│  mime_type: "image/jpeg"                                    │
│  size_bytes: 245760                                         │
│  platform: "telegram"                                       │
│  platform_data: {                  ← PRIVATE, never exposed │
│    "file_id": "AgACAgIAAxkBAAIC...",                       │
│    "file_unique_id": "AQADAgAT3o0xG3dQ"                     │
│  }                                                           │
│  created_at: "2025-11-19T10:30:00Z"                         │
│  expires_at: "2025-12-19T10:30:00Z" (optional)              │
│  session_id: "abc123"                                       │
│  user_id: "user_456"                                        │
└─────────────────────────────────────────────────────────────┘
```

### Data Model

#### FileMetadata Table

```sql
CREATE TABLE file_metadata (
    file_id VARCHAR(255) PRIMARY KEY,           -- UUID
    file_type VARCHAR(50) NOT NULL,             -- 'image', 'document', 'audio', 'video'
    mime_type VARCHAR(100),                      -- 'image/jpeg', 'application/pdf'
    size_bytes INTEGER,
    filename VARCHAR(500),                       -- Original filename if available

    -- Platform information
    platform VARCHAR(50) NOT NULL,               -- 'telegram', 'discord', 'web', 'url'
    platform_data JSONB NOT NULL,                -- Platform-specific identifiers (PRIVATE)

    -- Ownership and lifecycle
    session_id VARCHAR(255),                     -- Which session uploaded this
    user_id VARCHAR(255) NOT NULL,               -- Who uploaded this
    quiz_id VARCHAR(255),                        -- Related quiz
    created_at TIMESTAMP NOT NULL,
    expires_at TIMESTAMP,                        -- Optional expiration

    -- Metadata
    description TEXT,                            -- Optional description
    tags JSONB,                                  -- Optional tags

    FOREIGN KEY (session_id) REFERENCES sessions(session_id) ON DELETE CASCADE
);

CREATE INDEX idx_file_session ON file_metadata(session_id);
CREATE INDEX idx_file_user ON file_metadata(user_id);
CREATE INDEX idx_file_created ON file_metadata(created_at);
```

#### Platform-Specific Data Examples

**Telegram:**
```json
{
  "platform": "telegram",
  "platform_data": {
    "file_id": "AgACAgIAAxkBAAIC...",
    "file_unique_id": "AQADAgAT3o0xG3dQ",
    "file_size": 245760
  }
}
```

**Discord:**
```json
{
  "platform": "discord",
  "platform_data": {
    "attachment_id": "1234567890",
    "url": "https://cdn.discordapp.com/attachments/.../image.png",
    "proxy_url": "https://media.discordapp.net/attachments/.../image.png"
  }
}
```

**Web/Public URL:**
```json
{
  "platform": "url",
  "platform_data": {
    "url": "https://i.imgur.com/abc123.png",
    "validated": true,
    "validation_date": "2025-11-19T10:30:00Z"
  }
}
```

### File Reference Format

Variables store file references using a special URI format:

```python
# Format: file://{file_id}
"user_photo": "file://f7e3d9a1-4b2c-4e8f-9d6a-123456789abc"

# For arrays of files:
"user_gallery": [
    "file://f7e3d9a1-4b2c-4e8f-9d6a-123456789abc",
    "file://b2c4e8f9-1234-5678-abcd-ef0123456789"
]
```

### File Access Layer

```python
class FileAttachment:
    """
    Abstraction layer for file attachments.

    NEVER exposes platform_data directly.
    Provides safe access methods based on context.
    """

    def __init__(self, metadata: dict):
        self.file_id = metadata['file_id']
        self.file_type = metadata['file_type']
        self.mime_type = metadata['mime_type']
        self.size_bytes = metadata['size_bytes']
        self.platform = metadata['platform']
        self._platform_data = metadata['platform_data']  # PRIVATE

    def get_url_for_adapter(self, adapter_type: str, adapter_context: dict = None) -> str | None:
        """
        Get safe URL for display in specific adapter.

        Args:
            adapter_type: 'telegram', 'discord', 'web', 'api'
            adapter_context: Additional context (bot token, session, etc.)

        Returns:
            Safe URL or None if not displayable in this adapter
        """
        if self.platform == 'url':
            # Public URL - safe to return to anyone
            return self._platform_data['url']

        elif self.platform == 'telegram':
            if adapter_type == 'telegram':
                # Return file_id - Telegram bot can send by file_id
                return self._platform_data['file_id']
            elif adapter_type in ['discord', 'web', 'api']:
                # Generate temporary download URL via internal API
                # This proxies the request without exposing bot token
                return f"/api/files/{self.file_id}/download"

        elif self.platform == 'discord':
            if adapter_type == 'discord':
                # Discord attachment URL (may be temporary)
                return self._platform_data['url']
            else:
                # Proxy via internal API
                return f"/api/files/{self.file_id}/download"

        return None

    def can_display_in_adapter(self, adapter_type: str) -> bool:
        """Check if file can be displayed in given adapter."""
        return self.get_url_for_adapter(adapter_type) is not None

    def to_safe_dict(self) -> dict:
        """
        Export safe metadata for quiz creators.
        NEVER includes platform_data.
        """
        return {
            "file_id": self.file_id,
            "file_type": self.file_type,
            "mime_type": self.mime_type,
            "size_bytes": self.size_bytes,
            "filename": getattr(self, 'filename', None),
            "created_at": self.created_at,
            # platform and platform_data OMITTED
        }
```

### Storage Interface

```python
class FileStorage(ABC):
    """Abstract interface for file metadata storage."""

    @abstractmethod
    async def store_file_metadata(self, metadata: dict) -> str:
        """
        Store file metadata and return file_id.

        Args:
            metadata: File metadata including platform_data

        Returns:
            file_id: UUID reference to stored file
        """
        pass

    @abstractmethod
    async def get_file_metadata(self, file_id: str) -> dict | None:
        """
        Retrieve file metadata by file_id.

        Returns:
            Full metadata dict including platform_data (for internal use only)
        """
        pass

    @abstractmethod
    async def delete_file_metadata(self, file_id: str) -> bool:
        """Delete file metadata."""
        pass

    @abstractmethod
    async def get_files_for_session(self, session_id: str) -> list[dict]:
        """Get all files uploaded in a session."""
        pass

    @abstractmethod
    async def cleanup_expired_files(self) -> int:
        """Delete expired files and return count deleted."""
        pass
```

### Quiz JSON Schema Changes

**Old format (image_url in question):**
```json
{
  "id": 1,
  "data": {
    "type": "multiple_choice",
    "text": "What animal is this?",
    "image_url": "https://example.com/dog.jpg",  // OLD
    "options": [...]
  }
}
```

**New format (attachments array):**
```json
{
  "id": 1,
  "data": {
    "type": "multiple_choice",
    "text": "What animal is this?",
    "attachments": [                             // NEW
      {
        "type": "image",
        "source": "https://example.com/dog.jpg",  // URL or variable reference
        "display_mode": "inline",                 // 'inline', 'link', 'optional'
        "alt_text": "A picture of a dog"
      }
    ],
    "options": [...]
  }
}
```

**With variable substitution:**
```json
{
  "id": 2,
  "data": {
    "type": "text",
    "text": "Upload a photo of your pet",
    "expected_answer_type": "file",              // NEW
    "file_constraints": {
      "allowed_types": ["image"],
      "max_size_mb": 5,
      "required": true
    }
  },
  "score_updates": [
    {
      "condition": "answer != null",
      "update": {
        "user_pet_photo": "answer"  // Stores "file://..." reference
      }
    }
  ]
}
```

**Display uploaded file later:**
```json
{
  "id": 5,
  "data": {
    "type": "final_message",
    "text": "Here's the photo you uploaded:",
    "attachments": [
      {
        "type": "image",
        "source": "{variables.user_pet_photo}",  // Resolves to "file://..."
        "display_mode": "inline"
      }
    ]
  }
}
```

## Security Guarantees

### What Quiz Creators See

When creators download results, they receive:

```json
{
  "session_id": "abc123",
  "user_id": "user_456",
  "variables": {
    "score": 10,
    "user_pet_photo": {
      "file_id": "f7e3d9a1-4b2c-4e8f-9d6a-123456789abc",
      "file_type": "image",
      "mime_type": "image/jpeg",
      "size_bytes": 245760,
      "filename": "dog.jpg",
      "download_url": "/api/files/f7e3d9a1.../download"  // Proxied, safe
      // NO platform_data
      // NO Telegram file_id
      // NO bot tokens
    }
  }
}
```

### What Users See

**In quiz questions:**
- Images display normally (adapter handles platform-specific rendering)
- No file_id or platform data visible

**In their answers:**
- "You uploaded: dog.jpg (245 KB)"
- NO internal identifiers

### What's Never Exposed

- Telegram `file_id` (download URL contains bot token)
- Discord temporary attachment URLs (expire quickly)
- Internal file storage paths
- Platform-specific metadata

## Implementation Strategy

### Phase 1: Core File System
1. Create `FileMetadata` model and storage
2. Create `FileAttachment` class with safe access methods
3. Add file storage interface to SQL/File storage backends

### Phase 2: Adapter Integration
1. Update Telegram adapter to store file metadata
2. Update Discord adapter to store file metadata
3. Add file upload to Web adapter
4. Create file proxy API endpoint

### Phase 3: Quiz Engine Integration
1. Update quiz JSON validator for attachments
2. Add file reference resolution in engine
3. Update variable system to handle file references
4. Add file constraints validation

### Phase 4: Results Export
1. Filter platform_data from results
2. Add download URLs to exported files
3. Create file download API with auth

## Migration Path

### Backwards Compatibility

Support both old and new formats:

```python
# Old format still works
question["data"]["image_url"] = "https://example.com/image.jpg"

# Internally converted to:
question["data"]["attachments"] = [
    {"type": "image", "source": "https://example.com/image.jpg"}
]
```

### Gradual Rollout

1. **Phase 1**: Internal file storage works, but not exposed to quiz creators
2. **Phase 2**: Quiz creators can use file question types
3. **Phase 3**: Results export includes file metadata (sanitized)
4. **Phase 4**: Deprecate `image_url`, require `attachments`

## Open Questions

1. **File retention**: How long to keep uploaded files?
   - Per-quiz policy?
   - Global default (30 days)?
   - Keep until session deleted?

2. **File download auth**: Who can download files?
   - Quiz creator always
   - User who uploaded always
   - Others with token?

3. **Storage limits**: Quotas per user/quiz?
   - Max files per session?
   - Max total storage per user?

4. **Content moderation**: Scan uploaded files?
   - Virus scanning?
   - Image content detection?

## Benefits

✅ **Security**: Platform tokens never exposed
✅ **Privacy**: Creators don't see internal data
✅ **Portability**: Uniform file handling across platforms
✅ **Scalability**: Separate storage allows efficient querying
✅ **Auditability**: Track all file operations
✅ **Compliance**: Easy to implement retention policies

# Text File Analysis Feature

This document describes the safe regex search functionality for text files in PyQuizHub.

## Overview

PyQuizHub now supports uploading text files and performing safe regex searches on them. The implementation includes protection against ReDoS (Regular Expression Denial of Service) attacks and resource exhaustion.

## Security Features

### Regex Safety Validator (`pyquizhub/core/engine/regex_validator.py`)

The `RegexValidator` class provides multiple layers of protection:

1. **Pattern Length Limits**: Maximum 500 characters
2. **Text Length Limits**: Maximum 1 MB (1,000,000 characters)
3. **Execution Timeout**: 2 seconds maximum (Unix only)
4. **ReDoS Detection**: Identifies dangerous patterns:
   - Nested quantifiers: `(a+)+`, `(a*)*`
   - Overlapping alternations: `(a|a)+`, `(ab|a)+`
   - Excessive wildcards: Multiple `.*` or `.+` in sequence
5. **Pattern Validation**: Checks regex syntax before execution
6. **Match Limits**: Configurable maximum matches (default: 100)

### Text File Analyzer (`pyquizhub/core/engine/text_file_analyzer.py`)

The `TextFileAnalyzer` class provides:

1. **Multi-Encoding Support**: Tries UTF-8, UTF-16, Latin-1, CP1252
2. **File Size Limits**: Maximum 10 MB
3. **Safe Regex Search**: Uses `RegexValidator` for all searches
4. **Text Statistics**:
   - Line count
   - Word count
   - Character count
   - Text sample (first 500 chars)

## API Endpoint

### POST `/uploads/analyze_text/{file_id}`

Analyzes a text file with optional regex search.

**Parameters:**
- `file_id` (path): ID of uploaded file
- `pattern` (form, optional): Regex pattern to search for
- `case_sensitive` (form, optional): Case-sensitive search (default: true)
- `max_matches` (form, optional): Maximum matches to return (default: 100)

**Response:**
```json
{
  "file_id": "uuid",
  "filename": "example.txt",
  "analysis": {
    "line_count": 42,
    "word_count": 350,
    "char_count": 2150,
    "text_sample": "First 500 characters...",
    "truncated_sample": false,
    "search_results": {
      "matches": [
        {
          "match": "user@example.com",
          "start": 120,
          "end": 136,
          "groups": ["user", "example", "com"]
        }
      ],
      "count": 1,
      "pattern": "\\w+@\\w+\\.\\w+",
      "truncated": false,
      "case_sensitive": true
    }
  },
  "status": "success"
}
```

**Error Responses:**
- `400`: Invalid regex pattern or file read error
- `403`: Permission denied
- `404`: File not found
- `415`: Not a text file

## Usage in Quizzes

### Example Quiz: Text Analysis

See [text_analysis_quiz.json](../quizzes/text_analysis_quiz.json) for a complete example.

**Question 1: File Upload**
```json
{
  "id": 1,
  "data": {
    "type": "file_upload",
    "text": "Upload a text file for analysis",
    "file_types": ["text/plain", "text/markdown"],
    "max_size_mb": 5
  },
  "score_updates": [{
    "condition": "answer.file_id != ''",
    "update": {
      "uploaded_file_id": "answer.file_id"
    }
  }]
}
```

**API Integration: Text Analysis**
```json
{
  "id": "text_analyzer",
  "method": "POST",
  "timing": "before_question",
  "question_id": 2,
  "prepare_request": {
    "url_template": "http://api:8000/uploads/analyze_text/{variables.uploaded_file_id}",
    "body_template": {
      "pattern": "\\b\\w+@\\w+\\.\\w+\\b",
      "case_sensitive": true,
      "max_matches": 100
    }
  },
  "extract_response": {
    "variables": {
      "line_count": {"path": "analysis.line_count", "type": "integer"},
      "word_count": {"path": "analysis.word_count", "type": "integer"},
      "match_count": {"path": "analysis.search_results.count", "type": "integer"}
    }
  }
}
```

**Question 2: Results**
```json
{
  "id": 2,
  "data": {
    "type": "final_message",
    "text": "Lines: {variables.line_count}\\nWords: {variables.word_count}\\nEmails found: {variables.match_count}"
  }
}
```

## Safe Regex Patterns

### Allowed Patterns

✅ **Simple patterns:**
- `\d+` - One or more digits
- `\w+` - One or more word characters
- `[A-Z]+` - One or more uppercase letters

✅ **Email matching:**
- `\w+@\w+\.\w+` - Simple email
- `[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}` - RFC-compliant email

✅ **URL matching:**
- `https?://\S+` - Simple URL
- `https?://[^\s<>"{}|\\^`[\]]+` - More restrictive URL

### Dangerous Patterns (Blocked)

❌ **Nested quantifiers:**
- `(a+)+` - Exponential backtracking
- `(a*)*` - Exponential backtracking
- `(a+)*` - Exponential backtracking

❌ **Overlapping alternations:**
- `(a|a)+` - Redundant alternation
- `(ab|a)+` - Overlapping alternation

❌ **Excessive wildcards:**
- `.*.*.*` - Multiple wildcards in sequence
- `.+.+.+` - Multiple wildcards in sequence

## Testing

### Run Tests

```bash
# Test regex validator
micromamba run -n pyquizhub pytest tests/test_regex_validator.py -v

# Test text file analyzer
micromamba run -n pyquizhub pytest tests/test_text_file_analyzer.py -v
```

### Test Coverage

**Regex Validator Tests:**
- Pattern validation (length, syntax, dangerous patterns)
- Safe search with various patterns
- Timeout protection
- Match limits
- Case sensitivity

**Text File Analyzer Tests:**
- Multi-encoding support
- File size limits
- Text statistics (lines, words, characters)
- Regex search integration
- Error handling

## Performance Considerations

1. **File Size**: Limited to 10 MB to prevent memory exhaustion
2. **Pattern Complexity**: Dangerous patterns blocked at validation time
3. **Execution Time**: 2-second timeout prevents long-running searches (Unix only)
4. **Match Limits**: Default 100 matches prevents excessive memory usage
5. **Encoding Detection**: Tries 4 encodings sequentially, falls back to Latin-1

## Security Best Practices

1. **Always validate patterns**: Never trust user-provided regex patterns
2. **Set appropriate limits**: Adjust file size and match limits based on your use case
3. **Monitor timeouts**: Log timeout events to detect potential attacks
4. **Sanitize file names**: File names are already sanitized by the file upload system
5. **Rate limiting**: Consider adding rate limits for text analysis requests

## Future Enhancements

Potential improvements for future versions:

1. **Advanced patterns**: Whitelist of pre-approved complex patterns
2. **Multi-file analysis**: Analyze multiple files in a single request
3. **Export results**: Download search results as CSV/JSON
4. **Syntax highlighting**: Highlight matches in the original text
5. **Pattern library**: Common patterns (emails, URLs, phone numbers, etc.)

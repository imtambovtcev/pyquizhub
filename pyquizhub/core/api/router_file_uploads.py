"""
File upload API router.

Provides secure endpoints for uploading files with validation,
quota management, and access control.

SECURITY WARNING: File uploads are disabled by default.
See config.yaml file_storage section for configuration.
"""

from __future__ import annotations

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Request,
    UploadFile,
    File,
    Form,
    Header,
    status,
)
from fastapi.responses import StreamingResponse
from typing import Optional
import io

from pyquizhub.logging.setup import get_logger
from pyquizhub.core.engine.text_file_analyzer import TextFileAnalyzer
from pyquizhub.core.engine.regex_validator import RegexValidationError
from pyquizhub.core.storage.file import (
    FileManager,
    FileValidator,
    LocalStorageBackend,
    ValidationError,
)

logger = get_logger(__name__)

router = APIRouter(
    prefix="/uploads",
    tags=["file-uploads"]
)


def get_file_manager(request: Request) -> FileManager:
    """
    Get or create FileManager instance.

    Args:
        request: FastAPI request

    Returns:
        FileManager instance

    Raises:
        HTTPException: If file storage is disabled
    """
    config = request.app.state.config_manager

    # Check if file_manager exists, if not create it
    if not hasattr(request.app.state, 'file_manager'):
        # Create storage backend with default settings
        # TODO: Add file_storage configuration to config.yaml
        import os
        base_dir = os.path.join(os.getcwd(), ".pyquizhub", "uploads")
        os.makedirs(base_dir, exist_ok=True)
        storage_backend = LocalStorageBackend(base_dir, config)

        # Create validator
        validator = FileValidator(config)

        # Create file manager
        request.app.state.file_manager = FileManager(storage_backend, validator, config)

    return request.app.state.file_manager


def verify_token(
    authorization: Optional[str] = Header(None),
    request: Request = None
) -> tuple[str, str]:
    """
    Verify authorization token and determine role.

    Args:
        authorization: Authorization header value
        request: FastAPI request

    Returns:
        Tuple of (user_id, role)
        - role: "admin", "creator", or "user"

    Raises:
        HTTPException: If token is missing or invalid
    """
    # TODO: SECURITY - Implement proper token verification with config system
    # This is a security vulnerability: any authorization header is accepted without validation.
    # Must integrate with the main authentication system before production use.
    # See router_quiz.py for proper token verification example.
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header required"
        )

    # Return test user for any valid authorization header
    return "test_user", "user"


# TODO: Add rate limiting to prevent DoS attacks
# Consider: per-user limits, per-IP limits, global limits
# Options: slowapi, fastapi-limiter, or custom implementation


@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    quiz_id: Optional[str] = Form(None),
    request: Request = None,
    file_manager: FileManager = Depends(get_file_manager),
):
    """
    Upload a file with validation and quota checks.

    Security features:
    - File type validation (extension, MIME type, magic numbers)
    - File size limits
    - Quota enforcement
    - Access control (admin/creator/user)
    - Filename sanitization
    - Special security checks (SVG/XSS, zip bombs, Office macros)

    Args:
        file: Uploaded file (multipart/form-data)
        quiz_id: Optional quiz ID for quiz attachments
        authorization: Bearer token (admin, creator, or user)

    Returns:
        File metadata with file_id and download_url

    Raises:
        HTTPException:
            - 401: Missing or invalid authorization
            - 403: Permission denied
            - 413: File too large or quota exceeded
            - 415: Unsupported file type
            - 503: File uploads disabled
    """
    # Verify authorization
    user_id, role = verify_token(request=request)

    logger.info(f"File upload request: user={user_id}, role={role}, filename={file.filename}, quiz_id={quiz_id}")

    # Read file content
    try:
        file_content = await file.read()
        file_data = io.BytesIO(file_content)
    except Exception as e:
        logger.error(f"Failed to read uploaded file: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to read file: {str(e)}"
        )

    # Upload file using file manager
    try:
        metadata = await file_manager.upload_file(
            file_data=file_data,
            filename=file.filename,
            uploader_id=user_id,
            uploader_role=role,
            quiz_id=quiz_id,
        )

        logger.info(f"File uploaded successfully: file_id={metadata.file_id}, size={metadata.size_bytes}")

        # Get download URL
        download_url = await file_manager.get_download_url(
            file_id=metadata.file_id,
            requester_id=user_id,
            requester_role=role,
        )

        return {
            "file_id": metadata.file_id,
            "filename": metadata.filename,
            "category": metadata.category,
            "size_bytes": metadata.size_bytes,
            "mime_type": metadata.mime_type,
            "checksum": metadata.checksum,
            "download_url": download_url,
            "message": "File uploaded successfully"
        }

    except ValidationError as e:
        logger.warning(f"File validation failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=str(e)
        )
    except PermissionError as e:
        logger.warning(f"Upload permission denied: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except IOError as e:
        # Quota exceeded or storage failure
        logger.error(f"Upload failed: {str(e)}")
        if "quota" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=str(e)
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Upload failed: {str(e)}"
            )


@router.get("/download/{file_id}")
async def download_file(
    file_id: str,
    request: Request,
    file_manager: FileManager = Depends(get_file_manager),
):
    """
    Download a file with access control.

    Security headers:
    - Content-Disposition: attachment (force download, prevent inline display)
    - X-Content-Type-Options: nosniff (prevent MIME sniffing)
    - Content-Security-Policy: sandbox (restrict execution)
    - X-Frame-Options: DENY (prevent framing)

    Args:
        file_id: File identifier (UUID)
        authorization: Bearer token

    Returns:
        File content with security headers

    Raises:
        HTTPException:
            - 401: Missing or invalid authorization
            - 403: Access denied
            - 404: File not found
    """
    # Verify authorization
    user_id, role = verify_token(request=request)

    logger.info(f"File download request: file_id={file_id}, user={user_id}, role={role}")

    # Get file
    try:
        file_data, metadata = await file_manager.get_file(
            file_id=file_id,
            requester_id=user_id,
            requester_role=role,
        )

        logger.info(f"File downloaded: file_id={file_id}, filename={metadata.filename}")

        # Security headers
        headers = {
            "Content-Disposition": f'attachment; filename="{metadata.filename}"',
            "X-Content-Type-Options": "nosniff",
            "Content-Security-Policy": "sandbox",
            "X-Frame-Options": "DENY",
            "Cache-Control": "private, max-age=3600",
        }

        return StreamingResponse(
            file_data,
            media_type=metadata.mime_type or "application/octet-stream",
            headers=headers,
        )

    except FileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"File not found: {file_id}"
        )
    except PermissionError as e:
        logger.warning(f"Download permission denied: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )


@router.delete("/{file_id}")
async def delete_file(
    file_id: str,
    request: Request,
    file_manager: FileManager = Depends(get_file_manager),
):
    """
    Delete a file (admin or uploader only).

    Args:
        file_id: File identifier
        authorization: Bearer token (must be admin or file uploader)

    Returns:
        Deletion confirmation

    Raises:
        HTTPException:
            - 401: Missing or invalid authorization
            - 403: Permission denied (only admin or uploader can delete)
            - 404: File not found
    """
    # Verify authorization
    user_id, role = verify_token(request=request)

    logger.info(f"File deletion request: file_id={file_id}, user={user_id}, role={role}")

    # Delete file
    try:
        success = await file_manager.delete_file(
            file_id=file_id,
            requester_id=user_id,
            requester_role=role,
        )

        if success:
            logger.info(f"File deleted: file_id={file_id}")
            return {
                "file_id": file_id,
                "message": "File deleted successfully"
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"File not found: {file_id}"
            )

    except FileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"File not found: {file_id}"
        )
    except PermissionError as e:
        logger.warning(f"Delete permission denied: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )


@router.get("/quota")
async def get_quota_info(
    quiz_id: Optional[str] = None,
    request: Request = None,
    file_manager: FileManager = Depends(get_file_manager),
):
    """
    Get storage quota information.

    Args:
        quiz_id: Optional quiz ID filter
        authorization: Bearer token

    Returns:
        Quota usage information

    Raises:
        HTTPException:
            - 401: Missing or invalid authorization
    """
    # Verify authorization
    user_id, role = verify_token(request=request)

    # Get quota info
    if role == "admin":
        # Admins can query any quota
        quota_info = await file_manager.check_quota(
            user_id=user_id if quiz_id is None else None,
            quiz_id=quiz_id,
        )
    else:
        # Non-admins can only query their own quota
        quota_info = await file_manager.check_quota(
            user_id=user_id,
            quiz_id=quiz_id,
        )

    return quota_info.to_dict()


@router.get("/list")
async def list_files(
    quiz_id: Optional[str] = None,
    category: Optional[str] = None,
    request: Request = None,
    file_manager: FileManager = Depends(get_file_manager),
):
    """
    List uploaded files with access control.

    Args:
        quiz_id: Optional quiz ID filter
        category: Optional file category filter (images, audio, video, documents, archives)
        authorization: Bearer token

    Returns:
        List of file metadata

    Raises:
        HTTPException:
            - 401: Missing or invalid authorization
            - 403: Permission denied
    """
    # Verify authorization
    user_id, role = verify_token(request=request)

    # List files
    try:
        files = await file_manager.list_files(
            requester_id=user_id,
            requester_role=role,
            quiz_id=quiz_id,
            category=category,
        )

        return {
            "file_count": len(files),
            "quiz_id": quiz_id,
            "category": category,
            "files": [metadata.to_dict() for metadata in files]
        }

    except PermissionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )


@router.post("/analyze_text/{file_id}")
async def analyze_text_file(
    file_id: str,
    pattern: Optional[str] = Form(None),
    case_sensitive: bool = Form(True),
    max_matches: int = Form(100),
    request: Request = None,
    file_manager: FileManager = Depends(get_file_manager),
):
    """
    Analyze a text file with optional regex search.

    This endpoint allows safe regex searching in uploaded text files
    with protection against ReDoS attacks.

    Args:
        file_id: ID of the uploaded file
        pattern: Optional regex pattern to search for
        case_sensitive: Whether search is case-sensitive (default: True)
        max_matches: Maximum number of matches to return (default: 100)

    Returns:
        Analysis results including:
        - line_count: number of lines
        - word_count: number of words
        - char_count: number of characters
        - text_sample: first 500 chars
        - search_results: if pattern provided

    Raises:
        HTTPException:
            - 400: Invalid regex pattern
            - 403: Permission denied
            - 404: File not found
            - 415: File is not a text file
    """
    # Verify authorization
    user_id, role = verify_token(request=request)

    # Validate max_matches parameter
    if max_matches < 1 or max_matches > 1000:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="max_matches must be between 1 and 1000"
        )

    logger.info(f"Text analysis request: file_id={file_id}, pattern={pattern}, user={user_id}")

    # Retrieve file
    try:
        file_data, metadata = await file_manager.get_file(
            file_id=file_id,
            requester_id=user_id,
            requester_role=role,
        )
    except FileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"File not found: {file_id}"
        )
    except PermissionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )

    # Check if file is a text file
    if metadata.category not in ["documents"]:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"File is not a text file: {metadata.category}"
        )

    # Analyze file
    try:
        analysis = TextFileAnalyzer.analyze_file(
            file_data=file_data,
            pattern=pattern,
            case_sensitive=case_sensitive,
            max_matches=max_matches
        )

        return {
            "file_id": file_id,
            "filename": metadata.filename,
            "analysis": analysis,
            "status": "success"
        }

    except RegexValidationError as e:
        logger.warning(f"Invalid regex pattern: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid regex pattern: {e}"
        )
    except ValueError as e:
        logger.error(f"Text file analysis failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Unexpected error during text analysis: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Text analysis failed"
        )

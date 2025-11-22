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
from pyquizhub.core.api.dependencies import verify_token_and_rate_limit
from pyquizhub.core.api.errors import (
    raise_error,
    validation_error,
    not_found_error,
    permission_error,
    authentication_error,
    server_error
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
        request.app.state.file_manager = FileManager(
            storage_backend, validator, config)

    return request.app.state.file_manager


def verify_token(
    authorization: Optional[str] = Header(None),
    request: Request = None
) -> tuple[str, str]:
    """
    Verify authorization token and determine role.

    Uses the config system for proper token verification.
    Token priority: admin > creator > user

    Args:
        authorization: Authorization header value
        request: FastAPI request

    Returns:
        Tuple of (user_id, role)
        - role: "admin", "creator", or "user"

    Raises:
        HTTPException: If token is missing or invalid
    """
    from pyquizhub.config.settings import get_config_manager

    config = get_config_manager()

    try:
        user_id, role = config.verify_token_and_get_role(authorization)
        return user_id, role
    except ValueError as e:
        authentication_error(str(e))


def check_file_upload_permission(role: str) -> None:
    """
    Check if role has permission to upload files.

    Args:
        role: User role (admin, creator, user)

    Raises:
        HTTPException: If role cannot upload files
    """
    from pyquizhub.config.settings import get_config_manager

    config = get_config_manager()

    if not config.can_upload_files(role):
        permission_error(
            f"File uploads not allowed for role '{role}'",
            details=["Contact administrator to enable file uploads"]
        )


@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    quiz_id: Optional[str] = Form(None),
    request: Request = None,
    file_manager: FileManager = Depends(get_file_manager),
    auth: tuple[str, str] = Depends(verify_token_and_rate_limit),
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
            - 429: Rate limit exceeded
            - 503: File uploads disabled
    """
    # Unpack authenticated user info (already verified and rate-limited by dependency)
    user_id, role = auth

    # Check file upload permission for this role
    check_file_upload_permission(role)

    logger.info(
        f"File upload request: user={user_id}, role={role}, filename={
            file.filename}, quiz_id={quiz_id}")

    # Read file content
    try:
        file_content = await file.read()
        file_data = io.BytesIO(file_content)
    except (OSError, IOError, MemoryError) as e:
        logger.error(f"Failed to read uploaded file: {str(e)}")
        raise_error(
            message="Failed to read file",
            status_code=status.HTTP_400_BAD_REQUEST,
            details=[str(e)],
            code="FILE_READ_ERROR"
        )
    except UnicodeDecodeError as e:
        logger.error(f"File encoding error: {str(e)}")
        raise_error(
            message="File contains invalid characters or encoding",
            status_code=status.HTTP_400_BAD_REQUEST,
            code="ENCODING_ERROR"
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

        logger.info(
            f"File uploaded successfully: file_id={
                metadata.file_id}, size={
                metadata.size_bytes}")

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
        raise_error(
            message="File validation failed",
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            details=[str(e)],
            code="VALIDATION_ERROR"
        )
    except PermissionError as e:
        logger.warning(f"Upload permission denied: {str(e)}")
        permission_error(str(e))
    except IOError as e:
        # Quota exceeded or storage failure
        logger.error(f"Upload failed: {str(e)}")
        if "quota" in str(e).lower():
            raise_error(
                message="Quota exceeded",
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                details=[str(e)],
                code="QUOTA_EXCEEDED"
            )
        else:
            server_error(f"Upload failed: {str(e)}")


@router.get("/download/{file_id}")
async def download_file(
    file_id: str,
    request: Request,
    file_manager: FileManager = Depends(get_file_manager),
    auth: tuple[str, str] = Depends(verify_token_and_rate_limit),
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
            - 429: Rate limit exceeded
    """
    # Unpack authenticated user info (already verified and rate-limited by dependency)
    user_id, role = auth

    logger.info(
        f"File download request: file_id={file_id}, user={user_id}, role={role}")

    # Get file
    try:
        file_data, metadata = await file_manager.get_file(
            file_id=file_id,
            requester_id=user_id,
            requester_role=role,
        )

        logger.info(
            f"File downloaded: file_id={file_id}, filename={
                metadata.filename}")

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
        not_found_error("File", file_id)
    except PermissionError as e:
        logger.warning(f"Download permission denied: {str(e)}")
        permission_error(str(e))


@router.delete("/{file_id}")
async def delete_file(
    file_id: str,
    request: Request,
    file_manager: FileManager = Depends(get_file_manager),
    auth: tuple[str, str] = Depends(verify_token_and_rate_limit),
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
            - 429: Rate limit exceeded
    """
    # Unpack authenticated user info (already verified and rate-limited by dependency)
    user_id, role = auth

    logger.info(
        f"File deletion request: file_id={file_id}, user={user_id}, role={role}")

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
            not_found_error("File", file_id)

    except FileNotFoundError:
        not_found_error("File", file_id)
    except PermissionError as e:
        logger.warning(f"Delete permission denied: {str(e)}")
        permission_error(str(e))


@router.get("/quota")
async def get_quota_info(
    quiz_id: Optional[str] = None,
    request: Request = None,
    file_manager: FileManager = Depends(get_file_manager),
    auth: tuple[str, str] = Depends(verify_token_and_rate_limit),
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
            - 429: Rate limit exceeded
    """
    # Unpack authenticated user info (already verified and rate-limited by dependency)
    user_id, role = auth

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
    auth: tuple[str, str] = Depends(verify_token_and_rate_limit),
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
            - 429: Rate limit exceeded
    """
    # Unpack authenticated user info (already verified and rate-limited by dependency)
    user_id, role = auth

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
        permission_error(str(e))


@router.post("/analyze_text/{file_id}")
async def analyze_text_file(
    file_id: str,
    pattern: Optional[str] = Form(None),
    case_sensitive: bool = Form(True),
    max_matches: int = Form(100),
    request: Request = None,
    file_manager: FileManager = Depends(get_file_manager),
    auth: tuple[str, str] = Depends(verify_token_and_rate_limit),
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
            - 429: Rate limit exceeded
    """
    # Unpack authenticated user info (already verified and rate-limited by dependency)
    user_id, role = auth

    # Validate max_matches parameter
    if max_matches < 1 or max_matches > 1000:
        validation_error(
            details=["max_matches must be between 1 and 1000"],
            field="max_matches"
        )

    logger.info(
        f"Text analysis request: file_id={file_id}, pattern={pattern}, user={user_id}")

    # Retrieve file
    try:
        file_data, metadata = await file_manager.get_file(
            file_id=file_id,
            requester_id=user_id,
            requester_role=role,
        )
    except FileNotFoundError:
        not_found_error("File", file_id)
    except PermissionError as e:
        permission_error(str(e))

    # Check if file is a text file
    if metadata.category not in ["documents"]:
        raise_error(
            message="File is not a text file",
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            details=[f"File category: {metadata.category}"],
            code="INVALID_FILE_TYPE"
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
        validation_error(
            details=[f"Invalid regex pattern: {e}"],
            field="pattern"
        )
    except ValueError as e:
        logger.error(f"Text file analysis failed: {e}")
        validation_error(details=[str(e)])
    except (UnicodeDecodeError, LookupError) as e:
        logger.error(f"File encoding error during analysis: {e}")
        raise_error(
            message="File contains invalid encoding or unsupported character set",
            status_code=status.HTTP_400_BAD_REQUEST,
            code="ENCODING_ERROR"
        )
    except (OSError, IOError, MemoryError) as e:
        logger.error(f"File read error during analysis: {e}")
        server_error("Text analysis failed due to file read error")

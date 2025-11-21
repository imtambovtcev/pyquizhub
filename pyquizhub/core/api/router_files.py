"""
File API router.

Provides endpoints for file metadata and download operations.
Platform-specific identifiers are NEVER exposed.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse
from typing import Any
import io

from pyquizhub.logging.setup import get_logger
from pyquizhub.core.files import FileAttachment
from pyquizhub.core.files.sql_file_storage import SQLFileStorage
from pyquizhub.core.files.file_file_storage import FileBasedFileStorage

logger = get_logger(__name__)

router = APIRouter(
    prefix="/files",
    tags=["files"]
)


def get_file_storage(request: Request):
    """Get file storage instance from app state."""
    # Check if file_storage exists, if not create it based on storage_type
    if not hasattr(request.app.state, 'file_storage'):
        storage_type = request.app.state.config_manager.storage_type

        if storage_type == "sql":
            connection_string = request.app.state.config_manager.storage_sql_connection_string
            request.app.state.file_storage = SQLFileStorage(connection_string)
        else:  # file storage
            base_dir = request.app.state.config_manager.storage_file_base_dir
            request.app.state.file_storage = FileBasedFileStorage(f"{base_dir}/files")

    return request.app.state.file_storage


@router.get("/{file_id}/metadata")
async def get_file_metadata(
    file_id: str,
    request: Request,
    file_storage=Depends(get_file_storage)
):
    """
    Get file metadata (cheap operation).

    Returns sanitized metadata without platform-specific data.
    Safe to expose to quiz creators.

    Args:
        file_id: File UUID

    Returns:
        File metadata (file_type, mime_type, size, etc.)
        NEVER includes platform or platform_data
    """
    metadata = file_storage.get_file_metadata(file_id)

    if not metadata:
        raise HTTPException(status_code=404, detail="File not found")

    # Return safe metadata (no platform data)
    attachment = FileAttachment(metadata)
    return attachment.to_safe_dict()


@router.get("/{file_id}/download")
async def download_file(
    file_id: str,
    request: Request,
    adapter: str = "api",  # Which adapter is requesting (telegram/discord/web/api)
    file_storage=Depends(get_file_storage)
):
    """
    Download file or get download URL (expensive operation).

    For Telegram files: generates temporary download URL via bot API
    For Discord files: returns proxy URL or cached file
    For web/URL files: returns original URL or proxy

    This endpoint proxies platform-specific file access without
    exposing bot tokens or private URLs.

    Args:
        file_id: File UUID
        adapter: Requesting adapter type (telegram/discord/web/api)

    Returns:
        File content, redirect, or download URL
    """
    metadata = file_storage.get_file_metadata(file_id)

    if not metadata:
        raise HTTPException(status_code=404, detail="File not found")

    attachment = FileAttachment(metadata)

    # For now, just return metadata with instructions
    # TODO: Implement actual file download/proxy logic per platform
    if attachment.platform == 'url':
        # Public URL - safe to redirect
        url = attachment.get_url_for_adapter(adapter)
        return {"download_url": url, "type": "redirect"}

    elif attachment.platform == 'telegram':
        # Would need bot instance to generate download URL
        # For now, return instructions
        return {
            "message": "Telegram file download not yet implemented",
            "file_id": file_id,
            "platform": "telegram",
            "instructions": "Telegram files require bot API access to download"
        }

    elif attachment.platform == 'discord':
        # Discord files might be cached or require proxy
        return {
            "message": "Discord file download not yet implemented",
            "file_id": file_id,
            "platform": "discord"
        }

    else:
        return {
            "message": "File download not yet implemented for this platform",
            "file_id": file_id,
            "platform": attachment.platform
        }


@router.get("/{file_id}/url")
async def get_file_url(
    file_id: str,
    request: Request,
    adapter: str = "api",
    file_storage=Depends(get_file_storage)
):
    """
    Get safe URL for file in specific adapter context.

    This is what adapters use to display files to users.

    Args:
        file_id: File UUID
        adapter: Adapter type (telegram/discord/web/api)

    Returns:
        Safe URL or identifier for the adapter
    """
    metadata = file_storage.get_file_metadata(file_id)

    if not metadata:
        raise HTTPException(status_code=404, detail="File not found")

    attachment = FileAttachment(metadata)
    url = attachment.get_url_for_adapter(adapter)

    if url is None:
        raise HTTPException(
            status_code=400,
            detail=f"File cannot be displayed in {adapter} adapter"
        )

    return {
        "file_id": file_id,
        "adapter": adapter,
        "url": url,
        "can_display": True
    }


@router.get("/session/{session_id}")
async def get_session_files(
    session_id: str,
    request: Request,
    file_storage=Depends(get_file_storage)
):
    """
    Get all files uploaded in a session.

    Returns safe metadata only (no platform data).

    Args:
        session_id: Session ID

    Returns:
        List of file metadata
    """
    files = file_storage.get_files_for_session(session_id)

    return {
        "session_id": session_id,
        "file_count": len(files),
        "files": [FileAttachment(f).to_safe_dict() for f in files]
    }


@router.get("/user/{user_id}")
async def get_user_files(
    user_id: str,
    request: Request,
    quiz_id: str | None = None,
    file_storage=Depends(get_file_storage)
):
    """
    Get all files uploaded by a user.

    Returns safe metadata only (no platform data).

    Args:
        user_id: User ID
        quiz_id: Optional quiz ID filter

    Returns:
        List of file metadata
    """
    files = file_storage.get_files_for_user(user_id, quiz_id)

    return {
        "user_id": user_id,
        "quiz_id": quiz_id,
        "file_count": len(files),
        "files": [FileAttachment(f).to_safe_dict() for f in files]
    }


@router.get("/stats")
async def get_storage_stats(
    request: Request,
    user_id: str | None = None,
    file_storage=Depends(get_file_storage)
):
    """
    Get storage statistics.

    Args:
        user_id: Optional user ID to filter stats

    Returns:
        Storage statistics (file count, total bytes)
    """
    stats = file_storage.get_storage_stats(user_id)

    return {
        "user_id": user_id,
        **stats
    }


@router.delete("/cleanup")
async def cleanup_expired_files(
    request: Request,
    file_storage=Depends(get_file_storage)
):
    """
    Cleanup expired files.

    Deletes files past their expiration date.

    Returns:
        Number of files deleted
    """
    count = file_storage.cleanup_expired_files()

    return {
        "deleted_count": count,
        "message": f"Cleaned up {count} expired file(s)"
    }

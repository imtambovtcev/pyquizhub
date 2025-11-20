from fastapi.middleware.cors import CORSMiddleware
from pyquizhub.config.settings import get_config_manager
from pyquizhub.logging.setup import setup_logging, get_logger
from pydantic import ValidationError
import os
from pyquizhub.core.storage.sql_storage import SQLStorageManager
from pyquizhub.core.storage.file_storage import FileStorageManager
from pyquizhub.core.storage.storage_manager import StorageManager
from pyquizhub.core.api.router_quiz import router as quiz_router
from pyquizhub.core.api.router_creator import router as creator_router
from pyquizhub.core.api.router_admin import router as admin_router
from pyquizhub.core.api.router_files import router as files_router
from pyquizhub.core.api.router_file_uploads import router as file_uploads_router
from fastapi.middleware import Middleware
from fastapi.exceptions import RequestValidationError, ResponseValidationError
from fastapi.responses import JSONResponse
from fastapi import FastAPI, Request, Depends, HTTPException
from contextlib import asynccontextmanager
import logging


# Use basic logging before config is loaded
_basic_logger = logging.getLogger(__name__)

# Configure application config and logging at module level
_config_manager = get_config_manager()
try:
    _config_manager.load()
    _basic_logger.info("Configuration loaded successfully")
except Exception as e:
    _basic_logger.error(f"Failed to load configuration: {e}")
    raise

# Now setup custom logging
setup_logging(_config_manager.logging_config)

# Get configured logger after setup
logger = get_logger(__name__)
logger.debug("Loaded main.py")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.debug("Starting up the application")

    # Config is already loaded at module level, just store reference
    app.state.config_manager = _config_manager

    storage_type = _config_manager.storage_type
    if storage_type == "file":
        app.state.storage_manager = FileStorageManager(
            _config_manager.storage_file_base_dir)
    elif storage_type == "sql":
        app.state.storage_manager = SQLStorageManager(
            _config_manager.storage_sql_connection_string)
    else:
        logger.error(f"Unsupported storage type: {storage_type}")
        raise ValueError(f"Unsupported storage type: {storage_type}")

    logger.info("Application startup complete")

    yield

    # Shutdown
    logger.debug("Shutting down the application")
    if hasattr(app.state, "storage_manager"):
        storage_manager: StorageManager = app.state.storage_manager
        # storage_manager.close()
    logger.info("Application shutdown complete")


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def read_root():
    """Root endpoint for sanity check."""
    logger.info("Root endpoint accessed")
    return {"message": "Welcome to the Quiz Engine API"}


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
        request: Request,
        exc: RequestValidationError):
    error_details = exc.errors()
    for error in error_details:
        logger.error(f"Validation error: {error}, request: {request}")
    return JSONResponse(
        status_code=422,
        content={
            "message": "Invalid input received. Please check your request and try again."}
    )

# Include routers
app.include_router(admin_router, prefix="/admin", tags=["admin"])
app.include_router(creator_router, prefix="/creator", tags=["creator"])
app.include_router(quiz_router, prefix="/quiz", tags=["quiz"])
app.include_router(files_router, prefix="/api", tags=["files"])
app.include_router(file_uploads_router, tags=["file-uploads"])


if __name__ == "__main__":
    import uvicorn
    # Config already loaded at module level
    uvicorn.run(app, host=_config_manager.api_host,
                port=_config_manager.api_port)

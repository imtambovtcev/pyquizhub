from fastapi import FastAPI, Request, Depends, HTTPException
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError, ResponseValidationError
from fastapi.middleware import Middleware
from pyquizhub.core.api.router_admin import router as admin_router
from pyquizhub.core.api.router_creator import router as creator_router
from pyquizhub.core.api.router_quiz import router as quiz_router
from pyquizhub.core.storage.storage_manager import StorageManager
from pyquizhub.core.storage.file_storage import FileStorageManager
from pyquizhub.core.storage.sql_storage import SQLStorageManager
import os
import yaml
from pydantic import ValidationError
from pyquizhub.config.config_utils import load_config, get_config_value, get_logger

app = FastAPI()

# Configure logging
logger = get_logger(__name__)


@app.on_event("startup")
async def startup_event():
    config = load_config()
    app.state.config = config
    storage_type = get_config_value(config, "storage.type", "file")
    if storage_type == "file":
        app.state.storage_manager = FileStorageManager(
            get_config_value(config, "storage.file.base_dir", ".pyquizhub"))
    elif storage_type == "sql":
        app.state.storage_manager = SQLStorageManager(
            get_config_value(config, "storage.sql.connection_string", "sqlite:///pyquizhub.db"))
    else:
        logger.error(f"Unsupported storage type: {storage_type}")
        raise ValueError(f"Unsupported storage type: {storage_type}")

    logger.info("Application startup complete")


@app.on_event("shutdown")
async def shutdown_event():
    if hasattr(app.state, "storage_manager"):
        storage_manager: StorageManager = app.state.storage_manager
        # storage_manager.close()
    logger.info("Application shutdown complete")

# Include routers
app.include_router(admin_router, prefix="/admin", tags=["admin"])
app.include_router(creator_router, prefix="/creator", tags=["creator"])
app.include_router(quiz_router, prefix="/quiz", tags=["quiz"])


@app.get("/")
def read_root():
    """Root endpoint for sanity check."""
    return {"message": "Welcome to the Quiz Engine API"}


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    error_details = exc.errors()
    for error in error_details:
        logger.error(f"Validation error: {error}")
    return JSONResponse(
        status_code=422,
        content={
            "message": "Invalid input received. Please check your request and try again."}
    )

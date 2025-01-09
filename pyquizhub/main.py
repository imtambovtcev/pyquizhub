from fastapi import FastAPI, Request
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
import logging
from pydantic import ValidationError

app = FastAPI()

# Configure logging
logging.basicConfig(level=logging.ERROR)
logger = logging.getLogger(__name__)


def load_config(config_path: str = None) -> dict:
    if config_path is None:
        config_path = os.getenv("PYQUIZHUB_CONFIG_PATH", os.path.join(
            os.path.dirname(__file__), "config/config.yaml"))
    with open(config_path, "r") as f:
        return yaml.safe_load(f)


@app.on_event("startup")
async def startup_event():
    config = load_config()
    storage_type = config["storage"]["type"]
    if storage_type == "file":
        app.state.storage_manager = FileStorageManager(
            config["storage"]["file"]["base_dir"])
    elif storage_type == "sql":
        app.state.storage_manager = SQLStorageManager(
            config["storage"]["sql"]["connection_string"])
    else:
        raise ValueError(f"Unsupported storage type: {storage_type}")


@app.on_event("shutdown")
async def shutdown_event():
    if hasattr(app.state, "storage_manager"):
        storage_manager: StorageManager = app.state.storage_manager
        # storage_manager.close()

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

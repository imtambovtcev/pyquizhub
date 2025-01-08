from fastapi import APIRouter, HTTPException, Request
from pyquizhub.core.api.models import (
    QuizDetailResponse,
    ResultResponse,
    ParticipatedUsersResponse,
    ConfigPathResponse,
    CreateQuizRequest,
    QuizCreationResponse,
    TokenRequest,
    TokenResponse,
)
from pyquizhub.core.api.router_creator import create_quiz_logic, generate_token_logic
import os
import yaml

from pyquizhub.core.storage.storage_manager import StorageManager


router = APIRouter()


@router.get("/quiz/{quiz_id}", response_model=QuizDetailResponse)
def admin_get_quiz(quiz_id: str, req: Request):
    """
    Admin retrieves quiz details.
    """
    storage_manager: StorageManager = req.app.state.storage_manager
    try:
        quiz = storage_manager.get_quiz(quiz_id)
        return {
            "quiz_id": quiz_id,
            "title": quiz["metadata"]["title"],
            "creator_id": quiz["creator_id"],
            "data": quiz["data"],
        }
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Quiz not found")


@router.get("/results/{quiz_id}/{user_id}", response_model=ResultResponse)
def admin_get_results(quiz_id: str, user_id: str, session_id: str, req: Request):
    """
    Admin retrieves quiz results.
    """
    storage_manager: StorageManager = req.app.state.storage_manager
    results = storage_manager.get_results(user_id, quiz_id, session_id)
    if not results:
        raise HTTPException(status_code=404, detail="Results not found")
    return results


@router.get("/participated_users/{quiz_id}", response_model=ParticipatedUsersResponse)
def admin_participated_users(quiz_id: str, req: Request):
    """
    Admin retrieves users who participated in a quiz.
    """
    storage_manager: StorageManager = req.app.state.storage_manager
    user_ids = storage_manager.get_participated_users(quiz_id)
    return {"user_ids": user_ids}


@router.get("/config", response_model=ConfigPathResponse)
def admin_get_config(req: Request):
    """
    Admin retrieves the current configuration.
    """
    config_path = os.getenv("PYQUIZHUB_CONFIG_PATH", "config.yaml")
    try:
        with open(config_path, "r") as f:
            config_data = yaml.safe_load(f)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Config not found")
    return ConfigPathResponse(config_path=config_path, config_data=config_data)


@router.post("/create_quiz", response_model=QuizCreationResponse)
def admin_create_quiz(request: CreateQuizRequest, req: Request):
    """
    Admin creates a quiz (reusing creator logic).
    """
    storage_manager: StorageManager = req.app.state.storage_manager
    return create_quiz_logic(storage_manager, request)


@router.post("/generate_token", response_model=TokenResponse)
def admin_generate_token(request: TokenRequest, req: Request):
    """
    Admin generates a token (reusing creator logic).
    """
    storage_manager: StorageManager = req.app.state.storage_manager
    return generate_token_logic(storage_manager, request)

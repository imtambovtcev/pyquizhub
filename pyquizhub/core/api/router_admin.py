"""
Administrative API Router for PyQuizHub.

This module provides API endpoints for administrative operations including:
- Quiz management
- Results retrieval
- User participation tracking
- System configuration
- Token management
"""

from fastapi import APIRouter, HTTPException, Request, Depends
from pyquizhub.models import (
    QuizDetailResponseModel,
    QuizResultResponseModel,
    ParticipatedUsersResponseModel,
    ConfigPathResponseModel,
    CreateQuizRequestModel,
    QuizCreationResponseModel,
    TokenRequestModel,
    TokenResponseModel,
    AllQuizzesResponseModel,
    AllTokensResponseModel,
)
from pyquizhub.core.api.router_creator import create_quiz_logic, generate_token_logic, get_quiz_logic, get_participated_users_logic, get_results_by_quiz_logic
import os
import yaml
from pyquizhub.config.config_utils import get_token_from_config, get_logger
from pyquizhub.core.storage.storage_manager import StorageManager

logger = get_logger(__name__)
logger.debug("Loaded router_admin.py")
router = APIRouter()


def admin_token_dependency(request: Request):
    """
    Dependency to validate admin authentication token.

    Args:
        request: FastAPI Request object containing headers

    Raises:
        HTTPException: If admin token is invalid
    """
    token = request.headers.get("Authorization")
    expected_token = get_token_from_config("admin")
    if token != expected_token:
        raise HTTPException(status_code=403, detail="Invalid admin token")


@router.get("/quiz/{quiz_id}", response_model=QuizDetailResponseModel, dependencies=[Depends(admin_token_dependency)])
def admin_get_quiz(quiz_id: str, req: Request):
    """
    Retrieve details of a specific quiz.

    Args:
        quiz_id: Unique identifier of the quiz
        req: FastAPI Request object containing application state

    Returns:
        QuizDetailResponseModel: Quiz details

    Raises:
        HTTPException: If quiz is not found or access denied
    """
    logger.debug(f"Admin fetching quiz details for quiz_id: {quiz_id}")
    storage_manager: StorageManager = req.app.state.storage_manager
    return get_quiz_logic(storage_manager, quiz_id)


@router.get("/results/{quiz_id}", response_model=QuizResultResponseModel, dependencies=[Depends(admin_token_dependency)])
def admin_get_results_by_quiz(quiz_id: str, req: Request):
    """
    Retrieve quiz results by quiz ID.

    Args:
        quiz_id: Unique identifier of the quiz
        req: FastAPI Request object containing application state

    Returns:
        QuizResultResponseModel: Quiz results

    Raises:
        HTTPException: If results are not found or access denied
    """
    logger.debug(f"Admin fetching results for quiz_id: {quiz_id}")
    storage_manager: StorageManager = req.app.state.storage_manager
    return get_results_by_quiz_logic(storage_manager, quiz_id)


@router.get("/participated_users/{quiz_id}", response_model=ParticipatedUsersResponseModel, dependencies=[Depends(admin_token_dependency)])
def admin_participated_users(quiz_id: str, req: Request):
    """
    Retrieve users who participated in a quiz.

    Args:
        quiz_id: Unique identifier of the quiz
        req: FastAPI Request object containing application state

    Returns:
        ParticipatedUsersResponseModel: List of participated users

    Raises:
        HTTPException: If users are not found or access denied
    """
    logger.debug(f"Admin fetching participated users for quiz_id: {quiz_id}")
    storage_manager: StorageManager = req.app.state.storage_manager
    return get_participated_users_logic(storage_manager, quiz_id)


@router.get("/config", response_model=ConfigPathResponseModel, dependencies=[Depends(admin_token_dependency)])
def admin_get_config(req: Request):
    """
    Retrieve the current system configuration.

    Args:
        req: FastAPI Request object containing application state

    Returns:
        ConfigPathResponseModel: Configuration path and data

    Raises:
        HTTPException: If config file is not found or access denied
    """
    config_path = os.getenv("PYQUIZHUB_CONFIG_PATH", "config.yaml")
    try:
        with open(config_path, "r") as f:
            config_data = yaml.safe_load(f)
    except FileNotFoundError:
        logger.error(f"Config file not found at path: {config_path}")
        raise HTTPException(status_code=404, detail="Config not found")
    return ConfigPathResponseModel(config_path=config_path, config_data=config_data)


@router.post("/create_quiz", response_model=QuizCreationResponseModel, dependencies=[Depends(admin_token_dependency)])
def admin_create_quiz(request: CreateQuizRequestModel, req: Request):
    """
    Create a new quiz using the provided request data.

    Args:
        request: CreateQuizRequestModel containing quiz data
        req: FastAPI Request object containing application state

    Returns:
        QuizCreationResponseModel: Created quiz details

    Raises:
        HTTPException: If quiz creation fails or access denied
    """
    logger.debug(
        f"Admin creating quiz with title: {request.quiz.metadata.title}")
    storage_manager: StorageManager = req.app.state.storage_manager
    return create_quiz_logic(storage_manager, request)


@router.post("/generate_token", response_model=TokenResponseModel, dependencies=[Depends(admin_token_dependency)])
def admin_generate_token(request: TokenRequestModel, req: Request):
    """
    Generate a token for a specific quiz.

    Args:
        request: TokenRequestModel containing quiz ID
        req: FastAPI Request object containing application state

    Returns:
        TokenResponseModel: Generated token details

    Raises:
        HTTPException: If token generation fails or access denied
    """
    logger.debug(f"Admin generating token for quiz_id: {request.quiz_id}")
    storage_manager: StorageManager = req.app.state.storage_manager
    return generate_token_logic(storage_manager, request)


@router.get("/all_quizzes", response_model=AllQuizzesResponseModel, dependencies=[Depends(admin_token_dependency)])
def admin_get_all_quizzes(req: Request):
    """
    Retrieve all quizzes in the system.

    Args:
        req: FastAPI Request object containing application state

    Returns:
        AllQuizzesResponseModel: List of all quizzes

    Raises:
        HTTPException: If retrieval fails or access denied
    """
    logger.debug("Admin fetching all quizzes")
    storage_manager: StorageManager = req.app.state.storage_manager
    all_quizzes = storage_manager.get_all_quizzes()
    logger.info("Admin retrieved all quizzes")
    return AllQuizzesResponseModel(quizzes=all_quizzes)


@router.get("/all_tokens", response_model=AllTokensResponseModel, dependencies=[Depends(admin_token_dependency)])
def admin_get_all_tokens(req: Request):
    """
    Retrieve all tokens in the system.

    Args:
        req: FastAPI Request object containing application state

    Returns:
        AllTokensResponseModel: List of all tokens

    Raises:
        HTTPException: If retrieval fails or access denied
    """
    logger.debug("Admin fetching all tokens")
    storage_manager: StorageManager = req.app.state.storage_manager
    all_tokens = storage_manager.get_all_tokens()
    logger.info("Admin retrieved all tokens")
    return AllTokensResponseModel(tokens=all_tokens)

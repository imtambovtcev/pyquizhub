"""
Creator API Router for PyQuizHub.

This module provides API endpoints for quiz creators including:
- Quiz creation
- Token generation
- Result retrieval
- Quiz status monitoring
- Participant tracking

All endpoints require creator authentication and enforce appropriate permissions.
"""

from fastapi import APIRouter, HTTPException, Request, Depends
from pyquizhub.core.storage.storage_manager import StorageManager
from pyquizhub.core.engine.json_validator import QuizJSONValidator
from pyquizhub.utils import generate_quiz_token, generate_quiz_id
from pyquizhub.models import (
    CreateQuizRequestModel,
    QuizCreationResponseModel,
    TokenRequestModel,
    TokenResponseModel,
    QuizDetailResponseModel,
    ParticipatedUsersResponseModel,
    QuizResultResponseModel
)
from datetime import datetime
from pyquizhub.config.settings import get_logger

logger = get_logger(__name__)
logger.debug("Loaded router_admin.py")
router = APIRouter()


def creator_token_dependency(request: Request):
    """
    Dependency to validate creator authentication token.

    Args:
        request: FastAPI Request object containing headers

    Raises:
        HTTPException: If creator token is invalid or missing
    """
    from pyquizhub.config.settings import get_config_manager
    token = request.headers.get("Authorization")
    config_manager = get_config_manager()
    expected_token = config_manager.get_token("creator")

    # Check if creator token is configured
    if not expected_token:
        raise HTTPException(
            status_code=500,
            detail="Creator token not configured"
        )

    # Check if token is provided
    if not token:
        raise HTTPException(
            status_code=403,
            detail="Invalid creator token"
        )

    # Check if token matches
    if token != expected_token:
        raise HTTPException(
            status_code=403,
            detail="Invalid creator token"
        )


def create_quiz_logic(
        storage_manager: StorageManager,
        request: CreateQuizRequestModel) -> QuizCreationResponseModel:
    """
    Logic for creating a quiz, shared between creator and admin roles.

    Args:
        storage_manager: StorageManager instance
        request: CreateQuizRequestModel containing quiz definition

    Returns:
        QuizCreationResponseModel: Created quiz details

    Raises:
        HTTPException: If quiz validation fails
    """
    logger.debug(f"Creating quiz with title: {request.quiz.metadata.title}")
    # Validate the quiz structure
    validation_result = QuizJSONValidator.validate(request.quiz.model_dump())
    if validation_result["errors"]:
        logger.error(f"Quiz validation failed: {validation_result['errors']}")
        raise HTTPException(
            status_code=400, detail=validation_result["errors"])

    # Generate an ID and store it
    quiz_id = generate_quiz_id(request.quiz.metadata.title)
    quiz_data = request.quiz.model_dump()
    quiz_data["creator_id"] = request.creator_id
    storage_manager.add_quiz(quiz_id, quiz_data, request.creator_id)

    logger.info(f"Quiz {quiz_id} created by creator {request.creator_id}")

    return QuizCreationResponseModel(
        quiz_id=quiz_id, title=request.quiz.metadata.title)


def generate_token_logic(
        storage_manager: StorageManager,
        request: TokenRequestModel) -> TokenResponseModel:
    """
    Shared logic for generating quiz access tokens.

    Args:
        storage_manager: StorageManager instance
        request: TokenRequestModel containing quiz ID and token type

    Returns:
        TokenResponseModel: Generated token details
    """
    logger.debug(f"Generating token for quiz_id: {request.quiz_id}")
    token = generate_quiz_token()
    token_data = {"token": token,
                  "quiz_id": request.quiz_id, "type": request.type}
    storage_manager.add_tokens([token_data])

    logger.info(f"Token generated for quiz {request.quiz_id}")

    return TokenResponseModel(token=token)


def get_results_logic(
        storage_manager: StorageManager,
        user_id: str,
        quiz_id: str):
    """
    Get quiz results for a specific user.

    Args:
        storage_manager: StorageManager instance
        user_id: ID of the user
        quiz_id: ID of the quiz

    Returns:
        dict: User's quiz results
    """
    logger.debug(
        f"Fetching results for user_id: {user_id}, quiz_id: {quiz_id}")
    return storage_manager.get_results(user_id, quiz_id)


def get_results_by_quiz_logic(storage_manager: StorageManager, quiz_id: str):
    """
    Get all results for a specific quiz.

    Args:
        storage_manager: StorageManager instance
        quiz_id: ID of the quiz

    Returns:
        dict: All results for the quiz, grouped by user
    """
    logger.debug(f"Fetching results by quiz_id: {quiz_id}")
    results = storage_manager.get_results_by_quiz(quiz_id)
    for user_id, sessions in results.items():
        for session_id, result in sessions.items():
            result["timestamp"] = result["timestamp"]
    return {'results': results}


def get_quiz_logic(storage_manager: StorageManager, quiz_id: str):
    """
    Get quiz details and contents.

    Args:
        storage_manager: StorageManager instance
        quiz_id: ID of the quiz

    Returns:
        dict: Quiz details and metadata

    Raises:
        HTTPException: If quiz not found
    """
    logger.debug(f"Fetching quiz details for quiz_id: {quiz_id}")
    try:
        quiz = storage_manager.get_quiz(quiz_id)
        # quiz is already the quiz data (metadata, questions, etc.)
        return {
            "quiz_id": quiz_id,
            "title": quiz["metadata"]["title"],
            "creator_id": quiz.get("creator_id", "unknown"),
            "data": quiz,
        }
    except FileNotFoundError:
        logger.error(f"Quiz {quiz_id} not found")
        raise HTTPException(status_code=404, detail="Quiz not found")


def get_participated_users_logic(
        storage_manager: StorageManager,
        quiz_id: str):
    """
    Get list of users who participated in a quiz.

    Args:
        storage_manager: StorageManager instance
        quiz_id: ID of the quiz

    Returns:
        dict: List of user IDs who took the quiz
    """
    logger.debug(f"Fetching participated users for quiz_id: {quiz_id}")
    user_ids = storage_manager.get_participated_users(quiz_id)
    return {"user_ids": user_ids}


@router.post("/create_quiz",
             response_model=QuizCreationResponseModel,
             dependencies=[Depends(creator_token_dependency)])
def creator_create_quiz(request: CreateQuizRequestModel, req: Request):
    """
    Create a new quiz as a creator.

    Args:
        request: CreateQuizRequestModel containing quiz definition
        req: FastAPI Request object containing application state

    Returns:
        QuizCreationResponseModel: Created quiz details

    Raises:
        HTTPException: If quiz validation fails
    """
    logger.debug(
        f"Creator creating quiz with title: {request.quiz.metadata.title}")
    storage_manager: StorageManager = req.app.state.storage_manager
    return create_quiz_logic(storage_manager, request)


@router.post("/generate_token", response_model=TokenResponseModel,
             dependencies=[Depends(creator_token_dependency)])
def creator_generate_token(request: TokenRequestModel, req: Request):
    """
    Endpoint for creators to generate tokens.

    Args:
        request: TokenRequestModel containing quiz ID and token type
        req: FastAPI Request object containing application state

    Returns:
        TokenResponseModel: Generated token details
    """
    logger.debug(f"Creator generating token for quiz_id: {request.quiz_id}")
    storage_manager: StorageManager = req.app.state.storage_manager
    return generate_token_logic(storage_manager, request)


@router.get("/quiz/{quiz_id}",
            response_model=QuizDetailResponseModel,
            dependencies=[Depends(creator_token_dependency)])
def creator_get_quiz(quiz_id: str, req: Request):
    """
    Endpoint for creators to get quiz details.

    Args:
        quiz_id: ID of the quiz
        req: FastAPI Request object containing application state

    Returns:
        dict: Quiz details and metadata

    Raises:
        HTTPException: If quiz not found or permission denied
    """
    logger.debug(f"Creator fetching quiz details for quiz_id: {quiz_id}")
    storage_manager: StorageManager = req.app.state.storage_manager
    user_id = req.headers.get("X-User-ID")
    if not storage_manager.user_has_permission_for_quiz_creation(user_id):
        logger.error(
            f"Permission denied for user {user_id} to access quiz {quiz_id}")
        raise HTTPException(status_code=403, detail="Permission denied")
    return get_quiz_logic(storage_manager, quiz_id)


@router.get("/participated_users/{quiz_id}",
            response_model=ParticipatedUsersResponseModel,
            dependencies=[Depends(creator_token_dependency)])
def creator_participated_users(quiz_id: str, req: Request):
    """
    Endpoint for creators to get participated users.

    Args:
        quiz_id: ID of the quiz
        req: FastAPI Request object containing application state

    Returns:
        dict: List of user IDs who took the quiz

    Raises:
        HTTPException: If permission denied
    """
    logger.debug(f"Creator fetching participated users for quiz_id: {quiz_id}")
    storage_manager: StorageManager = req.app.state.storage_manager
    user_id = req.headers.get("X-User-ID")
    if not storage_manager.user_has_permission_for_quiz_creation(user_id):
        logger.error(
            f"Permission denied for user {user_id} to access participated users for quiz {quiz_id}")
        raise HTTPException(status_code=403, detail="Permission denied")
    return get_participated_users_logic(storage_manager, quiz_id)


@router.get("/results/{quiz_id}",
            response_model=QuizResultResponseModel,
            dependencies=[Depends(creator_token_dependency)])
def creator_get_results_by_quiz(quiz_id: str, req: Request):
    """
    Endpoint for creators to get quiz results by quiz ID.

    Args:
        quiz_id: ID of the quiz
        req: FastAPI Request object containing application state

    Returns:
        dict: All results for the quiz, grouped by user

    Raises:
        HTTPException: If permission denied
    """
    logger.debug(f"Creator fetching results for quiz_id: {quiz_id}")
    storage_manager: StorageManager = req.app.state.storage_manager
    user_id = req.headers.get("X-User-ID")
    if not storage_manager.user_has_permission_for_quiz_creation(user_id):
        logger.error(
            f"Permission denied for user {user_id} to access results for quiz {quiz_id}")
        raise HTTPException(status_code=403, detail="Permission denied")
    return get_results_by_quiz_logic(storage_manager, quiz_id)

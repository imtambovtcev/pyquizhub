from fastapi import APIRouter, HTTPException, Request, Depends
from pyquizhub.core.storage.storage_manager import StorageManager
from pyquizhub.core.engine.json_validator import QuizJSONValidator
from pyquizhub.utils import generate_quiz_token, generate_quiz_id
from pyquizhub.models import (
    CreateQuizRequest,
    QuizCreationResponse,
    TokenRequest,
    TokenResponse,
    QuizDetailResponse,
    ParticipatedUsersResponse,
    ResultResponse
)
from datetime import datetime
from pyquizhub.config.config_utils import get_token_from_config, get_logger

logger = get_logger(__name__)
router = APIRouter()


def creator_token_dependency(request: Request):
    token = request.headers.get("Authorization")
    expected_token = get_token_from_config("creator")
    if token != expected_token:
        raise HTTPException(status_code=403, detail="Invalid creator token")


def create_quiz_logic(storage_manager: StorageManager, request: CreateQuizRequest) -> QuizCreationResponse:
    """
    Logic for creating a quiz. Shared between creator and admin.
    """
    logger.debug(f"Creating quiz with title: {request.quiz.metadata.title}")
    # Validate the quiz structure
    validation_result = QuizJSONValidator.validate(request.quiz.dict())
    if validation_result["errors"]:
        logger.error(f"Quiz validation failed: {validation_result['errors']}")
        raise HTTPException(
            status_code=400, detail=validation_result["errors"])

    # Generate an ID and store it
    quiz_id = generate_quiz_id(request.quiz.metadata.title)
    quiz_data = request.quiz.dict()
    quiz_data["creator_id"] = request.creator_id
    storage_manager.add_quiz(quiz_id, quiz_data, request.creator_id)

    logger.info(f"Quiz {quiz_id} created by creator {request.creator_id}")

    return QuizCreationResponse(quiz_id=quiz_id, title=request.quiz.metadata.title)


def generate_token_logic(storage_manager: StorageManager, request: TokenRequest) -> TokenResponse:
    """
    Logic for generating a quiz token. Shared between creator and admin.
    """
    logger.debug(f"Generating token for quiz_id: {request.quiz_id}")
    token = generate_quiz_token()
    token_data = {"token": token,
                  "quiz_id": request.quiz_id, "type": request.type}
    storage_manager.add_tokens([token_data])

    logger.info(f"Token generated for quiz {request.quiz_id}")

    return TokenResponse(token=token)


def get_results_logic(storage_manager: StorageManager, user_id: str, quiz_id: str):
    """
    Logic for getting quiz results.
    """
    logger.debug(
        f"Fetching results for user_id: {user_id}, quiz_id: {quiz_id}")
    return storage_manager.get_results(user_id, quiz_id)


def get_results_by_quiz_logic(storage_manager: StorageManager, quiz_id: str):
    """
    Logic for getting quiz results by quiz ID.
    """
    logger.debug(f"Fetching results by quiz_id: {quiz_id}")
    results = storage_manager.get_results_by_quiz(quiz_id)
    for user_id, sessions in results.items():
        for session_id, result in sessions.items():
            result["timestamp"] = result["timestamp"]
    return {'results': results}


def get_quiz_logic(storage_manager: StorageManager, quiz_id: str):
    """
    Logic for getting quiz details.
    """
    logger.debug(f"Fetching quiz details for quiz_id: {quiz_id}")
    try:
        quiz = storage_manager.get_quiz(quiz_id)
        return {
            "quiz_id": quiz_id,
            "title": quiz["metadata"]["title"],
            "creator_id": quiz["creator_id"],
            "data": quiz["data"],
        }
    except FileNotFoundError:
        logger.error(f"Quiz {quiz_id} not found")
        raise HTTPException(status_code=404, detail="Quiz not found")


def get_participated_users_logic(storage_manager: StorageManager, quiz_id: str):
    """
    Logic for getting participated users.
    """
    logger.debug(f"Fetching participated users for quiz_id: {quiz_id}")
    user_ids = storage_manager.get_participated_users(quiz_id)
    return {"user_ids": user_ids}


@router.post("/create_quiz", response_model=QuizCreationResponse, dependencies=[Depends(creator_token_dependency)])
def creator_create_quiz(request: CreateQuizRequest, req: Request):
    """
    Endpoint for creators to create a quiz.
    """
    logger.debug(
        f"Creator creating quiz with title: {request.quiz.metadata.title}")
    storage_manager: StorageManager = req.app.state.storage_manager
    return create_quiz_logic(storage_manager, request)


@router.post("/generate_token", response_model=TokenResponse, dependencies=[Depends(creator_token_dependency)])
def creator_generate_token(request: TokenRequest, req: Request):
    """
    Endpoint for creators to generate tokens.
    """
    logger.debug(f"Creator generating token for quiz_id: {request.quiz_id}")
    storage_manager: StorageManager = req.app.state.storage_manager
    return generate_token_logic(storage_manager, request)


@router.get("/quiz/{quiz_id}", response_model=QuizDetailResponse, dependencies=[Depends(creator_token_dependency)])
def creator_get_quiz(quiz_id: str, req: Request):
    """
    Endpoint for creators to get quiz details.
    """
    logger.debug(f"Creator fetching quiz details for quiz_id: {quiz_id}")
    storage_manager: StorageManager = req.app.state.storage_manager
    user_id = req.headers.get("X-User-ID")
    if not storage_manager.user_has_permission_for_quiz_creation(user_id):
        logger.error(
            f"Permission denied for user {user_id} to access quiz {quiz_id}")
        raise HTTPException(status_code=403, detail="Permission denied")
    return get_quiz_logic(storage_manager, quiz_id)


@router.get("/participated_users/{quiz_id}", response_model=ParticipatedUsersResponse, dependencies=[Depends(creator_token_dependency)])
def creator_participated_users(quiz_id: str, req: Request):
    """
    Endpoint for creators to get participated users.
    """
    logger.debug(f"Creator fetching participated users for quiz_id: {quiz_id}")
    storage_manager: StorageManager = req.app.state.storage_manager
    user_id = req.headers.get("X-User-ID")
    if not storage_manager.user_has_permission_for_quiz_creation(user_id):
        logger.error(
            f"Permission denied for user {user_id} to access participated users for quiz {quiz_id}")
        raise HTTPException(status_code=403, detail="Permission denied")
    return get_participated_users_logic(storage_manager, quiz_id)


@router.get("/results/{quiz_id}", response_model=ResultResponse, dependencies=[Depends(creator_token_dependency)])
def creator_get_results_by_quiz(quiz_id: str, req: Request):
    """
    Endpoint for creators to get quiz results by quiz ID.
    """
    logger.debug(f"Creator fetching results for quiz_id: {quiz_id}")
    storage_manager: StorageManager = req.app.state.storage_manager
    user_id = req.headers.get("X-User-ID")
    if not storage_manager.user_has_permission_for_quiz_creation(user_id):
        logger.error(
            f"Permission denied for user {user_id} to access results for quiz {quiz_id}")
        raise HTTPException(status_code=403, detail="Permission denied")
    return get_results_by_quiz_logic(storage_manager, quiz_id)

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
    token = request.headers.get("Authorization")
    expected_token = get_token_from_config("admin")
    if token != expected_token:
        raise HTTPException(status_code=403, detail="Invalid admin token")


@router.get("/quiz/{quiz_id}", response_model=QuizDetailResponseModel, dependencies=[Depends(admin_token_dependency)])
def admin_get_quiz(quiz_id: str, req: Request):
    """
    Admin retrieves quiz details.
    """
    logger.debug(f"Admin fetching quiz details for quiz_id: {quiz_id}")
    storage_manager: StorageManager = req.app.state.storage_manager
    return get_quiz_logic(storage_manager, quiz_id)


@router.get("/results/{quiz_id}", response_model=QuizResultResponseModel, dependencies=[Depends(admin_token_dependency)])
def admin_get_results_by_quiz(quiz_id: str, req: Request):
    """
    Admin retrieves quiz results by quiz ID.
    """
    logger.debug(f"Admin fetching results for quiz_id: {quiz_id}")
    storage_manager: StorageManager = req.app.state.storage_manager
    return get_results_by_quiz_logic(storage_manager, quiz_id)


@router.get("/participated_users/{quiz_id}", response_model=ParticipatedUsersResponseModel, dependencies=[Depends(admin_token_dependency)])
def admin_participated_users(quiz_id: str, req: Request):
    """
    Admin retrieves users who participated in a quiz.
    """
    logger.debug(f"Admin fetching participated users for quiz_id: {quiz_id}")
    storage_manager: StorageManager = req.app.state.storage_manager
    return get_participated_users_logic(storage_manager, quiz_id)


@ router.get("/config", response_model=ConfigPathResponseModel, dependencies=[Depends(admin_token_dependency)])
def admin_get_config(req: Request):
    """
    Admin retrieves the current configuration.
    """
    config_path = os.getenv("PYQUIZHUB_CONFIG_PATH", "config.yaml")
    try:
        with open(config_path, "r") as f:
            config_data = yaml.safe_load(f)
    except FileNotFoundError:
        logger.error(f"Config file not found at path: {config_path}")
        raise HTTPException(status_code=404, detail="Config not found")
    return ConfigPathResponse(config_path=config_path, config_data=config_data)


@ router.post("/create_quiz", response_model=QuizCreationResponseModel, dependencies=[Depends(admin_token_dependency)])
def admin_create_quiz(request: CreateQuizRequestModel, req: Request):
    """
    Admin creates a quiz (reusing creator logic).
    """
    logger.debug(
        f"Admin creating quiz with title: {request.quiz.metadata.title}")
    storage_manager: StorageManager = req.app.state.storage_manager
    return create_quiz_logic(storage_manager, request)


@ router.post("/generate_token", response_model=TokenResponseModel, dependencies=[Depends(admin_token_dependency)])
def admin_generate_token(request: TokenRequestModel, req: Request):
    """
    Admin generates a token (reusing creator logic).
    """
    logger.debug(f"Admin generating token for quiz_id: {request.quiz_id}")
    storage_manager: StorageManager = req.app.state.storage_manager
    return generate_token_logic(storage_manager, request)


@ router.get("/all_quizzes", response_model=AllQuizzesResponseModel, dependencies=[Depends(admin_token_dependency)])
def admin_get_all_quizzes(req: Request):
    """
    Admin retrieves all quizzes.
    """
    logger.debug("Admin fetching all quizzes")
    storage_manager: StorageManager = req.app.state.storage_manager
    all_quizzes = storage_manager.get_all_quizzes()
    logger.info("Admin retrieved all quizzes")
    return AllQuizzesResponseModel(quizzes=all_quizzes)


@ router.get("/all_tokens", response_model=AllTokensResponseModel, dependencies=[Depends(admin_token_dependency)])
def admin_get_all_tokens(req: Request):
    """
    Admin retrieves all tokens.
    """
    logger.debug("Admin fetching all tokens")
    storage_manager: StorageManager = req.app.state.storage_manager
    all_tokens = storage_manager.get_all_tokens()
    logger.info("Admin retrieved all tokens")
    return AllTokensResponseModel(tokens=all_tokens)

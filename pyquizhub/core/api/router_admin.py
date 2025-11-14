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
    AllUsersResponseModel,
    AllResultsResponseModel,
    AllSessionsResponseModel,
    SessionDetailModel,
)
from pyquizhub.core.api.router_creator import create_quiz_logic, generate_token_logic, get_quiz_logic, get_participated_users_logic, get_results_by_quiz_logic
import os
from pyquizhub.config.settings import get_logger
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
    from pyquizhub.config.settings import get_config_manager
    token = request.headers.get("Authorization")
    config_manager = get_config_manager()
    expected_token = config_manager.get_token("admin")
    if token != expected_token:
        raise HTTPException(status_code=403, detail="Invalid admin token")


@router.get("/quiz/{quiz_id}",
            response_model=QuizDetailResponseModel,
            dependencies=[Depends(admin_token_dependency)])
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


@router.put("/quiz/{quiz_id}",
            dependencies=[Depends(admin_token_dependency)])
def admin_update_quiz(quiz_id: str, req: Request):
    """
    Update an existing quiz.

    Args:
        quiz_id: Unique identifier of the quiz to update
        req: FastAPI Request object containing application state and JSON body

    Returns:
        dict: Success message

    Raises:
        HTTPException: If quiz is not found or update fails
    """
    logger.debug(f"Admin updating quiz: {quiz_id}")
    storage_manager: StorageManager = req.app.state.storage_manager

    try:
        # Get raw JSON body
        import asyncio
        body = asyncio.run(req.json())

        # Extract quiz data - support both formats
        if 'quiz' in body:
            quiz_data = body['quiz']
        else:
            quiz_data = body

        storage_manager.update_quiz(quiz_id, quiz_data)
        logger.info(f"Admin updated quiz: {quiz_id}")
        return {"message": f"Quiz {quiz_id} updated successfully", "quiz_id": quiz_id}
    except FileNotFoundError:
        logger.error(f"Quiz {quiz_id} not found for update")
        raise HTTPException(status_code=404, detail="Quiz not found")
    except Exception as e:
        logger.error(f"Failed to update quiz {quiz_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update quiz: {str(e)}"
        )


@router.delete("/quiz/{quiz_id}",
               dependencies=[Depends(admin_token_dependency)])
def admin_delete_quiz(quiz_id: str, req: Request):
    """
    Delete a quiz and all associated data (tokens, sessions).

    Args:
        quiz_id: Unique identifier of the quiz to delete
        req: FastAPI Request object containing application state

    Returns:
        dict: Success message

    Raises:
        HTTPException: If quiz is not found or deletion fails
    """
    logger.debug(f"Admin deleting quiz: {quiz_id}")
    storage_manager: StorageManager = req.app.state.storage_manager

    try:
        storage_manager.delete_quiz(quiz_id)
        logger.info(f"Admin deleted quiz: {quiz_id}")
        return {"message": f"Quiz {quiz_id} deleted successfully"}
    except FileNotFoundError:
        logger.error(f"Quiz {quiz_id} not found for deletion")
        raise HTTPException(status_code=404, detail="Quiz not found")
    except Exception as e:
        logger.error(f"Failed to delete quiz {quiz_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete quiz: {str(e)}"
        )


@router.get("/results/{quiz_id}",
            response_model=QuizResultResponseModel,
            dependencies=[Depends(admin_token_dependency)])
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


@router.get("/participated_users/{quiz_id}",
            response_model=ParticipatedUsersResponseModel,
            dependencies=[Depends(admin_token_dependency)])
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


@router.get("/config", response_model=ConfigPathResponseModel,
            dependencies=[Depends(admin_token_dependency)])
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
    try:
        from pyquizhub.config.settings import get_config_manager
        config_manager = get_config_manager()
        config_path = config_manager.get_config_path()
        config_data = config_manager.get_config()
        return ConfigPathResponseModel(
            config_path=config_path,
            config_data=config_data)
    except FileNotFoundError:
        logger.error(f"Config file not found")
        raise HTTPException(status_code=404, detail="Config not found")


@router.post("/create_quiz",
             response_model=QuizCreationResponseModel,
             dependencies=[Depends(admin_token_dependency)])
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


@router.post("/generate_token", response_model=TokenResponseModel,
             dependencies=[Depends(admin_token_dependency)])
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


@router.get("/all_quizzes", response_model=AllQuizzesResponseModel,
            dependencies=[Depends(admin_token_dependency)])
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


@router.get("/all_tokens", response_model=AllTokensResponseModel,
            dependencies=[Depends(admin_token_dependency)])
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


@router.delete("/token/{token}",
               dependencies=[Depends(admin_token_dependency)])
def admin_delete_token(token: str, req: Request):
    """
    Delete a specific token.

    Args:
        token: Token string to delete
        req: FastAPI Request object containing application state

    Returns:
        dict: Success message

    Raises:
        HTTPException: If token not found or deletion fails
    """
    logger.debug(f"Admin deleting token: {token}")
    storage_manager: StorageManager = req.app.state.storage_manager

    try:
        storage_manager.remove_token(token)
        logger.info(f"Admin deleted token: {token}")
        return {"message": f"Token {token} deleted successfully"}
    except Exception as e:
        logger.error(f"Failed to delete token {token}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete token: {str(e)}"
        )


# ============================================================================
# API Routes - User Management
# ============================================================================

@router.get("/all_users", response_model=AllUsersResponseModel,
            dependencies=[Depends(admin_token_dependency)])
def admin_get_all_users(req: Request):
    """
    Retrieve all users in the system.

    Args:
        req: FastAPI Request object containing application state

    Returns:
        AllUsersResponseModel: Dictionary of all users

    Raises:
        HTTPException: If retrieval fails or access denied
    """
    logger.debug("Admin fetching all users")
    storage_manager: StorageManager = req.app.state.storage_manager
    try:
        all_users = storage_manager.get_users()
        logger.info(f"Admin retrieved {len(all_users)} users")
        return AllUsersResponseModel(users=all_users)
    except Exception as e:
        logger.error(f"Failed to retrieve users: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve users: {str(e)}"
        )


# ============================================================================
# API Routes - Results (Extended)
# ============================================================================

@router.get("/all_results", response_model=AllResultsResponseModel,
            dependencies=[Depends(admin_token_dependency)])
def admin_get_all_results(req: Request):
    """
    Retrieve all results in the system.

    Args:
        req: FastAPI Request object containing application state

    Returns:
        AllResultsResponseModel: Dictionary of all results

    Raises:
        HTTPException: If retrieval fails or access denied
    """
    logger.debug("Admin fetching all results")
    storage_manager: StorageManager = req.app.state.storage_manager
    try:
        all_results = storage_manager.get_all_results()
        logger.info(f"Admin retrieved all results")
        return AllResultsResponseModel(results=all_results)
    except Exception as e:
        logger.error(f"Failed to retrieve results: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve results: {str(e)}"
        )


# ============================================================================
# API Routes - Sessions (Extended)
# ============================================================================

@router.get("/all_sessions", response_model=AllSessionsResponseModel,
            dependencies=[Depends(admin_token_dependency)])
def admin_get_all_sessions(req: Request):
    """
    Retrieve all active sessions in the system.

    Args:
        req: FastAPI Request object containing application state

    Returns:
        AllSessionsResponseModel: List of all sessions

    Raises:
        HTTPException: If retrieval fails or access denied
    """
    logger.debug("Admin fetching all sessions")
    storage_manager: StorageManager = req.app.state.storage_manager
    try:
        # Get all sessions grouped by user
        sessions_by_user = storage_manager.get_all_sessions()

        # Flatten sessions and load detailed session data
        sessions = []
        for user_id, session_ids in sessions_by_user.items():
            for session_id in session_ids:
                # Load session state to get details
                session_data = storage_manager.load_session_state(session_id)
                if session_data:
                    sessions.append(SessionDetailModel(
                        session_id=session_data.get('session_id', session_id),
                        user_id=session_data.get('user_id', user_id),
                        quiz_id=session_data.get('quiz_id', 'unknown'),
                        created_at=session_data.get('created_at', ''),
                        updated_at=session_data.get('updated_at', ''),
                        current_question_id=session_data.get('current_question_id'),
                        completed=session_data.get('completed', False)
                    ))

        logger.info(f"Admin retrieved {len(sessions)} sessions")
        return AllSessionsResponseModel(sessions=sessions)
    except Exception as e:
        logger.error(f"Failed to retrieve sessions: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve sessions: {str(e)}"
        )

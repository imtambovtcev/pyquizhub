"""
Quiz API Router for PyQuizHub.

This module provides API endpoints for quiz-taking functionality including:
- Starting quiz sessions 
- Processing answers
- Handling quiz flow
- Managing quiz state
- Token validation

The router handles quiz session management and interaction between users and 
quiz engine instances.
"""

from fastapi import APIRouter, HTTPException, Request, Depends
from pyquizhub.core.storage.storage_manager import StorageManager
from pyquizhub.core.engine.engine import QuizEngine
from pyquizhub.models import (
    NextQuestionResponseModel,
    AnswerRequestModel,
    StartQuizRequestModel,
    StartQuizResponseModel,
    SubmitAnswerResponseModel
)
import uuid
from datetime import datetime
from typing import Dict
import os
from pyquizhub.config.settings import get_logger

logger = get_logger(__name__)
logger.debug("Loaded router_quiz.py")
router = APIRouter()


def user_token_dependency(request: Request):
    """
    Dependency to validate user authentication token.

    Args:
        request: FastAPI Request object containing headers

    Raises:
        HTTPException: If user token is invalid
    """
    from pyquizhub.config.settings import get_config_manager
    token = request.headers.get("Authorization")
    config_manager = get_config_manager()
    expected_token = config_manager.get_token("user")
    if token != expected_token:
        raise HTTPException(status_code=403, detail="Invalid user token")


# In-memory dictionary to hold active quiz engines for each quiz_id
quiz_engines: Dict[str, QuizEngine] = {}


@router.post("/start_quiz", response_model=StartQuizResponseModel, dependencies=[Depends(user_token_dependency)])
def start_quiz(request: StartQuizRequestModel, req: Request):
    """
    Start a new quiz session for a user.

    Args:
        request: StartQuizRequestModel containing token and user ID
        req: FastAPI Request object containing application state

    Returns:
        StartQuizResponseModel: Initial quiz session data and first question

    Raises:
        HTTPException: If token is invalid or quiz not found
    """
    logger.debug(
        f"Starting quiz with token: {request.token} for user: {request.user_id}")
    # Retrieve the storage manager from app.state
    storage_manager: StorageManager = req.app.state.storage_manager

    # Validate token and get quiz ID
    quiz_id = storage_manager.get_quiz_id_by_token(request.token)
    if not quiz_id:
        logger.error(f"Invalid or expired token: {request.token}")
        raise HTTPException(status_code=404, detail="Invalid or expired token")

    # Check token type and remove if single-use
    token_type = storage_manager.get_token_type(request.token)
    if token_type == "single-use":
        storage_manager.remove_token(request.token)

    # Load quiz data
    quiz = storage_manager.get_quiz(quiz_id)

    # Initialize a QuizEngine for this quiz if not already present
    if quiz_id not in quiz_engines:
        quiz_engines[quiz_id] = QuizEngine(quiz)

    # Start a new session
    quiz_engine: QuizEngine = quiz_engines[quiz_id]
    session_id = str(uuid.uuid4())
    question = quiz_engine.start_quiz(session_id)

    logger.info(
        f"Started quiz session {session_id} for user {request.user_id} on quiz {quiz_id}")

    return StartQuizResponseModel(
        quiz_id=quiz_id,
        user_id=request.user_id,
        session_id=session_id,
        title=quiz["metadata"]["title"],
        question=question
    )


@router.post("/submit_answer/{quiz_id}", response_model=SubmitAnswerResponseModel, dependencies=[Depends(user_token_dependency)])
def submit_answer(quiz_id: str, request: AnswerRequestModel, req: Request):
    """
    Submit an answer and get the next question.

    Args:
        quiz_id: ID of the active quiz
        request: AnswerRequestModel containing answer data
        req: FastAPI Request object containing application state

    Returns:
        SubmitAnswerResponseModel: Next question or quiz completion status

    Raises:
        HTTPException: If quiz not found or answer invalid
    """
    logger.debug(
        f"Submitting answer for quiz_id: {quiz_id}, user_id: {request.user_id}")
    # Retrieve the storage manager from app.state
    storage_manager: StorageManager = req.app.state.storage_manager

    # Extract details from the request
    user_id = request.user_id
    session_id = request.session_id
    answer = request.answer["answer"]

    # Ensure the quiz engine exists for the given quiz_id
    if quiz_id not in quiz_engines:
        logger.error(
            f"Quiz not found for quiz_id: {quiz_id} with token: {request.headers.get('Authorization')}")
        raise HTTPException(status_code=404, detail="Quiz not found")

    # Process the answer using the QuizEngine
    quiz_engine: QuizEngine = quiz_engines[quiz_id]
    next_question = quiz_engine.answer_question(session_id, answer)

    # If there are no more questions, save the results
    if next_question["id"] is None:
        results = quiz_engine.get_results(session_id)
        results["timestamp"] = datetime.now().isoformat()
        storage_manager.add_results(user_id, quiz_id, session_id, results)
        logger.info(
            f"Quiz session {session_id} for user {user_id} on quiz {quiz_id} completed")

    return SubmitAnswerResponseModel(
        quiz_id=quiz_id,
        user_id=user_id,
        session_id=session_id,
        title=quiz_engine.quiz["metadata"]["title"],
        question=next_question
    )

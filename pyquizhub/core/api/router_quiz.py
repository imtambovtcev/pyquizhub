from fastapi import APIRouter, HTTPException, Request, Depends
from pyquizhub.core.storage.storage_manager import StorageManager
from pyquizhub.core.engine.engine import QuizEngine
from pyquizhub.models import (
    NextQuestionResponse,
    AnswerRequest,
    StartQuizRequest,
    StartQuizResponse,
    SubmitAnswerResponse
)
import uuid
from datetime import datetime
from typing import Dict
import os
from pyquizhub.config.config_utils import get_token_from_config, get_logger

logger = get_logger(__name__)
router = APIRouter()


def user_token_dependency(request: Request):
    token = request.headers.get("Authorization")
    expected_token = get_token_from_config("user")
    if token != expected_token:
        raise HTTPException(status_code=403, detail="Invalid user token")


# In-memory dictionary to hold active quiz engines for each quiz_id
quiz_engines: Dict[str, QuizEngine] = {}


@router.post("/start_quiz", response_model=StartQuizResponse, dependencies=[Depends(user_token_dependency)])
def start_quiz(request: StartQuizRequest, req: Request):
    """Start a quiz session using a token."""
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

    return StartQuizResponse(
        quiz_id=quiz_id,
        user_id=request.user_id,
        session_id=session_id,
        title=quiz["metadata"]["title"],
        question=question
    )


@router.post("/submit_answer/{quiz_id}", response_model=SubmitAnswerResponse, dependencies=[Depends(user_token_dependency)])
def submit_answer(quiz_id: str, request: AnswerRequest, req: Request):
    """Submit an answer for the current question and get the next question."""
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

    return SubmitAnswerResponse(
        quiz_id=quiz_id,
        user_id=user_id,
        session_id=session_id,
        title=quiz_engine.quiz["metadata"]["title"],
        question=next_question
    )

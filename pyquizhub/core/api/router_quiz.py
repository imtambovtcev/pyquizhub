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


def _is_final_message(question: dict) -> bool:
    """
    Check if a question is a final message (display-only, no answer required).

    Args:
        question: Question dictionary

    Returns:
        True if question type is 'final_message', False otherwise
    """
    if not question or not question.get("data"):
        return False
    return question["data"].get("type") == "final_message"


@router.post("/start_quiz", response_model=StartQuizResponseModel,
             dependencies=[Depends(user_token_dependency)])
def start_quiz(request: StartQuizRequestModel, req: Request):
    """
    Start a new quiz session for a user.

    Creates a new stateless engine instance, generates initial state,
    and persists the session to storage.

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
    quiz_data = storage_manager.get_quiz(quiz_id)

    # Create engine instance (stateless, created per request)
    engine = QuizEngine(quiz_data)

    # Get initial state from engine
    engine_state = engine.start_quiz()

    # Generate session ID (API layer responsibility)
    session_id = str(uuid.uuid4())

    # Get first question
    first_question = engine.get_current_question(engine_state)

    # Build complete session data (merge engine state + metadata)
    session_data = {
        # Metadata (API layer)
        "session_id": session_id,
        "user_id": request.user_id,
        "quiz_id": quiz_id,
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
        # Engine state
        "current_question_id": engine_state["current_question_id"],
        "scores": engine_state["scores"],
        "answers": engine_state["answers"],
        "completed": engine_state["completed"],
        "api_data": engine_state.get("api_data", {})
    }

    # Persist session immediately
    storage_manager.save_session_state(session_data)

    logger.info(
        f"Started quiz session {session_id} for user {request.user_id} on quiz {quiz_id}")

    # If first question is a final_message, auto-complete the quiz
    if _is_final_message(first_question):
        logger.info(f"First question is final_message, auto-completing quiz {quiz_id}")
        # Process final message (no answer needed)
        final_state = engine.answer_question(engine_state, None)

        # Save final results
        storage_manager.add_results(
            user_id=request.user_id,
            quiz_id=quiz_id,
            session_id=session_id,
            results={
                "scores": final_state["scores"],
                "answers": final_state["answers"],
                "timestamp": datetime.now().isoformat()
            }
        )
        storage_manager.delete_session_state(session_id)
        logger.info(f"Auto-completed quiz session {session_id}")

        # Return with completed status (question=None indicates completion)
        return StartQuizResponseModel(
            quiz_id=quiz_id,
            user_id=request.user_id,
            session_id=session_id,
            title=quiz_data["metadata"]["title"],
            question=first_question  # Show the final message
        )

    return StartQuizResponseModel(
        quiz_id=quiz_id,
        user_id=request.user_id,
        session_id=session_id,
        title=quiz_data["metadata"]["title"],
        question=first_question
    )


@router.post("/submit_answer/{quiz_id}",
             response_model=SubmitAnswerResponseModel,
             dependencies=[Depends(user_token_dependency)])
def submit_answer(quiz_id: str, request: AnswerRequestModel, req: Request):
    """
    Submit an answer and get the next question.

    Loads session state, creates stateless engine, processes answer,
    updates and persists the new state.

    Args:
        quiz_id: ID of the active quiz
        request: AnswerRequestModel containing answer data
        req: FastAPI Request object containing application state

    Returns:
        SubmitAnswerResponseModel: Next question or quiz completion status

    Raises:
        HTTPException: If session not found or answer invalid
    """
    logger.debug(
        f"Submitting answer for quiz_id: {quiz_id}, user_id: {request.user_id}")

    storage_manager: StorageManager = req.app.state.storage_manager

    # Extract details from the request
    user_id = request.user_id
    session_id = request.session_id
    answer = request.answer["answer"]

    # Load session state from storage
    session_data = storage_manager.load_session_state(session_id)
    logger.info(
        f"Loaded session data keys: {session_data.keys() if session_data else 'None'}")
    logger.info(
        f"Session data api_data: {session_data.get('api_data', 'NOT FOUND') if session_data else 'N/A'}")
    if not session_data:
        logger.error(f"Session {session_id} not found")
        raise HTTPException(status_code=404, detail="Session not found")

    # Verify quiz_id matches (security check)
    if session_data["quiz_id"] != quiz_id:
        logger.error(
            f"Quiz ID mismatch: expected {session_data['quiz_id']}, got {quiz_id}")
        raise HTTPException(status_code=400, detail="Quiz ID mismatch")

    # Extract engine state (without metadata)
    engine_state = {
        "current_question_id": session_data["current_question_id"],
        "scores": session_data["scores"],
        "answers": session_data["answers"],
        "completed": session_data["completed"],
        "api_data": session_data.get("api_data", {})
    }

    # Load quiz data
    quiz_data = storage_manager.get_quiz(quiz_id)

    # Create engine instance (fresh, per request)
    engine = QuizEngine(quiz_data)

    # Process answer (pure function, returns new state)
    try:
        new_engine_state = engine.answer_question(engine_state, answer)
    except ValueError as e:
        logger.error(f"Invalid answer for session {session_id}: {e}")
        raise HTTPException(status_code=400, detail=str(e))

    # Get next question
    next_question = engine.get_current_question(new_engine_state)

    # Update session data with new engine state
    session_data.update({
        "current_question_id": new_engine_state["current_question_id"],
        "scores": new_engine_state["scores"],
        "answers": new_engine_state["answers"],
        "completed": new_engine_state["completed"],
        "api_data": new_engine_state.get("api_data", {}),
        "updated_at": datetime.now().isoformat()
    })

    # Save updated session state
    storage_manager.update_session_state(session_id, session_data)

    # Check if next question is a final_message
    if next_question and _is_final_message(next_question):
        logger.info(f"Next question is final_message, auto-completing quiz {quiz_id}")
        # Process final message (no answer needed)
        final_state = engine.answer_question(new_engine_state, None)

        # Save final results
        storage_manager.add_results(
            user_id=user_id,
            quiz_id=quiz_id,
            session_id=session_id,
            results={
                "scores": final_state["scores"],
                "answers": final_state["answers"],
                "timestamp": datetime.now().isoformat()
            }
        )
        storage_manager.delete_session_state(session_id)
        logger.info(f"Auto-completed quiz session {session_id} after final_message")

        # Return the final message question (with completed=True implicitly)
        return SubmitAnswerResponseModel(
            quiz_id=quiz_id,
            user_id=user_id,
            session_id=session_id,
            title=quiz_data["metadata"]["title"],
            question=next_question  # Show the final message, next call will return None
        )

    # If completed, save final results and clean up session
    if new_engine_state["completed"]:
        storage_manager.add_results(
            user_id=user_id,
            quiz_id=quiz_id,
            session_id=session_id,
            results={
                "scores": new_engine_state["scores"],
                "answers": new_engine_state["answers"],
                "timestamp": datetime.now().isoformat()
            }
        )
        storage_manager.delete_session_state(session_id)
        logger.info(
            f"Completed quiz session {session_id} for user {user_id} on quiz {quiz_id}")

    return SubmitAnswerResponseModel(
        quiz_id=quiz_id,
        user_id=user_id,
        session_id=session_id,
        title=quiz_data["metadata"]["title"],
        question=next_question
    )

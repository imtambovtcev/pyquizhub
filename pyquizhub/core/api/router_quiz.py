from fastapi import APIRouter, HTTPException, Request
from pyquizhub.core.storage.storage_manager import StorageManager
from pyquizhub.core.engine.engine import QuizEngine
from pyquizhub.core.api.models import (
    NextQuestionResponse,
    AnswerRequest
)
import uuid
from datetime import datetime
from typing import Dict
import os

router = APIRouter()

# In-memory dictionary to hold active quiz engines for each quiz_id
quiz_engines: Dict[str, QuizEngine] = {}


@router.post("/start_quiz", response_model=NextQuestionResponse)
def start_quiz(token: str, user_id: str, request: Request):
    """Start a quiz session using a token."""
    # Retrieve the storage manager from app.state
    storage_manager: StorageManager = request.app.state.storage_manager

    # Validate token and get quiz ID
    quiz_id = storage_manager.get_quiz_id_by_token(token)
    if not quiz_id:
        raise HTTPException(status_code=404, detail="Invalid or expired token")

    # Check token type and remove if single-use
    token_type = storage_manager.get_token_type(token)
    if token_type == "single-use":
        storage_manager.remove_token(token)

    # Load quiz data
    quiz = storage_manager.get_quiz(quiz_id)

    # Initialize a QuizEngine for this quiz if not already present
    if quiz_id not in quiz_engines:
        quiz_engines[quiz_id] = QuizEngine(quiz)

    # Start a new session
    quiz_engine: QuizEngine = quiz_engines[quiz_id]
    session_id = str(uuid.uuid4())
    question = quiz_engine.start_quiz(session_id)

    return {
        "quiz_id": quiz_id,
        "user_id": user_id,
        "session_id": session_id,
        "title": quiz["metadata"]["title"],
        "question": question
    }


@router.post("/submit_answer/{quiz_id}", response_model=NextQuestionResponse)
def submit_answer(quiz_id: str, request: AnswerRequest, req: Request):
    """Submit an answer for the current question and get the next question."""
    # Retrieve the storage manager from app.state
    storage_manager: StorageManager = req.app.state.storage_manager

    # Extract details from the request
    user_id = request.user_id
    session_id = request.session_id
    answer = request.answer["answer"]

    # Ensure the quiz engine exists for the given quiz_id
    if quiz_id not in quiz_engines:
        raise HTTPException(status_code=404, detail="Quiz not found")

    # Process the answer using the QuizEngine
    quiz_engine: QuizEngine = quiz_engines[quiz_id]
    next_question = quiz_engine.answer_question(session_id, answer)

    # If there are no more questions, save the results
    if next_question["id"] is None:
        results = quiz_engine.get_results(session_id)
        results["timestamp"] = datetime.now().isoformat()
        storage_manager.add_results(user_id, quiz_id, session_id, results)

    return {
        "quiz_id": quiz_id,
        "user_id": user_id,
        "session_id": session_id,
        "title": quiz_engine.quiz["metadata"]["title"],
        "question": next_question
    }

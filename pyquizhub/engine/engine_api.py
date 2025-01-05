from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from typing import Dict, List, Optional
from pyquizhub.storage.file_storage import FileStorageManager
from pyquizhub.storage.sql_storage import SQLStorageManager
from pyquizhub.storage.storage_manager import StorageManager
from pyquizhub.engine.json_validator import QuizJSONValidator
import uuid
import yaml
from pyquizhub.utils import generate_token as generate_quiz_token
from pyquizhub.engine.engine import QuizEngine

# Load configuration
CONFIG_PATH = "pyquizhub/config/config.yaml"
with open(CONFIG_PATH, "r") as f:
    config = yaml.safe_load(f)

# Initialize storage manager


def get_storage_manager() -> StorageManager:
    storage_type = config["storage"]["type"]
    if storage_type == "file":
        return FileStorageManager(config["storage"]["file"]["base_dir"])
    elif storage_type == "sql":
        return SQLStorageManager(config["storage"]["sql"]["connection_string"])
    else:
        raise ValueError(f"Unsupported storage type: {storage_type}")


storage_manager: StorageManager = get_storage_manager()

# Pool of quiz engines for active quizzes
quiz_engines: dict[str:QuizEngine] = {}

app = FastAPI()

# Pydantic models


class Metadata(BaseModel):
    title: str
    description: Optional[str] = None
    author: Optional[str] = None
    version: Optional[str] = None


class Quiz(BaseModel):
    metadata: Metadata
    scores: Dict[str, int]
    questions: List[Dict]
    transitions: Dict[str, List[Dict]]


class TokenRequest(BaseModel):
    quiz_id: str
    type: str  # "permanent" or "single-use"


class QuizResponse(BaseModel):
    quiz_id: str
    title: str


class TokenResponse(BaseModel):
    token: str


class AnswerRequest(BaseModel):
    user_id: str
    answer: Dict[str, str]


class ResultResponse(BaseModel):
    scores: Dict[str, int]
    answers: Dict[str, str]


class NextQuestionResponse(BaseModel):
    quiz_id: str
    title: str
    question: Optional[Dict] = None


class CreateQuizRequest(BaseModel):
    quiz: Quiz
    creator_id: str


class ParticipatedUsersResponse(BaseModel):
    user_ids: List[str]


def _get_results(quiz_id: str, user_id: str):
    """Creator: Get the results for a user."""
    results = storage_manager.get_results(user_id, quiz_id)
    if not results:
        raise HTTPException(status_code=404, detail="Results not found")
    return results


def _get_participated_users(quiz_id: str):
    """Creator: Get all users who participated in a quiz."""
    user_ids = storage_manager.get_participated_users(quiz_id)
    return {"user_ids": user_ids}

# Routes


@app.get("/")
def read_root():
    return {"message": "Welcome to the Quiz Engine API"}


# Admin commands

@app.post("/admin/create_quiz", response_model=QuizResponse)
def admin_create_quiz(request: CreateQuizRequest):
    """Admin: Create a new quiz."""
    quiz_id = f"quiz_{str(uuid.uuid4())[:8]}"
    creator_id = request.creator_id

    # Validate quiz
    validation_result = QuizJSONValidator.validate(request.quiz.dict())
    if validation_result["errors"]:
        raise HTTPException(
            status_code=400, detail=validation_result["errors"])

    quiz_data = request.quiz.dict()
    quiz_data["creator_id"] = creator_id
    storage_manager.add_quiz(quiz_id, quiz_data, creator_id)
    return {"quiz_id": quiz_id, "title": request.quiz.metadata.title}


@app.get("/admin/quiz/{quiz_id}")
def admin_get_quiz(quiz_id: str):
    """Admin: Retrieve a quiz by its ID."""
    try:
        quiz = storage_manager.get_quiz(quiz_id)
        return quiz
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Quiz not found")


@app.get("/admin/quizzes")
def admin_get_all_quizzes():
    """Admin: Retrieve all quizzes."""
    return storage_manager.get_all_quizzes()


@app.get("/admin/tokens")
def admin_get_all_tokens():
    """Admin: Retrieve all tokens."""
    return storage_manager.get_all_tokens()


@app.get("/admin/results/{quiz_id}/{user_id}", response_model=ResultResponse)
def get_results(quiz_id: str, user_id: str):
    """Admin: Get the results for a user."""
    return _get_results(quiz_id, user_id)


@app.get("/admin/participated_users/{quiz_id}", response_model=ParticipatedUsersResponse)
def get_participated_users(quiz_id: str):
    """Admin: Get all users who participated in a quiz."""
    return _get_participated_users(quiz_id)


# Creator commands


@app.post("/creator/create_quiz", response_model=QuizResponse)
def create_quiz(request: CreateQuizRequest):
    """Creator: Create a new quiz."""
    quiz_id = f"quiz_{str(uuid.uuid4())[:8]}"
    creator_id = request.creator_id

    # Check if user has permission to create quizzes
    if not storage_manager.user_has_permission_for_quiz_creation(creator_id):
        raise HTTPException(
            status_code=403, detail="User does not have permission to create quizzes")

    # Validate quiz
    validation_result = QuizJSONValidator.validate(request.quiz.dict())
    if validation_result["errors"]:
        raise HTTPException(
            status_code=400, detail=validation_result["errors"])

    quiz_data = request.quiz.dict()
    quiz_data["creator_id"] = creator_id
    storage_manager.add_quiz(quiz_id, quiz_data, creator_id)
    return {"quiz_id": quiz_id, "title": request.quiz.metadata.title}


@app.post("/creator/generate_token", response_model=TokenResponse)
def generate_token(request: TokenRequest):
    """Creator: Generate a token for accessing a quiz."""
    quiz_id = request.quiz_id
    try:
        storage_manager.get_quiz(quiz_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Quiz not found")

    token = str(uuid.uuid4())[:8].upper()
    token_data = {"token": token, "quiz_id": quiz_id, "type": request.type}
    storage_manager.add_tokens([token_data])

    return {"token": token}


@app.get("/creator/results/{quiz_id}/{user_id}", response_model=ResultResponse)
def get_results(quiz_id: str, user_id: str):
    """Creator: Get the results for a user."""
    return _get_results(quiz_id, user_id)


@app.get("/creator/participated_users/{quiz_id}", response_model=ParticipatedUsersResponse)
def get_participated_users(quiz_id: str):
    """Creator: Get all users who participated in a quiz."""
    return _get_participated_users(quiz_id)


# User commands

@app.post("/start_quiz", response_model=NextQuestionResponse)
def start_quiz(token: str, user_id: str):
    """User: Start a quiz using a token."""
    quiz_id = storage_manager.get_quiz_id_by_token(token)

    if not quiz_id:
        raise HTTPException(status_code=404, detail="Invalid or expired token")

    token_type = storage_manager.get_token_type(token)
    if token_type == "single-use":
        storage_manager.remove_token(token)

    quiz = storage_manager.get_quiz(quiz_id)
    if quiz_id not in quiz_engines:
        quiz_engines[quiz_id] = QuizEngine(quiz)

    quiz_engine: QuizEngine = quiz_engines[quiz_id]

    question = quiz_engine.start_quiz(user_id)
    return {
        "quiz_id": quiz_id,
        "title": quiz["metadata"]["title"],
        "question": question
    }


@app.post("/submit_answer/{quiz_id}", response_model=NextQuestionResponse)
def submit_answer(quiz_id: str, request: AnswerRequest):
    """User: Submit an answer for a quiz question."""
    user_id = request.user_id
    answer = request.answer['answer']

    if quiz_id not in quiz_engines:
        raise HTTPException(status_code=404, detail="Quiz not found")

    quiz_engine: QuizEngine = quiz_engines[quiz_id]

    next_question = quiz_engine.answer_question(user_id, answer)

    if next_question["id"] is None:
        # Quiz is complete
        storage_manager.add_results(
            user_id, quiz_id, quiz_engine.get_results(user_id))

    return {
        "quiz_id": quiz_id,
        "title": quiz_engine.quiz["metadata"]["title"],
        "question": next_question
    }

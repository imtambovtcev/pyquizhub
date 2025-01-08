from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError, ResponseValidationError
from pydantic import BaseModel
from typing import Dict, List, Optional, Any
from pyquizhub.core.storage.file_storage import FileStorageManager
from pyquizhub.core.storage.sql_storage import SQLStorageManager
from pyquizhub.core.storage.storage_manager import StorageManager
from pyquizhub.core.engine.json_validator import QuizJSONValidator
import uuid
import yaml
from pyquizhub.utils import generate_quiz_token, generate_quiz_id
from pyquizhub.core.engine.engine import QuizEngine
from datetime import datetime
import os

app = FastAPI()

# Dependency: Load configuration dynamically


def load_config(config_path: str = None) -> Dict:
    """Load configuration from the specified path."""
    if config_path is None:
        config_path = os.getenv("PYQUIZHUB_CONFIG_PATH", os.path.abspath(os.path.join(
            os.path.dirname(__file__), "../../config/config.yaml")))
    try:
        with open(config_path, "r") as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        raise RuntimeError(f"Configuration file not found at {config_path}")
    except Exception as e:
        raise RuntimeError(f"Error loading configuration: {e}")

# Initialize storage manager


def get_storage_manager() -> StorageManager:
    """Initialize the storage manager based on the configuration."""
    config = load_config()
    storage_type = config["storage"]["type"]
    if storage_type == "file":
        return FileStorageManager(config["storage"]["file"]["base_dir"])
    elif storage_type == "sql":
        return SQLStorageManager(config["storage"]["sql"]["connection_string"])
    else:
        raise ValueError(f"Unsupported storage type: {storage_type}")


# Pool of quiz engines for active quizzes
quiz_engines: Dict[str, QuizEngine] = {}


@app.exception_handler(ResponseValidationError)
async def response_validation_exception_handler(request: Request, exc: ResponseValidationError):
    return JSONResponse(
        status_code=422,
        content={"detail": "Response validation error",
                 "errors": exc.errors()},
    )


@app.exception_handler(RequestValidationError)
async def request_validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={"detail": "Request validation error", "errors": exc.errors()},
    )

# Pydantic models


class Metadata(BaseModel):
    title: str
    description: Optional[str] = None
    author: Optional[str] = None
    version: Optional[str] = None


class Quiz(BaseModel):
    metadata: Metadata
    scores: Dict[str, float]
    questions: List[Dict]
    transitions: Dict[str, List[Dict]]


class TokenRequest(BaseModel):
    quiz_id: str
    type: str  # "permanent" or "single-use"


class QuizData(BaseModel):
    title: str
    questions: List[Dict[str, Any]]


class QuizCreationResponse(BaseModel):
    quiz_id: str
    title: str


class QuizDetailResponse(BaseModel):
    quiz_id: str
    title: str
    creator_id: str
    data: QuizData


class TokenResponse(BaseModel):
    token: str


class AnswerRequest(BaseModel):
    user_id: str
    session_id: str
    answer: Dict[str, str]


class ResultResponse(BaseModel):
    scores: Dict[str, int]
    answers: Dict[str, str]


class NextQuestionResponse(BaseModel):
    quiz_id: str
    user_id: str
    session_id: str
    title: str
    question: Optional[Dict] = None


class CreateQuizRequest(BaseModel):
    quiz: Quiz
    creator_id: str


class ParticipatedUsersResponse(BaseModel):
    user_ids: List[str]


class ConfigPathResponse(BaseModel):
    config_path: str
    config_data: Dict[str, Any]

# Helper functions


def _get_results(storage_manager: StorageManager, quiz_id: str, user_id: str, session_id: str):
    results = storage_manager.get_results(user_id, quiz_id, session_id)
    if not results:
        raise HTTPException(status_code=404, detail="Results not found")
    return results


def _get_participated_users(storage_manager: StorageManager, quiz_id: str):
    user_ids = storage_manager.get_participated_users(quiz_id)
    return {"user_ids": user_ids}


def _create_quiz(storage_manager: StorageManager, quiz: Quiz, creator_id: str) -> QuizCreationResponse:
    validation_result = QuizJSONValidator.validate(quiz.dict())
    if validation_result["errors"]:
        raise HTTPException(
            status_code=400, detail=validation_result["errors"])

    quiz_id = generate_quiz_id(quiz.metadata.title)
    quiz_data = quiz.dict()
    quiz_data["creator_id"] = creator_id
    storage_manager.add_quiz(quiz_id, quiz_data, creator_id)
    return QuizCreationResponse(quiz_id=quiz_id, title=quiz.metadata.title)


def _generate_token(storage_manager: StorageManager, quiz_id: str, token_type: str) -> TokenResponse:
    token = generate_quiz_token()
    token_data = {"token": token, "quiz_id": quiz_id, "type": token_type}
    storage_manager.add_tokens([token_data])
    return TokenResponse(token=token)

# Routes


@app.get("/")
def read_root():
    return {"message": "Welcome to the Quiz Engine API"}


@app.post("/admin/create_quiz", response_model=QuizCreationResponse)
def admin_create_quiz(request: CreateQuizRequest):
    storage_manager = get_storage_manager()
    return _create_quiz(storage_manager, request.quiz, request.creator_id)


@app.post("/admin/generate_token", response_model=TokenResponse)
def admin_generate_token(request: TokenRequest):
    storage_manager = get_storage_manager()
    return _generate_token(storage_manager, request.quiz_id, request.type)


@app.get("/admin/quiz/{quiz_id}", response_model=QuizDetailResponse)
def admin_get_quiz(quiz_id: str):
    storage_manager = get_storage_manager()
    try:
        quiz = storage_manager.get_quiz(quiz_id)
        return {
            "quiz_id": quiz_id,
            "title": quiz["metadata"]["title"],
            "creator_id": quiz["creator_id"],
            "data": quiz["data"]
        }
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Quiz not found")


@app.get("/admin/results/{quiz_id}/{user_id}", response_model=ResultResponse)
def get_results(quiz_id: str, user_id: str, session_id: str):
    storage_manager = get_storage_manager()
    return _get_results(storage_manager, quiz_id, user_id, session_id)


@app.get("/admin/participated_users/{quiz_id}", response_model=ParticipatedUsersResponse)
def get_participated_users(quiz_id: str):
    storage_manager = get_storage_manager()
    return _get_participated_users(storage_manager, quiz_id)


@app.get("/admin/config", response_model=ConfigPathResponse)
def get_config():
    config_path = os.getenv("PYQUIZHUB_CONFIG_PATH", os.path.abspath(os.path.join(
        os.path.dirname(__file__), "../../config/config.yaml")))
    config_data = load_config(config_path)
    return ConfigPathResponse(config_path=config_path, config_data=config_data)


@app.post("/start_quiz", response_model=NextQuestionResponse)
def start_quiz(token: str, user_id: str):
    storage_manager = get_storage_manager()
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
    session_id = str(uuid.uuid4())
    question = quiz_engine.start_quiz(session_id)
    return {
        "quiz_id": quiz_id,
        "user_id": user_id,
        "session_id": session_id,
        "title": quiz["metadata"]["title"],
        "question": question
    }


@app.post("/submit_answer/{quiz_id}", response_model=NextQuestionResponse)
def submit_answer(quiz_id: str, request: AnswerRequest):
    storage_manager = get_storage_manager()
    user_id = request.user_id
    session_id = request.session_id
    answer = request.answer["answer"]

    if quiz_id not in quiz_engines:
        raise HTTPException(status_code=404, detail="Quiz not found")

    quiz_engine: QuizEngine = quiz_engines[quiz_id]
    next_question = quiz_engine.answer_question(session_id, answer)

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

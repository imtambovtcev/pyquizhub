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


storage_manager = get_storage_manager()

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


class CreateQuizRequest(BaseModel):
    quiz: Quiz
    creator_id: str


# In-memory cache for single-use tokens
single_use_tokens = set()

# Routes


@app.get("/")
def read_root():
    return {"message": "Welcome to the Quiz Engine API"}


@app.post("/create_quiz", response_model=QuizResponse)
def create_quiz(request: CreateQuizRequest):
    """Create a new quiz."""
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
    storage_manager.add_quiz(quiz_id, quiz_data)
    return {"quiz_id": quiz_id, "title": request.quiz.metadata.title}


@app.get("/quiz/{quiz_id}")
def get_quiz(quiz_id: str):
    """Retrieve a quiz by its ID."""
    try:
        quiz = storage_manager.get_quiz(quiz_id)
        return quiz
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Quiz not found")


@app.post("/generate_token", response_model=TokenResponse)
def generate_token(request: TokenRequest):
    """Generate a token for accessing a quiz."""
    quiz_id = request.quiz_id
    try:
        storage_manager.get_quiz(quiz_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Quiz not found")

    token = str(uuid.uuid4())[:8].upper()
    if request.type == "single-use":
        single_use_tokens.add(token)
    elif request.type == "permanent":
        tokens = storage_manager.get_tokens()
        tokens.append(
            {"token": token, "quiz_id": quiz_id, "type": "permanent"})
        storage_manager.add_tokens(tokens)
    else:
        raise HTTPException(status_code=400, detail="Invalid token type")

    return {"token": token}


@app.post("/start_quiz")
def start_quiz(token: str, user_id: str):
    """Start a quiz using a token."""
    tokens = storage_manager.get_tokens()
    token_data = next((t for t in tokens if t["token"] == token), None)

    if not token_data and token not in single_use_tokens:
        raise HTTPException(status_code=404, detail="Invalid or expired token")

    if token in single_use_tokens:
        single_use_tokens.remove(token)

    quiz_id = token_data["quiz_id"] if token_data else None
    quiz = storage_manager.get_quiz(quiz_id)
    return {"quiz_id": quiz_id, "title": quiz["metadata"]["title"], "questions": quiz["questions"]}


@app.post("/submit_answer/{quiz_id}", response_model=ResultResponse)
def submit_answer(quiz_id: str, request: AnswerRequest):
    """Submit an answer for a quiz question."""
    user_id = request.user_id
    user_results = storage_manager.get_results(user_id, quiz_id) or {
        "scores": {}, "answers": {}}

    # Update answers
    user_results["answers"].update(request.answer)

    # Update scores based on the submitted answer
    quiz = storage_manager.get_quiz(quiz_id)
    for question in quiz["questions"]:
        if question["id"] in request.answer:
            answer = request.answer[question["id"]]
            for update in question.get("score_updates", []):
                condition = update["condition"]
                if eval(condition, {}, {"answer": answer, **user_results["scores"]}):
                    for score, value in update["update"].items():
                        user_results["scores"][score] = eval(
                            value, {}, user_results["scores"])

    storage_manager.add_results(user_id, quiz_id, user_results)
    return user_results


@app.get("/results/{quiz_id}/{user_id}", response_model=ResultResponse)
def get_results(quiz_id: str, user_id: str):
    """Get the results for a user."""
    results = storage_manager.get_results(user_id, quiz_id)
    if not results:
        raise HTTPException(status_code=404, detail="Results not found")
    return results


@app.post("/add_quiz", response_model=QuizResponse)
def add_quiz(quiz: Quiz):
    """Add an existing quiz to the storage."""
    quiz_id = generate_quiz_token()
    # Validate quiz
    validation_result = QuizJSONValidator.validate(quiz.dict())
    if validation_result["errors"]:
        raise HTTPException(
            status_code=400, detail=validation_result["errors"])

    try:
        storage_manager.get_quiz(quiz_id)
        raise HTTPException(
            status_code=400, detail="Quiz with this ID already exists")
    except FileNotFoundError:
        storage_manager.add_quiz(quiz_id, quiz.dict())
        return {"quiz_id": quiz_id, "title": quiz.metadata.title}

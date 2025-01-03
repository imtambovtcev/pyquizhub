from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from typing import Dict, List, Optional
from pyquizhub.storage.file_storage import FileStorageManager
from pyquizhub.storage.sql_storage import SQLStorageManager
from pyquizhub.storage.storage_manager import StorageManager
import uuid
import os
import yaml

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


class Quiz(BaseModel):
    title: str
    questions: List[Dict]
    metadata: Optional[Dict] = None


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
    answer: Dict


class ResultResponse(BaseModel):
    scores: Dict
    answers: Dict


# In-memory cache for single-use tokens
single_use_tokens = set()

# Routes


@app.get("/")
def read_root():
    return {"message": "Welcome to the Quiz Engine API"}


@app.post("/create_quiz", response_model=QuizResponse)
def create_quiz(quiz: Quiz):
    """Create a new quiz."""
    quiz_id = f"quiz_{str(uuid.uuid4())[:8]}"
    storage_manager.save_quiz(quiz_id, quiz.dict())
    return {"quiz_id": quiz_id, "title": quiz.title}


@app.get("/quiz/{quiz_id}")
def get_quiz(quiz_id: str):
    """Retrieve a quiz by its ID."""
    try:
        quiz = storage_manager.load_quiz(quiz_id)
        return quiz
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Quiz not found")


@app.post("/generate_token", response_model=TokenResponse)
def generate_token(request: TokenRequest):
    """Generate a token for accessing a quiz."""
    quiz_id = request.quiz_id
    try:
        storage_manager.load_quiz(quiz_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Quiz not found")

    token = str(uuid.uuid4())[:8].upper()
    if request.type == "single-use":
        single_use_tokens.add(token)
    elif request.type == "permanent":
        tokens = storage_manager.load_tokens()
        tokens.append(
            {"token": token, "quiz_id": quiz_id, "type": "permanent"})
        storage_manager.save_tokens(tokens)
    else:
        raise HTTPException(status_code=400, detail="Invalid token type")

    return {"token": token}


@app.post("/start_quiz")
def start_quiz(token: str, user_id: str):
    """Start a quiz using a token."""
    tokens = storage_manager.load_tokens()
    token_data = next((t for t in tokens if t["token"] == token), None)

    if not token_data and token not in single_use_tokens:
        raise HTTPException(status_code=404, detail="Invalid or expired token")

    if token in single_use_tokens:
        single_use_tokens.remove(token)

    quiz_id = token_data["quiz_id"] if token_data else None
    quiz = storage_manager.load_quiz(quiz_id)
    return {"quiz_id": quiz_id, "title": quiz["title"], "questions": quiz["questions"]}


@app.post("/submit_answer/{quiz_id}", response_model=ResultResponse)
def submit_answer(quiz_id: str, request: AnswerRequest):
    """Submit an answer for a quiz question."""
    user_id = request.user_id
    user_results = storage_manager.load_results(user_id, quiz_id) or {
        "scores": {}, "answers": {}}

    # Update answers
    user_results["answers"].update(request.answer)

    # Update scores based on the submitted answer
    quiz = storage_manager.load_quiz(quiz_id)
    for question in quiz["questions"]:
        if question["id"] in request.answer:
            answer = request.answer[question["id"]]
            for update in question.get("score_updates", []):
                condition = update["condition"]
                if eval(condition, {}, {"answer": answer, **user_results["scores"]}):
                    for score, value in update["update"].items():
                        user_results["scores"][score] = user_results["scores"].get(
                            score, 0) + value

    storage_manager.save_results(user_id, quiz_id, user_results)
    return user_results


@app.get("/results/{quiz_id}/{user_id}", response_model=ResultResponse)
def get_results(quiz_id: str, user_id: str):
    """Get the results for a user."""
    results = storage_manager.load_results(user_id, quiz_id)
    if not results:
        raise HTTPException(status_code=404, detail="Results not found")
    return results

from pydantic import BaseModel
from typing import Dict, List, Optional, Any


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

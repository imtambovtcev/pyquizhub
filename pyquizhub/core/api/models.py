from pydantic import BaseModel
from typing import Optional, Any, List, Dict


class Metadata(BaseModel):
    title: str
    description: Optional[str] = None
    author: Optional[str] = None
    version: Optional[str] = None


class Quiz(BaseModel):
    metadata: Metadata
    scores: dict[str, float]
    questions: list[dict]
    transitions: dict[str, list[dict]]


class TokenRequest(BaseModel):
    quiz_id: str
    type: str  # "permanent" or "single-use"


class QuizData(BaseModel):
    title: str
    questions: list[dict[str, Any]]


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
    answer: dict[str, str]


class ResultDetailResponse(BaseModel):
    user_id: str
    quiz_id: str
    session_id: str
    scores: dict[str, float]
    answers: list[dict[str, Any]]
    timestamp: str


class ResultResponse(BaseModel):
    results: dict[str, dict[str, ResultDetailResponse]]


class Question(BaseModel):
    id: int | None
    data: dict[str, Any] | None
    error: Optional[str] = None


class NextQuestionResponse(BaseModel):
    quiz_id: str
    user_id: str
    session_id: str
    title: str
    question: Optional[Question | None] = None


class CreateQuizRequest(BaseModel):
    quiz: Quiz
    creator_id: str


class ParticipatedUsersResponse(BaseModel):
    user_ids: list[str]


class ConfigPathResponse(BaseModel):
    config_path: str
    config_data: dict[str, Any]


class AllQuizzesResponse(BaseModel):
    quizzes: Dict[str, Any]


class AllTokensResponse(BaseModel):
    tokens: Dict[str, List[Dict[str, Any]]]

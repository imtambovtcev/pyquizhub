from pydantic import BaseModel, model_validator
from typing import Optional, Any


# Metadata Models
class MetadataModel(BaseModel):
    title: str
    description: Optional[str] = None
    author: Optional[str] = None
    version: Optional[str] = None


# Quiz Models
class QuizModel(BaseModel):
    metadata: MetadataModel
    questions: list[dict]
    transitions: dict[str, list[dict]]
    # Support new (variables) format only
    variables: dict[str, dict]
    api_integrations: Optional[list[dict]] = None


class QuizContentModel(BaseModel):
    title: str
    questions: list[dict[str, Any]]


class QuizCreationResponseModel(BaseModel):
    quiz_id: str
    title: str


class QuizDetailResponseModel(BaseModel):
    quiz_id: str
    title: str
    creator_id: str
    # Changed from QuizContentModel to accept full quiz structure
    data: dict[str, Any]


class CreateQuizRequestModel(BaseModel):
    quiz: QuizModel
    creator_id: str


class AllQuizzesResponseModel(BaseModel):
    quizzes: dict[str, Any]


# Token Models
class TokenRequestModel(BaseModel):
    quiz_id: str
    type: str  # "permanent" or "single-use"


class TokenResponseModel(BaseModel):
    token: str


class AllTokensResponseModel(BaseModel):
    tokens: dict[str, list[dict[str, Any]]]


# Answer Models
class AnswerRequestModel(BaseModel):
    user_id: str
    session_id: str
    answer: dict[str, str | int | float | list | None]


# Question Models
class QuestionModel(BaseModel):
    id: int | None
    data: dict[str, Any] | None
    error: Optional[str] = None


class SubmitAnswerResponseModel(BaseModel):
    quiz_id: str
    user_id: str
    session_id: str
    title: str
    question: Optional[QuestionModel] = None


# Result Models
class QuizResultDetailModel(BaseModel):
    user_id: str
    quiz_id: str
    session_id: str
    scores: dict[str, float]
    answers: list[dict[str, Any]]
    timestamp: str


class QuizResultResponseModel(BaseModel):
    results: dict[str, dict[str, QuizResultDetailModel]]


class NextQuestionResponseModel(BaseModel):
    quiz_id: str
    user_id: str
    session_id: str
    title: str
    question: Optional[QuestionModel | None] = None


# User Models
class ParticipatedUsersResponseModel(BaseModel):
    user_ids: list[str]


# Config Models
class ConfigPathResponseModel(BaseModel):
    config_path: Optional[str] = None
    config_data: dict[str, Any]


# Start Quiz Models
class StartQuizRequestModel(BaseModel):
    token: str
    user_id: str


class StartQuizResponseModel(BaseModel):
    quiz_id: str
    user_id: str
    session_id: str
    title: str
    question: QuestionModel


# Admin Models
class AllUsersResponseModel(BaseModel):
    users: dict[str, Any]


class AllResultsResponseModel(BaseModel):
    results: dict[str, dict[str, Any]]


class SessionDetailModel(BaseModel):
    session_id: str
    user_id: str
    quiz_id: str
    created_at: str
    updated_at: str
    current_question_id: Optional[int] = None
    completed: bool = False


class AllSessionsResponseModel(BaseModel):
    sessions: list[SessionDetailModel]

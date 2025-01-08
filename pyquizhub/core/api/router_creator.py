from fastapi import APIRouter, HTTPException, Request
from pyquizhub.core.storage.storage_manager import StorageManager
from pyquizhub.core.engine.json_validator import QuizJSONValidator
from pyquizhub.utils import generate_quiz_token, generate_quiz_id
from pyquizhub.core.api.models import (
    CreateQuizRequest,
    QuizCreationResponse,
    TokenRequest,
    TokenResponse
)

router = APIRouter()


def create_quiz_logic(storage_manager: StorageManager, request: CreateQuizRequest) -> QuizCreationResponse:
    """
    Logic for creating a quiz. Shared between creator and admin.
    """
    # Validate the quiz structure
    validation_result = QuizJSONValidator.validate(request.quiz.dict())
    if validation_result["errors"]:
        raise HTTPException(
            status_code=400, detail=validation_result["errors"])

    # Generate an ID and store it
    quiz_id = generate_quiz_id(request.quiz.metadata.title)
    quiz_data = request.quiz.dict()
    quiz_data["creator_id"] = request.creator_id
    storage_manager.add_quiz(quiz_id, quiz_data, request.creator_id)

    return QuizCreationResponse(quiz_id=quiz_id, title=request.quiz.metadata.title)


def generate_token_logic(storage_manager: StorageManager, request: TokenRequest) -> TokenResponse:
    """
    Logic for generating a quiz token. Shared between creator and admin.
    """
    token = generate_quiz_token()
    token_data = {"token": token,
                  "quiz_id": request.quiz_id, "type": request.type}
    storage_manager.add_tokens([token_data])
    return TokenResponse(token=token)


@router.post("/create_quiz", response_model=QuizCreationResponse)
def creator_create_quiz(request: CreateQuizRequest, req: Request):
    """
    Endpoint for creators to create a quiz.
    """
    storage_manager: StorageManager = req.app.state.storage_manager
    return create_quiz_logic(storage_manager, request)


@router.post("/generate_token", response_model=TokenResponse)
def creator_generate_token(request: TokenRequest, req: Request):
    """
    Endpoint for creators to generate tokens.
    """
    storage_manager: StorageManager = req.app.state.storage_manager
    return generate_token_logic(storage_manager, request)

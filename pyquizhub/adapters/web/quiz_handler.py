import requests
from fastapi import HTTPException
from pyquizhub.config.config_utils import get_logger
from pyquizhub.core.api.models import StartQuizRequest, SubmitAnswerRequest
import json

logger = get_logger(__name__)
print(f'{logger.hasHandlers() = }')
print(f'{logger.handlers = }')
print(f'{logger.handlers[1].baseFilename = }')


class QuizHandler:
    def __init__(self, config):
        self.base_url = config["api"]["base_url"]

    def get_headers(self):
        return {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

    async def start_quiz(self, request: StartQuizRequest):
        try:
            logger.info(
                f"Starting quiz for user {request.user_id} with token {request.token}")
            logger.debug(f"Request URL: {self.base_url}/quiz/start_quiz")
            logger.debug(
                f"Request params: token={request.token}, user_id={request.user_id}")
            response = requests.post(
                f"{self.base_url}/quiz/start_quiz",
                params={"token": request.token, "user_id": request.user_id},
                headers=self.get_headers()
            )

            if response.status_code == 200:
                logger.info(f"Received response: {response.json()}")
                return response.json()

            logger.error(
                f"Failed to start quiz: {response.json().get('detail', 'Unknown error')}")
            raise HTTPException(status_code=response.status_code,
                                detail=response.json().get("detail"))
        except Exception as e:
            logger.error(f"Error starting quiz: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    async def submit_answer(self, request: SubmitAnswerRequest):
        try:
            logger.info(
                f"Submitting answer for user {request.user_id} in session {request.session_id}")
            logger.debug(
                f"Request URL: {self.base_url}/quiz/submit_answer/{request.quiz_id}")
            logger.debug(
                f"Request body: user_id={request.user_id}, session_id={request.session_id}, answer={request.answer}")
            response = requests.post(
                f"{self.base_url}/quiz/submit_answer/{request.quiz_id}",
                json={
                    "user_id": request.user_id,
                    "session_id": request.session_id,
                    "answer": request.answer
                },
                headers=self.get_headers()
            )
            if response.status_code == 200:
                logger.info(f"Received response: {response.json()}")
                return response.json()
            logger.error(
                f"Failed to submit answer: {response.json().get('detail', 'Unknown error')}")
            raise HTTPException(status_code=response.status_code,
                                detail=response.json().get("detail"))
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {e}")
            raise HTTPException(
                status_code=400, detail="Invalid JSON response")
        except Exception as e:
            logger.error(f"Error submitting answer: {e}")
            raise HTTPException(status_code=500, detail=str(e))

import requests
from fastapi import HTTPException
from pyquizhub.config.config_utils import get_logger

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

    async def start_quiz(self, token: str, user_id: str):
        try:
            logger.info(f"Starting quiz for user {user_id} with token {token}")
            logger.debug(f"Request URL: {self.base_url}/quiz/start_quiz")
            logger.debug(f"Request params: token={token}, user_id={user_id}")
            response = requests.post(
                f"{self.base_url}/quiz/start_quiz",
                params={"token": token, "user_id": user_id},
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

    async def submit_answer(self, quiz_id: str, user_id: str,
                            session_id: str, answer: str):
        try:
            logger.info(
                f"Submitting answer for user {user_id} in session {session_id}")
            logger.debug(
                f"Request URL: {self.base_url}/quiz/submit_answer/{quiz_id}")
            logger.debug(
                f"Request body: user_id={user_id}, session_id={session_id}, answer={answer}")
            response = requests.post(
                f"{self.base_url}/quiz/submit_answer/{quiz_id}",
                json={
                    "user_id": user_id,
                    "session_id": session_id,
                    "answer": answer
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
        except Exception as e:
            logger.error(f"Error submitting answer: {e}")
            raise HTTPException(status_code=500, detail=str(e))

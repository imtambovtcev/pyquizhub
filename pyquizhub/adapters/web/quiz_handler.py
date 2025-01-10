import requests
from fastapi import HTTPException


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
            response = requests.post(
                f"{self.base_url}/start_quiz",
                json={"token": token, "user_id": user_id},
                headers=self.get_headers()
            )
            if response.status_code == 200:
                return response.json()
            raise HTTPException(status_code=response.status_code,
                                detail=response.json().get("detail"))
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    async def submit_answer(self, quiz_id: str, user_id: str,
                            session_id: str, question_id: str, answer: str):
        try:
            response = requests.post(
                f"{self.base_url}/submit_answer/{quiz_id}",
                json={
                    "user_id": user_id,
                    "session_id": session_id,
                    "question_id": question_id,
                    "answer": answer
                },
                headers=self.get_headers()
            )
            if response.status_code == 200:
                return response.json()
            raise HTTPException(status_code=response.status_code,
                                detail=response.json().get("detail"))
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

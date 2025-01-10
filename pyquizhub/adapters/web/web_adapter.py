from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from .quiz_handler import QuizHandler
from pyquizhub.config.config_utils import load_config
import uuid

import os

# Get the current directory path
current_dir = os.path.dirname(os.path.abspath(__file__))

app = FastAPI()
templates = Jinja2Templates(directory=os.path.join(current_dir, "templates"))
app.mount("/static",
          StaticFiles(directory=os.path.join(current_dir, "static")),
          name="static")

config = load_config()
quiz_handler = QuizHandler(config)


@app.get("/")
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/start")
async def start_quiz(request: Request, token: str = Form(...)):
    user_id = str(uuid.uuid4())
    try:
        response = await quiz_handler.start_quiz(token, user_id)
        return templates.TemplateResponse(
            "quiz.html",
            {
                "request": request,
                "question": response["question"],
                "quiz_id": response["quiz_id"],
                "session_id": response["session_id"],
                "user_id": user_id
            }
        )
    except HTTPException as e:
        return templates.TemplateResponse(
            "index.html",
            {
                "request": request,
                "error": e.detail
            }
        )


@app.post("/submit")
async def submit_answer(
    request: Request,
    quiz_id: str = Form(...),
    user_id: str = Form(...),
    session_id: str = Form(...),
    question_id: str = Form(...),
    answer: str = Form(...)
):
    try:
        response = await quiz_handler.submit_answer(
            quiz_id, user_id, session_id, question_id, answer
        )
        return templates.TemplateResponse(
            "quiz.html",
            {
                "request": request,
                "question": response["question"],
                "quiz_id": quiz_id,
                "session_id": session_id,
                "user_id": user_id
            }
        )
    except HTTPException as e:
        return templates.TemplateResponse(
            "quiz.html",
            {
                "request": request,
                "error": e.detail,
                "quiz_id": quiz_id,
                "session_id": session_id,
                "user_id": user_id
            }
        )

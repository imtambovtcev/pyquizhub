from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from .quiz_handler import QuizHandler
from pyquizhub.config.config_utils import load_config, get_logger
import uuid
import json
import os

# Get the current directory path
current_dir = os.path.dirname(os.path.abspath(__file__))

app = FastAPI()
templates = Jinja2Templates(directory=os.path.join(current_dir, "templates"))
app.mount("/static",
          StaticFiles(directory=os.path.join(current_dir, "static")),
          name="static")

config = load_config()

logger = get_logger(__name__)

quiz_handler = QuizHandler(config)


@app.get("/")
async def home(request: Request):
    logger.debug("Home page accessed")
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/start")
async def start_quiz(request: Request, token: str = Form(...)):
    user_id = str(uuid.uuid4())
    try:
        logger.info(f"Starting quiz for user {user_id} with token {token}")
        response = await quiz_handler.start_quiz(token, user_id)
        logger.info(f"Received response: {response}")
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
        logger.error(f"Error starting quiz: {e.detail}")
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
    answer: str = Form(...)
):
    try:
        logger.info(
            f"Submitting answer for user {user_id} in session {session_id}")
        answer_dict = json.loads(answer)
        response = await quiz_handler.submit_answer(
            quiz_id, user_id, session_id, answer_dict
        )
        logger.info(f"Received response: {response}")
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
    except (HTTPException, json.JSONDecodeError) as e:
        logger.error(f"Error submitting answer: {e}")
        return templates.TemplateResponse(
            "quiz.html",
            {
                "request": request,
                "error": str(e),
                "quiz_id": quiz_id,
                "session_id": session_id,
                "user_id": user_id
            }
        )

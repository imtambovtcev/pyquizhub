import click
import requests
import json
import yaml
import os
from pyquizhub.config.config_utils import get_token_from_config, get_logger
from pyquizhub.models import StartQuizRequestModel, StartQuizResponseModel, SubmitAnswerResponseModel, AnswerRequestModel

logger = get_logger(__name__)


def load_config():
    """Load configuration from the environment variable or default path."""
    config_path = os.getenv("PYQUIZHUB_CONFIG_PATH", os.path.abspath(os.path.join(
        os.path.dirname(__file__), "../../config/config.yaml")))
    try:
        with open(config_path, "r") as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        click.echo(f"Error: Configuration file not found at {config_path}.")
        raise
    except Exception as e:
        click.echo(f"Error loading configuration: {e}")
        raise


def get_headers():
    config = load_config()
    headers = {"Content-Type": "application/json"}
    token = get_token_from_config("user")
    if token:
        headers["Authorization"] = token
    return headers


@click.group()
@click.pass_context
def user_cli(ctx):
    """User CLI for participating in quizzes."""
    ctx.ensure_object(dict)
    ctx.obj["CONFIG"] = load_config()


@user_cli.command()
@click.option("--user-id", required=True, help="User ID")
@click.option("--token", required=True, help="Quiz token")
@click.pass_context
def start(ctx, user_id, token):
    """Start a quiz."""
    try:
        logger.debug(f"Starting quiz with token: {token} for user: {user_id}")
        config = ctx.obj["CONFIG"]
        base_url = config["api"]["base_url"]

        request_data = StartQuizRequestModel(token=token, user_id=user_id)
        response = requests.post(
            f"{base_url}/quiz/start_quiz",
            json=request_data.dict(),
            headers=get_headers()
        )
        if response.status_code == 200:
            response_data = StartQuizResponseModel(**response.json())
            click.echo(f"Starting quiz: {response_data.title}")
            handle_quiz_loop(ctx, response_data.quiz_id, user_id,
                             response_data.session_id, response_data)
        else:
            click.echo(
                f"Failed to start quiz: {response.json().get('detail', 'Unknown error')}")
            click.echo(response.json().get("errors", ""))
    except Exception as e:
        click.echo(f"Error: {e}")


def handle_quiz_loop(ctx, quiz_id, user_id, session_id, initial_response):
    """Handle the quiz loop."""
    question = initial_response.question
    while question and question.id is not None:
        answer = handle_question(question)
        response = submit_answer(
            ctx, quiz_id, user_id, session_id, answer)
        if not response:
            click.echo("Failed to submit answer.")
            return
        question = response.question
    click.echo("Quiz completed!")


def handle_question(question):
    """Handle a single quiz question."""
    if question.data["type"] == "final_message":
        click.echo(question.data["text"])
        return None
    elif question.data["type"] == "multiple_choice":
        click.echo(f"Question {question.id}: {question.data['text']}")
        for idx, option in enumerate(question.data.get("options", [])):
            click.echo(f"  {idx + 1}: {option['label']}")
        answer = click.prompt("Enter the number of your choice", type=int)
        return {"answer": question.data["options"][answer - 1]["value"]}
    elif question.data["type"] == "multiple_select":
        click.echo(f"Question {question.id}: {question.data['text']}")
        for idx, option in enumerate(question.data.get("options", [])):
            click.echo(f"  {idx + 1}: {option['label']}")
        answer = click.prompt(
            "Enter the numbers of your choices separated by commas", type=str)
        selected_options = [question.data["options"]
                            [int(idx) - 1]["value"] for idx in answer.split(",")]
        return {"answer": selected_options}
    elif question.data["type"] == "integer":
        click.echo(f"Question {question.id}: {question.data['text']}")
        answer = click.prompt("Enter your answer", type=int)
        return {"answer": answer}
    elif question.data["type"] == "float":
        click.echo(f"Question {question.id}: {question.data['text']}")
        answer = click.prompt("Enter your answer", type=float)
        return {"answer": answer}
    elif question.data["type"] == "text":
        click.echo(f"Question {question.id}: {question.data['text']}")
        answer = click.prompt("Enter your answer", type=str)
        return {"answer": answer}
    else:
        return {"answer": click.prompt("Your answer")}


def submit_answer(ctx, quiz_id, user_id, session_id, answer):
    """Submit an answer for a quiz question."""
    try:
        logger.debug(
            f"Submitting answer for quiz_id: {quiz_id}, user_id: {user_id}, session_id: {session_id}")
        config = ctx.obj["CONFIG"]
        base_url = config["api"]["base_url"]

        answer_request = AnswerRequestModel(
            user_id=user_id,
            session_id=session_id,
            answer=answer
        )

        response = requests.post(
            f"{base_url}/quiz/submit_answer/{quiz_id}",
            json=answer_request.dict(),
            headers=get_headers()
        )
        if response.status_code == 200:
            return SubmitAnswerResponseModel(**response.json())
        else:
            click.echo(
                f"Failed to submit answer: {response.json().get('detail', 'Unknown error')}")
            return None
    except json.JSONDecodeError as e:
        click.echo(f"JSON decode error: {e}")
        return None
    except Exception as e:
        click.echo(f"Error: {e}")
        return None


if __name__ == "__main__":
    user_cli()

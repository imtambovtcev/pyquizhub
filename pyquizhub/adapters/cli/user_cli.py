import click
import requests
import json
import yaml
import os
from pyquizhub.config.config_utils import get_token_from_config


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
        config = ctx.obj["CONFIG"]
        base_url = config["api"]["base_url"]

        response = requests.post(
            f"{base_url}/quiz/start_quiz?token={token}&user_id={user_id}",
            headers=get_headers()
        )
        if response.status_code == 200:
            quiz_id = response.json().get("quiz_id")
            session_id = response.json().get("session_id")
            click.echo(f"Starting quiz: {response.json().get('title')}")
            handle_quiz_loop(ctx, quiz_id, user_id,
                             session_id, response.json())
        else:
            click.echo(
                f"Failed to start quiz: {response.json().get('detail', 'Unknown error')}")
            click.echo(response.json().get("errors", ""))
    except Exception as e:
        click.echo(f"Error: {e}")


def handle_quiz_loop(ctx, quiz_id, user_id, session_id, initial_response):
    """Handle the quiz loop."""
    question = initial_response["question"]
    while question.get('id', None) is not None:
        answer = handle_question(question)
        response = submit_answer(
            ctx, quiz_id, user_id, session_id, question["id"], answer)
        if not response:
            click.echo("Failed to submit answer.")
            return
        question = response.get("question")
    click.echo("Quiz completed!")


def handle_question(question):
    """Handle a single quiz question."""
    if question["data"]["type"] == "final_message":
        click.echo(question["data"]["text"])
        return None
    elif question["data"]["type"] == "multiple_choice":
        click.echo(f"Question {question['id']}: {question['data']['text']}")
        for idx, option in enumerate(question["data"].get("options", [])):
            click.echo(f"  {idx + 1}: {option['label']}")
        answer = click.prompt("Enter the number of your choice", type=int)
        return {"answer": question["data"]["options"][answer - 1]["value"]}
    else:
        return {"answer": click.prompt("Your answer")}


def submit_answer(ctx, quiz_id, user_id, session_id, question_id, answer):
    """Submit an answer for a quiz question."""
    try:
        config = ctx.obj["CONFIG"]
        base_url = config["api"]["base_url"]

        response = requests.post(
            f"{base_url}/quiz/submit_answer/{quiz_id}",
            json={"user_id": user_id, "session_id": session_id,
                  "question_id": question_id, "answer": answer},
            headers=get_headers()
        )
        if response.status_code == 200:
            return response.json()
        else:
            click.echo(
                f"Failed to submit answer: {response.json().get('detail', 'Unknown error')}")
            return None
    except Exception as e:
        click.echo(f"Error: {e}")
        return None


if __name__ == "__main__":
    user_cli()

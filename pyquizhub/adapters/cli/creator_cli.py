import click
import requests
import json
import os
from pyquizhub.config.settings import get_config_manager, get_logger
from pyquizhub.models import CreateQuizRequestModel, QuizCreationResponseModel, TokenRequestModel, TokenResponseModel, QuizResultResponseModel

logger = get_logger(__name__)
logger.debug("Loaded creator_cli.py")


def get_headers():
    """Get request headers with creator token."""
    config_manager = get_config_manager()
    headers = {"Content-Type": "application/json"}
    token = config_manager.get_token("creator")
    if token:
        headers["Authorization"] = token
    return headers


@click.group()
@click.pass_context
def creator_cli(ctx):
    """Creator CLI for managing quizzes."""
    ctx.ensure_object(dict)
    config_manager = get_config_manager()
    config_manager.load()
    ctx.obj["CONFIG_MANAGER"] = config_manager


@creator_cli.command()
@click.option("--file",
              required=True,
              type=click.Path(exists=True),
              help="Path to the quiz JSON file")
@click.option("--creator-id", default="-1", help="Creator ID (default: -1)")
@click.pass_context
def add(ctx, file, creator_id):
    """Add an existing quiz to the storage."""
    try:
        logger.debug(
            f"Adding quiz from file: {file} with creator_id: {creator_id}")
        config_manager = ctx.obj["CONFIG_MANAGER"]
        base_url = config_manager.api_base_url

        with open(file, "r") as f:
            quiz_data = json.load(f)

        request_data = CreateQuizRequestModel(
            quiz=quiz_data, creator_id=creator_id)
        response = requests.post(
            f"{base_url}/creator/create_quiz",
            json=request_data.dict(),
            headers=get_headers(),
        )
        if response.status_code == 200:
            response_data = QuizCreationResponseModel(**response.json())
            click.echo("Quiz added successfully.")
            click.echo(f"Quiz ID: {response_data.quiz_id}")
        else:
            detail = response.json().get('detail', 'Unknown error')
            click.echo(f"Failed to add quiz: {detail}")
            click.echo(response.json().get("errors", ""))
    except FileNotFoundError:
        click.echo("Error: File not found.")
    except Exception as e:
        click.echo(f"Error: {e}")


@creator_cli.command()
@click.option("--quiz-id", required=True, help="Quiz ID")
@click.option("--token-type", required=True,
              type=click.Choice(["permanent", "single-use"]), help="Token type")
@click.pass_context
def token(ctx, quiz_id, token_type):
    """Generate a token for a quiz."""
    try:
        logger.debug(
            f"Generating token for quiz_id: {quiz_id} with token_type: {token_type}")
        config_manager = ctx.obj["CONFIG_MANAGER"]
        base_url = config_manager.api_base_url

        request_data = TokenRequestModel(quiz_id=quiz_id, type=token_type)
        response = requests.post(
            f"{base_url}/creator/generate_token",
            json=request_data.dict(),
            headers=get_headers())
        if response.status_code == 200:
            response_data = TokenResponseModel(**response.json())
            click.echo(f"Token generated successfully: {response_data.token}")
        else:
            detail = response.json().get('detail', 'Unknown error')
            click.echo(f"Failed to generate token: {detail}")
    except Exception as e:
        click.echo(f"Error: {e}")


@creator_cli.command()
@click.option("--quiz-id", required=True, help="Quiz ID")
@click.pass_context
def results(ctx, quiz_id):
    """View results for a quiz."""
    try:
        logger.debug(f"Fetching results for quiz_id: {quiz_id}")
        config_manager = ctx.obj["CONFIG_MANAGER"]
        base_url = config_manager.api_base_url

        response = requests.get(
            f"{base_url}/creator/results/{quiz_id}", headers=get_headers())
        if response.status_code == 200:
            response_data = QuizResultResponseModel(**response.json())
            click.echo("Quiz results:")
            for user_id, sessions in response_data.results.items():
                click.echo(f"User ID: {user_id}")
                for session_id, result in sessions.items():
                    click.echo(f"  Session ID: {session_id}")
                    click.echo(f"    Scores: {result.scores}")
                    click.echo(f"    Answers: {result.answers}")
        else:
            detail = response.json().get('detail', 'Unknown error')
            click.echo(f"Failed to fetch results: {detail}")
    except Exception as e:
        click.echo(f"Error: {e}")


@creator_cli.command()
@click.pass_context
def check(ctx):
    """Check if the API is working correctly."""
    try:
        logger.debug("Checking if the API is working correctly")
        config_manager = ctx.obj["CONFIG_MANAGER"]
        base_url = config_manager.api_base_url

        response = requests.get(f"{base_url}/", headers=get_headers())
        if response.status_code == 200:
            click.echo("API is working correctly.")
        else:
            detail = response.json().get('detail', 'Unknown error')
            click.echo(f"API check failed: {detail}")
    except Exception as e:
        click.echo(f"Error: {e}")


if __name__ == "__main__":
    creator_cli()

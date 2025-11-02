import click
import requests
import json
import os
from pyquizhub.config.settings import get_config_manager
from pyquizhub.config.config_utils import get_logger
from pyquizhub.models import CreateQuizRequestModel, QuizCreationResponseModel, TokenRequestModel, TokenResponseModel, QuizResultResponseModel

logger = get_logger(__name__)
logger.debug("Loaded admin_cli.py")


def get_headers():
    """Get request headers with admin token."""
    config_manager = get_config_manager()
    headers = {"Content-Type": "application/json"}
    token = config_manager.get_token("admin")
    if token:
        headers["Authorization"] = token
    return headers


@click.group()
@click.pass_context
def admin_cli(ctx):
    """Admin CLI for managing quizzes."""
    ctx.ensure_object(dict)
    config_manager = get_config_manager()
    config_manager.load()
    ctx.obj["CONFIG_MANAGER"] = config_manager


@admin_cli.command()
@click.option("--file", required=True, type=click.Path(exists=True), help="Path to the quiz JSON file")
@click.option("--creator-id", default="-1", help="Creator ID (default: -1)")
@click.pass_context
def add(ctx, file, creator_id):
    """Add an existing quiz to the storage."""
    try:
        config_manager = ctx.obj["CONFIG_MANAGER"]
        base_url = config_manager.api_base_url

        with open(file, "r") as f:
            quiz_data = json.load(f)

        request_data = CreateQuizRequestModel(
            quiz=quiz_data, creator_id=creator_id)
        response = requests.post(
            f"{base_url}/admin/create_quiz",
            json=request_data.dict(),
            headers=get_headers(),
        )
        if response.status_code == 200:
            response_data = QuizCreationResponseModel(**response.json())
            click.echo("Quiz added successfully.")
            click.echo(f"Quiz ID: {response_data.quiz_id}")
        else:
            click.echo(
                f"Failed to add quiz: {response.json().get('detail', 'Unknown error')}")
            click.echo(response.json().get("errors", ""))
    except FileNotFoundError:
        click.echo("Error: File not found.")
    except Exception as e:
        click.echo(f"Error: {e}")


@admin_cli.command()
@click.option("--quiz-id", required=True, help="Quiz ID")
@click.option("--token-type", required=True, type=click.Choice(["permanent", "single-use"]), help="Token type")
@click.pass_context
def token(ctx, quiz_id, token_type):
    """Generate a token for a quiz."""
    try:
        config_manager = ctx.obj["CONFIG_MANAGER"]
        base_url = config_manager.api_base_url

        request_data = TokenRequestModel(quiz_id=quiz_id, type=token_type)
        response = requests.post(
            f"{base_url}/admin/generate_token", json=request_data.dict(), headers=get_headers()
        )
        if response.status_code == 200:
            response_data = TokenResponseModel(**response.json())
            click.echo(f"Token generated successfully: {response_data.token}")
        else:
            click.echo(
                f"Failed to generate token: {response.json().get('detail', 'Unknown error')}")
    except Exception as e:
        click.echo(f"Error: {e}")


@admin_cli.command()
@click.option("--quiz-id", required=True, help="Quiz ID")
@click.pass_context
def results(ctx, quiz_id):
    """View results for a quiz."""
    try:
        config_manager = ctx.obj["CONFIG_MANAGER"]
        base_url = config_manager.api_base_url

        response = requests.get(
            f"{base_url}/admin/results/{quiz_id}", headers=get_headers())
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
            click.echo(
                f"Failed to fetch results: {response.json().get('detail', 'Unknown error')}")
    except Exception as e:
        click.echo(f"Error: {e}")


@admin_cli.command()
@click.pass_context
def check(ctx):
    """Check if the API is working correctly."""
    try:
        config_manager = ctx.obj["CONFIG_MANAGER"]
        base_url = config_manager.api_base_url

        response = requests.get(f"{base_url}/", headers=get_headers())
        if response.status_code == 200:
            click.echo("API is working correctly.")
        else:
            click.echo(
                f"API check failed: {response.json().get('detail', 'Unknown error')}")
    except Exception as e:
        click.echo(f"Error: {e}")


if __name__ == "__main__":
    admin_cli()

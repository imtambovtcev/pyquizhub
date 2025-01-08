import click
import requests
import json
import yaml
import os


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


@click.group()
@click.pass_context
def cli(ctx):
    """Quiz Engine CLI"""
    ctx.ensure_object(dict)
    ctx.obj["CONFIG"] = load_config()


@cli.command()
@click.option("--file", required=True, type=click.Path(exists=True), help="Path to the quiz JSON file")
@click.option("--creator-id", default="-1", help="Creator ID (default: -1)")
@click.pass_context
def add(ctx, file, creator_id):
    """Add an existing quiz to the storage."""
    try:
        config = ctx.obj["CONFIG"]
        base_url = config["api"]["base_url"]

        with open(file, "r") as f:
            quiz_data = json.load(f)

        response = requests.post(
            f"{base_url}/admin/create_quiz",
            json={"quiz": quiz_data, "creator_id": creator_id},
            headers={"Content-Type": "application/json"},
        )
        if response.status_code == 200:
            click.echo("Quiz added successfully.")
            click.echo(f"Quiz ID: {response.json().get('quiz_id')}")
        else:
            click.echo(
                f"Failed to add quiz: {response.json().get('detail', 'Unknown error')}")
            click.echo(response.json().get("errors", ""))
    except FileNotFoundError:
        click.echo("Error: File not found.")
    except Exception as e:
        click.echo(f"Error: {e}")


@cli.command()
@click.option("--user-id", required=True, help="User ID")
@click.option("--token", required=True, help="Quiz token")
@click.pass_context
def start(ctx, user_id, token):
    """Start a quiz."""
    try:
        config = ctx.obj["CONFIG"]
        base_url = config["api"]["base_url"]

        response = requests.post(
            f"{base_url}/quiz/start_quiz?token={token}&user_id={user_id}")
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


@cli.command()
@click.option("--quiz-id", required=True, help="Quiz ID")
@click.option("--user-id", required=True, help="User ID")
@click.option("--session-id", required=True, help="Session ID")
@click.pass_context
def results(ctx, quiz_id, user_id, session_id):
    """View results for a quiz."""
    try:
        config = ctx.obj["CONFIG"]
        base_url = config["api"]["base_url"]

        response = requests.get(
            f"{base_url}/results/{quiz_id}/{user_id}/{session_id}")
        if response.status_code == 200:
            data = response.json()
            click.echo("Your results:")
            click.echo(f"Scores: {data['scores']}")
            click.echo(f"Answers: {data['answers']}")
        else:
            click.echo(
                f"Failed to fetch results: {response.json().get('detail', 'Unknown error')}")
    except Exception as e:
        click.echo(f"Error: {e}")


@cli.command()
@click.option("--quiz-id", required=True, help="Quiz ID")
@click.option("--token-type", required=True, type=click.Choice(["permanent", "single-use"]), help="Token type")
@click.pass_context
def token(ctx, quiz_id, token_type):
    """Generate a token for a quiz."""
    try:
        config = ctx.obj["CONFIG"]
        base_url = config["api"]["base_url"]

        response = requests.post(
            f"{base_url}/admin/generate_token", json={"quiz_id": quiz_id, "type": token_type}
        )
        if response.status_code == 200:
            data = response.json()
            click.echo(f"Token generated successfully: {data['token']}")
        else:
            click.echo(
                f"Failed to generate token: {response.json().get('detail', 'Unknown error')}")
    except Exception as e:
        click.echo(f"Error: {e}")


@cli.command()
@click.pass_context
def check(ctx):
    """Check if the API is working correctly."""
    try:
        config = ctx.obj["CONFIG"]
        base_url = config["api"]["base_url"]

        response = requests.get(f"{base_url}/")
        if response.status_code == 200:
            click.echo("API is working correctly.")
        else:
            click.echo(
                f"API check failed: {response.json().get('detail', 'Unknown error')}")
    except Exception as e:
        click.echo(f"Error: {e}")


if __name__ == "__main__":
    cli()

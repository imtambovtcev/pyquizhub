import click
import requests
import json
import yaml

# Load configuration
CONFIG_PATH = "pyquizhub/config/config.yaml"
with open(CONFIG_PATH, "r") as f:
    config = yaml.safe_load(f)

# Load the base URL from the configuration file
BASE_URL = config["api"]["base_url"]


@click.group()
def cli():
    """Quiz Engine CLI"""
    pass


@cli.command()
@click.option("--file", required=True, type=click.Path(exists=True), help="Path to the quiz JSON file")
@click.option("--creator-id", default="-1", help="Creator ID (default: -1)")
def add(file, creator_id):
    """Add an existing quiz to the storage."""
    try:
        with open(file, "r") as f:
            quiz_data = json.load(f)

        response = requests.post(
            f"{BASE_URL}/admin/create_quiz",
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
def start(user_id, token):
    """Start a quiz."""
    try:
        response = requests.post(
            f"{BASE_URL}/start_quiz?token={token}&user_id={user_id}")
        if response.status_code == 200:
            quiz_id = response.json().get("quiz_id")
            session_id = response.json().get("session_id")
            click.echo(f"Starting quiz: {response.json().get('title')}")
            handle_quiz_loop(quiz_id, user_id, session_id, response.json())
        else:
            click.echo(
                f"Failed to start quiz: {response.json().get('detail', 'Unknown error')}")
            click.echo(response.json().get("errors", ""))
    except Exception as e:
        click.echo(f"Error: {e}")


def handle_quiz_loop(quiz_id, user_id, session_id, initial_response):
    """Handle the quiz loop."""
    question = initial_response["question"]
    while question.get('id', None) is not None:
        answer = handle_question(question)
        response = submit_answer(
            quiz_id, user_id, session_id, question["id"], answer)
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


def submit_answer(quiz_id, user_id, session_id, question_id, answer):
    """Submit an answer for a quiz question."""
    try:
        response = requests.post(
            f"{BASE_URL}/submit_answer/{quiz_id}",
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
def results(quiz_id, user_id, session_id):
    """View results for a quiz."""
    try:
        response = requests.get(
            f"{BASE_URL}/results/{quiz_id}/{user_id}/{session_id}")
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
def token(quiz_id, token_type):
    """Generate a token for a quiz."""
    try:
        response = requests.post(
            f"{BASE_URL}/admin/generate_token", json={"quiz_id": quiz_id, "type": token_type}
        )
        if response.status_code == 200:
            data = response.json()
            click.echo(f"Token generated successfully: {data['token']}")
        else:
            click.echo(
                f"Failed to generate token: {response.json().get('detail', 'Unknown error')}")
    except Exception as e:
        click.echo(f"Error: {e}")


if __name__ == "__main__":
    cli()

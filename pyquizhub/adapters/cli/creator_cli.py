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
    token = get_token_from_config("creator")
    if token:
        headers["Authorization"] = token
    return headers


@click.group()
@click.pass_context
def creator_cli(ctx):
    """Creator CLI for managing quizzes."""
    ctx.ensure_object(dict)
    ctx.obj["CONFIG"] = load_config()


@creator_cli.command()
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
            headers=get_headers(),
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


if __name__ == "__main__":
    creator_cli()

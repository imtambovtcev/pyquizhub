from click.testing import CliRunner
from pyquizhub.adapters.cli.cli import cli
import os
import pytest
from unittest.mock import patch
from requests.models import Response as RequestsResponse


def extract_value(output, prefix):
    """Utility to extract a value from CLI output based on a prefix."""
    for line in output.split("\n"):
        if line.startswith(prefix):
            return line.split(prefix)[1].strip()
    return None


@pytest.fixture
def mock_requests(api_client):
    """Fixture to mock requests and redirect them to the TestClient."""
    with patch('pyquizhub.adapters.cli.cli.requests.post') as mock_post, \
            patch('pyquizhub.adapters.cli.cli.requests.get') as mock_get:
        def convert_response(api_response):
            """Convert TestClient response to requests.Response."""
            response = RequestsResponse()
            response.status_code = api_response.status_code
            response.headers = api_response.headers
            response._content = api_response.content
            response.encoding = api_response.encoding
            response.reason = api_response.reason_phrase
            response.url = api_response.url
            return response

        def mock_post_side_effect(url, json=None, headers=None, **kwargs):
            path = url.replace('http://testserver', '')
            api_response = api_client.post(path, json=json, headers=headers)
            return convert_response(api_response)

        def mock_get_side_effect(url, params=None, headers=None, **kwargs):
            path = url.replace('http://testserver', '')
            api_response = api_client.get(path, params=params, headers=headers)
            return convert_response(api_response)

        mock_post.side_effect = mock_post_side_effect
        mock_get.side_effect = mock_get_side_effect

        yield


@pytest.fixture
def quiz_id(api_client, config_path, mock_requests):
    """Fixture to add a quiz and return the quiz ID."""
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            'add',
            '--file',
            os.path.join(
                os.path.dirname(
                    __file__), "../test_quiz_jsons/complex_quiz.json"
            ),
        ],
        env={"PYQUIZHUB_CONFIG_PATH": str(config_path)},
    )

    assert result.exit_code == 0
    assert "Quiz added successfully." in result.output

    quiz_id = extract_value(result.output, "Quiz ID: ")
    assert quiz_id, "Quiz ID could not be extracted."
    return quiz_id


@pytest.fixture
def token(api_client, config_path, quiz_id, mock_requests):
    """Fixture to generate a token for a quiz."""
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ['token', '--quiz-id', quiz_id, '--token-type', 'permanent'],
        env={"PYQUIZHUB_CONFIG_PATH": str(config_path)},
    )

    assert result.exit_code == 0
    assert "Token generated successfully: " in result.output

    token = extract_value(result.output, "Token generated successfully: ")
    assert token, "Token could not be extracted."
    return token


def test_add_quiz(quiz_id):
    """Test that the quiz ID is correctly returned."""
    assert quiz_id, "Quiz ID could not be extracted."


def test_generate_token(token):
    """Test that the token is correctly returned."""
    assert token, "Token could not be extracted."


def test_start_quiz(api_client, config_path, token, mock_requests):
    """Test starting a quiz and verifying the flow."""
    runner = CliRunner()

    # Simulate user inputs for the questions
    inputs = "1\n2\n"  # Answer 'Yes' for the first question and 'No' for the second
    result = runner.invoke(
        cli,
        ['start', '--token', token, '--user-id', '42'],
        input=inputs,
        env={"PYQUIZHUB_CONFIG_PATH": str(config_path)},
    )

    assert result.exit_code == 0
    assert "Starting quiz: Complex Quiz" in result.output
    assert "Question 1: Do you like apples?" in result.output
    assert "Quiz completed!" in result.output


def test_check_connection(api_client, config_path, mock_requests):
    """Test checking the API connection."""
    runner = CliRunner()
    result = runner.invoke(
        cli, ['check'], env={"PYQUIZHUB_CONFIG_PATH": str(config_path)}
    )

    assert result.exit_code == 0
    assert "API is working correctly." in result.output


def test_cli_flow(api_client, config_path, token, mock_requests):
    """End-to-end test of the CLI workflow."""
    test_start_quiz(api_client, config_path, token, mock_requests)

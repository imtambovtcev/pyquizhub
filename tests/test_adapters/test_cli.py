from click.testing import CliRunner
from pyquizhub.adapters.cli.cli import cli


def extract_value(output, prefix):
    """Utility to extract a value from CLI output based on a prefix."""
    for line in output.split("\n"):
        if line.startswith(prefix):
            return line.split(prefix)[1].strip()
    return None


def test_add_quiz(adapter_api):
    """Test adding a quiz and extracting the quiz ID."""
    runner = CliRunner()
    result = runner.invoke(
        cli, ['add', '--file', 'tests/test_quiz_jsons/complex_quiz.json']
    )

    assert result.exit_code == 0
    assert "Quiz added successfully." in result.output

    quiz_id = extract_value(result.output, "Quiz ID: ")
    assert quiz_id, "Quiz ID could not be extracted."
    return quiz_id


def test_generate_token(adapter_api):
    """Test generating a token for a quiz and extracting the token."""
    quiz_id = test_add_quiz(adapter_api)  # Reuse the prior test’s logic
    runner = CliRunner()
    result = runner.invoke(
        cli, ['token', '--quiz-id', quiz_id, '--token-type', 'permanent']
    )

    assert result.exit_code == 0
    assert "Token generated successfully: " in result.output

    token = extract_value(result.output, "Token generated successfully: ")
    assert token, "Token could not be extracted."
    return token


def test_start_quiz(adapter_api):
    """Test starting a quiz and verifying the flow."""
    quiz_id = test_add_quiz(adapter_api)
    token = test_generate_token(adapter_api)
    runner = CliRunner()

    # Simulate user inputs for the questions
    inputs = "1\n2\n"  # Answer 'Yes' for the first question and 'No' for the second
    result = runner.invoke(
        cli, ['start', '--token', token, '--user-id', '42'], input=inputs)

    assert result.exit_code == 0
    assert "Starting quiz: Complex Quiz" in result.output
    assert "Question 1: Do you like apples?" in result.output
    assert "Quiz completed!" in result.output


def test_cli_flow(adapter_api):
    """End-to-end test of the CLI workflow."""
    quiz_id = test_add_quiz(adapter_api)
    token = test_generate_token(adapter_api)
    test_start_quiz(adapter_api)

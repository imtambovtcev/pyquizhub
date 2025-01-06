
from click.testing import CliRunner
from pyquizhub.adapters.cli.cli import cli  # Import the Click CLI group


def extract_value(output, prefix):
    """Utility to extract a value from CLI output based on a prefix."""
    for line in output.split("\n"):
        if line.startswith(prefix):
            return line.split(prefix)[1].strip()
    return None


def test_add_quiz():
    """Test adding a quiz and extracting the quiz ID."""
    runner = CliRunner()
    result = runner.invoke(
        cli, ['add', '--file', 'tests/test_quiz_jsons/complex_quiz.json'])

    assert result.exit_code == 0
    assert "Quiz added successfully." in result.output

    quiz_id = extract_value(result.output, "Quiz ID: ")
    assert quiz_id, "Quiz ID could not be extracted."
    return quiz_id


def test_generate_token():
    """Test generating a token for a quiz and extracting the token."""
    quiz_id = test_add_quiz()
    runner = CliRunner()
    result = runner.invoke(
        cli, ['token', '--quiz-id', quiz_id, '--token-type', 'permanent'])

    assert result.exit_code == 0
    assert "Token generated successfully: " in result.output

    token = extract_value(result.output, "Token generated successfully: ")
    assert token, "Token could not be extracted."
    return token


def test_start_quiz():
    """Test starting a quiz and verifying the flow."""
    quiz_id = test_add_quiz()
    token = test_generate_token()
    runner = CliRunner()

    # Simulate user inputs for the questions
    inputs = "1\n2\n"  # Answer 'Yes' for the first question and 'No' for the second
    result = runner.invoke(
        cli, ['start', '--token', token, '--user-id', '42'], input=inputs)

    assert result.exit_code == 0
    assert "Starting quiz: Complex Quiz" in result.output

    # Check the first question
    assert "Question 1: Do you like apples?" in result.output

    # Check completion message
    assert "Quiz completed!" in result.output


def test_cli_flow():
    """End-to-end test of the CLI workflow."""
    quiz_id = test_add_quiz()
    token = test_generate_token()
    test_start_quiz()

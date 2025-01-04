import argparse
import requests
import sys
import yaml
import json

# Load configuration
CONFIG_PATH = "pyquizhub/config/config.yaml"
with open(CONFIG_PATH, "r") as f:
    config = yaml.safe_load(f)

# Load the base URL from the configuration file
BASE_URL = config["api"]["base_url"]


def add_quiz(file_path=None):
    """Add an existing quiz to the storage."""
    if not file_path:
        file_path = input("Enter the path to the quiz JSON file: ").strip()
    try:
        with open(file_path, "r") as f:
            quiz_data = json.load(f)
        response = requests.post(f"{BASE_URL}/add_quiz", json=quiz_data)
        if response.status_code == 200:
            print("Quiz added successfully.")
            print("Quiz ID:", response.json().get("quiz_id"))
        else:
            print("Failed to add quiz:", response.json().get(
                "detail", "Unknown error"))
    except FileNotFoundError:
        print("Error: File not found.")
    except Exception as e:
        print(f"Error: {e}")


def start_quiz(user_id, token):
    """Start a quiz."""
    response = requests.post(
        f"{BASE_URL}/start_quiz?token={token}&user_id={user_id}")
    if response.status_code == 200:
        quiz = response.json()
        print(f"Starting quiz: {quiz['title']}")
        print("Answer the following questions:")
        results = {}
        for question in quiz["questions"]:
            print(f"Question {question['id']}: {question['text']}")
            if question["type"] == "multiple_choice":
                print("Options:")
                for idx, option in enumerate(question.get("options", [])):
                    print(f"  {idx + 1}: {option}")
                answer = input("Enter the number of your choice: ").strip()
                results[question["id"]] = answer
            else:
                answer = input("Your answer: ").strip()
                results[question["id"]] = answer
        submit_answers(quiz["quiz_id"], user_id, results)
    else:
        print("Failed to start quiz:", response.json().get(
            "detail", "Unknown error"))


def submit_answers(quiz_id, user_id, answers):
    """Submit answers for a quiz."""
    response = requests.post(
        f"{BASE_URL}/submit_answers/{quiz_id}", json={"user_id": user_id, "answers": answers})
    if response.status_code == 200:
        data = response.json()
        print("Answers submitted successfully!")
        print("Your scores:", data["scores"])
    else:
        print("Failed to submit answers:",
              response.json().get("detail", "Unknown error"))


def view_results():
    """View results for a quiz."""
    quiz_id = input("Enter the quiz ID: ").strip()
    user_id = input("Enter your user ID: ").strip()
    response = requests.get(f"{BASE_URL}/results/{quiz_id}/{user_id}")
    if response.status_code == 200:
        data = response.json()
        print("Your results:")
        print("Scores:", data["scores"])
        print("Answers:", data["answers"])
    else:
        print("Failed to fetch results:",
              response.json().get("detail", "Unknown error"))


def generate_token(quiz_id, token_type):
    """Generate a token for a quiz."""
    response = requests.post(
        f"{BASE_URL}/generate_token", json={"quiz_id": quiz_id, "type": token_type})
    if response.status_code == 200:
        data = response.json()
        print(f"Token generated successfully: {data['token']}")
    else:
        print("Failed to generate token:",
              response.json().get("detail", "Unknown error"))


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Quiz Engine CLI")
    parser.add_argument("command", choices=[
                        "add", "start", "results", "token"], help="Command to execute")
    parser.add_argument(
        "--file", help="Path to the quiz JSON file (for 'add' command only)")
    parser.add_argument(
        "--user_id", help="User ID (for 'start' command only)")
    parser.add_argument(
        "--token", help="Quiz token (for 'start' command only)")
    parser.add_argument(
        "--quiz_id", help="Quiz ID (for 'token' command only)")
    parser.add_argument(
        "--token_type", help="Token type (permanent/single-use) (for 'token' command only)")
    args = parser.parse_args()

    if args.command == "add":
        add_quiz(file_path=args.file)
    elif args.command == "start":
        if not args.user_id or not args.token:
            print("Error: 'start' command requires --user_id and --token arguments.")
            sys.exit(1)
        start_quiz(user_id=args.user_id, token=args.token)
    elif args.command == "results":
        view_results()
    elif args.command == "token":
        if not args.quiz_id or not args.token_type:
            print("Error: 'token' command requires --quiz_id and --token_type arguments.")
            sys.exit(1)
        generate_token(quiz_id=args.quiz_id, token_type=args.token_type)
    else:
        print("Unknown command. Use --help for usage instructions.")
        sys.exit(1)


if __name__ == "__main__":
    main()

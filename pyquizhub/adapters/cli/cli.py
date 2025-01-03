import argparse
import requests
import sys
import yaml

# Load configuration
CONFIG_PATH = "pyquizhub/config/config.yaml"
with open(CONFIG_PATH, "r") as f:
    config = yaml.safe_load(f)

# Load the base URL from the configuration file
BASE_URL = config["api"]["base_url"]


def create_quiz():
    """Create a new quiz."""
    title = input("Enter the quiz title: ")
    questions = []
    print("Enter questions (leave question text empty to finish):")
    while True:
        question_text = input("Question text: ").strip()
        if not question_text:
            break
        question_type = input(
            "Question type (multiple_choice/text/number): ").strip()
        options = []
        if question_type == "multiple_choice":
            print("Enter options (leave option empty to finish):")
            while True:
                option = input("Option: ").strip()
                if not option:
                    break
                options.append(option)
        questions.append(
            {"text": question_text, "type": question_type, "options": options})

    quiz = {"title": title, "questions": questions}
    response = requests.post(f"{BASE_URL}/create_quiz", json=quiz)
    if response.status_code == 200:
        data = response.json()
        print(f"Quiz created successfully with ID: {data['quiz_id']}")
    else:
        print("Failed to create quiz:", response.json().get(
            "detail", "Unknown error"))


def start_quiz():
    """Start a quiz."""
    token = input("Enter the quiz token: ").strip()
    user_id = input("Enter your user ID: ").strip()
    response = requests.post(
        f"{BASE_URL}/start_quiz", json={"token": token, "user_id": user_id})
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
        f"{BASE_URL}/submit_answer/{quiz_id}", json={"user_id": user_id, "answer": answers})
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


def generate_token():
    """Generate a token for a quiz."""
    quiz_id = input("Enter the quiz ID: ").strip()
    token_type = input("Enter token type (permanent/single-use): ").strip()
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
                        "create", "start", "results", "token"], help="Command to execute")
    args = parser.parse_args()

    if args.command == "create":
        create_quiz()
    elif args.command == "start":
        start_quiz()
    elif args.command == "results":
        view_results()
    elif args.command == "token":
        generate_token()
    else:
        print("Unknown command. Use --help for usage instructions.")
        sys.exit(1)


if __name__ == "__main__":
    main()

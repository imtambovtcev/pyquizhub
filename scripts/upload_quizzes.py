#!/usr/bin/env python3
"""
Upload quizzes to PyQuizHub API
"""

import json
import os
import requests
from pathlib import Path

API_URL = "http://localhost:8000"
ADMIN_TOKEN = os.getenv(
    "PYQUIZHUB_ADMIN_TOKEN",
    "your-secret-admin-token-here")


def upload_quiz(quiz_file_path):
    """Upload a single quiz to the API"""
    quiz_path = Path(quiz_file_path)
    quiz_name = quiz_path.stem

    print(f"📤 Uploading: {quiz_name}")

    try:
        # Load quiz JSON
        with open(quiz_path, 'r') as f:
            quiz_data = json.load(f)

        # Create request payload
        payload = {
            "quiz": quiz_data,
            "creator_id": "admin"
        }

        # Upload quiz
        response = requests.post(
            f"{API_URL}/admin/create_quiz",
            json=payload,
            headers={
                "Content-Type": "application/json",
                "Authorization": ADMIN_TOKEN
            }
        )

        if response.status_code == 200:
            result = response.json()
            quiz_id = result.get("quiz_id")
            print(f"✅ Success! Quiz ID: {quiz_id}")

            # Generate a permanent token
            token_payload = {
                "quiz_id": quiz_id,
                "type": "permanent"
            }

            token_response = requests.post(
                f"{API_URL}/admin/generate_token",
                json=token_payload,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": ADMIN_TOKEN
                }
            )

            if token_response.status_code == 200:
                token = token_response.json().get("token")
                print(f"🎫 Token: {token}")

            return quiz_id, token
        else:
            print(f"❌ Failed: {response.status_code} - {response.text}")
            return None, None

    except Exception as e:
        print(f"❌ Error: {e}")
        return None, None
    finally:
        print("")


def main():
    print("🚀 Uploading quizzes to PyQuizHub...")
    print(f"API URL: {API_URL}\n")

    quizzes_uploaded = {}

    # Upload main test quizzes
    print("=== Main Test Quizzes ===")
    test_quizzes = [
        "tests/test_quiz_jsons/simple_quiz.json",
        "tests/test_quiz_jsons/complex_weather_quiz.json",
        "tests/test_quiz_jsons/joke_quiz_static_api.json",
        "tests/test_quiz_jsons/joke_quiz_dynamic_api.json"
    ]

    for quiz_file in test_quizzes:
        if os.path.exists(quiz_file):
            quiz_id, token = upload_quiz(quiz_file)
            if quiz_id:
                quizzes_uploaded[Path(quiz_file).stem] = {
                    "quiz_id": quiz_id,
                    "token": token
                }
        else:
            print(f"⚠️  File not found: {quiz_file}\n")

    # Upload the practical quiz
    print("=== Practical Quiz ===")
    practical_quiz = "quizzes/python_knowledge_quiz.json"
    if os.path.exists(practical_quiz):
        quiz_id, token = upload_quiz(practical_quiz)
        if quiz_id:
            quizzes_uploaded[Path(practical_quiz).stem] = {
                "quiz_id": quiz_id,
                "token": token
            }
    else:
        print(f"⚠️  File not found: {practical_quiz}\n")

    # Print summary
    print("=" * 60)
    print("📋 Upload Summary")
    print("=" * 60)
    for name, info in quizzes_uploaded.items():
        print(f"\n{name}:")
        print(f"  Quiz ID: {info['quiz_id']}")
        print(f"  Token:   {info['token']}")

    # Save to file for easy reference
    with open("quiz_tokens.json", "w") as f:
        json.dump(quizzes_uploaded, f, indent=2)
    print(f"\n💾 Quiz information saved to quiz_tokens.json")
    print("\n🎉 Done!")


if __name__ == "__main__":
    main()

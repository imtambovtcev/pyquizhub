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


def clean_database():
    """Clean the database by deleting all existing quizzes"""
    print("🧹 Cleaning database...")

    try:
        # Get all existing quizzes
        response = requests.get(
            f"{API_URL}/admin/all_quizzes",
            headers={
                "Content-Type": "application/json",
                "Authorization": ADMIN_TOKEN
            }
        )

        if response.status_code != 200:
            print(
                f"⚠️  Failed to get quizzes: {response.status_code} - {response.text}\n")
            return False

        quizzes = response.json().get("quizzes", {})
        quiz_count = len(quizzes)

        if quiz_count == 0:
            print("✅ Database is already clean (no quizzes found)\n")
            return True

        print(f"   Found {quiz_count} quizzes to delete...")

        # Delete each quiz
        deleted = 0
        for quiz_id in quizzes.keys():
            delete_response = requests.delete(
                f"{API_URL}/admin/quiz/{quiz_id}",
                headers={
                    "Content-Type": "application/json",
                    "Authorization": ADMIN_TOKEN
                }
            )

            if delete_response.status_code == 200:
                deleted += 1
            else:
                status = delete_response.status_code
                print(f"   ⚠️  Failed to delete quiz {quiz_id}: {status}")

        print(f"✅ Database cleaned: deleted {deleted}/{quiz_count} quizzes\n")
        return deleted == quiz_count

    except Exception as e:
        print(f"❌ Error cleaning database: {e}\n")
        return False


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

    # Clean database first
    if not clean_database():
        print("⚠️  Warning: Database clean failed, but continuing with upload...\n")

    quizzes_uploaded = {}

    # Upload comprehensive test quizzes
    print("=== Adapter Test Quizzes ===")
    test_quizzes = [
        # All 5 input types in one quiz with verification
        "tests/test_quiz_jsons/test_quiz_input_types.json",
        # API integration (static and dynamic)
        "tests/test_quiz_jsons/joke_quiz_static_api.json",
        "tests/test_quiz_jsons/joke_quiz_dynamic_api.json",
        # All 19 attachment formats (images, audio, video, documents)
        "tests/test_quiz_jsons/test_quiz_file_types.json",
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

    # Upload file upload quizzes (demos for file upload feature)
    print("=== File Upload (with Color API) ===")
    file_upload_quizzes = [
        "quizzes/color_detector_quiz.json",  # Color analysis with file upload
    ]

    for quiz_file in file_upload_quizzes:
        if os.path.exists(quiz_file):
            quiz_id, token = upload_quiz(quiz_file)
            if quiz_id:
                quizzes_uploaded[Path(quiz_file).stem] = {
                    "quiz_id": quiz_id,
                    "token": token
                }
        else:
            print(f"⚠️  File not found: {quiz_file}\n")

    # Print summary
    print("=" * 60)
    print("📋 Upload Summary")
    print("=" * 60)
    for name, info in quizzes_uploaded.items():
        print(f"\n{name}:")
        print(f"  Quiz ID: {info['quiz_id']}")
        print(f"  Token:   {info['token']}")

    print("\n" + "=" * 60)
    print("📡 Retrieving Quiz Tokens via API")
    print("=" * 60)
    print("\nTo retrieve all tokens later, use:")
    print(
        f"  curl -H 'Authorization: {ADMIN_TOKEN}' {API_URL}/admin/all_tokens")

    print("\nTo get tokens for a specific quiz:")
    print(
        f"  curl -H 'Authorization: {ADMIN_TOKEN}' {API_URL}/admin/all_tokens | jq '.tokens[\"QUIZ_ID\"]'")

    print("\n🎉 Done!")


if __name__ == "__main__":
    main()

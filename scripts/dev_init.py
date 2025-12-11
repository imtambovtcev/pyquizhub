#!/usr/bin/env python3
"""
Development initialization script.

This script runs on startup in dev mode to:
1. Wait for API to be ready
2. Clean database (delete existing quizzes, tokens, sessions, results)
3. Upload standard test quizzes from tests/test_quiz_jsons/
4. Create a default creator account (for creator_web login)

Usage:
    python scripts/dev_init.py

Environment variables:
    PYQUIZHUB_API_URL: API base URL (default: http://localhost:8000)
    PYQUIZHUB_ADMIN_TOKEN: Admin token for API authentication
    DEFAULT_CREATOR_ID: Default creator ID (default: dev_creator)
    DEFAULT_CREATOR_PASSWORD: Default creator password (default: creator123)
"""

import os
import sys
import time
import json
import requests
from pathlib import Path

# Configuration
API_URL = os.getenv("PYQUIZHUB_API_URL", "http://localhost:8000")
ADMIN_TOKEN = os.getenv("PYQUIZHUB_ADMIN_TOKEN", "test-admin-token")
DEFAULT_CREATOR_ID = os.getenv("DEFAULT_CREATOR_ID", "dev_creator")
DEFAULT_CREATOR_PASSWORD = os.getenv("DEFAULT_CREATOR_PASSWORD", "creator123")

# Quiz files to upload - comprehensive test set for all adapter features
QUIZ_DIR = Path(__file__).parent.parent / "tests" / "test_quiz_jsons"
PROD_QUIZ_DIR = Path(__file__).parent.parent / "quizzes"

# Main test quizzes - comprehensive tests for all adapter features
MAIN_QUIZZES = [
    # All input types in one quiz (multiple_choice, multiple_select, text, integer, float)
    "test_quiz_input_types.json",    # 5 input types with verification
    # API integration
    "joke_quiz_static_api.json",     # static API call at quiz start
    "joke_quiz_dynamic_api.json",    # dynamic API call before each question
    # Attachments (images, audio, video, documents)
    "test_quiz_file_types.json",     # all 19 attachment formats
]

# Production quizzes (file upload with external API)
PROD_QUIZZES = [
    "color_detector_quiz.json",      # file_upload question type with Color API
]


def wait_for_api(max_retries: int = 30, delay: float = 2.0) -> bool:
    """Wait for API to be ready."""
    print(f"Waiting for API at {API_URL}...")

    for i in range(max_retries):
        try:
            response = requests.get(f"{API_URL}/", timeout=5)
            if response.status_code == 200:
                print(f"API is ready!")
                return True
        except requests.exceptions.RequestException:
            pass

        print(f"  Retry {i + 1}/{max_retries}...")
        time.sleep(delay)

    print("ERROR: API not available after retries")
    return False


def clean_database() -> bool:
    """Clean all data from database via admin API."""
    print("Cleaning database...")

    headers = {"Authorization": ADMIN_TOKEN}

    # Delete all quizzes (this cascades to tokens, sessions, results)
    try:
        # Get all quizzes
        response = requests.get(
            f"{API_URL}/admin/all_quizzes",
            headers=headers,
            timeout=10
        )

        if response.status_code != 200:
            print(f"  Warning: Could not get quizzes: {response.status_code}")
            return True  # Continue anyway - database might be empty

        quizzes = response.json().get("quizzes", {})

        for quiz_id in quizzes.keys():
            delete_response = requests.delete(
                f"{API_URL}/admin/quiz/{quiz_id}",
                headers=headers,
                timeout=10
            )
            if delete_response.status_code == 200:
                print(f"  Deleted quiz: {quiz_id}")
            else:
                status = delete_response.status_code
                print(f"  Warning: Could not delete {quiz_id}: {status}")

        print("Database cleaned!")
        return True

    except requests.exceptions.RequestException as e:
        print(f"  Warning: Database clean failed: {e}")
        return True  # Continue anyway


def upload_quiz_file(quiz_path: Path, headers: dict) -> tuple:
    """Upload a single quiz file and return (quiz_id, token) or (None, None)."""
    try:
        with open(quiz_path, "r") as f:
            quiz_data = json.load(f)

        # Create quiz
        response = requests.post(
            f"{API_URL}/admin/create_quiz",
            headers=headers,
            json={"quiz": quiz_data, "creator_id": DEFAULT_CREATOR_ID},
            timeout=10
        )

        if response.status_code == 200:
            result = response.json()
            quiz_id = result.get("quiz_id")
            print(f"  ✓ {quiz_path.name} -> {quiz_id}")

            # Generate token
            token_response = requests.post(
                f"{API_URL}/admin/generate_token",
                headers=headers,
                json={"quiz_id": quiz_id, "type": "permanent"},
                timeout=10
            )

            if token_response.status_code == 200:
                token = token_response.json().get("token")
                print(f"    Token: {token}")
                return quiz_id, token
            else:
                print("    Warning: Could not generate token")
                return quiz_id, None
        else:
            print(f"  ✗ {quiz_path.name}: {response.status_code}")
            # Show short error message
            try:
                err = response.json()
                if "detail" in err:
                    detail = err["detail"]
                    if isinstance(detail, dict) and "error" in detail:
                        print(f"    {detail['error'].get('message', '')}")
            except Exception:
                pass
            return None, None

    except Exception as e:
        print(f"  ✗ {quiz_path.name}: {e}")
        return None, None


def upload_quizzes() -> dict:
    """Upload all test quizzes and return quiz_id -> token mapping."""
    headers = {
        "Authorization": ADMIN_TOKEN,
        "Content-Type": "application/json"
    }

    quiz_tokens = {}

    # Upload main test quizzes
    print("\nUploading test quizzes (question types & features)...")
    for quiz_file in MAIN_QUIZZES:
        quiz_path = QUIZ_DIR / quiz_file
        if not quiz_path.exists():
            print(f"  Warning: {quiz_file} not found")
            continue
        quiz_id, token = upload_quiz_file(quiz_path, headers)
        if quiz_id and token:
            quiz_tokens[quiz_id] = token

    # Upload production quizzes (file upload demos)
    print("\nUploading production quizzes (file upload demos)...")
    for quiz_file in PROD_QUIZZES:
        quiz_path = PROD_QUIZ_DIR / quiz_file
        if not quiz_path.exists():
            print(f"  Warning: {quiz_file} not found")
            continue
        quiz_id, token = upload_quiz_file(quiz_path, headers)
        if quiz_id and token:
            quiz_tokens[quiz_id] = token

    print(f"\nUploaded {len(quiz_tokens)} quizzes total!")
    return quiz_tokens


def print_summary(quiz_tokens: dict):
    """Print summary of created resources."""
    print("\n" + "=" * 60)
    print("DEV ENVIRONMENT INITIALIZED")
    print("=" * 60)

    print(f"\nCreator Web Login (http://localhost:9001):")
    print(f"  Creator ID: {DEFAULT_CREATOR_ID}")
    print(f"  Password: {DEFAULT_CREATOR_PASSWORD}")

    print(f"\nUploaded Quizzes:")
    for quiz_id, token in quiz_tokens.items():
        print(f"  {quiz_id}: {token}")

    print(f"\nWeb Interface: http://localhost:8080")
    print(f"Admin Interface: http://localhost:8081")
    print(f"Creator Interface: http://localhost:9001")
    print(f"API: http://localhost:8000")

    print("=" * 60 + "\n")


def main():
    print("\n" + "=" * 60)
    print("PyQuizHub Dev Initialization")
    print("=" * 60 + "\n")

    # Wait for API
    if not wait_for_api():
        sys.exit(1)

    # Clean database
    clean_database()

    # Upload quizzes
    quiz_tokens = upload_quizzes()

    # Print summary
    print_summary(quiz_tokens)

    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""
Test the Python Knowledge Quiz
"""

import json
import requests

API_URL = "http://localhost:8000"

# Load quiz token
with open("quiz_tokens.json", "r") as f:
    tokens = json.load(f)

python_quiz_token = tokens["python_knowledge_quiz"]["token"]
user_id = "test_python_learner"

print("🎓 Testing Python Knowledge Quiz")
print("=" * 60)

# Start quiz
print("\n1️⃣ Starting quiz...")
response = requests.post(
    f"{API_URL}/quiz/start_quiz",
    json={"token": python_quiz_token, "user_id": user_id},
    headers={"Authorization": "your-secure-user-token-here"}
)

if response.status_code != 200:
    print(f"❌ Failed to start quiz: {response.text}")
    exit(1)

data = response.json()
session_id = data["session_id"]
print(f"✅ Quiz started! Session ID: {session_id}")

# Answer all questions correctly
correct_answers = [
    "correct",  # Q1: list creation
    "correct",  # Q2: comments
    "correct",  # Q3: type(5.0)
    "correct",  # Q4: def keyword
    "correct",  # Q5: len() function
    "correct",  # Q6: array is not valid
    "correct",  # Q7: while loop syntax
    "correct",  # Q8: append() method
    "correct",  # Q9: pip
    "correct",  # Q10: floor division
]

question_num = 1
for answer_value in correct_answers:
    print(f"\n{question_num + 1}️⃣ Answering question {question_num}...")

    response = requests.post(
        f"{API_URL}/quiz/submit_answer/{data['quiz_id']}",
        json={
            "user_id": user_id,
            "session_id": session_id,
            "answer": {"answer": answer_value}
        },
        headers={"Authorization": "your-secure-user-token-here"}
    )

    if response.status_code == 200:
        result = response.json()
        question_data = result.get("question", {})

        if question_data and question_data.get("data", {}).get("type") == "final_message":
            print("✅ Reached final message!")
            final_text = question_data["data"]["text"]
            print("\n" + "=" * 60)
            print("📊 FINAL RESULTS")
            print("=" * 60)
            print(final_text)
            break
        else:
            print(f"✅ Answer submitted successfully")
    else:
        print(f"❌ Failed to submit answer: {response.text}")
        break

    question_num += 1

print("\n" + "=" * 60)
print("✅ Quiz test completed!")
print("=" * 60)

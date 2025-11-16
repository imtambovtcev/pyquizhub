#!/bin/bash

# Script to upload quizzes to PyQuizHub
# Make sure the API server is running before executing

API_URL="http://localhost:8000"
ADMIN_TOKEN="${PYQUIZHUB_ADMIN_TOKEN:-your-secret-admin-token-here}"

echo "🚀 Uploading quizzes to PyQuizHub..."
echo "API URL: $API_URL"
echo ""

# Function to upload a quiz
upload_quiz() {
    local quiz_file=$1
    local quiz_name=$(basename "$quiz_file" .json)

    echo "📤 Uploading: $quiz_name"

    # Create request payload
    local payload=$(jq -n \
        --argfile quiz "$quiz_file" \
        '{quiz: $quiz, creator_id: "admin"}')

    # Upload quiz
    response=$(curl -s -X POST "$API_URL/admin/create_quiz" \
        -H "Content-Type: application/json" \
        -H "Authorization: $ADMIN_TOKEN" \
        -d "$payload")

    # Check response
    if echo "$response" | jq -e '.quiz_id' > /dev/null 2>&1; then
        quiz_id=$(echo "$response" | jq -r '.quiz_id')
        echo "✅ Success! Quiz ID: $quiz_id"

        # Generate a permanent token for this quiz
        token_payload=$(jq -n \
            --arg qid "$quiz_id" \
            '{quiz_id: $qid, type: "permanent"}')

        token_response=$(curl -s -X POST "$API_URL/admin/generate_token" \
            -H "Content-Type: application/json" \
            -H "Authorization: $ADMIN_TOKEN" \
            -d "$token_payload")

        token=$(echo "$token_response" | jq -r '.token')
        echo "🎫 Token: $token"
    else
        echo "❌ Failed: $response"
    fi
    echo ""
}

# Upload main test quizzes
echo "=== Main Test Quizzes ==="
upload_quiz "tests/test_quiz_jsons/simple_quiz.json"
upload_quiz "tests/test_quiz_jsons/complex_weather_quiz.json"
upload_quiz "tests/test_quiz_jsons/joke_quiz_static_api.json"
upload_quiz "tests/test_quiz_jsons/joke_quiz_dynamic_api.json"

# Upload the new practical quiz
echo "=== Practical Quiz ==="
upload_quiz "quizzes/python_knowledge_quiz.json"

echo "🎉 Done!"

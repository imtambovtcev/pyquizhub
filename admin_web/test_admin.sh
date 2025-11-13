#!/bin/bash
# Test script for admin web interface

echo "Testing PyQuizHub Admin Web Interface"
echo "======================================"
echo ""

# Check if admin-web container is running
echo "Checking if admin-web container is running..."
if docker ps | grep -q pyquizhub-admin-web; then
    echo "✓ Admin web container is running"
else
    echo "✗ Admin web container is not running"
    echo "  Start it with: docker compose up -d admin-web"
    exit 1
fi

echo ""
echo "Testing endpoints..."
echo ""

# Test health endpoint
echo "1. Health check:"
curl -s http://localhost:8081/api/health | python3 -m json.tool

echo ""
echo ""

# Test admin interface homepage
echo "2. Homepage (should return HTML):"
curl -s -I http://localhost:8081/ | grep "HTTP\|Content-Type"

echo ""
echo ""

# Test static files
echo "3. CSS file (should return 200):"
curl -s -I http://localhost:8081/static/css/admin.css | grep "HTTP\|Content-Type"

echo ""
echo ""

# Test settings endpoint
echo "4. Settings endpoint:"
curl -s http://localhost:8081/api/settings | python3 -m json.tool | head -20

echo ""
echo ""

echo "======================================"
echo "Admin interface is accessible at:"
echo "  http://localhost:8081"
echo ""
echo "Available pages:"
echo "  - Dashboard:      http://localhost:8081/"
echo "  - Quizzes:        http://localhost:8081/quizzes"
echo "  - Create Quiz:    http://localhost:8081/quiz/create"
echo "  - Tokens:         http://localhost:8081/tokens"
echo "  - Users:          http://localhost:8081/users"
echo "  - Results:        http://localhost:8081/results"
echo "  - Sessions:       http://localhost:8081/sessions"
echo "  - Settings:       http://localhost:8081/settings"

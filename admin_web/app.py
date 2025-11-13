"""
Admin Web Interface for PyQuizHub

Standalone admin service for managing quizzes, tokens, users, and results.
Runs independently from the user-facing web interface.
"""

from flask import Flask, render_template, request, jsonify, send_from_directory
from flask_cors import CORS
import requests
import os
import json
from typing import Dict, Any

# Simple logger since we're standalone
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__,
            template_folder='templates',
            static_folder='static')
CORS(app)

# Configuration from environment variables


def _require_env(var_name: str) -> str:
    val = os.environ.get(var_name)
    if val is None:
        raise RuntimeError(
            f"Missing required environment variable: {var_name}")
    return val


API_BASE_URL = _require_env('PYQUIZHUB_API_URL')
ADMIN_TOKEN = _require_env('PYQUIZHUB_ADMIN_TOKEN')
PORT = int(_require_env('ADMIN_PORT'))


def make_admin_request(endpoint: str, method: str = 'GET',
                       json_data: Dict[str, Any] = None) -> tuple:
    """
    Make an authenticated request to the admin API.

    Args:
        endpoint: API endpoint path (without /admin prefix)
        method: HTTP method
        json_data: JSON payload for POST/PUT requests

    Returns:
        Tuple of (response_data, status_code)
    """
    headers = {
        'Content-Type': 'application/json',
        'Authorization': ADMIN_TOKEN
    }

    url = f"{API_BASE_URL}/admin/{endpoint}"
    logger.debug(f"Admin API request: {method} {url}")

    try:
        if method == 'GET':
            response = requests.get(url, headers=headers, timeout=10)
        elif method == 'POST':
            response = requests.post(
                url, headers=headers, json=json_data, timeout=10)
        elif method == 'DELETE':
            response = requests.delete(url, headers=headers, timeout=10)
        else:
            return {"error": f"Unsupported method: {method}"}, 405

        return response.json(), response.status_code
    except requests.exceptions.RequestException as e:
        logger.error(f"API request failed: {e}")
        return {"error": str(e)}, 500
    except json.JSONDecodeError:
        return {"error": "Invalid JSON response from API"}, 500


# ============================================================================
# Routes - Pages
# ============================================================================

@app.route('/')
def index():
    """Admin dashboard home page."""
    return render_template('index.html')


@app.route('/quizzes')
def quizzes_page():
    """Quiz management page."""
    return render_template('quizzes.html')


@app.route('/quiz/create')
def create_quiz_page():
    """Quiz creation page."""
    return render_template('create_quiz.html')


@app.route('/quiz/<quiz_id>')
def quiz_detail_page(quiz_id):
    """Quiz detail and management page."""
    return render_template('quiz_detail.html', quiz_id=quiz_id)


@app.route('/tokens')
def tokens_page():
    """Token management page."""
    return render_template('tokens.html')


@app.route('/users')
def users_page():
    """User management page."""
    return render_template('users.html')


@app.route('/results')
def results_page():
    """Results viewing page."""
    return render_template('results.html')


@app.route('/sessions')
def sessions_page():
    """Active sessions monitoring page."""
    return render_template('sessions.html')


@app.route('/settings')
def settings_page():
    """System settings and configuration page."""
    return render_template('settings.html')


# ============================================================================
# API Routes - Quiz Management
# ============================================================================

@app.route('/api/quizzes', methods=['GET'])
def get_quizzes():
    """Get all quizzes."""
    data, status = make_admin_request('all_quizzes')
    return jsonify(data), status


@app.route('/api/quiz/<quiz_id>', methods=['GET'])
def get_quiz(quiz_id):
    """Get a specific quiz."""
    data, status = make_admin_request(f'quiz/{quiz_id}')
    return jsonify(data), status


@app.route('/api/quiz', methods=['POST'])
def create_quiz():
    """Create a new quiz."""
    quiz_data = request.json
    if not quiz_data or 'quiz' not in quiz_data:
        return jsonify({"error": "Missing quiz data"}), 400

    data, status = make_admin_request('create_quiz', 'POST', quiz_data)
    return jsonify(data), status


@app.route('/api/quiz/<quiz_id>', methods=['DELETE'])
def delete_quiz(quiz_id):
    """Delete a quiz."""
    # Note: delete_quiz endpoint might not exist, need to check
    data, status = make_admin_request(f'delete_quiz/{quiz_id}', 'DELETE')
    return jsonify(data), status


# ============================================================================
# API Routes - Token Management
# ============================================================================

@app.route('/api/tokens', methods=['GET'])
def get_all_tokens():
    """Get all tokens."""
    data, status = make_admin_request('all_tokens')
    return jsonify(data), status


@app.route('/api/tokens/<quiz_id>', methods=['GET'])
def get_quiz_tokens(quiz_id):
    """Get tokens for a specific quiz."""
    # Note: This endpoint might not exist in the API
    data, status = make_admin_request(f'tokens/{quiz_id}')
    return jsonify(data), status


@app.route('/api/token/generate', methods=['POST'])
def generate_token():
    """Generate a new token."""
    token_data = request.json
    if not token_data or 'quiz_id' not in token_data:
        return jsonify({"error": "Missing quiz_id"}), 400

    data, status = make_admin_request('generate_token', 'POST', token_data)
    return jsonify(data), status


@app.route('/api/token/<token>', methods=['DELETE'])
def delete_token(token):
    """Delete a token."""
    data, status = make_admin_request(f'token/{token}', 'DELETE')
    return jsonify(data), status


# ============================================================================
# API Routes - User Management
# ============================================================================

@app.route('/api/users', methods=['GET'])
def get_users():
    """Get all users - NOT IMPLEMENTED IN API YET."""
    # This endpoint doesn't exist in the current API
    return jsonify({
        "error": "User management not yet implemented in API",
        "users": []
    }), 501


@app.route('/api/users', methods=['POST'])
def add_user():
    """Add a new user - NOT IMPLEMENTED IN API YET."""
    return jsonify({
        "error": "User management not yet implemented in API"
    }), 501


# ============================================================================
# API Routes - Results
# ============================================================================

@app.route('/api/results', methods=['GET'])
def get_all_results():
    """Get all results - NOT FULLY IMPLEMENTED."""
    # API only has results per quiz, not all results
    return jsonify({
        "error": "All results endpoint not available. Use /api/results/quiz/<quiz_id>",
        "results": []
    }), 501


@app.route('/api/results/quiz/<quiz_id>', methods=['GET'])
def get_quiz_results(quiz_id):
    """Get results for a specific quiz."""
    data, status = make_admin_request(f'results/{quiz_id}')
    return jsonify(data), status


@app.route('/api/results/user/<user_id>', methods=['GET'])
def get_user_results(user_id):
    """Get results for a specific user - NOT IMPLEMENTED."""
    return jsonify({
        "error": "User results endpoint not yet implemented in API",
        "results": []
    }), 501


# ============================================================================
# API Routes - Sessions
# ============================================================================

@app.route('/api/sessions', methods=['GET'])
def get_all_sessions():
    """Get all active sessions - NOT IMPLEMENTED."""
    return jsonify({
        "error": "Sessions endpoint not yet implemented in API",
        "sessions": []
    }), 501


@app.route('/api/sessions/user/<user_id>', methods=['GET'])
def get_user_sessions(user_id):
    """Get sessions for a specific user - NOT IMPLEMENTED."""
    return jsonify({
        "error": "User sessions endpoint not yet implemented in API",
        "sessions": []
    }), 501


@app.route('/api/sessions/quiz/<quiz_id>', methods=['GET'])
def get_quiz_sessions(quiz_id):
    """Get sessions for a specific quiz - NOT IMPLEMENTED."""
    return jsonify({
        "error": "Quiz sessions endpoint not yet implemented in API",
        "sessions": []
    }), 501


# ============================================================================
# Utility Routes
# ============================================================================

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    try:
        # Check if API is accessible (use root endpoint)
        response = requests.get(f"{API_BASE_URL}/", timeout=5)
        api_healthy = response.status_code == 200
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        api_healthy = False

    return jsonify({
        "admin_web": "healthy",
        "api_connection": "healthy" if api_healthy else "unhealthy",
        "api_url": API_BASE_URL
    }), 200 if api_healthy else 503


@app.route('/api/settings', methods=['GET'])
def get_system_settings():
    """Get system configuration and settings."""
    try:
        # Get config from admin API
        headers = {
            'Authorization': ADMIN_TOKEN
        }
        response = requests.get(
            f"{API_BASE_URL}/admin/config",
            headers=headers,
            timeout=10
        )

        if response.status_code == 200:
            config_data = response.json()

            # Extract key settings
            config = config_data.get('config_data', {})

            settings = {
                "storage_type": config.get('storage', {}).get('type', 'unknown'),
                "database": {
                    "type": config.get('storage', {}).get('type', 'unknown'),
                    "connection_string": "***hidden***" if config.get('storage', {}).get('type') == 'sql' else None
                },
                "api": {
                    "host": config.get('api', {}).get('host', '0.0.0.0'),
                    "port": config.get('api', {}).get('port', 8000)
                },
                "logging": {
                    "level": config.get('logging', {}).get('level', 'INFO'),
                    "format": config.get('logging', {}).get('format', 'json')
                },
                "config_path": config_data.get('config_path', 'unknown'),
                "full_config": config
            }

            return jsonify(settings), 200
        else:
            return jsonify({
                "error": f"Failed to fetch config: {response.status_code}"
            }), response.status_code

    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to get system settings: {e}")
        return jsonify({"error": str(e)}), 500
    except Exception as e:
        logger.error(f"Unexpected error getting settings: {e}")
        return jsonify({"error": str(e)}), 500


# ============================================================================
# Static Files
# ============================================================================

@app.route('/static/<path:filename>')
def serve_static(filename):
    """Serve static files."""
    return send_from_directory('static', filename)


# ============================================================================
# Main
# ============================================================================

if __name__ == '__main__':
    logger.info(f"Starting PyQuizHub Admin Interface on port {PORT}")
    logger.info(f"API URL: {API_BASE_URL}")
    logger.info(
        f"Admin token: {'***' + ADMIN_TOKEN[-4:] if len(ADMIN_TOKEN) > 4 else '****'}")
    app.run(host='0.0.0.0', port=PORT, debug=os.environ.get(
        'DEBUG', 'false').lower() == 'true')

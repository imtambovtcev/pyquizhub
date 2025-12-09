"""
Creator Web Interface for PyQuizHub

Web interface for quiz creators to:
- Create and manage quizzes (JSON upload)
- View statistics for their quizzes
- Generate and manage tokens
- View participant results

Runs independently from admin interface with creator-level permissions.
Requires authentication - creators cannot be anonymous.
"""

from flask import Flask, render_template, request, jsonify, send_from_directory, redirect, url_for, session
from flask_cors import CORS
from functools import wraps
import requests
import os
import json
from typing import Dict, Any

import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__,
            template_folder='templates',
            static_folder='static')
app.secret_key = os.environ.get('FLASK_SECRET_KEY', os.urandom(24).hex())
CORS(app)


def _require_env(var_name: str) -> str:
    val = os.environ.get(var_name)
    if val is None:
        raise RuntimeError(
            f"Missing required environment variable: {var_name}")
    return val


API_BASE_URL = _require_env('PYQUIZHUB_API_URL')
CREATOR_TOKEN = _require_env('PYQUIZHUB_CREATOR_TOKEN')
PORT = int(os.environ.get('CREATOR_PORT', '9001'))
# Password for creator login - separate from CREATOR_TOKEN which is for
# API auth
CREATOR_PASSWORD = os.environ.get('CREATOR_PASSWORD', 'creator123')


# ============================================================================
# Authentication
# ============================================================================

def login_required(f):
    """Decorator to require authentication for routes."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'creator_id' not in session:
            # For API routes, return 401
            if request.path.startswith('/api/'):
                return jsonify({"error": "Authentication required"}), 401
            # For page routes, redirect to login
            return redirect(url_for('login_page'))
        return f(*args, **kwargs)
    return decorated_function


def get_current_creator_id() -> str | None:
    """Get the current logged-in creator ID."""
    return session.get('creator_id')


def make_creator_request(endpoint: str, method: str = 'GET',
                         json_data: Dict[str, Any] = None,
                         creator_id: str = None) -> tuple:
    """
    Make an authenticated request to the creator API.

    Args:
        endpoint: API endpoint path (without /creator prefix)
        method: HTTP method
        json_data: JSON payload for POST/PUT requests
        creator_id: Creator ID for X-User-ID header

    Returns:
        Tuple of (response_data, status_code)
    """
    headers = {
        'Content-Type': 'application/json',
        'Authorization': CREATOR_TOKEN
    }
    if creator_id:
        headers['X-User-ID'] = creator_id

    url = f"{API_BASE_URL}/creator/{endpoint}"
    logger.debug(f"Creator API request: {method} {url}")

    try:
        if method == 'GET':
            response = requests.get(url, headers=headers, timeout=10)
        elif method == 'POST':
            response = requests.post(
                url, headers=headers, json=json_data, timeout=10)
        elif method == 'PUT':
            response = requests.put(
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
# Routes - Authentication
# ============================================================================

@app.route('/login', methods=['GET'])
def login_page():
    """Login page."""
    if 'creator_id' in session:
        return redirect(url_for('index'))
    return render_template('login.html')


# Simple in-memory user storage for development
# In production, this should be backed by a database
_registered_creators: dict[str, str] = {}  # creator_id -> password_hash


def _hash_password(password: str) -> str:
    """Simple password hashing (use bcrypt in production)."""
    import hashlib
    return hashlib.sha256(password.encode()).hexdigest()


@app.route('/api/register', methods=['POST'])
def register():
    """Register a new creator."""
    data = request.json
    if not data:
        return jsonify({"error": "Missing request body"}), 400

    creator_id = data.get('creator_id', '').strip()
    password = data.get('password', '')

    if not creator_id:
        return jsonify({"error": "Creator ID is required"}), 400

    if len(creator_id) < 3:
        return jsonify(
            {"error": "Creator ID must be at least 3 characters"}), 400

    if len(password) < 4:
        return jsonify(
            {"error": "Password must be at least 4 characters"}), 400

    # Check if creator already exists
    if creator_id in _registered_creators:
        return jsonify({"error": "Creator ID already exists"}), 409

    # Register the creator
    _registered_creators[creator_id] = _hash_password(password)
    logger.info(f"Creator registered: {creator_id}")

    # Auto-login after registration
    session['creator_id'] = creator_id
    session['creator_name'] = creator_id

    return jsonify({"success": True, "creator_id": creator_id}), 200


@app.route('/api/login', methods=['POST'])
def login():
    """Authenticate creator."""
    data = request.json
    if not data:
        return jsonify({"error": "Missing request body"}), 400

    creator_id = data.get('creator_id', '').strip()
    password = data.get('password', '')

    if not creator_id:
        return jsonify({"error": "Creator ID is required"}), 400

    # Check registered creators first
    if creator_id in _registered_creators:
        if _registered_creators[creator_id] == _hash_password(password):
            session['creator_id'] = creator_id
            session['creator_name'] = creator_id
            logger.info(f"Creator logged in: {creator_id}")
            return jsonify({"success": True, "creator_id": creator_id}), 200
        return jsonify({"error": "Invalid password"}), 401

    # Fall back to shared password for dev/testing
    if password == CREATOR_PASSWORD:
        session['creator_id'] = creator_id
        session['creator_name'] = creator_id
        logger.info(f"Creator logged in (shared password): {creator_id}")
        return jsonify({"success": True, "creator_id": creator_id}), 200

    return jsonify({"error": "Invalid credentials"}), 401


@app.route('/api/logout', methods=['POST'])
def logout():
    """Log out the current creator."""
    creator_id = session.pop('creator_id', None)
    session.pop('creator_name', None)
    if creator_id:
        logger.info(f"Creator logged out: {creator_id}")
    return jsonify({"success": True}), 200


@app.route('/logout')
def logout_page():
    """Log out and redirect to login."""
    session.pop('creator_id', None)
    session.pop('creator_name', None)
    return redirect(url_for('login_page'))


# ============================================================================
# Routes - Pages (Protected)
# ============================================================================

@app.route('/')
@login_required
def index():
    """Creator dashboard home page."""
    return render_template('index.html', creator_id=get_current_creator_id())


@app.route('/quizzes')
@login_required
def quizzes_page():
    """Quiz management page - list creator's quizzes."""
    return render_template('quizzes.html', creator_id=get_current_creator_id())


@app.route('/quiz/create')
@login_required
def create_quiz_page():
    """Quiz creation page - JSON upload."""
    return render_template(
        'create_quiz.html',
        creator_id=get_current_creator_id())


@app.route('/quiz/<quiz_id>')
@login_required
def quiz_detail_page(quiz_id):
    """Quiz detail page - view quiz and statistics."""
    return render_template(
        'quiz_detail.html',
        quiz_id=quiz_id,
        creator_id=get_current_creator_id())


@app.route('/quiz/<quiz_id>/statistics')
@login_required
def quiz_statistics_page(quiz_id):
    """Quiz statistics page - detailed analytics."""
    return render_template(
        'statistics.html',
        quiz_id=quiz_id,
        creator_id=get_current_creator_id())


@app.route('/tokens')
@login_required
def tokens_page():
    """Token management page."""
    return render_template('tokens.html', creator_id=get_current_creator_id())


# ============================================================================
# API Routes - Quiz Management
# ============================================================================

@app.route('/api/quizzes', methods=['GET'])
@login_required
def get_quizzes():
    """Get creator's quizzes (placeholder - needs API endpoint)."""
    creator_id = get_current_creator_id()
    # TODO: Need creator-specific endpoint to list only their quizzes
    # For now, return empty list
    return jsonify({"quizzes": {}, "creator_id": creator_id,
                   "message": "List creator's quizzes - endpoint needed"}), 200


@app.route('/api/quiz/<quiz_id>', methods=['GET'])
@login_required
def get_quiz(quiz_id):
    """Get a specific quiz."""
    creator_id = get_current_creator_id()
    data, status = make_creator_request(
        f'quiz/{quiz_id}', creator_id=creator_id)
    return jsonify(data), status


@app.route('/api/validate-quiz', methods=['POST'])
@login_required
def validate_quiz():
    """Validate a quiz JSON structure."""
    quiz_data = request.json
    if not quiz_data:
        return jsonify({"error": "Missing quiz data"}), 400

    try:
        from pyquizhub.core.engine.json_validator import QuizJSONValidator

        result = QuizJSONValidator.validate(quiz_data)

        return jsonify({
            "errors": result.get("errors", []),
            "warnings": result.get("warnings", [])
        }), 200

    except ImportError as e:
        logger.error(f"Failed to import validator: {e}")
        return jsonify({"error": "Validator not available"}), 500
    except Exception as e:
        logger.error(f"Validation error: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/quiz', methods=['POST'])
@login_required
def create_quiz():
    """Create a new quiz."""
    quiz_data = request.json
    if not quiz_data or 'quiz' not in quiz_data:
        return jsonify({"error": "Missing quiz data"}), 400

    creator_id = get_current_creator_id()
    # Set creator_id in the request
    quiz_data['creator_id'] = creator_id
    data, status = make_creator_request(
        'create_quiz', 'POST', quiz_data, creator_id=creator_id)
    return jsonify(data), status


# ============================================================================
# API Routes - Token Management
# ============================================================================

@app.route('/api/token/generate', methods=['POST'])
@login_required
def generate_token():
    """Generate a new token for a quiz."""
    token_data = request.json
    if not token_data or 'quiz_id' not in token_data:
        return jsonify({"error": "Missing quiz_id"}), 400

    creator_id = get_current_creator_id()
    data, status = make_creator_request(
        'generate_token', 'POST', token_data, creator_id=creator_id)
    return jsonify(data), status


# ============================================================================
# API Routes - Statistics & Results
# ============================================================================

@app.route('/api/quiz/<quiz_id>/results', methods=['GET'])
@login_required
def get_quiz_results(quiz_id):
    """Get results for a specific quiz."""
    creator_id = get_current_creator_id()
    data, status = make_creator_request(
        f'results/{quiz_id}', creator_id=creator_id)
    return jsonify(data), status


@app.route('/api/quiz/<quiz_id>/participants', methods=['GET'])
@login_required
def get_quiz_participants(quiz_id):
    """Get participants who took a quiz."""
    creator_id = get_current_creator_id()
    data, status = make_creator_request(
        f'participated_users/{quiz_id}', creator_id=creator_id)
    return jsonify(data), status


@app.route('/api/quiz/<quiz_id>/statistics', methods=['GET'])
@login_required
def get_quiz_statistics(quiz_id):
    """Get aggregated statistics for a quiz."""
    creator_id = get_current_creator_id()

    # Get results
    results_data, results_status = make_creator_request(
        f'results/{quiz_id}', creator_id=creator_id)

    if results_status != 200:
        return jsonify(results_data), results_status

    # Calculate statistics from results
    results = results_data.get('results', {})

    total_participants = len(results)
    total_completions = 0
    scores = []

    for user_id, sessions in results.items():
        for session_id, result in sessions.items():
            total_completions += 1
            # Extract score if available
            result_scores = result.get('scores', {})
            if 'score' in result_scores:
                scores.append(result_scores['score'])

    stats = {
        'quiz_id': quiz_id,
        'total_participants': total_participants,
        'total_completions': total_completions,
        'average_score': sum(scores) / len(scores) if scores else 0,
        'min_score': min(scores) if scores else 0,
        'max_score': max(scores) if scores else 0,
        'score_distribution': _calculate_distribution(scores) if scores else {}
    }

    return jsonify(stats), 200


def _calculate_distribution(scores: list) -> dict:
    """Calculate score distribution in quartiles."""
    if not scores:
        return {}

    sorted_scores = sorted(scores)
    n = len(sorted_scores)

    return {
        '0-25%': len([s for s in scores if s <= sorted_scores[n // 4]]) if n > 0 else 0,
        '25-50%': len([s for s in scores if sorted_scores[n // 4] < s <= sorted_scores[n // 2]]) if n > 1 else 0,
        '50-75%': len([s for s in scores if sorted_scores[n // 2] < s <= sorted_scores[3 * n // 4]]) if n > 2 else 0,
        '75-100%': len([s for s in scores if s > sorted_scores[3 * n // 4]]) if n > 3 else 0,
    }


# ============================================================================
# Utility Routes
# ============================================================================

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    try:
        response = requests.get(f"{API_BASE_URL}/", timeout=5)
        api_healthy = response.status_code == 200
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        api_healthy = False

    return jsonify({
        "creator_web": "healthy",
        "api_connection": "healthy" if api_healthy else "unhealthy",
        "api_url": API_BASE_URL
    }), 200 if api_healthy else 503


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
    logger.info(f"Starting PyQuizHub Creator Interface on port {PORT}")
    logger.info(f"API URL: {API_BASE_URL}")
    logger.info(
        f"Creator token: {'***' + CREATOR_TOKEN[-4:] if len(CREATOR_TOKEN) > 4 else '****'}")
    app.run(host='0.0.0.0', port=PORT, debug=os.environ.get(
        'DEBUG', 'false').lower() == 'true')

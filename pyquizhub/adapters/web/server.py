from flask import Flask, send_from_directory, request, jsonify
from flask_cors import CORS
import requests
import os
from pyquizhub.config.settings import get_config_manager
from pyquizhub.config.config_utils import get_logger

logger = get_logger(__name__)

app = Flask(__name__)
CORS(app)

# Load config and get API URL and token
config_manager = get_config_manager()
config_manager.load()

API_BASE_URL = config_manager.api_base_url
USER_TOKEN = config_manager.get_token("user")


def proxy_request(path, method='GET', json=None):
    """Proxy requests to the core API with user token."""
    headers = {
        'Content-Type': 'application/json',
        'Authorization': USER_TOKEN
    }

    url = f"{API_BASE_URL}/{path}"
    logger.debug(f"Proxying {method} request to: {url}")

    try:
        if method == 'GET':
            response = requests.get(url, headers=headers)
        elif method == 'POST':
            response = requests.post(url, headers=headers, json=json)

        return jsonify(response.json()), response.status_code
    except Exception as e:
        logger.error(f"Error proxying request: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/')
def index():
    return send_from_directory('.', 'index.html')


@app.route('/style.css')
def style():
    return send_from_directory('.', 'style.css')


@app.route('/app.js')
def app_js():
    return send_from_directory('.', 'app.js')


@app.route('/api/quiz/start_quiz', methods=['POST'])
def start_quiz():
    return proxy_request('quiz/start_quiz', 'POST', request.json)


@app.route('/api/quiz/submit_answer/<quiz_id>', methods=['POST'])
def submit_answer(quiz_id):
    return proxy_request(f'quiz/submit_answer/{quiz_id}', 'POST', request.json)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)

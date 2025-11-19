"""
Tests for admin web adapter status functionality.

This module tests the /api/adapters/status endpoint in the admin web interface.
"""
import pytest
import json
from unittest.mock import patch, MagicMock
import os
import sys

# Mock environment variables before importing admin_web.app
os.environ['PYQUIZHUB_API_URL'] = 'http://test-api:8000'
os.environ['PYQUIZHUB_ADMIN_TOKEN'] = 'test-admin-token'
os.environ['ADMIN_PORT'] = '8081'

# Add admin_web to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'admin_web'))

from admin_web.app import app as admin_app


@pytest.fixture
def admin_client():
    """Create a Flask test client for admin web."""
    admin_app.config['TESTING'] = True
    with admin_app.test_client() as client:
        yield client


def test_adapter_status_endpoint_exists(admin_client):
    """Test that the adapter status endpoint exists."""
    response = admin_client.get('/api/adapters/status')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert 'adapters' in data


def test_adapter_status_cli_always_available(admin_client):
    """Test that CLI adapter is always shown as available."""
    response = admin_client.get('/api/adapters/status')
    assert response.status_code == 200
    data = json.loads(response.data)

    assert 'cli' in data['adapters']
    assert data['adapters']['cli']['status'] == 'available'
    assert data['adapters']['cli']['name'] == 'CLI Adapter'
    assert 'always available' in data['adapters']['cli']['description'].lower()


@patch('admin_web.app.requests.get')
def test_adapter_status_web_running(mock_get, admin_client):
    """Test web adapter status when web service is running."""
    # Mock successful response from web service
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_get.return_value = mock_response

    response = admin_client.get('/api/adapters/status')
    assert response.status_code == 200
    data = json.loads(response.data)

    assert 'web' in data['adapters']
    assert data['adapters']['web']['status'] == 'running'
    assert data['adapters']['web']['name'] == 'Web Adapter'
    assert data['adapters']['web']['url'] == 'http://localhost:8080'


@patch('admin_web.app.requests.get')
def test_adapter_status_web_stopped(mock_get, admin_client):
    """Test web adapter status when web service is not responding."""
    # Mock connection error
    import requests
    mock_get.side_effect = requests.exceptions.ConnectionError()

    response = admin_client.get('/api/adapters/status')
    assert response.status_code == 200
    data = json.loads(response.data)

    assert 'web' in data['adapters']
    assert data['adapters']['web']['status'] == 'stopped'
    assert data['adapters']['web']['url'] is None


@patch.dict(os.environ, {'TELEGRAM_BOT_TOKEN': '123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11'})
def test_adapter_status_telegram_configured(admin_client):
    """Test telegram adapter status when token is configured."""
    response = admin_client.get('/api/adapters/status')
    assert response.status_code == 200
    data = json.loads(response.data)

    assert 'telegram' in data['adapters']
    assert data['adapters']['telegram']['status'] == 'running'
    assert data['adapters']['telegram']['name'] == 'Telegram Bot'
    assert 'configured' in data['adapters']['telegram']['description'].lower()


@patch.dict(os.environ, {'TELEGRAM_BOT_TOKEN': ''}, clear=True)
def test_adapter_status_telegram_not_configured(admin_client):
    """Test telegram adapter status when token is not configured."""
    response = admin_client.get('/api/adapters/status')
    assert response.status_code == 200
    data = json.loads(response.data)

    assert 'telegram' in data['adapters']
    assert data['adapters']['telegram']['status'] == 'not_configured'
    assert 'no token' in data['adapters']['telegram']['description'].lower()


def test_adapter_status_returns_all_adapters(admin_client):
    """Test that all three adapters are returned."""
    response = admin_client.get('/api/adapters/status')
    assert response.status_code == 200
    data = json.loads(response.data)

    assert len(data['adapters']) == 3
    assert 'cli' in data['adapters']
    assert 'web' in data['adapters']
    assert 'telegram' in data['adapters']


def test_adapter_status_json_structure(admin_client):
    """Test that adapter status has the correct JSON structure."""
    response = admin_client.get('/api/adapters/status')
    assert response.status_code == 200
    data = json.loads(response.data)

    # Check each adapter has required fields
    for adapter_id in ['cli', 'web', 'telegram']:
        adapter = data['adapters'][adapter_id]
        assert 'name' in adapter
        assert 'status' in adapter
        assert 'description' in adapter
        assert isinstance(adapter['name'], str)
        assert isinstance(adapter['status'], str)
        assert isinstance(adapter['description'], str)

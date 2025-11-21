"""Pytest configuration for E2E tests."""
from __future__ import annotations

import subprocess
import time
from typing import Generator

import pytest
import requests


@pytest.fixture(scope="session")
def docker_services() -> Generator[None, None, None]:
    """Ensure Docker services are running for E2E tests."""
    # Check if services are already running
    result = subprocess.run(
        ["docker", "compose", "ps", "-q"],
        capture_output=True,
        text=True,
        check=False
    )

    if not result.stdout.strip():
        # Start services
        subprocess.run(
            ["docker", "compose", "up", "-d"],
            check=True
        )
        # Wait for services to be ready
        time.sleep(10)

    # Wait for API to be ready
    max_retries = 30
    for _ in range(max_retries):
        try:
            response = requests.get("http://localhost:8000/health", timeout=1)
            if response.status_code == 200:
                break
        except requests.exceptions.RequestException:
            pass
        time.sleep(1)

    # Wait for web adapter to be ready
    for _ in range(max_retries):
        try:
            response = requests.get("http://localhost:8080", timeout=1)
            if response.status_code == 200:
                break
        except requests.exceptions.RequestException:
            pass
        time.sleep(1)

    yield

    # Note: We don't tear down services here as they may be used across
    # multiple test sessions


@pytest.fixture
def api_base_url() -> str:
    """Return the API base URL."""
    return "http://localhost:8000"


@pytest.fixture
def web_base_url() -> str:
    """Return the web adapter base URL."""
    return "http://localhost:8080"


@pytest.fixture
def admin_token() -> str:
    """Return the admin token for API calls."""
    return "your-secure-admin-token-here"


@pytest.fixture
def user_token() -> str:
    """Return the user token for API calls."""
    return "your-secure-user-token-here"

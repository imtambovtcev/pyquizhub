"""
Tests for Color Analysis API.

These tests verify the Color API functionality for file upload demonstrations.
The Color API must be running for these tests to pass.

Start Color API:
    python scripts/color_api.py
    # Or with Docker: docker compose -f docker-compose.dev.yml up color-api
"""

import pytest
import requests
import io
from PIL import Image


COLOR_API_URL = "http://localhost:5001"


def is_color_api_available():
    """Check if Color API is running."""
    try:
        response = requests.get(f"{COLOR_API_URL}/health", timeout=1)
        return response.status_code == 200
    except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
        return False


# Skip all tests in this module if Color API is not running
pytestmark = pytest.mark.skipif(
    not is_color_api_available(),
    reason="Color API not running (start with: python scripts/color_api.py)"
)


@pytest.fixture
def create_colored_image():
    """Fixture to create test images with specific colors."""
    def _create_image(color_rgb, size=(100, 100)):
        img = Image.new('RGB', size, color=color_rgb)
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='PNG')
        img_bytes.seek(0)
        return img_bytes
    return _create_image


def test_color_api_health():
    """Test Color API health check endpoint."""
    response = requests.get(f"{COLOR_API_URL}/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "Color Analysis API"


def test_color_api_documentation():
    """Test Color API documentation endpoint."""
    response = requests.get(f"{COLOR_API_URL}/")

    assert response.status_code == 200
    data = response.json()
    assert "endpoints" in data
    assert "/analyze" in data["endpoints"]


@pytest.mark.parametrize("color_name,color_rgb,expected_name", [
    ("Red", (255, 0, 0), "red"),
    ("Green", (0, 255, 0), "green"),
    ("Blue", (0, 0, 255), "blue"),
    ("Yellow", (255, 255, 0), "yellow"),
    ("Cyan", (0, 255, 255), "cyan"),
    ("Magenta", (255, 0, 255), "magenta"),
    ("White", (255, 255, 255), "white"),
    ("Black", (0, 0, 0), "black"),
    ("Gray", (128, 128, 128), "gray"),
    ("Orange", (255, 165, 0), "orange"),
])
def test_color_detection(
        create_colored_image,
        color_name,
        color_rgb,
        expected_name):
    """Test dominant color detection for various colors."""
    # Create test image
    img_bytes = create_colored_image(color_rgb)

    # Send to Color API
    response = requests.post(
        f"{COLOR_API_URL}/analyze",
        files={"image": ("test.png", img_bytes, "image/png")},
        timeout=5
    )

    # Verify response
    assert response.status_code == 200, f"API returned {
        response.status_code}: {
        response.text}"

    data = response.json()
    assert "dominant_color" in data
    assert "color_name" in data
    assert "status" in data
    assert data["status"] == "success"

    # Verify color detection
    assert data["color_name"] == expected_name, \
        f"Expected {expected_name}, got {data['color_name']} for {color_name}"

    # Verify hex color format
    assert data["dominant_color"].startswith("#")
    assert len(data["dominant_color"]) == 7  # #RRGGBB


def test_color_api_no_image():
    """Test Color API error handling when no image is provided."""
    response = requests.post(f"{COLOR_API_URL}/analyze")

    assert response.status_code == 400
    data = response.json()
    assert "error" in data


def test_color_api_empty_filename():
    """Test Color API error handling with empty filename."""
    files = {"image": ("", io.BytesIO(b""), "image/png")}
    response = requests.post(f"{COLOR_API_URL}/analyze", files=files)

    assert response.status_code == 400
    data = response.json()
    assert "error" in data


def test_color_api_invalid_image():
    """Test Color API error handling with invalid image data."""
    files = {"image": ("test.png", io.BytesIO(b"not an image"), "image/png")}
    response = requests.post(f"{COLOR_API_URL}/analyze", files=files)

    assert response.status_code == 400
    data = response.json()
    assert "error" in data
    assert "Invalid image" in data["error"] or "Processing failed" in data["error"]


def test_color_api_various_image_formats(create_colored_image):
    """Test Color API with different image formats."""
    formats = ["PNG", "JPEG"]
    color_rgb = (255, 0, 0)  # Red

    for fmt in formats:
        # Create image in specific format
        img = Image.new('RGB', (100, 100), color=color_rgb)
        img_bytes = io.BytesIO()
        img.save(img_bytes, format=fmt)
        img_bytes.seek(0)

        # Test with Color API
        response = requests.post(
            f"{COLOR_API_URL}/analyze",
            files={"image": (f"test.{fmt.lower()}", img_bytes, f"image/{fmt.lower()}")},
            timeout=5
        )

        assert response.status_code == 200, \
            f"Failed for format {fmt}: {response.status_code}"

        data = response.json()
        assert data["status"] == "success"
        assert data["color_name"] == "red"


def test_color_api_large_image(create_colored_image):
    """Test Color API with larger image."""
    # Create larger image (500x500)
    img = Image.new('RGB', (500, 500), color=(0, 255, 0))  # Green
    img_bytes = io.BytesIO()
    img.save(img_bytes, format='PNG')
    img_bytes.seek(0)

    response = requests.post(
        f"{COLOR_API_URL}/analyze",
        files={"image": ("large.png", img_bytes, "image/png")},
        timeout=5
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["color_name"] == "green"

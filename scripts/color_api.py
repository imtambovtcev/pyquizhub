#!/usr/bin/env python3
"""
Test API for dominant color detection.

This simple API receives an image file and returns the dominant color.
Used for testing PyQuizHub file upload functionality.

Run: python scripts/color_api.py
"""

from flask import Flask, request, jsonify
from PIL import Image
import io
from collections import Counter

app = Flask(__name__)


def get_dominant_color(image_data: bytes) -> str:
    """
    Extract dominant color from image.

    Args:
        image_data: Image binary data

    Returns:
        Hex color string (e.g., "#FF5733")
    """
    try:
        # Open image
        img = Image.open(io.BytesIO(image_data))

        # Convert to RGB if needed
        if img.mode != 'RGB':
            img = img.convert('RGB')

        # Resize for faster processing
        img = img.resize((150, 150))

        # Get all pixels
        pixels = list(img.getdata())

        # Find most common color
        most_common = Counter(pixels).most_common(1)[0][0]

        # Convert to hex
        hex_color = '#{:02x}{:02x}{:02x}'.format(*most_common)

        return hex_color

    except Exception as e:
        raise ValueError(f"Failed to process image: {str(e)}")


@app.route('/analyze', methods=['POST'])
def analyze_image():
    """
    Analyze image and return dominant color.

    Expects:
        - multipart/form-data with 'image' file

    Returns:
        JSON: {
            "dominant_color": "#RRGGBB",
            "color_name": "approximate color name"
        }
    """
    # Check if file is present
    if 'image' not in request.files:
        return jsonify({
            "error": "No image file provided",
            "message": "Please upload an image file with key 'image'"
        }), 400

    file = request.files['image']

    # Check if file has a filename
    if file.filename == '':
        return jsonify({
            "error": "Empty filename",
            "message": "No file selected"
        }), 400

    try:
        # Read file data
        image_data = file.read()

        # Get dominant color
        dominant_color = get_dominant_color(image_data)

        # Approximate color name
        color_name = approximate_color_name(dominant_color)

        return jsonify({
            "dominant_color": dominant_color,
            "color_name": color_name,
            "status": "success"
        }), 200

    except ValueError as e:
        return jsonify({
            "error": "Invalid image",
            "message": str(e)
        }), 400
    except Exception as e:
        return jsonify({
            "error": "Processing failed",
            "message": str(e)
        }), 500


def approximate_color_name(hex_color: str) -> str:
    """
    Get approximate color name from hex code.

    Args:
        hex_color: Hex color string (e.g., "#FF5733")

    Returns:
        Approximate color name
    """
    # Remove '#' and convert to RGB
    hex_color = hex_color.lstrip('#')
    r, g, b = int(hex_color[0:2], 16), int(
        hex_color[2:4], 16), int(hex_color[4:6], 16)

    # Simple color approximation based on RGB values
    if r > 200 and g < 100 and b < 100:
        return "red"
    elif r < 100 and g > 200 and b < 100:
        return "green"
    elif r < 100 and g < 100 and b > 200:
        return "blue"
    elif r > 200 and g > 200 and b < 100:
        return "yellow"
    elif r > 200 and g < 100 and b > 200:
        return "magenta"
    elif r < 100 and g > 200 and b > 200:
        return "cyan"
    elif r > 200 and g > 150 and b < 100:
        return "orange"
    elif r > 150 and g < 100 and b > 150:
        return "purple"
    elif r > 200 and g > 200 and b > 200:
        return "white"
    elif r < 50 and g < 50 and b < 50:
        return "black"
    elif abs(r - g) < 30 and abs(g - b) < 30 and abs(r - b) < 30:
        return "gray"
    elif r > 150 and g > 100 and b < 100:
        return "brown"
    else:
        return "mixed"


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint."""
    return jsonify({
        "status": "healthy",
        "service": "Color Analysis API",
        "version": "1.0"
    }), 200


@app.route('/', methods=['GET'])
def index():
    """API documentation."""
    return jsonify({
        "service": "Color Analysis API",
        "version": "1.0",
        "endpoints": {
            "/analyze": {
                "method": "POST",
                "description": "Analyze image and return dominant color",
                "params": {
                    "image": "Image file (multipart/form-data)"
                },
                "response": {
                    "dominant_color": "Hex color code (e.g., #FF5733)",
                    "color_name": "Approximate color name (e.g., 'red')",
                    "status": "success"
                }
            },
            "/health": {
                "method": "GET",
                "description": "Health check endpoint"
            }
        },
        "example_curl": "curl -X POST -F 'image=@photo.jpg' http://localhost:5001/analyze"
    }), 200


if __name__ == '__main__':
    print("=" * 60)
    print("Color Analysis API Starting...")
    print("=" * 60)
    print("API will be available at: http://localhost:5001")
    print("")
    print("Endpoints:")
    print("  GET  /            - API documentation")
    print("  GET  /health      - Health check")
    print("  POST /analyze     - Analyze image dominant color")
    print("")
    print("Example usage:")
    print("  curl -X POST -F 'image=@photo.jpg' http://localhost:5001/analyze")
    print("=" * 60)
    print("")

    # Run on port 5001 to avoid conflicts with PyQuizHub API (port 8000)
    app.run(host='0.0.0.0', port=5001, debug=True)

FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install poetry for dependency management
RUN pip install poetry

# Copy pyproject.toml and poetry.lock for pyquizhub package
COPY pyproject.toml poetry.lock* README.md ./

# Copy pyquizhub package (needed for validation imports)
COPY pyquizhub ./pyquizhub

# Install pyquizhub dependencies (for validator)
RUN poetry config virtualenvs.create false && \
    poetry install --no-interaction --no-ansi --only main

# Note: Flask, flask-cors, and requests are already installed by poetry

# Copy creator web application
COPY creator_web/ /app/creator_web/

WORKDIR /app/creator_web

# Expose port
EXPOSE 9001

# Run the application
CMD ["python", "app.py"]

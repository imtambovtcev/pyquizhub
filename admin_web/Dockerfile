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
# No need to reinstall with pip (removes version conflict)

# Copy admin web application
COPY admin_web/ /app/admin_web/

WORKDIR /app/admin_web

# Expose port
EXPOSE 8081

# Run the application
CMD ["python", "app.py"]

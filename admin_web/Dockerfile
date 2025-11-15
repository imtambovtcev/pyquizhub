FROM python:3.10-slim

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

# Install additional Flask dependencies for admin web
RUN pip install --no-cache-dir \
    flask==3.0.0 \
    flask-cors==4.0.0 \
    requests==2.31.0

# Copy admin web application
COPY admin_web/ /app/admin_web/

WORKDIR /app/admin_web

# Expose port
EXPOSE 8081

# Run the application
CMD ["python", "app.py"]

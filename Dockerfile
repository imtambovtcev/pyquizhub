FROM python:3.10-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install poetry
RUN pip install poetry

# Copy dependency files and README (needed for poetry install)
COPY pyproject.toml poetry.lock* README.md ./

# Copy the package source (needed for poetry install)
COPY pyquizhub ./pyquizhub

# Configure poetry to not create virtual environment
RUN poetry config virtualenvs.create false

# Install dependencies
RUN poetry install --no-interaction --no-ansi

# Copy the rest of the project
COPY . .

# Create data directory for file storage (if needed)
RUN mkdir -p /app/data

# Expose port
EXPOSE 8000

# Run the application
# Config will be auto-discovered or set via PYQUIZHUB_CONFIG_PATH env var
CMD ["poetry", "run", "uvicorn", "pyquizhub.main:app", "--host", "0.0.0.0", "--port", "8000"]
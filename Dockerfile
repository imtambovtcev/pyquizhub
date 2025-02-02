FROM python:3.10-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install poetry
RUN pip install poetry

# Copy the entire project
COPY . .

# Copy config.yaml
COPY pyquizhub/config/config.yaml /app/config/config.yaml

# Configure poetry to not create virtual environment
RUN poetry config virtualenvs.create false

# Install dependencies
RUN poetry install

# Expose port
EXPOSE 8000

# Run the application
CMD ["poetry", "run", "uvicorn", "pyquizhub.main:app", "--host", "0.0.0.0", "--port", "8000"]
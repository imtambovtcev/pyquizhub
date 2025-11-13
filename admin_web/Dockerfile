FROM python:3.10-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
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

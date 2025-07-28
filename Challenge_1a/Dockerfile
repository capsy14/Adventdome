FROM --platform=linux/amd64 python:3.11-slim

WORKDIR /app

# Install system dependencies for PyMuPDF
RUN apt-get update && apt-get install -y \
    build-essential \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip first
RUN pip install --upgrade pip

# Copy Docker-optimized requirements (lighter dependencies)
COPY requirements-docker.txt .
RUN pip install --trusted-host pypi.org --trusted-host pypi.python.org --trusted-host files.pythonhosted.org --no-cache-dir -r requirements-docker.txt

# Copy the production processing script
COPY process_pdfs_production.py .

# Create expected input/output directories
RUN mkdir -p /app/input /app/output

# Run the production script
CMD ["python", "process_pdfs_production.py"]
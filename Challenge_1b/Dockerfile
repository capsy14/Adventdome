FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Install system dependencies for PDF processing
RUN apt-get update && apt-get install -y \
    libmupdf-dev \
    mupdf-tools \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip and install packages without SSL verification (for corporate networks)
RUN pip install --upgrade pip

# Copy requirements first for better caching
COPY requirements.txt /app/

# Install Python dependencies with trusted hosts (minimal offline-compatible)
RUN pip install --trusted-host pypi.org --trusted-host pypi.python.org --trusted-host files.pythonhosted.org --no-cache-dir -r requirements.txt

# Copy application code
COPY *.py /app/

# Create directories for input and output
RUN mkdir -p /app/data/input /app/data/output

# Set environment variables for CPU-only execution
ENV CUDA_VISIBLE_DEVICES=""
ENV OMP_NUM_THREADS=4

# Make main.py executable
RUN chmod +x /app/main.py

# Default command
CMD ["python", "main.py", "/app/data/input/input.json", "/app/data/input/PDFs/", "/app/data/output/output.json"]
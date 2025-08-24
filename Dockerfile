# Use Python 3.9 slim image as base
FROM python:3.9-slim

# Set working directory
WORKDIR /app


# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libffi-dev \
    curl \
    unrar \
    unrar-free \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p temp comics config

# Expose port
EXPOSE 5000

# Run the application
CMD ["python", "app.py"]

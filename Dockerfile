# Use Python 3.9 slim image as base
FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Install system dependencies including proper unrar tools
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libffi-dev \
    curl \
    unrar \
    unrar-free \
    p7zip-full \
    zip \
    unzip \
    && rm -rf /var/lib/apt/lists/*

# Create symbolic link for unrar to ensure rarfile package can find it
RUN ln -sf /usr/bin/unrar /usr/bin/rar

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create necessary directories with proper permissions
RUN mkdir -p temp comics config && \
    chmod 755 temp comics config

# Make test script executable
RUN chmod +x test_rar.py

# Set environment variable to help rarfile find unrar
ENV RARFILE_UNRAR_TOOL=/usr/bin/unrar

# Expose port
EXPOSE 5000

# Health check to verify RAR functionality
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python test_rar.py || exit 1

# Run the application
CMD ["python", "app.py"]

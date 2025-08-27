# Use Python 3.9 slim image as base
FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Install system dependencies including PeaZip for RAR/CBR handling
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libffi-dev \
    curl \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Install PeaZip for RAR/CBR handling
RUN wget -O peazip.deb https://github.com/peazip/PeaZip/releases/download/9.5.0/peazip_9.5.0.LINUX.GTK2-2_amd64.deb && \
    apt-get update && \
    apt-get install -y ./peazip.deb && \
    rm peazip.deb && \
    rm -rf /var/lib/apt/lists/*

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
RUN chmod +x test_peazip.py

# Expose port
EXPOSE 5000

# Health check to verify PeaZip functionality
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python test_peazip.py || exit 1

# Run the application
CMD ["python", "app.py"]

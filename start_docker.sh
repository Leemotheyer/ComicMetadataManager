#!/bin/bash

# Comic Metadata Manager Docker Startup Script

set -e

echo "🚀 Starting Comic Metadata Manager in Docker..."

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first."
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

# Create necessary directories if they don't exist
echo "📁 Creating necessary directories..."
mkdir -p comics config temp

# Set proper permissions
echo "🔐 Setting directory permissions..."
chmod 755 comics config temp

# Check if container is already running
if docker-compose ps | grep -q "comic-metadata-manager"; then
    echo "⚠️  Container is already running. Stopping it first..."
    docker-compose down
fi

# Build and start the container
echo "🔨 Building and starting container..."
docker-compose up --build -d

# Wait a moment for the container to start
echo "⏳ Waiting for container to start..."
sleep 5

# Check container status
if docker-compose ps | grep -q "Up"; then
    echo "✅ Container is running successfully!"
    echo "🌐 Access the application at: http://localhost:5000"
    echo ""
    echo "📋 Useful commands:"
    echo "  View logs: docker-compose logs -f comic-metadata"
    echo "  Stop container: docker-compose down"
    echo "  Test RAR functionality: docker-compose exec comic-metadata python test_rar.py"
    echo "  Access shell: docker-compose exec comic-metadata bash"
else
    echo "❌ Container failed to start. Check logs with: docker-compose logs comic-metadata"
    exit 1
fi
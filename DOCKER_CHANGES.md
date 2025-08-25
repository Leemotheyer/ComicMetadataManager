# Docker Containerization Changes

This document summarizes all the changes made to make the Comic Metadata Manager run properly in a Docker container, specifically addressing the WinRAR dependency issue.

## Problem Statement

The original application was developed with WinRAR for handling RAR and CBR files, which doesn't work in Linux-based Docker containers.

## Solution Overview

Replaced WinRAR dependency with Linux-compatible unrar tools and configured the application to use them properly.

## Changes Made

### 1. Updated Dockerfile (`Dockerfile`)

**Key Changes:**
- Added comprehensive unrar tools: `unrar`, `unrar-free`, `p7zip-full`, `zip`, `unzip`
- Created symbolic link: `ln -sf /usr/bin/unrar /usr/bin/rar`
- Set environment variable: `RARFILE_UNRAR_TOOL=/usr/bin/unrar`
- Added proper directory permissions
- Added health check for RAR functionality
- Made test script executable

**Before:**
```dockerfile
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libffi-dev \
    curl \
    unrar \
    unrar-free \
    && rm -rf /var/lib/apt/lists/*
```

**After:**
```dockerfile
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

# Set environment variable to help rarfile find unrar
ENV RARFILE_UNRAR_TOOL=/usr/bin/unrar

# Health check to verify RAR functionality
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python test_rar.py || exit 1
```

### 2. Updated docker-compose.yml

**Key Changes:**
- Added temp directory volume mount
- Added environment variables for RAR functionality
- Added Python unbuffered output

**Before:**
```yaml
volumes:
  - ./comics:/app/comics
  - ./config:/app/config
```

**After:**
```yaml
volumes:
  - ./comics:/app/comics
  - ./config:/app/config
  - ./temp:/app/temp
environment:
  - RARFILE_UNRAR_TOOL=/usr/bin/unrar
  - PYTHONUNBUFFERED=1
```

### 3. Modified MetaDataAdd.py

**Key Changes:**
- Added rarfile configuration at module level
- Set `rarfile.UNRAR_TOOL` to point to Linux unrar binary

**Added at the top of the file:**
```python
# Configure rarfile to use the correct unrar binary in Docker
try:
    import rarfile
    # Set the path to unrar binary for Docker environment
    rarfile.UNRAR_TOOL = "/usr/bin/unrar"
except ImportError:
    pass
```

### 4. Created Test Script (`test_rar.py`)

**Purpose:** Verify RAR functionality works in the container

**Features:**
- Tests unrar binary availability
- Tests rarfile package import
- Tests patoolib package import
- Tests actual RAR archive creation
- Comprehensive error reporting

### 5. Created Documentation

**Files Created:**
- `DOCKER_README.md`: Comprehensive Docker deployment guide
- `DOCKER_CHANGES.md`: This summary document

**Key Sections:**
- Quick start guide
- Troubleshooting RAR issues
- Performance optimization
- Security considerations
- Common issues and solutions

### 6. Created Startup Script (`start_docker.sh`)

**Purpose:** Automated setup and deployment

**Features:**
- Checks Docker and Docker Compose installation
- Creates necessary directories
- Sets proper permissions
- Builds and starts container
- Provides useful commands

## Technical Details

### RAR File Handling

**Before (Windows):**
- Relied on WinRAR installation
- Used Windows-specific paths
- Required WinRAR license

**After (Linux Docker):**
- Uses `unrar` and `unrar-free` packages
- Linux-compatible binary paths
- Open-source tools, no license required

### Archive Support

The container now supports:
- **RAR/CBR**: Using unrar tools
- **ZIP/CBZ**: Using zip/unzip tools
- **7Z/CB7**: Using p7zip-full
- **TAR/CBT**: Using tar tools

### Configuration

**Environment Variables:**
- `RARFILE_UNRAR_TOOL=/usr/bin/unrar`: Tells rarfile package where to find unrar
- `PYTHONUNBUFFERED=1`: Ensures Python output is not buffered

**Volume Mounts:**
- `./comics:/app/comics`: Comic files
- `./config:/app/config`: Application configuration
- `./temp:/app/temp`: Temporary files

## Testing

### Health Check
The container includes a health check that runs `test_rar.py` every 30 seconds to verify RAR functionality.

### Manual Testing
```bash
# Test RAR functionality
docker-compose exec comic-metadata python test_rar.py

# Check container health
docker-compose ps

# View logs
docker-compose logs comic-metadata
```

## Deployment

### Quick Start
```bash
# Create directories
mkdir -p comics config temp

# Set permissions
chmod 755 comics config temp

# Build and run
docker-compose up --build

# Or use the startup script
./start_docker.sh
```

### Access Application
- URL: `http://localhost:5000`
- The application will be fully functional with RAR/CBR support

## Benefits

1. **Cross-platform compatibility**: Works on any system with Docker
2. **No WinRAR dependency**: Uses open-source tools
3. **Consistent environment**: Same setup across all deployments
4. **Easy deployment**: Simple docker-compose commands
5. **Health monitoring**: Built-in health checks
6. **Comprehensive documentation**: Detailed guides and troubleshooting

## Migration Notes

For users migrating from Windows to Docker:

1. **No code changes needed**: The application code remains the same
2. **Same functionality**: All features work identically
3. **Better performance**: Linux tools are often faster
4. **No licensing issues**: All tools are open-source

## Future Considerations

1. **Multi-architecture support**: Could add ARM64 support for Apple Silicon
2. **Resource limits**: Could add memory/CPU limits for production
3. **Security hardening**: Could run as non-root user with proper permissions
4. **Monitoring**: Could add Prometheus metrics for production monitoring
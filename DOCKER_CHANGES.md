# Docker Containerization Changes

This document summarizes all the changes made to make the Comic Metadata Manager run properly in a Docker container, specifically addressing the RAR/CBR file handling issue.

## Problem Statement

The original application was developed with WinRAR for handling RAR and CBR files, which doesn't work in Linux-based Docker containers. The previous solution using unrar tools was not working reliably.

## Solution Overview

Replaced WinRAR dependency with PeaZip, a cross-platform archive manager that works reliably in Linux-based Docker containers for handling RAR and CBR files.

## Changes Made

### 1. Updated Dockerfile (`Dockerfile`)

**Key Changes:**
- Replaced unrar tools with PeaZip installation
- Removed unrar-related environment variables and symbolic links
- Updated health check to test PeaZip functionality
- Renamed test script to reflect PeaZip usage

**Before:**
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

**After:**
```dockerfile
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

# Health check to verify PeaZip functionality
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python test_peazip.py || exit 1
```

### 2. Updated docker-compose.yml

**Key Changes:**
- Removed RARFILE_UNRAR_TOOL environment variable
- Kept other environment variables for Python functionality

**Before:**
```yaml
environment:
  - RARFILE_UNRAR_TOOL=/usr/bin/unrar
  - PYTHONUNBUFFERED=1
```

**After:**
```yaml
environment:
  - PYTHONUNBUFFERED=1
```

### 3. Modified MetaDataAdd.py

**Key Changes:**
- Removed rarfile import and configuration
- Added PeaZip subprocess handling for RAR/CBR files
- Added PeaZip availability checking
- Updated error messages to reference PeaZip instead of WinRAR

**Removed:**
```python
# Configure rarfile to use the correct unrar binary in Docker
try:
    import rarfile
    # Set the path to unrar binary for Docker environment
    rarfile.UNRAR_TOOL = "/usr/bin/unrar"
except ImportError:
    pass
```

**Added:**
```python
import subprocess

class ComicMetadataInjector:
    def __init__(self):
        self.supported_formats = ['.cbr', '.cbz', '.cbt', '.cb7']
        self.temp_dir = None
        self.peazip_path = "/usr/bin/peazip"
    
    def _check_peazip_available(self):
        """Check if PeaZip is available on the system"""
        try:
            result = subprocess.run([self.peazip_path, "-help"], 
                                  capture_output=True, text=True, timeout=10)
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError, subprocess.SubprocessError):
            return False
```

### 4. Created Test Script (`test_peazip.py`)

**Purpose:** Verify PeaZip functionality works in the container

**Key Features:**
- Tests PeaZip binary availability
- Tests PeaZip command execution
- Tests actual RAR archive creation and extraction
- Comprehensive error handling and cleanup

**Usage:**
- Health check verification
- Troubleshooting PeaZip issues
- Manual testing of RAR/CBR functionality

## Technical Details

### RAR File Handling

**Before:**
- Relied on WinRAR installation
- Required WinRAR license
- Used rarfile Python package

**After:**
- Uses PeaZip (open source)
- No license requirements
- Direct subprocess calls to PeaZip binary

### Supported Formats

**Archive Types:**
- **RAR/CBR**: Using PeaZip
- **ZIP/CBZ**: Using patoolib (unchanged)
- **7Z/CB7**: Using patoolib (unchanged)
- **TAR/CBT**: Using patoolib (unchanged)

### Environment Variables

**Removed:**
- `RARFILE_UNRAR_TOOL=/usr/bin/unrar`: No longer needed

**Kept:**
- `PYTHONUNBUFFERED=1`: For proper logging in Docker
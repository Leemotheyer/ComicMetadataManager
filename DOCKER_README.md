# Docker Deployment Guide

This guide explains how to run the Comic Metadata Manager in a Docker container, with special attention to RAR/CBR file handling.

## Prerequisites

- Docker installed on your system
- Docker Compose installed
- At least 2GB of available RAM

## Quick Start

1. **Clone or download the application files**

2. **Create necessary directories:**
   ```bash
   mkdir -p comics config temp
   ```

3. **Build and run the container:**
   ```bash
   docker-compose up --build
   ```

4. **Access the application:**
   Open your browser and go to `http://localhost:5000`

## Directory Structure

The application expects the following directory structure:

```
your-app-directory/
├── comics/          # Your comic files (CBR, CBZ, etc.)
├── config/          # Application configuration
├── temp/            # Temporary files
├── Dockerfile
├── docker-compose.yml
└── ... (other app files)
```

## RAR/CBR File Support

The Docker container includes the following tools for handling RAR and CBR files:

- **unrar**: For extracting RAR archives
- **unrar-free**: Alternative RAR extraction tool
- **p7zip-full**: For 7z archives
- **zip/unzip**: For ZIP archives

### Troubleshooting RAR Issues

If you encounter issues with RAR/CBR files:

1. **Check container health:**
   ```bash
   docker-compose ps
   ```

2. **View container logs:**
   ```bash
   docker-compose logs comic-metadata
   ```

3. **Test RAR functionality:**
   ```bash
   docker-compose exec comic-metadata python test_rar.py
   ```

4. **Access container shell:**
   ```bash
   docker-compose exec comic-metadata bash
   ```

## Configuration

### Environment Variables

The following environment variables are set in the container:

- `RARFILE_UNRAR_TOOL=/usr/bin/unrar`: Path to unrar binary
- `PYTHONUNBUFFERED=1`: Ensures Python output is not buffered

### Volume Mounts

- `./comics:/app/comics`: Your comic files
- `./config:/app/config`: Application configuration
- `./temp:/app/temp`: Temporary files

## Common Issues and Solutions

### Issue: "WinRAR not found" errors

**Solution:** The container uses Linux-compatible unrar tools instead of WinRAR. The application has been configured to use these tools automatically.

### Issue: Permission denied errors

**Solution:** Ensure the directories have proper permissions:
```bash
chmod 755 comics config temp
```

### Issue: Archive creation fails

**Solution:** Check if the unrar binary is available:
```bash
docker-compose exec comic-metadata which unrar
```

### Issue: Container won't start

**Solution:** Check the logs for specific errors:
```bash
docker-compose logs comic-metadata
```

## Performance Optimization

### Memory Usage

The application can be memory-intensive when processing large comic files. Consider:

1. **Increase Docker memory limit** (if using Docker Desktop)
2. **Process files in smaller batches**
3. **Monitor container resource usage:**
   ```bash
   docker stats comic-metadata-manager
   ```

### Storage

- Ensure you have sufficient disk space for temporary files
- The `temp` directory may grow during processing
- Consider mounting the temp directory to an SSD for better performance

## Development

### Rebuilding the Container

After making changes to the code:

```bash
docker-compose down
docker-compose up --build
```

### Running Tests

Test RAR functionality:
```bash
docker-compose exec comic-metadata python test_rar.py
```

### Debugging

Access the container for debugging:
```bash
docker-compose exec comic-metadata bash
```

## Security Considerations

- The container runs as root (required for file operations)
- Only mount necessary directories
- Consider using Docker secrets for sensitive configuration
- Regularly update the base image for security patches

## Backup and Recovery

### Configuration Backup

Backup your configuration:
```bash
cp -r config config_backup
```

### Data Recovery

To recover from a failed container:
1. Stop the container: `docker-compose down`
2. Check logs: `docker-compose logs comic-metadata`
3. Fix any issues
4. Restart: `docker-compose up`

## Support

If you encounter issues:

1. Check the container logs
2. Run the RAR test script
3. Verify directory permissions
4. Ensure sufficient disk space and memory

For additional help, check the main README.md file or create an issue in the project repository.
# Application Logging Feature

## Overview

The Comic Metadata Manager now includes a comprehensive logging system that captures all application activities, API calls, volume processing, and scheduled tasks. This feature allows users to view a complete history of what the application has been doing and track its automatic operations.

## Features

### Log Storage
- **File Storage**: Logs are automatically saved to `config/app.log` in the config directory
- **In-Memory Storage**: Real-time access to recent logs for the web interface
- **Persistent History**: Log files persist between application restarts

### Log Levels
- **INFO**: General information about application operations
- **WARNING**: Non-critical issues or important notices
- **ERROR**: Error conditions that need attention
- **DEBUG**: Detailed debugging information

### Log Sources
- **app**: General application events
- **api**: API endpoint calls and responses
- **task**: Scheduled task operations
- **volume**: Volume processing and metadata operations

### Web Interface
- **Logs Page**: Accessible via the "Logs" link in the navigation
- **Real-time Viewing**: View logs with automatic refresh capability
- **Filtering**: Filter logs by level, source, and date range
- **Statistics**: View log statistics and counts
- **Export**: Export logs in JSON or TXT format

## Usage

### Accessing Logs
1. Navigate to the "Logs" page from the main navigation
2. View recent logs in the main display area
3. Use filters to narrow down specific log entries
4. Enable auto-refresh to see new logs as they occur

### Filtering Logs
- **Log Level**: Filter by INFO, WARNING, ERROR, or DEBUG
- **Source**: Filter by app, api, task, or volume
- **Limit**: Choose how many log entries to display (50-1000)
- **Date Range**: Filter by start and end dates (coming soon)

### Exporting Logs
- **JSON Export**: Download logs in structured JSON format
- **TXT Export**: Download logs in plain text format
- **Filtered Export**: Export only filtered log entries

### Log Management
- **Clear Logs**: Remove all stored logs (use with caution)
- **Auto-refresh**: Automatically update logs every 5 seconds
- **Statistics**: View counts of different log levels and sources

## Technical Details

### Log Format
Each log entry contains:
```json
{
  "timestamp": "2025-08-28T13:56:57.263164",
  "level": "INFO",
  "message": "Application startup",
  "source": "app"
}
```

### File Storage
- **Location**: `config/app.log`
- **Format**: Standard logging format with timestamps
- **Encoding**: UTF-8
- **Rotation**: Manual (clear logs when needed)

### API Endpoints
- `GET /api/logs` - Retrieve logs with optional filtering
- `GET /api/logs/stats` - Get log statistics
- `POST /api/logs/clear` - Clear all logs
- `GET /api/logs/export` - Export logs in specified format

### Integration
The logging system automatically captures:
- All `print()` statements (converted to logging calls)
- API requests and responses
- Volume processing operations
- Scheduled task executions
- Error conditions and exceptions

## Benefits

1. **Transparency**: See exactly what the application is doing
2. **Debugging**: Easily identify issues and track their causes
3. **Monitoring**: Monitor automatic operations and scheduled tasks
4. **History**: Maintain a complete record of application activity
5. **Troubleshooting**: Quickly identify and resolve problems

## Configuration

The logging system is automatically configured when the application starts. No additional configuration is required. Logs are stored in the same config directory as other application settings.

## Future Enhancements

- **Log Rotation**: Automatic log file rotation based on size or time
- **Log Compression**: Compress old log files to save space
- **Advanced Filtering**: More sophisticated filtering options
- **Log Alerts**: Notifications for specific log events
- **Performance Metrics**: Track application performance through logs
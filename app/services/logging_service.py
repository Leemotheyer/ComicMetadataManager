"""
Logging Service for Comic Metadata Manager
Handles application logging with file storage and retrieval
"""

import os
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
import threading
from collections import deque
import sys

class LoggingService:
    """Manages application logging with file storage and retrieval"""
    
    def __init__(self, config_dir: str = 'config', max_log_entries: int = 1000):
        """Initialize the logging service
        
        Args:
            config_dir: Directory to store log files
            max_log_entries: Maximum number of log entries to keep in memory
        """
        self.config_dir = Path(config_dir)
        self.log_file = self.config_dir / 'app.log'
        self.max_log_entries = max_log_entries
        
        # In-memory log storage for real-time access
        self.log_entries = deque(maxlen=max_log_entries)
        self.lock = threading.Lock()
        
        # Ensure config directory exists
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        # Setup file logging
        self._setup_file_logging()
        
        # Capture stdout/stderr
        self._setup_stdout_capture()
    
    def _setup_file_logging(self):
        """Setup file-based logging"""
        # Create formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # Setup file handler
        file_handler = logging.FileHandler(self.log_file, encoding='utf-8')
        file_handler.setFormatter(formatter)
        file_handler.setLevel(logging.INFO)
        
        # Setup logger
        self.logger = logging.getLogger('comic_metadata_manager')
        self.logger.setLevel(logging.INFO)
        self.logger.addHandler(file_handler)
        
        # Prevent duplicate handlers
        self.logger.propagate = False
    
    def _setup_stdout_capture(self):
        """Capture stdout and stderr to also log them"""
        class LoggedStream:
            def __init__(self, original_stream, log_service, level):
                self.original_stream = original_stream
                self.log_service = log_service
                self.level = level
            
            def write(self, text):
                if text.strip():  # Only log non-empty lines
                    self.log_service.log(self.level, text.strip())
                self.original_stream.write(text)
            
            def flush(self):
                self.original_stream.flush()
        
        # Capture stdout and stderr
        sys.stdout = LoggedStream(sys.stdout, self, 'INFO')
        sys.stderr = LoggedStream(sys.stderr, self, 'ERROR')
    
    def log(self, level: str, message: str, source: str = 'app'):
        """Log a message with timestamp and level
        
        Args:
            level: Log level (INFO, WARNING, ERROR, DEBUG)
            message: Log message
            source: Source of the log (app, api, task, etc.)
        """
        timestamp = datetime.now().isoformat()
        
        log_entry = {
            'timestamp': timestamp,
            'level': level.upper(),
            'message': message,
            'source': source
        }
        
        # Add to in-memory storage
        with self.lock:
            self.log_entries.append(log_entry)
        
        # Write to file
        self.logger.log(
            getattr(logging, level.upper(), logging.INFO),
            f"[{source.upper()}] {message}"
        )
    
    def info(self, message: str, source: str = 'app'):
        """Log an info message"""
        self.log('INFO', message, source)
    
    def warning(self, message: str, source: str = 'app'):
        """Log a warning message"""
        self.log('WARNING', message, source)
    
    def error(self, message: str, source: str = 'app'):
        """Log an error message"""
        self.log('ERROR', message, source)
    
    def debug(self, message: str, source: str = 'app'):
        """Log a debug message"""
        self.log('DEBUG', message, source)
    
    def get_logs(self, limit: int = 100, level: Optional[str] = None, 
                 source: Optional[str] = None, start_date: Optional[str] = None,
                 end_date: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get logs with optional filtering
        
        Args:
            limit: Maximum number of logs to return
            level: Filter by log level
            source: Filter by source
            start_date: Filter by start date (ISO format)
            end_date: Filter by end date (ISO format)
            
        Returns:
            List of log entries
        """
        with self.lock:
            logs = list(self.log_entries)
        
        # Apply filters
        if level:
            logs = [log for log in logs if log['level'] == level.upper()]
        
        if source:
            logs = [log for log in logs if log['source'] == source]
        
        if start_date:
            logs = [log for log in logs if log['timestamp'] >= start_date]
        
        if end_date:
            logs = [log for log in logs if log['timestamp'] <= end_date]
        
        # Return most recent logs up to limit
        return logs[-limit:] if limit else logs
    
    def get_log_stats(self) -> Dict[str, Any]:
        """Get statistics about the logs
        
        Returns:
            Dictionary with log statistics
        """
        with self.lock:
            logs = list(self.log_entries)
        
        if not logs:
            return {
                'total_entries': 0,
                'levels': {},
                'sources': {},
                'oldest_entry': None,
                'newest_entry': None
            }
        
        # Count by level
        levels = {}
        for log in logs:
            level = log['level']
            levels[level] = levels.get(level, 0) + 1
        
        # Count by source
        sources = {}
        for log in logs:
            source = log['source']
            sources[source] = sources.get(source, 0) + 1
        
        return {
            'total_entries': len(logs),
            'levels': levels,
            'sources': sources,
            'oldest_entry': logs[0]['timestamp'] if logs else None,
            'newest_entry': logs[-1]['timestamp'] if logs else None
        }
    
    def clear_logs(self):
        """Clear all logs from memory and file"""
        with self.lock:
            self.log_entries.clear()
        
        # Clear file
        if self.log_file.exists():
            self.log_file.unlink()
        
        # Recreate file handler
        for handler in self.logger.handlers[:]:
            self.logger.removeHandler(handler)
        
        self._setup_file_logging()
    
    def export_logs(self, format: str = 'json') -> str:
        """Export logs in specified format
        
        Args:
            format: Export format (json, txt)
            
        Returns:
            Exported logs as string
        """
        with self.lock:
            logs = list(self.log_entries)
        
        if format.lower() == 'json':
            return json.dumps(logs, indent=2, ensure_ascii=False)
        elif format.lower() == 'txt':
            lines = []
            for log in logs:
                lines.append(f"[{log['timestamp']}] {log['level']} [{log['source']}] {log['message']}")
            return '\n'.join(lines)
        else:
            raise ValueError(f"Unsupported format: {format}")

# Global logging service instance
logging_service = LoggingService()
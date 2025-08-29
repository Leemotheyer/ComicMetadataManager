"""
Configuration settings for the Comic Metadata Manager
"""

import os
from pathlib import Path

class Config:
    """Base configuration class"""
    
    # Flask settings
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    
    # Database settings
    DATABASE_PATH = os.path.join('config', 'volumes.db')
    
    # Logging settings
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
    LOG_FILE = os.path.join('config', 'app.log')
    
    # API settings
    KAPOWARR_API_KEY = os.environ.get('KAPOWARR_API_KEY', '')
    KAPOWARR_URL = os.environ.get('KAPOWARR_URL', '')
    COMICVINE_API_KEY = os.environ.get('COMICVINE_API_KEY', '')
    
    # File paths
    COMICS_DIR = os.environ.get('COMICS_DIR', 'comics')
    TEMP_DIR = os.environ.get('TEMP_DIR', 'temp')
    
    @staticmethod
    def init_app(app):
        """Initialize application with config"""
        pass

class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True

class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False

class TestingConfig(Config):
    """Testing configuration"""
    TESTING = True
    DATABASE_PATH = ':memory:'

config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}

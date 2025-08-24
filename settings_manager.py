"""
Settings Manager for Comic Metadata Manager
Handles configuration storage, retrieval, and validation
"""

import json
import os
from typing import Dict, Any, Optional
from pathlib import Path


class SettingsManager:
    """Manages application settings and configuration"""
    
    DEFAULT_SETTINGS = {
        'kapowarr_url': 'http://192.168.1.205:5656',
        'kapowarr_api_key': '',
        'comicvine_api_key': '',
        'temp_directory': './temp',
        'max_concurrent_tasks': 3,
        'task_timeout': 30,
        'flask_secret_key': 'your-secret-key-here-change-this-in-production'
    }
    
    def __init__(self, config_file: str = 'config/config.json'):
        """Initialize the settings manager
        
        Args:
            config_file: Path to the configuration file
        """
        self.config_file = Path(config_file)
        self.settings = self.load_settings()
    
    def load_settings(self) -> Dict[str, Any]:
        """Load settings from the configuration file
        
        Returns:
            Dictionary containing the current settings
        """
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    loaded_settings = json.load(f)
                    
                # Merge with defaults to ensure all required settings exist
                settings = self.DEFAULT_SETTINGS.copy()
                settings.update(loaded_settings)
                return settings
            except (json.JSONDecodeError, IOError) as e:
                print(f"Warning: Could not load settings from {self.config_file}: {e}")
                return self.DEFAULT_SETTINGS.copy()
        else:
            # Create example config file with helpful comments
            self.create_example_config()
            return self.DEFAULT_SETTINGS.copy()
    
    def save_settings(self, settings: Dict[str, Any]) -> bool:
        """Save settings to the configuration file
        
        Args:
            settings: Dictionary containing the settings to save
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Ensure the directory exists
            self.config_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Validate settings before saving
            validated_settings = self.validate_settings(settings)
            
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(validated_settings, f, indent=2, ensure_ascii=False)
            
            # Update current settings
            self.settings = validated_settings
            return True
        except (IOError, OSError) as e:
            print(f"Error saving settings to {self.config_file}: {e}")
            return False
    
    def validate_settings(self, settings: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and sanitize settings
        
        Args:
            settings: Raw settings dictionary
            
        Returns:
            Validated and sanitized settings dictionary
        """
        validated = {}
        
        # Kapowarr URL
        kapowarr_url = settings.get('kapowarr_url', '').strip()
        if kapowarr_url:
            # Ensure URL has protocol
            if not kapowarr_url.startswith(('http://', 'https://')):
                kapowarr_url = 'http://' + kapowarr_url
            validated['kapowarr_url'] = kapowarr_url.rstrip('/')
        else:
            validated['kapowarr_url'] = self.DEFAULT_SETTINGS['kapowarr_url']
        
        # API Keys
        validated['kapowarr_api_key'] = settings.get('kapowarr_api_key', '').strip()
        validated['comicvine_api_key'] = settings.get('comicvine_api_key', '').strip()
        
        # Temp Directory
        temp_dir = settings.get('temp_directory', '').strip()
        if temp_dir:
            # Ensure it's a relative path
            if os.path.isabs(temp_dir):
                temp_dir = os.path.relpath(temp_dir)
            validated['temp_directory'] = temp_dir
        else:
            validated['temp_directory'] = self.DEFAULT_SETTINGS['temp_directory']
        
        # Numeric settings with bounds checking
        max_tasks = settings.get('max_concurrent_tasks')
        if max_tasks is not None:
            try:
                max_tasks = int(max_tasks)
                validated['max_concurrent_tasks'] = max(1, min(10, max_tasks))
            except (ValueError, TypeError):
                validated['max_concurrent_tasks'] = self.DEFAULT_SETTINGS['max_concurrent_tasks']
        else:
            validated['max_concurrent_tasks'] = self.DEFAULT_SETTINGS['max_concurrent_tasks']
        
        timeout = settings.get('task_timeout')
        if timeout is not None:
            try:
                timeout = int(timeout)
                validated['task_timeout'] = max(5, min(120, timeout))
            except (ValueError, TypeError):
                validated['task_timeout'] = self.DEFAULT_SETTINGS['task_timeout']
        else:
            validated['task_timeout'] = self.DEFAULT_SETTINGS['task_timeout']
        
        return validated
    
    def get_setting(self, key: str, default: Any = None) -> Any:
        """Get a specific setting value
        
        Args:
            key: Setting key to retrieve
            default: Default value if setting doesn't exist
            
        Returns:
            Setting value or default
        """
        return self.settings.get(key, default)
    
    def set_setting(self, key: str, value: Any) -> bool:
        """Set a specific setting value
        
        Args:
            key: Setting key to set
            value: Value to set
            
        Returns:
            True if successful, False otherwise
        """
        self.settings[key] = value
        return self.save_settings(self.settings)
    
    def get_all_settings(self) -> Dict[str, Any]:
        """Get all current settings
        
        Returns:
            Dictionary containing all settings
        """
        return self.settings.copy()
    
    def reset_to_defaults(self) -> bool:
        """Reset all settings to default values
        
        Returns:
            True if successful, False otherwise
        """
        return self.save_settings(self.DEFAULT_SETTINGS.copy())
    
    def test_kapowarr_connection(self) -> Dict[str, Any]:
        """Test the Kapowarr connection using current settings
        
        Returns:
            Dictionary with connection test results
        """
        import requests
        
        try:
            url = f"{self.settings['kapowarr_url']}/api/volumes/stats"
            params = {'api_key': self.settings['kapowarr_api_key']}
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            # Check for volumes in the result field (Kapowarr API structure)
            if 'result' in data and 'volumes' in data['result']:
                return {
                    'success': True,
                    'message': f"Connected successfully! Found {data['result']['volumes']} volumes.",
                    'data': data
                }
            # Also check for volumes at top level (fallback)
            elif 'volumes' in data:
                return {
                    'success': True,
                    'message': f"Connected successfully! Found {data['volumes']} volumes.",
                    'data': data
                }
            else:
                return {
                    'success': False,
                    'message': 'Invalid response format from Kapowarr API'
                }
        except requests.exceptions.RequestException as e:
            return {
                'success': False,
                'message': f"Connection failed: {str(e)}"
            }
        except Exception as e:
            return {
                'success': False,
                'message': f"Unexpected error: {str(e)}"
            }
    
    def test_comicvine_connection(self) -> Dict[str, Any]:
        """Test the ComicVine connection using current settings
        
        Returns:
            Dictionary with connection test results
        """
        import requests
        
        try:
            url = "https://comicvine.gamespot.com/api/search/"
            params = {
                'api_key': self.settings['comicvine_api_key'],
                'format': 'json',
                'query': 'batman',
                'limit': 1
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            if data.get('status_code') == 1:
                return {
                    'success': True,
                    'message': 'ComicVine API connection successful!',
                    'data': data
                }
            else:
                return {
                    'success': False,
                    'message': f"ComicVine API error: {data.get('error', 'Unknown error')}"
                }
        except requests.exceptions.RequestException as e:
            return {
                'success': False,
                'message': f"Connection failed: {str(e)}"
            }
        except Exception as e:
            return {
                'success': False,
                'message': f"Unexpected error: {str(e)}"
            }
    
    def create_example_config(self) -> bool:
        """Create an example configuration file with helpful comments
        
        Returns:
            True if successful, False otherwise
        """
        try:
            # Ensure the config directory exists
            self.config_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Create example config with comments
            example_config = {
                "kapowarr_url": "http://your-kapowarr-server:port",
                "kapowarr_api_key": "your-kapowarr-api-key-here",
                "comicvine_api_key": "your-comicvine-api-key-here",
                "temp_directory": "./temp",
                "max_concurrent_tasks": 3,
                "task_timeout": 30,
                "flask_secret_key": "your-secret-key-here-change-this-in-production"
            }
            
            # Save the example config
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(example_config, f, indent=2, ensure_ascii=False)
            
            print(f"✅ Created example configuration file: {self.config_file}")
            print("📝 Please edit the config file with your actual API keys and settings")
            print("🔑 You can get your API keys from:")
            print("   - Kapowarr: Check your Kapowarr server settings")
            print("   - ComicVine: https://comicvine.gamespot.com/api/")
            
            return True
            
        except Exception as e:
            print(f"❌ Error creating example config: {e}")
            return False
    
    def ensure_temp_directory(self) -> bool:
        """Ensure the temporary directory exists
        
        Returns:
            True if successful, False otherwise
        """
        try:
            temp_dir = Path(self.settings['temp_directory'])
            temp_dir.mkdir(parents=True)
            return True
        except Exception as e:
            print(f"Error creating temp directory {self.settings['temp_directory']}: {e}")
            return False


# Global settings manager instance
settings_manager = SettingsManager()

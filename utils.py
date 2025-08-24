"""
Utility functions for Comic Metadata application
Contains non-Flask specific functions that can be reused across the application
"""

import os
import json
import time
import requests
import shutil
from datetime import datetime


def test_kapowarr_connection_with_settings(settings):
    """Test Kapowarr connection using specific settings"""
    try:
        url = f"{settings['kapowarr_url']}/api/volumes/stats"
        params = {'api_key': settings['kapowarr_api_key']}
        
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
                'message': f"Connected successfully! Found {data['result']['volumes']} volumes.",
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


def test_comicvine_connection_with_settings(settings):
    """Test ComicVine connection using specific settings"""
    try:
        url = "https://comicvine.gamespot.com/api/search/"
        params = {
            'api_key': settings['comicvine_api_key'],
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


def cleanup_temp_files():
    """Clean up temporary files"""
    try:
        temp_dirs = [d for d in os.listdir('.') if d.startswith('temp_xml')]
        for temp_dir in temp_dirs:
            if os.path.isdir(temp_dir):
                shutil.rmtree(temp_dir)
        return True
    except Exception as e:
        print(f"Error cleaning up temp files: {e}")
        return False


def cleanup_temp_directories():
    """Clean up any orphaned temporary directories"""
    try:
        cleaned_dirs = []
        failed_dirs = []
        
        # Look for various types of temp directories
        temp_patterns = [
            "temp_xml_*",
            "temp_injection_*",
            "temp_*"
        ]
        
        for pattern in temp_patterns:
            temp_dirs = [d for d in os.listdir('.') if d.startswith(pattern.replace('*', ''))]
            for temp_dir_path in temp_dirs:
                if os.path.exists(temp_dir_path) and os.path.isdir(temp_dir_path):
                    try:
                        shutil.rmtree(temp_dir_path)
                        cleaned_dirs.append(temp_dir_path)
                    except Exception as cleanup_error:
                        failed_dirs.append(f"{temp_dir_path}: {cleanup_error}")
        
        if cleaned_dirs:
            message = f"Cleaned up {len(cleaned_dirs)} temporary directories"
        else:
            message = "No temporary directories found to clean up"
            
        return {
            'success': True,
            'message': message,
            'cleaned_dirs': cleaned_dirs,
            'failed_dirs': failed_dirs,
            'total_cleaned': len(cleaned_dirs)
        }
        
    except Exception as e:
        return {'success': False, 'error': str(e)}


def generate_xml_files(metadata, output_dir="temp_xml"):
    """Generate XML files for comic metadata"""
    try:
        # Create temporary directory
        os.makedirs(output_dir, exist_ok=True)
        
        # Create a temporary metadata file for the XML generator
        temp_metadata_file = os.path.join(output_dir, "temp_metadata.json")
        with open(temp_metadata_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
        
        # Generate XML files using the existing method
        from CreateXML import ComicInfoXMLGenerator
        xml_generator = ComicInfoXMLGenerator()
        xml_generator.generate_xml_files(temp_metadata_file, output_dir)
        
        # Return the output directory path instead of a zip file
        return output_dir
    except Exception as e:
        print(f"Error generating XML files: {e}")
        return None


def get_file_size_mb(file_path):
    """Get file size in megabytes"""
    try:
        size_bytes = os.path.getsize(file_path)
        return round(size_bytes / (1024 * 1024), 2)
    except Exception:
        return 0


def format_timestamp(timestamp):
    """Format timestamp for display"""
    try:
        dt = datetime.fromtimestamp(timestamp)
        return dt.strftime('%Y-%m-%d %H:%M:%S')
    except Exception:
        return "Unknown"


def safe_filename(filename):
    """Convert filename to safe version for file system"""
    # Remove or replace unsafe characters
    unsafe_chars = '<>:"/\\|?*'
    for char in unsafe_chars:
        filename = filename.replace(char, '_')
    return filename


def map_kapowarr_to_local_path(kapowarr_folder_path, kapowarr_parent_folder, local_parent_folder='comics'):
    """
    Map a Kapowarr folder path to a local file system path.
    
    Args:
        kapowarr_folder_path: The folder path from Kapowarr (e.g., "/comics-1/DC Comics/Batgirl (2025)")
        kapowarr_parent_folder: The parent folder setting from Kapowarr (e.g., "/comics-1")
        local_parent_folder: The local parent folder to map to (e.g., "comics")
    
    Returns:
        The mapped local path (e.g., "comics/DC Comics/Batgirl (2025)")
    
    Example:
        >>> map_kapowarr_to_local_path("/comics-1/DC Comics/Batgirl (2025)", "/comics-1", "comics")
        "comics/DC Comics/Batgirl (2025)"
    """
    try:
        # Store original path for fallback
        original_path = kapowarr_folder_path
        
        # Remove leading slash from kapowarr_folder_path if present for comparison
        if kapowarr_folder_path.startswith('/'):
            kapowarr_folder_path_no_slash = kapowarr_folder_path[1:]
        else:
            kapowarr_folder_path_no_slash = kapowarr_folder_path
        
        # Remove leading slash from kapowarr_parent_folder if present
        if kapowarr_parent_folder.startswith('/'):
            kapowarr_parent_folder_no_slash = kapowarr_parent_folder[1:]
        else:
            kapowarr_parent_folder_no_slash = kapowarr_parent_folder
        
        # Check if the kapowarr_folder_path starts with the kapowarr_parent_folder
        if kapowarr_folder_path_no_slash.startswith(kapowarr_parent_folder_no_slash):
            # Extract the relative path after the parent folder
            relative_path = kapowarr_folder_path_no_slash[len(kapowarr_parent_folder_no_slash):]
            # Remove leading slash if present
            if relative_path.startswith('/'):
                relative_path = relative_path[1:]
            
            # Combine local parent folder with relative path
            # Use forward slashes for consistency across platforms
            if local_parent_folder.startswith('/'):
                local_parent_folder_no_slash = local_parent_folder[1:]
            else:
                local_parent_folder_no_slash = local_parent_folder
            
            # Build the path without leading slash for relative paths
            local_path = f"{local_parent_folder_no_slash}/{relative_path}"
            
            # Normalize path separators but preserve forward slashes for display
            local_path = local_path.replace('\\', '/')
            
            return local_path
        else:
            # If the path doesn't start with the expected parent folder, return as-is
            # This handles cases where the folder structure might be different
            # Preserve the original format including leading slash
            return original_path
            
    except Exception as e:
        print(f"Error mapping Kapowarr path to local path: {e}")
        # Return original path if mapping fails
        return kapowarr_folder_path

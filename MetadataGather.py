import os
import requests
import json
from typing import List, Dict, Optional
from settings_manager import settings_manager
import time

class ComicMetadataFetcher:
    def __init__(self):
        self.kapowarr_api_key = settings_manager.get_setting('kapowarr_api_key')
        self.comicvine_api_key = settings_manager.get_setting('comicvine_api_key')
        self.kapowarr_url = settings_manager.get_setting('kapowarr_url')
        
        if not self.kapowarr_api_key:
            raise ValueError("KAPOWARR_API_KEY not found in config/config.json")
        if not self.comicvine_api_key:
            raise ValueError("COMICVINE_API_KEY not found in config/config.json")
    
    def search_kapowarr_volume(self, volume_id: str) -> Optional[Dict]:
        """Get a specific volume by ID from Kapowarr"""
        # Direct volume lookup by ID
        volume_url = f"{self.kapowarr_url}/api/volumes/{volume_id}"
        params = {
            'api_key': self.kapowarr_api_key
        }
        
        try:
            response = requests.get(volume_url, params=params)
            response.raise_for_status()
            data = response.json()
            
            if data and data.get('result'):
                print(f"Found volume with ID: {volume_id}")
                return data
            else:
                print(f"No volume found with ID: {volume_id}")
                return None
                
        except requests.exceptions.RequestException as e:
            print(f"Error getting volume from Kapowarr: {e}")
            return None
    
    def get_volume_issues(self, volume_data: Dict) -> List[Dict]:
        """Extract issues from volume data returned by Kapowarr"""
        issues = volume_data.get('result', {}).get('issues', [])
        print(f"Found {len(issues)} issues in volume")
        return issues
    
    def get_comicvine_metadata(self, comicvine_id: str, retry_count: int = 0) -> Optional[Dict]:
        """Get metadata for a specific issue from ComicVine API with retry logic"""
        base_url = "https://comicvine.gamespot.com/api"
        params = {
            'api_key': self.comicvine_api_key,
            'format': 'json'
        }
        
        url = f"{base_url}/issue/4000-{comicvine_id}/"
        
        try:
            print(f"Fetching ComicVine metadata for issue {comicvine_id}...")
            headers = {
                'User-Agent': 'ComicMetadataFetcher/1.0 (https://github.com/yourusername/comic-metadata-fetcher)'
            }
            response = requests.get(url, params=params, headers=headers)
            
            # Check if we got a successful response
            if response.status_code == 200:
                data = response.json()
                
                if data.get('status_code') == 1:  # Success
                    print(f"Successfully fetched metadata for issue {comicvine_id}")
                    return data['results']
                else:
                    print(f"ComicVine API error: {data.get('error')}")
                    return None
            elif response.status_code == 403 and retry_count < 2:
                print(f"403 Forbidden - retrying in 5 seconds... (attempt {retry_count + 1})")
                time.sleep(5)
                return self.get_comicvine_metadata(comicvine_id, retry_count + 1)
            else:
                print(f"HTTP {response.status_code}: {response.text}")
                return None
                
        except requests.exceptions.RequestException as e:
            print(f"Error fetching ComicVine metadata: {e}")
            return None
        except json.JSONDecodeError as e:
            print(f"Error parsing ComicVine response: {e}")
            return None
    
    def process_volume(self, volume_id: str) -> Dict:
        """Main method to process a volume and get metadata for all issues"""
        print(f"Processing volume ID: {volume_id}")
        
        # Get volume from Kapowarr
        volume = self.search_kapowarr_volume(volume_id)
        if not volume:
            return {}
        
        volume_info = volume.get('result', {})
        print(f"Volume found: {volume_info.get('folder', 'Unknown')}")
        print(f"Volume ID: {volume_info.get('id', 'Unknown')}")
        print(f"Issue count: {volume_info.get('issue_count', 'Unknown')}")
        
        # Get all issues from the volume data
        issues = self.get_volume_issues(volume)
        if not issues:
            return {}
        
        # Process each issue
        metadata_results = {}
        for issue in issues:
            comicvine_id = issue.get('comicvine_id')
            if comicvine_id:
                print(f"Processing issue {issue.get('issue_number', 'Unknown')} (ComicVine ID: {comicvine_id})")
                
                # Get ComicVine metadata
                metadata = self.get_comicvine_metadata(comicvine_id)
                if metadata:
                    metadata_results[comicvine_id] = {
                        'kapowarr_issue': issue,
                        'comicvine_metadata': metadata
                    }
                
                # Rate limiting for ComicVine API
                time.sleep(1.0)
            else:
                print(f"Issue {issue.get('issue_number', 'Unknown')} has no ComicVine ID")
        
        return metadata_results
    
    def save_metadata(self, metadata: Dict, filename: str = None):
        """Save metadata to a JSON file"""
        if not filename:
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            filename = f"comic_metadata_{timestamp}.json"
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
        
        print(f"Metadata saved to {filename}")

def main():
    """Main function to run the script"""
    try:
        fetcher = ComicMetadataFetcher()
        
        # Get volume ID from user input
        volume_id = input("Enter the volume ID to process: ").strip()
        if not volume_id:
            print("Volume ID cannot be empty")
            return
        
        # Validate that input is a number
        try:
            int(volume_id)
        except ValueError:
            print("Volume ID must be a number")
            return
        
        # Process the volume
        metadata = fetcher.process_volume(volume_id)
        
        if metadata:
            print(f"\nSuccessfully processed {len(metadata)} issues")
            
            # Save metadata to file
            save_choice = input("Save metadata to file? (y/n): ").lower().strip()
            if save_choice == 'y':
                filename = input("Enter filename (or press Enter for default): ").strip()
                fetcher.save_metadata(metadata, filename if filename else None)
        else:
            print("No metadata was collected")
            
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    main()

import requests
import time
import os
from settings_manager import settings_manager

def check_volume_exists(volume_id, api_key, base_url="http://192.168.1.205:5656"):
    """
    Check if a volume exists by making a request to the volumes endpoint.
    Returns True if the volume exists, False otherwise.
    """
    url = f"{base_url}/api/volumes/{volume_id}?api_key={api_key}"
    
    try:
        response = requests.get(url, timeout=10)
        
        # Check if the response indicates a valid volume
        if response.status_code == 200:
            try:
                data = response.json()
                # Check if the response has valid data structure
                if (data and 
                    isinstance(data, dict) and 
                    data.get("error") is None and 
                    data.get("result") and 
                    isinstance(data["result"], dict) and
                    data["result"].get("id") is not None):
                    return True
            except ValueError:
                # Invalid JSON response
                pass
        elif response.status_code == 404:
            # Explicit 404 means volume doesn't exist
            return False
        
        return False
        
    except requests.exceptions.RequestException as e:
        print(f"Error checking volume {volume_id}: {e}")
        return False

def get_total_volumes_from_stats(api_key, base_url="http://192.168.1.205:5656"):
    """
    Get the total number of volumes from the stats endpoint.
    """
    url = f"{base_url}/api/volumes/stats?api_key={api_key}"
    print(f"Getting total volumes from stats: {url}")
    
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if (data and 
                isinstance(data, dict) and 
                data.get("error") is None and 
                data.get("result") and 
                isinstance(data["result"], dict)):
                total_volumes = data["result"].get("volumes")
                if total_volumes is not None:
                    return total_volumes
        print(f"Failed to get total volumes from stats. Response: {response.text}")
        return None
    except Exception as e:
        print(f"Error getting stats: {e}")
        return None

def count_all_volumes():
    """
    Count all volumes in the Kapowarr API by incrementing volume IDs
    until we reach the total count from stats.
    """
    api_key = settings_manager.get_setting('kapowarr_api_key')
    
    if not api_key:
        print("Error: KAPOWARR_API_KEY not found in config/config.json")
        return
    
    print("Starting volume count...")
    print(f"Using API key: {api_key[:8]}...")
    print("-" * 50)
    
    # Get total volumes from stats first
    total_volumes = get_total_volumes_from_stats(api_key)
    if total_volumes is None:
        print("Could not determine total volumes from stats. Exiting.")
        return
    
    print(f"Total volumes expected from stats: {total_volumes}")
    print("-" * 50)
    
    volume_count = 0
    volume_id = 1  # Start from volume ID 1 instead of 0
    consecutive_failures = 0
    max_consecutive_failures = 15  # Failsafe after 15 consecutive failures
    
    while volume_count < total_volumes:
        print(f"Checking volume {volume_id}...", end=" ")
        
        if check_volume_exists(volume_id, api_key):
            print("✓ Found")
            volume_count += 1
            consecutive_failures = 0  # Reset failure counter
        else:
            print("✗ Not found")
            consecutive_failures += 1
        
        # Failsafe: if we've checked more volumes than expected and hit max consecutive failures
        if volume_id >= total_volumes and consecutive_failures >= max_consecutive_failures:
            print(f"\nFailsafe triggered: {consecutive_failures} consecutive failures after checking {volume_id} volumes")
            break
        
        volume_id += 1
        
        # Add a small delay to be respectful to the API
        time.sleep(0.1)
        
        # Progress indicator every 10 volumes
        if volume_id % 10 == 0:
            print(f"Progress: {volume_id} volumes checked, {volume_count}/{total_volumes} found")
    
    print("-" * 50)
    print(f"Volume counting completed!")
    print(f"Total volumes found: {volume_count}")
    print(f"Last volume ID checked: {volume_id - 1}")
    print(f"Target from stats: {total_volumes}")

if __name__ == "__main__":
    count_all_volumes()

"""
Volume Service - Handles volume management and metadata processing
"""

import time
import threading
import queue
from typing import List, Dict, Optional, Any
from app.models.volume_database import VolumeDatabase
from app.services.metadata_service import MetadataService
from app.utils.kapowarr_utils import check_volume_exists, get_total_volumes_from_stats
from app.utils.path_utils import map_kapowarr_to_local_path
from app.core.config import settings_manager


class VolumeService:
    """Service for managing volumes and their metadata"""
    
    def __init__(self):
        self.api_key = settings_manager.get_setting('kapowarr_api_key')
        self.base_url = settings_manager.get_setting('kapowarr_url')
        self.metadata_service = MetadataService()
        self.volume_db = VolumeDatabase()
        
        # Check for new volumes on initialization
        self.check_for_new_volumes()
    
    def check_for_new_volumes(self):
        """Check if Kapowarr stats have changed and update cache if needed"""
        try:
            print("🔍 Checking for new volumes on startup...")
            current_total = get_total_volumes_from_stats(self.api_key, self.base_url)
            
            if current_total is not None:
                if self.volume_db.check_kapowarr_stats_changed(current_total):
                    last_total = self.volume_db.get_last_kapowarr_stats()
                    print(f"📊 Kapowarr stats changed: {last_total or 'None'} → {current_total} volumes")
                    print("🔄 Updating cache to include new volumes...")
                    
                    # Force refresh the cache
                    self.get_volume_list(force_refresh=True)
                else:
                    print(f"✅ Kapowarr stats unchanged: {current_total} volumes")
            else:
                print("⚠️ Could not get current Kapowarr stats")
                
        except Exception as e:
            print(f"❌ Error checking for new volumes: {e}")
    
    def get_volume_list(self, limit: int = 100, force_refresh: bool = False) -> List[Dict[str, Any]]:
        """Get a list of available volumes using database cache or fresh search"""
        
        print(f"🔍 get_volume_list called with limit={limit}, force_refresh={force_refresh}")
        
        # Check if we have valid cached data and don't need to force refresh
        if not force_refresh:
            print("📚 Checking cache validity...")
            cache_valid = self.volume_db.is_cache_valid()
            print(f"📚 Cache valid: {cache_valid}")
            
            if cache_valid:
                print("📚 Using cached volume data")
                cached_volumes = self.volume_db.get_volumes(limit)
                print(f"📚 Retrieved {len(cached_volumes) if cached_volumes else 0} volumes from cache")
                if cached_volumes:
                    print(f"✅ Retrieved {len(cached_volumes)} volumes from cache")
                    return cached_volumes
                else:
                    print("⚠️ Cache validation passed but no volumes found in database")
            else:
                print("⚠️ Cache validation failed")
        else:
            print("🔄 Force refresh requested, skipping cache check")
        
        print("🔄 Cache expired or force refresh requested, searching for volumes...")
        
        # Perform fresh search
        volumes = []
        total_volumes = get_total_volumes_from_stats(self.api_key, self.base_url)
        
        if total_volumes is None:
            print("Warning: Could not get total volumes from stats, using limit-based search")
            max_check = limit
            target_count = limit
        else:
            # If we have stats, use the total_volumes as our target, but search beyond to find all volumes
            max_check = total_volumes * 2  # Search beyond the expected total to find all volumes
            target_count = total_volumes
            print(f"Stats indicate {total_volumes} volumes, searching up to {max_check} to find all available volumes")
        
        volume_count = 0
        consecutive_failures = 0
        max_consecutive_failures = 15  # Same failsafe as KapowarrSearch.py
        
        for volume_id in range(1, max_check + 1):
            if check_volume_exists(volume_id, self.api_key, self.base_url):
                # Get volume details to extract folder name
                folder_name = f'Volume {volume_id}'
                try:
                    volume_details = self.get_volume_details(volume_id)
                    if volume_details and 'folder' in volume_details:
                        # Use the path mapping utility to convert Kapowarr path to local path
                        kapowarr_parent_folder = settings_manager.get_setting('kapowarr_parent_folder', '/comics-1')
                        folder_name = map_kapowarr_to_local_path(
                            volume_details['folder'], 
                            kapowarr_parent_folder, 
                            'comics'  # Changed from '/comics' to 'comics' for relative path
                        )
                    else:
                        folder_name = volume_details.get('volume_folder', f'Volume {volume_id}') if volume_details else f'Volume {volume_id}'
                    # Small delay to be respectful to the API when fetching volume details
                    time.sleep(0.02)
                except:
                    folder_name = f'Volume {volume_id}'
                
                volumes.append({
                    'id': volume_id,
                    'volume_folder': folder_name,
                    'status': 'available'
                })
                volume_count += 1
                consecutive_failures = 0  # Reset failure counter
            else:
                consecutive_failures += 1
            
            # Stop when we reach the target volume count
            if volume_count >= target_count:
                print(f"Target volume count ({target_count}) reached, stopping search")
                break
            
            # Failsafe: if we've hit max consecutive failures, stop searching
            if consecutive_failures >= max_consecutive_failures:
                print(f"Failsafe triggered: {consecutive_failures} consecutive failures after checking {volume_id} volumes")
                break
            
            # Progress indicator every 10 volumes
            if volume_id % 10 == 0:
                print(f"Progress: {volume_id} volumes checked, {volume_count} found")
        
        print(f"Volume search completed: {volume_count} volumes found out of {volume_id} checked")
        
        # Store volumes in database for future use
        if volumes:
            self.volume_db.store_volumes(volumes)
            print(f"💾 Stored {len(volumes)} volumes in database cache")
        
        return volumes
    
    def get_volume_details(self, volume_id: int) -> Optional[Dict[str, Any]]:
        """Get detailed information about a specific volume"""
        try:
            # Check database first
            cached_details = self.volume_db.get_volume_details(volume_id)
            if cached_details:
                print(f"📚 Using cached volume details for volume {volume_id}")
                return cached_details
            
            # Fetch from API if not in database
            print(f"🔄 Fetching volume details for volume {volume_id} from API")
            volume = self.metadata_service.search_kapowarr_volume(str(volume_id))
            if volume and volume.get('result'):
                # Store in database for future use
                self.volume_db.store_volume_details(volume_id, volume['result'])
                print(f"💾 Stored volume {volume_id} details in database")
                return volume['result']
            return None
        except Exception as e:
            print(f"Error getting volume details: {e}")
            return None
    
    def process_volume_metadata(self, volume_id: int, manual_override: bool = False) -> Dict[str, Any]:
        """Process metadata for a volume and return results
        
        Args:
            volume_id: ID of the volume to process
            manual_override: If True, reprocess issues even if they already have metadata
        """
        try:
            print(f"🔄 Starting metadata processing for volume {volume_id} (manual_override={manual_override})")
            
            # First get volume details to see which issues have files
            volume_details = self.get_volume_details(volume_id)
            if not volume_details or 'issues' not in volume_details:
                print(f"No volume details or issues found for volume {volume_id}")
                return {}
            
            # Filter issues to only include those with files
            issues_with_files = []
            skipped_count = 0
            
            for issue in volume_details['issues']:
                if issue.get('files') and len(issue['files']) > 0:
                    issues_with_files.append(issue)
                else:
                    skipped_count += 1
            
            if skipped_count > 0:
                print(f"Skipping {skipped_count} issues without files from volume {volume_id}")
            
            if not issues_with_files:
                print(f"No issues with files found in volume {volume_id}")
                return {}
            
            print(f"Found {len(issues_with_files)} issues with files in volume {volume_id}")
            
            # Check which issues already have metadata processed
            issues_needing_metadata = []
            already_processed_count = 0
            
            for issue in issues_with_files:
                comicvine_id = issue.get('comicvine_id')
                if comicvine_id:
                    # Check if this issue already has metadata processed
                    issue_status = self.volume_db.get_issue_metadata_status(volume_id, comicvine_id)
                    if issue_status and issue_status.get('metadata_processed', False):
                        if manual_override:
                            # Manual override: include this issue for reprocessing
                            issues_needing_metadata.append(issue)
                            print(f"🔄 Manual override: including already processed issue {issue.get('issue_number', 'Unknown')} for reprocessing")
                        else:
                            # Scheduled task: skip already processed issues
                            already_processed_count += 1
                            print(f"Issue {issue.get('issue_number', 'Unknown')} already has metadata processed, skipping")
                            continue
                    else:
                        issues_needing_metadata.append(issue)
                        print(f"Issue {issue.get('issue_number', 'Unknown')} needs metadata processing")
                else:
                    print(f"Issue {issue.get('issue_number', 'Unknown')} has no ComicVine ID")
            
            if already_processed_count > 0 and not manual_override:
                print(f"Skipping {already_processed_count} already processed issues from volume {volume_id}")
            
            if not issues_needing_metadata:
                if manual_override:
                    print(f"🔄 Manual override: all issues in volume {volume_id} already have metadata, but reprocessing anyway...")
                    # For manual override, process all issues even if they already have metadata
                    issues_needing_metadata = issues_with_files.copy()
                else:
                    print(f"All issues in volume {volume_id} already have metadata processed")
                    # Update volume status to indicate all issues are processed
                    self.volume_db.update_volume_status(volume_id, metadata_processed=True)
                    return {}
            
            # Now process metadata for issues that need it
            if manual_override:
                print(f"🔄 Manual override: processing metadata for {len(issues_needing_metadata)} issues in volume {volume_id}")
                if already_processed_count > 0:
                    print(f"🔄 Note: {already_processed_count} issues already have metadata but will be reprocessed due to manual override")
            else:
                print(f"Processing metadata for {len(issues_needing_metadata)} issues that need it in volume {volume_id}")
            
            metadata_results = {}
            for issue in issues_needing_metadata:
                comicvine_id = issue.get('comicvine_id')
                issue_number = issue.get('issue_number', 'Unknown')
                
                print(f"Processing issue {issue_number} (ComicVine ID: {comicvine_id})")
                
                # Get ComicVine metadata directly
                metadata = self.metadata_service.get_comicvine_metadata(comicvine_id)
                if metadata:
                    metadata_results[comicvine_id] = {
                        'kapowarr_issue': issue,
                        'comicvine_metadata': metadata
                    }
                    
                    # Update issue metadata status
                    self.volume_db.update_issue_metadata_status(
                        volume_id, 
                        comicvine_id, 
                        issue_number,
                        metadata_processed=True
                    )
                    
                    print(f"✅ Successfully processed metadata for issue {issue_number}")
                else:
                    print(f"❌ Failed to get metadata for issue {issue_number}")
                
                # Rate limiting for ComicVine API
                time.sleep(1.0)
            
            print(f"Successfully processed metadata for {len(metadata_results)} issues")
            
            # Check if all issues in the volume now have metadata
            all_issues_processed = True
            for issue in issues_with_files:
                comicvine_id = issue.get('comicvine_id')
                if comicvine_id:
                    issue_status = self.volume_db.get_issue_metadata_status(volume_id, comicvine_id)
                    if not issue_status or not issue_status.get('metadata_processed', False):
                        all_issues_processed = False
                        break
            
            # Update volume status if all issues are processed
            if all_issues_processed:
                self.volume_db.update_volume_status(volume_id, metadata_processed=True)
                print(f"✅ All issues in volume {volume_id} now have metadata processed")
            
            return metadata_results
            
        except Exception as e:
            print(f"Error processing volume metadata: {e}")
            return {}
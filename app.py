from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, send_file
import os
import json
import time
from datetime import datetime
import threading
import queue
import tempfile

# Import functions from existing scripts
from KapowarrSearch import check_volume_exists, get_total_volumes_from_stats
from MetadataGather import ComicMetadataFetcher
from settings_manager import settings_manager
from volume_database import volume_db
from scheduled_tasks import ScheduledTaskManager

# Import utility functions
from utils import (
    test_kapowarr_connection_with_settings,
    test_comicvine_connection_with_settings,
    cleanup_temp_files,
    cleanup_temp_directories,
    generate_xml_files,
    map_kapowarr_to_local_path
)

# Import logging service
from app.services.logging_service import logging_service

app = Flask(__name__, static_folder='static')
app.secret_key = settings_manager.get_setting('flask_secret_key')

# Global variables for background tasks
task_queue = queue.Queue()
task_results = {}

class VolumeManager:
    def __init__(self):
        self.api_key = settings_manager.get_setting('kapowarr_api_key')
        self.base_url = settings_manager.get_setting('kapowarr_url')
        self.metadata_fetcher = ComicMetadataFetcher()
        
        # Only check for new volumes if API key is configured
        if self.is_configured():
            self.check_for_new_volumes()
        else:
            logging_service.warning("⚠️ Kapowarr API key not configured. Skipping volume check on startup.", "app")
    
    def is_configured(self):
        """Check if the VolumeManager has the required configuration"""
        # Check if API key is set and not a placeholder
        api_key_valid = (self.api_key and 
                        self.api_key.strip() and 
                        self.api_key != 'your-kapowarr-api-key-here' and
                        self.api_key != '')
        
        # Check if base URL is set and not a placeholder
        base_url_valid = (self.base_url and 
                         self.base_url.strip() and 
                         self.base_url != 'http://your-kapowarr-server:port' and
                         self.base_url != '')
        
        return api_key_valid and base_url_valid
    
    def check_for_new_volumes(self):
        """Check if Kapowarr stats have changed and update cache if needed"""
        try:
            logging_service.info("🔍 Checking for new volumes on startup...", "volume")
            current_total = get_total_volumes_from_stats(self.api_key, self.base_url)
            
            if current_total is not None:
                if volume_db.check_kapowarr_stats_changed(current_total):
                    last_total = volume_db.get_last_kapowarr_stats()
                    logging_service.info(f"📊 Kapowarr stats changed: {last_total or 'None'} → {current_total} volumes", "volume")
                    logging_service.info("🔄 Updating cache to include new volumes...", "volume")
                    
                    # Force refresh the cache
                    self.get_volume_list(force_refresh=True)
                else:
                    logging_service.info(f"✅ Kapowarr stats unchanged: {current_total} volumes", "volume")
            else:
                logging_service.warning("⚠️ Could not get current Kapowarr stats", "volume")
                
        except Exception as e:
            logging_service.error(f"❌ Error checking for new volumes: {e}", "volume")
    
    def get_volume_list(self, limit=100, force_refresh=False):
        """Get a list of available volumes using database cache or fresh search"""
        
        logging_service.debug(f"🔍 get_volume_list called with limit={limit}, force_refresh={force_refresh}", "volume")
        
        # Check if we have valid cached data and don't need to force refresh
        if not force_refresh:
            logging_service.debug("📚 Checking cache validity...", "volume")
            cache_valid = volume_db.is_cache_valid()
            logging_service.debug(f"📚 Cache valid: {cache_valid}", "volume")
            
            if cache_valid:
                logging_service.debug("📚 Using cached volume data", "volume")
                cached_volumes = volume_db.get_volumes(limit)
                logging_service.debug(f"📚 Retrieved {len(cached_volumes) if cached_volumes else 0} volumes from cache", "volume")
                if cached_volumes:
                    logging_service.info(f"✅ Retrieved {len(cached_volumes)} volumes from cache", "volume")
                    return cached_volumes
                else:
                    logging_service.warning("⚠️ Cache validation passed but no volumes found in database", "volume")
            else:
                logging_service.warning("⚠️ Cache validation failed", "volume")
        else:
            logging_service.info("🔄 Force refresh requested, skipping cache check", "volume")
        
        logging_service.info("🔄 Cache expired or force refresh requested, searching for volumes...", "volume")
        
        # Perform fresh search
        volumes = []
        total_volumes = get_total_volumes_from_stats(self.api_key, self.base_url)
        
        if total_volumes is None:
            logging_service.warning("Warning: Could not get total volumes from stats, using limit-based search", "volume")
            max_check = limit
            target_count = limit
        else:
            # If we have stats, use the total_volumes as our target, but search beyond to find all volumes
            max_check = total_volumes * 2  # Search beyond the expected total to find all volumes
            target_count = total_volumes
            logging_service.info(f"Stats indicate {total_volumes} volumes, searching up to {max_check} to find all available volumes", "volume")
        
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
                logging_service.info(f"Target volume count ({target_count}) reached, stopping search", "volume")
                break
            
            # Failsafe: if we've hit max consecutive failures, stop searching
            if consecutive_failures >= max_consecutive_failures:
                logging_service.warning(f"Failsafe triggered: {consecutive_failures} consecutive failures after checking {volume_id} volumes", "volume")
                break
            
            # Progress indicator every 10 volumes
            if volume_id % 10 == 0:
                logging_service.debug(f"Progress: {volume_id} volumes checked, {volume_count} found", "volume")
        
        logging_service.info(f"Volume search completed: {volume_count} volumes found out of {volume_id} checked", "volume")
        
        # Store volumes in database for future use
        if volumes:
            volume_db.store_volumes(volumes)
            logging_service.info(f"💾 Stored {len(volumes)} volumes in database cache", "volume")
        
        return volumes
    
    def get_volume_details(self, volume_id):
        """Get detailed information about a specific volume"""
        try:
            # Check database first
            cached_details = volume_db.get_volume_details(volume_id)
            if cached_details:
                logging_service.debug(f"📚 Using cached volume details for volume {volume_id}", "volume")
                return cached_details
            
            # Fetch from API if not in database
            logging_service.info(f"🔄 Fetching volume details for volume {volume_id} from API", "volume")
            volume = self.metadata_fetcher.search_kapowarr_volume(str(volume_id))
            if volume and volume.get('result'):
                # Store in database for future use
                volume_db.store_volume_details(volume_id, volume['result'])
                logging_service.info(f"💾 Stored volume {volume_id} details in database", "volume")
                return volume['result']
            return None
        except Exception as e:
            logging_service.error(f"Error getting volume details: {e}", "volume")
            return None
    
    def process_volume_metadata(self, volume_id, manual_override=False):
        """Process metadata for a volume and return results
        
        Args:
            volume_id: ID of the volume to process
            manual_override: If True, reprocess issues even if they already have metadata
        """
        try:
            logging_service.info(f"🔄 Starting metadata processing for volume {volume_id} (manual_override={manual_override})", "volume")
            
            # First get volume details to see which issues have files
            volume_details = self.get_volume_details(volume_id)
            if not volume_details or 'issues' not in volume_details:
                logging_service.warning(f"No volume details or issues found for volume {volume_id}", "volume")
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
                logging_service.info(f"Skipping {skipped_count} issues without files from volume {volume_id}", "volume")
            
            if not issues_with_files:
                logging_service.warning(f"No issues with files found in volume {volume_id}", "volume")
                return {}
            
            logging_service.info(f"Found {len(issues_with_files)} issues with files in volume {volume_id}", "volume")
            
            # Check which issues already have metadata processed
            issues_needing_metadata = []
            already_processed_count = 0
            
            for issue in issues_with_files:
                comicvine_id = issue.get('comicvine_id')
                if comicvine_id:
                    # Check if this issue already has metadata processed
                    issue_status = volume_db.get_issue_metadata_status(volume_id, comicvine_id)
                    if issue_status and issue_status.get('metadata_processed', False):
                        if manual_override:
                            # Manual override: include this issue for reprocessing
                            issues_needing_metadata.append(issue)
                            logging_service.info(f"🔄 Manual override: including already processed issue {issue.get('issue_number', 'Unknown')} for reprocessing", "volume")
                        else:
                            # Scheduled task: skip already processed issues
                            already_processed_count += 1
                            logging_service.debug(f"Issue {issue.get('issue_number', 'Unknown')} already has metadata processed, skipping", "volume")
                            continue
                    else:
                        issues_needing_metadata.append(issue)
                        logging_service.debug(f"Issue {issue.get('issue_number', 'Unknown')} needs metadata processing", "volume")
                else:
                    logging_service.warning(f"Issue {issue.get('issue_number', 'Unknown')} has no ComicVine ID", "volume")
            
            if already_processed_count > 0 and not manual_override:
                logging_service.info(f"Skipping {already_processed_count} already processed issues from volume {volume_id}", "volume")
            
            if not issues_needing_metadata:
                if manual_override:
                    logging_service.info(f"🔄 Manual override: all issues in volume {volume_id} already have metadata, but reprocessing anyway...", "volume")
                    # For manual override, process all issues even if they already have metadata
                    issues_needing_metadata = issues_with_files.copy()
                else:
                    logging_service.info(f"All issues in volume {volume_id} already have metadata processed", "volume")
                    # Update volume status to indicate all issues are processed
                    volume_db.update_volume_status(volume_id, metadata_processed=True)
                    return {}
            
            # Now process metadata for issues that need it
            if manual_override:
                logging_service.info(f"🔄 Manual override: processing metadata for {len(issues_needing_metadata)} issues in volume {volume_id}", "volume")
                if already_processed_count > 0:
                    logging_service.info(f"🔄 Note: {already_processed_count} issues already have metadata but will be reprocessed due to manual override", "volume")
            else:
                logging_service.info(f"Processing metadata for {len(issues_needing_metadata)} issues that need it in volume {volume_id}", "volume")
            
            # Import the metadata injector for processing individual issues
            from MetaDataAdd import ComicMetadataInjector
            injector = ComicMetadataInjector()
            
            metadata_results = {}
            for issue in issues_needing_metadata:
                comicvine_id = issue.get('comicvine_id')
                issue_number = issue.get('issue_number', 'Unknown')
                
                logging_service.info(f"Processing issue {issue_number} (ComicVine ID: {comicvine_id})", "volume")
                
                # Get ComicVine metadata directly
                metadata = self.metadata_fetcher.get_comicvine_metadata(comicvine_id)
                if metadata:
                    # Find the issue index in the volume details
                    issue_index = None
                    for i, vol_issue in enumerate(volume_details['issues']):
                        if vol_issue.get('comicvine_id') == comicvine_id:
                            issue_index = i
                            break
                    
                    if issue_index is not None:
                        # Process and inject metadata for this specific issue
                        result = injector.process_issue_metadata(
                            volume_id, 
                            issue_index, 
                            volume_details, 
                            self.metadata_fetcher, 
                            volume_db
                        )
                        
                        if result['success']:
                            metadata_results[comicvine_id] = {
                                'kapowarr_issue': issue,
                                'comicvine_metadata': metadata,
                                'injection_result': result
                            }
                            logging_service.info(f"✅ Successfully processed and injected metadata for issue {issue_number}", "volume")
                        else:
                            logging_service.error(f"❌ Failed to inject metadata for issue {issue_number}: {result.get('error', 'Unknown error')}", "volume")
                    else:
                        logging_service.error(f"❌ Could not find issue index for issue {issue_number}", "volume")
                else:
                    logging_service.error(f"❌ Failed to get metadata for issue {issue_number}", "volume")
                
                # Rate limiting for ComicVine API
                time.sleep(1.0)
            
            logging_service.info(f"Successfully processed metadata for {len(metadata_results)} issues", "volume")
            
            # Check if all issues in the volume now have metadata
            all_issues_processed = True
            for issue in issues_with_files:
                comicvine_id = issue.get('comicvine_id')
                if comicvine_id:
                    issue_status = volume_db.get_issue_metadata_status(volume_id, comicvine_id)
                    if not issue_status or not issue_status.get('metadata_processed', False):
                        all_issues_processed = False
                        break
            
            # Update volume status if all issues are processed
            if all_issues_processed:
                volume_db.update_volume_status(volume_id, metadata_processed=True)
                logging_service.info(f"✅ All issues in volume {volume_id} now have metadata processed", "volume")
            
            return metadata_results
            
        except Exception as e:
            logging_service.error(f"Error processing volume metadata: {e}", "volume")
            return {}
    


# Initialize volume manager
volume_manager = VolumeManager()

# Initialize scheduled task manager
scheduled_task_manager = ScheduledTaskManager(volume_manager, volume_db, settings_manager)

@app.route('/')
def index():
    """Main page showing volume list"""
    # Check if configuration is complete
    is_configured = volume_manager.is_configured()
    
    return render_template('index.html', config={
        'KAPOWARR_API_KEY': volume_manager.api_key,
        'KAPOWARR_URL': volume_manager.base_url,
        'IS_CONFIGURED': is_configured
    })

@app.route('/volume/<int:volume_id>')
def volume_detail(volume_id):
    """Show details for a specific volume"""
    volume_details = volume_manager.get_volume_details(volume_id)
    if not volume_details:
        flash('Volume not found', 'error')
        return redirect(url_for('index'))
    
    return render_template('volume_detail.html', 
                         volume=volume_details, 
                         volume_id=volume_id,
                         config={
                             'KAPOWARR_API_KEY': volume_manager.api_key,
                             'KAPOWARR_URL': volume_manager.base_url
                         })

@app.route('/scheduled-tasks')
def scheduled_tasks():
    """Display the scheduled tasks management page"""
    try:
        return render_template('scheduled_tasks.html', config=settings_manager)
    except Exception as e:
        flash(f'Error loading scheduled tasks page: {str(e)}', 'error')
        return redirect(url_for('index'))

@app.route('/logs')
def logs_page():
    """Display the application logs page"""
    try:
        return render_template('logs.html')
    except Exception as e:
        flash(f'Error loading logs page: {str(e)}', 'error')
        return redirect(url_for('index'))

@app.route('/api/volumes')
def get_volumes():
    """API endpoint to get volumes"""
    try:
        # Check if app is configured
        if not volume_manager.is_configured():
            return jsonify({
                'success': False, 
                'error': 'App not configured. Please set up your API keys in the Settings page.'
            })
        
        limit = request.args.get('limit', 100, type=int)
        
        logging_service.info(f"API request for volumes with limit: {limit}", "api")
        volumes = volume_manager.get_volume_list(limit)
        logging_service.info(f"Returning {len(volumes)} volumes", "api")
        return jsonify({'success': True, 'volumes': volumes})
    except Exception as e:
        logging_service.error(f"Error in get_volumes: {e}", "api")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/volume/<int:volume_id>/metadata', methods=['POST'])
def process_volume_metadata(volume_id):
    """Process metadata for a volume"""
    try:
        # Start background task
        task_id = f"metadata_{volume_id}_{int(time.time())}"
        
        def metadata_task():
            try:
                # Manual button press: always allow processing (manual_override=True)
                metadata = volume_manager.process_volume_metadata(volume_id, manual_override=True)
                
                # Get total issues from volume details for comparison
                volume_details = volume_manager.get_volume_details(volume_id)
                total_issues = len(volume_details.get('issues', [])) if volume_details else 0
                issues_with_files = len(metadata) if metadata else 0
                
                task_results[task_id] = {
                    'status': 'completed',
                    'result': metadata,
                    'message': f'Successfully processed {issues_with_files} issues with files (skipped {total_issues - issues_with_files} without files)'
                }
            except Exception as e:
                task_results[task_id] = {
                    'status': 'error',
                    'error': str(e)
                }
        
        # Start task in background
        thread = threading.Thread(target=metadata_task)
        thread.daemon = True
        thread.start()
        
        return jsonify({
            'success': True,
            'task_id': task_id,
            'message': 'Metadata processing started'
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/volumes/batch/metadata', methods=['POST'])
def batch_process_volume_metadata():
    """Process metadata for multiple volumes"""
    try:
        data = request.get_json()
        volume_ids = data.get('volume_ids', [])
        
        if not volume_ids:
            return jsonify({'success': False, 'error': 'No volume IDs provided'})
        
        # Start background task for batch processing
        task_id = f"batch_metadata_{int(time.time())}"
        
        def batch_metadata_task():
            try:
                results = []
                total_processed = 0
                total_errors = 0
                
                for volume_id in volume_ids:
                    try:
                        # Process each volume
                        metadata = volume_manager.process_volume_metadata(volume_id, manual_override=True)
                        
                        # Get total issues from volume details for comparison
                        volume_details = volume_manager.get_volume_details(volume_id)
                        total_issues = len(volume_details.get('issues', [])) if volume_details else 0
                        issues_with_files = len(metadata) if metadata else 0
                        
                        results.append({
                            'volume_id': volume_id,
                            'success': True,
                            'issues_processed': issues_with_files,
                            'issues_skipped': total_issues - issues_with_files,
                            'message': f'Successfully processed {issues_with_files} issues with files'
                        })
                        total_processed += 1
                        
                    except Exception as e:
                        results.append({
                            'volume_id': volume_id,
                            'success': False,
                            'error': str(e)
                        })
                        total_errors += 1
                
                task_results[task_id] = {
                    'status': 'completed',
                    'result': results,
                    'message': f'Batch processing completed. {total_processed} successful, {total_errors} errors.'
                }
                
            except Exception as e:
                task_results[task_id] = {
                    'status': 'error',
                    'error': str(e)
                }
        
        # Start task in background
        thread = threading.Thread(target=batch_metadata_task)
        thread.daemon = True
        thread.start()
        
        return jsonify({
            'success': True,
            'task_id': task_id,
            'message': f'Batch metadata processing started for {len(volume_ids)} volumes'
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/volume/<int:volume_id>/issue/<int:issue_index>/metadata', methods=['POST'])
def process_issue_metadata(volume_id, issue_index):
    """Process metadata for a specific issue by index and inject into comic files"""
    try:
        # Start background task
        task_id = f"issue_metadata_{volume_id}_{issue_index}_{int(time.time())}"
        
        def issue_metadata_task():
            try:
                # Get volume details to find the specific issue
                volume_details = volume_manager.get_volume_details(volume_id)
                if not volume_details or 'issues' not in volume_details:
                    task_results[task_id] = {
                        'status': 'error',
                        'error': 'Volume or issues not found'
                    }
                    return
                
                # Use the new method from MetaDataAdd
                from MetaDataAdd import ComicMetadataInjector
                injector = ComicMetadataInjector()
                
                result = injector.process_issue_metadata(
                    volume_id, 
                    issue_index, 
                    volume_details, 
                    volume_manager.metadata_fetcher, 
                    volume_db
                )
                
                if result['success']:
                    task_results[task_id] = {
                        'status': 'completed',
                        'result': result['result'],
                        'message': result['message']
                    }
                else:
                    task_results[task_id] = {
                        'status': 'error',
                        'error': result['error']
                    }
                
            except Exception as e:
                task_results[task_id] = {
                    'status': 'error',
                    'error': str(e)
                }
        
        # Start task in background
        thread = threading.Thread(target=issue_metadata_task)
        thread.daemon = True
        thread.start()
        
        return jsonify({
            'success': True,
            'task_id': task_id,
            'message': f'Metadata processing and injection started for issue {issue_index}'
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/task/<task_id>/status')
def get_task_status(task_id):
    """Get status of a background task"""
    if task_id in task_results:
        return jsonify(task_results[task_id])
    else:
        return jsonify({'status': 'not_found'})

@app.route('/api/volume/<int:volume_id>/xml', methods=['POST'])
def prepare_xml_for_injection(volume_id):
    """Prepare XML metadata for comic file injection"""
    try:
        # Get metadata first - manual button press should always work
        metadata = volume_manager.process_volume_metadata(volume_id, manual_override=True)
        if not metadata:
            return jsonify({'success': False, 'error': 'No metadata available for this volume'})
        
        # Generate XML files
        temp_dir = f"temp_xml_{volume_id}_{int(time.time())}"
        xml_dir = generate_xml_files(metadata, temp_dir)
        
        if xml_dir and os.path.exists(xml_dir):
            # Count XML files generated
            xml_files = [f for f in os.listdir(xml_dir) if f.endswith('.xml')]
            xml_count = len(xml_files)
            
            if xml_count > 0:
                # Update database status
                volume_db.update_volume_status(volume_id, xml_generated=True)
                
                return jsonify({
                    'success': True,
                    'message': f'Successfully generated {xml_count} XML files',
                    'xml_count': xml_count,
                    'output_directory': xml_dir,
                    'xml_files': xml_files
                })
            else:
                return jsonify({
                    'success': False,
                    'message': 'No XML files were generated'
                })
        else:
            return jsonify({
                'success': False,
                'message': 'Failed to generate XML files'
            })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/volume/<int:volume_id>/inject', methods=['POST'])
def inject_metadata_into_comics(volume_id):
    """Inject metadata into comic files for a specific volume"""
    try:
        # Get volume details to get the folder path
        volume_details = volume_manager.get_volume_details(volume_id)
        if not volume_details:
            return jsonify({'success': False, 'error': 'Volume details not found'})
        
        # Get the folder path from volume details
        kapowarr_folder_path = volume_details.get('folder')
        if not kapowarr_folder_path:
            return jsonify({'success': False, 'error': 'No folder path found for this volume'})
        
        # Check if XML files exist
        xml_dir = f"temp_xml_{volume_id}_{int(time.time())}"
        if not os.path.exists(xml_dir):
            # Try to find existing XML directory
            existing_dirs = [d for d in os.listdir('.') if d.startswith(f'temp_xml_{volume_id}_')]
            if existing_dirs:
                xml_dir = existing_dirs[0]
            else:
                return jsonify({'success': False, 'error': 'No XML files found for this volume. Generate XML first.'})
        
        # Get list of XML files
        xml_files = []
        for item in os.listdir(xml_dir):
            if item.endswith('.xml'):
                xml_files.append(os.path.join(xml_dir, item))
        
        if not xml_files:
            return jsonify({'success': False, 'error': 'No XML files found in the output directory'})
        
        # Import and use the metadata injector
        from MetaDataAdd import ComicMetadataInjector
        
        injector = ComicMetadataInjector()
        result = injector.inject_metadata(volume_id, xml_files, kapowarr_folder_path)
        
        if result['success']:
            # Update database status
            volume_db.update_volume_status(volume_id, metadata_injected=True)
            
            return jsonify({
                'success': True,
                'message': result['message'],
                'results': result['results'],
                'local_folder': result['local_folder'],
                'kapowarr_folder': result['kapowarr_folder']
            })
        else:
            return jsonify({
                'success': False,
                'error': result['error']
            })
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/download/<path:filename>')
def download_file(filename):
    """Download generated files"""
    try:
        file_path = os.path.join('temp_xml', filename)
        if os.path.exists(file_path):
            return send_file(file_path, as_attachment=True)
        else:
            flash('File not found', 'error')
            return redirect(url_for('index'))
    except Exception as e:
        flash(f'Error downloading file: {e}', 'error')
        return redirect(url_for('index'))

@app.route('/settings')
def settings_page():
    """Settings page"""
    return render_template('settings.html', 
                         settings=settings_manager.get_all_settings(),
                         config={
                             'KAPOWARR_API_KEY': settings_manager.get_setting('kapowarr_api_key'),
                             'KAPOWARR_URL': settings_manager.get_setting('kapowarr_url')
                         })

@app.route('/api/settings', methods=['POST'])
def save_settings():
    """Save application settings"""
    try:
        settings = request.get_json()
        if settings_manager.save_settings(settings):
            return jsonify({'success': True, 'message': 'Settings saved successfully'})
        else:
            return jsonify({'success': False, 'error': 'Failed to save settings'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/settings/test', methods=['POST'])
def test_settings():
    """Test connection settings"""
    try:
        settings = request.get_json()
        
        # Test Kapowarr connection with passed settings
        kapowarr_result = test_kapowarr_connection_with_settings(settings)
        
        # Test ComicVine connection with passed settings
        comicvine_result = test_comicvine_connection_with_settings(settings)
        
        return jsonify({
            'success': True,
            'kapowarr': kapowarr_result,
            'comicvine': comicvine_result
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})



@app.route('/cleanup', methods=['POST'])
def cleanup_temp_files():
    """Clean up temporary files"""
    try:
        if cleanup_temp_files():
            flash('Temporary files cleaned up', 'success')
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'error': 'Failed to clean up temporary files'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/cache/info')
def get_cache_info():
    """Get information about the volume cache"""
    try:
        cache_info = volume_db.get_cache_info()
        return jsonify({'success': True, 'cache_info': cache_info})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/cache/clear', methods=['POST'])
def clear_cache():
    """Clear the volume cache"""
    try:
        if volume_db.clear_cache():
            return jsonify({'success': True, 'message': 'Volume cache cleared successfully'})
        else:
            return jsonify({'success': False, 'error': 'Failed to clear cache'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/cache/refresh', methods=['POST'])
def refresh_cache():
    """Force refresh of the volume cache"""
    try:
        # Force refresh by getting volumes with force_refresh=True
        volumes = volume_manager.get_volume_list(force_refresh=True)
        return jsonify({
            'success': True, 
            'message': f'Cache refreshed successfully. Found {len(volumes)} volumes.',
            'volumes_count': len(volumes)
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/cache/check-new', methods=['POST'])
def check_for_new_volumes():
    """Check if there are new volumes and update cache if needed"""
    try:
        # Get current Kapowarr stats
        current_total = get_total_volumes_from_stats(volume_manager.api_key, volume_manager.base_url)
        
        if current_total is None:
            return jsonify({'success': False, 'error': 'Could not get current Kapowarr stats'})
        
        # Check if stats have changed
        if volume_db.check_kapowarr_stats_changed(current_total):
            last_total = volume_db.get_last_kapowarr_stats()
            
            # Update cache with new volumes
            volumes = volume_manager.get_volume_list(force_refresh=True)
            
            return jsonify({
                'success': True,
                'new_volumes_found': True,
                'message': f'New volumes detected! Kapowarr stats changed from {last_total or "None"} to {current_total} volumes. Cache updated with {len(volumes)} volumes.',
                'volumes_count': len(volumes),
                'stats_change': {
                    'from': last_total,
                    'to': current_total
                }
            })
        else:
            return jsonify({
                'success': True,
                'new_volumes_found': False,
                'message': f'No new volumes detected. Kapowarr stats unchanged: {current_total} volumes.',
                'volumes_count': current_total
            })
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/cache/update-paths', methods=['POST'])
def update_database_paths():
    """Update database paths to use relative paths instead of absolute paths"""
    try:
        if volume_db.update_paths_to_relative():
            return jsonify({
                'success': True, 
                'message': 'Database paths updated to relative format successfully'
            })
        else:
            return jsonify({
                'success': False, 
                'error': 'Failed to update database paths'
            })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/cache/migrate-schema', methods=['POST'])
def migrate_database_schema():
    """Force database schema migration to add missing columns"""
    try:
        if volume_db.force_schema_migration():
            return jsonify({
                'success': True, 
                'message': 'Database schema migration completed successfully'
            })
        else:
            return jsonify({
                'success': False, 
                'error': 'Failed to migrate database schema'
            })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/cleanup/temp', methods=['POST'])
def cleanup_temp_directories():
    """Clean up any orphaned temporary directories"""
    try:
        result = cleanup_temp_directories()
        return jsonify(result)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# Scheduled Tasks API Endpoints
@app.route('/api/scheduled-tasks/status', methods=['GET'])
def get_scheduled_tasks_status():
    """Get the status of the scheduled task system"""
    try:
        stats = scheduled_task_manager.get_stats()
        config = scheduled_task_manager.get_config()
        scheduled_tasks = scheduled_task_manager.get_scheduled_tasks()
        
        return jsonify({
            'success': True,
            'running': scheduled_task_manager.running,
            'stats': stats,
            'config': config,
            'scheduled_tasks': scheduled_tasks
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/scheduled-tasks/start', methods=['POST'])
def start_scheduled_tasks():
    """Start the scheduled task system"""
    try:
        scheduled_task_manager.start()
        return jsonify({
            'success': True,
            'message': 'Scheduled task system started successfully'
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/scheduled-tasks/stop', methods=['POST'])
def stop_scheduled_tasks():
    """Stop the scheduled task system"""
    try:
        scheduled_task_manager.stop()
        return jsonify({
            'success': True,
            'message': 'Scheduled task system stopped successfully'
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/scheduled-tasks/run-task', methods=['POST'])
def run_scheduled_task_now():
    """Run a specific scheduled task immediately"""
    try:
        data = request.get_json()
        task_name = data.get('task_name')
        
        if not task_name:
            return jsonify({'success': False, 'error': 'Task name is required'})
        
        scheduled_task_manager.run_task_now(task_name)
        
        return jsonify({
            'success': True,
            'message': f'Task "{task_name}" started successfully'
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/scheduled-tasks/config', methods=['POST'])
def update_scheduled_tasks_config():
    """Update the configuration of the scheduled task system"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'success': False, 'error': 'Configuration data is required'})
        
        scheduled_task_manager.update_config(data)
        
        return jsonify({
            'success': True,
            'message': 'Scheduled task configuration updated successfully'
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/scheduled-tasks/config/reset', methods=['POST'])
def reset_scheduled_tasks_config():
    """Reset the configuration to default values"""
    try:
        scheduled_task_manager.reset_config_to_defaults()
        
        return jsonify({
            'success': True,
            'message': 'Scheduled task configuration reset to defaults successfully'
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

def start_scheduled_tasks():
    """Start the scheduled task system"""
    try:
        scheduled_task_manager.start()
        print("✅ Scheduled task system started successfully")
    except Exception as e:
        print(f"❌ Failed to start scheduled task system: {e}")

@app.route('/api/volume/<int:volume_id>/issue/<int:issue_index>/reset-status', methods=['POST'])
def reset_issue_metadata_status(volume_id, issue_index):
    """Reset metadata status for a specific issue to allow reprocessing"""
    try:
        # Get volume details to find the specific issue
        volume_details = volume_manager.get_volume_details(volume_id)
        if not volume_details or 'issues' not in volume_details:
            return jsonify({'success': False, 'error': 'Volume or issues not found'})
        
        # Check if issue index is valid
        if issue_index < 0 or issue_index >= len(volume_details['issues']):
            return jsonify({
                'success': False, 
                'error': f'Issue index {issue_index} is out of range. Volume has {len(volume_details["issues"])} issues.'
            })
        
        # Get the specific issue by index
        target_issue = volume_details['issues'][issue_index]
        comicvine_id = target_issue.get('comicvine_id')
        
        if not comicvine_id:
            return jsonify({'success': False, 'error': f'Issue {issue_index} has no ComicVine ID'})
        
        # Reset the issue metadata status
        if volume_db.update_issue_metadata_status(
            volume_id, 
            comicvine_id, 
            target_issue.get('issue_number', 'Unknown'),
            metadata_processed=False,
            metadata_injected=False
        ):
            return jsonify({
                'success': True,
                'message': f'Successfully reset metadata status for issue {issue_index}',
                'issue_number': target_issue.get('issue_number', 'Unknown'),
                'comicvine_id': comicvine_id
            })
        else:
            return jsonify({'success': False, 'error': 'Failed to reset issue metadata status'})
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/volume/<int:volume_id>/reset-all-issues', methods=['POST'])
def reset_all_issues_metadata_status(volume_id):
    """Reset metadata status for all issues in a volume to allow reprocessing"""
    try:
        # Get volume details
        volume_details = volume_manager.get_volume_details(volume_id)
        if not volume_details or 'issues' not in volume_details:
            return jsonify({'success': False, 'error': 'Volume or issues not found'})
        
        # Reset status for all issues
        reset_count = 0
        for issue in volume_details['issues']:
            comicvine_id = issue.get('comicvine_id')
            if comicvine_id:
                if volume_db.update_issue_metadata_status(
                    volume_id,
                    comicvine_id,
                    issue.get('issue_number', 'Unknown'),
                    metadata_processed=False,
                    metadata_injected=False
                ):
                    reset_count += 1
        
        # Also reset volume status
        volume_db.update_volume_status(
            volume_id, 
            metadata_processed=False,
            xml_generated=False,
            metadata_injected=False
        )
        
        return jsonify({
            'success': True,
            'message': f'Successfully reset metadata status for {reset_count} issues in volume {volume_id}',
            'issues_reset': reset_count,
            'volume_id': volume_id
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/volume/<int:volume_id>/issue-status')
def get_volume_issue_status(volume_id):
    """Get detailed metadata status for all issues in a volume"""
    try:
        # Get volume details
        volume_details = volume_manager.get_volume_details(volume_id)
        if not volume_details or 'issues' not in volume_details:
            return jsonify({'success': False, 'error': 'Volume or issues not found'})
        
        # Use the new method from volume_database
        result = volume_db.get_volume_issue_status(volume_id, volume_details)
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# Logs API endpoints
@app.route('/api/logs')
def get_logs():
    """Get application logs with optional filtering"""
    try:
        limit = request.args.get('limit', 100, type=int)
        level = request.args.get('level', None)
        source = request.args.get('source', None)
        start_date = request.args.get('start_date', None)
        end_date = request.args.get('end_date', None)
        
        logs = logging_service.get_logs(
            limit=limit,
            level=level,
            source=source,
            start_date=start_date,
            end_date=end_date
        )
        
        return jsonify({
            'success': True,
            'logs': logs
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/logs/stats')
def get_log_stats():
    """Get log statistics"""
    try:
        stats = logging_service.get_log_stats()
        return jsonify(stats)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/logs/clear', methods=['POST'])
def clear_logs():
    """Clear all application logs"""
    try:
        logging_service.clear_logs()
        return jsonify({'success': True, 'message': 'Logs cleared successfully'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/logs/export')
def export_logs():
    """Export logs in specified format"""
    try:
        format_type = request.args.get('format', 'json')
        level = request.args.get('level', None)
        source = request.args.get('source', None)
        limit = request.args.get('limit', None, type=int)
        
        # Get filtered logs
        logs = logging_service.get_logs(
            limit=limit,
            level=level,
            source=source
        )
        
        # Export in requested format
        if format_type == 'json':
            from flask import Response
            return Response(
                json.dumps(logs, indent=2, ensure_ascii=False),
                mimetype='application/json',
                headers={'Content-Disposition': f'attachment; filename=logs_{datetime.now().strftime("%Y%m%d")}.json'}
            )
        elif format_type == 'txt':
            from flask import Response
            lines = []
            for log in logs:
                lines.append(f"[{log['timestamp']}] {log['level']} [{log['source']}] {log['message']}")
            
            return Response(
                '\n'.join(lines),
                mimetype='text/plain',
                headers={'Content-Disposition': f'attachment; filename=logs_{datetime.now().strftime("%Y%m%d")}.txt'}
            )
        else:
            return jsonify({'success': False, 'error': f'Unsupported format: {format_type}'})
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

if __name__ == '__main__':
    # Start scheduled tasks
    start_scheduled_tasks()
    
    # Start Flask app
    app.run(debug=True, host='0.0.0.0', port=5000)

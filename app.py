from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, send_file
import os
import json
import time
from datetime import datetime
import threading
import queue
import tempfile
import zipfile

# Import functions from existing scripts
from KapowarrSearch import check_volume_exists, get_total_volumes_from_stats
from MetadataGather import ComicMetadataFetcher
from CreateXML import ComicInfoXMLGenerator
from settings_manager import settings_manager
from volume_database import volume_db

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
        self.xml_generator = ComicInfoXMLGenerator()
        
        # Check for new volumes on initialization
        self.check_for_new_volumes()
    
    def check_for_new_volumes(self):
        """Check if Kapowarr stats have changed and update cache if needed"""
        try:
            print("🔍 Checking for new volumes on startup...")
            current_total = get_total_volumes_from_stats(self.api_key, self.base_url)
            
            if current_total is not None:
                if volume_db.check_kapowarr_stats_changed(current_total):
                    last_total = volume_db.get_last_kapowarr_stats()
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
    
    def get_volume_list(self, limit=100, force_refresh=False):
        """Get a list of available volumes using database cache or fresh search"""
        
        # Check if we have valid cached data and don't need to force refresh
        if not force_refresh and volume_db.is_cache_valid():
            print("📚 Using cached volume data")
            cached_volumes = volume_db.get_volumes(limit)
            if cached_volumes:
                print(f"✅ Retrieved {len(cached_volumes)} volumes from cache")
                return cached_volumes
        
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
            volume_db.store_volumes(volumes)
            print(f"💾 Stored {len(volumes)} volumes in database cache")
        
        return volumes
    
    def get_volume_details(self, volume_id):
        """Get detailed information about a specific volume"""
        try:
            # Check database first
            cached_details = volume_db.get_volume_details(volume_id)
            if cached_details:
                print(f"📚 Using cached volume details for volume {volume_id}")
                return cached_details
            
            # Fetch from API if not in database
            print(f"🔄 Fetching volume details for volume {volume_id} from API")
            volume = self.metadata_fetcher.search_kapowarr_volume(str(volume_id))
            if volume and volume.get('result'):
                # Store in database for future use
                volume_db.store_volume_details(volume_id, volume['result'])
                print(f"💾 Stored volume {volume_id} details in database")
                return volume['result']
            return None
        except Exception as e:
            print(f"Error getting volume details: {e}")
            return None
    
    def process_volume_metadata(self, volume_id):
        """Process metadata for a volume and return results"""
        try:
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
            
            # Now process metadata only for issues with files by calling ComicVine API directly
            print(f"Processing metadata for {len(issues_with_files)} issues with files in volume {volume_id}")
            
            metadata_results = {}
            for issue in issues_with_files:
                comicvine_id = issue.get('comicvine_id')
                if comicvine_id:
                    print(f"Processing issue {issue.get('issue_number', 'Unknown')} (ComicVine ID: {comicvine_id})")
                    
                    # Get ComicVine metadata directly
                    metadata = self.metadata_fetcher.get_comicvine_metadata(comicvine_id)
                    if metadata:
                        metadata_results[comicvine_id] = {
                            'kapowarr_issue': issue,
                            'comicvine_metadata': metadata
                        }
                    
                    # Rate limiting for ComicVine API
                    time.sleep(1.0)
                else:
                    print(f"Issue {issue.get('issue_number', 'Unknown')} has no ComicVine ID")
            
            print(f"Successfully processed metadata for {len(metadata_results)} issues with files")
            
            # Update database status
            volume_db.update_volume_status(volume_id, metadata_processed=True)
            
            return metadata_results
            
        except Exception as e:
            print(f"Error processing volume metadata: {e}")
            return {}
    
    def generate_xml_files(self, metadata, output_dir="temp_xml"):
        """Generate XML files for metadata"""
        try:
            # Create temporary directory
            os.makedirs(output_dir, exist_ok=True)
            
            # Create a temporary metadata file for the XML generator
            temp_metadata_file = os.path.join(output_dir, "temp_metadata.json")
            with open(temp_metadata_file, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False)
            
            # Generate XML files using the existing method
            self.xml_generator.generate_xml_files(temp_metadata_file, output_dir)
            
            # Create zip file
            zip_filename = f"comic_info_xml_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
            zip_path = os.path.join(output_dir, zip_filename)
            
            with zipfile.ZipFile(zip_path, 'w') as zipf:
                for root, dirs, files in os.walk(output_dir):
                    for file in files:
                        if file.endswith('.xml'):
                            file_path = os.path.join(root, file)
                            arcname = os.path.relpath(file_path, output_dir)
                            zipf.write(file_path, arcname)
            
            return zip_path
        except Exception as e:
            print(f"Error generating XML files: {e}")
            return None

# Initialize volume manager
volume_manager = VolumeManager()

@app.route('/')
def index():
    """Main page showing volume list"""
    return render_template('index.html', config={
        'KAPOWARR_API_KEY': volume_manager.api_key,
        'KAPOWARR_URL': volume_manager.base_url
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

@app.route('/api/volumes')
def get_volumes():
    """API endpoint to get volumes"""
    try:
        limit = request.args.get('limit', 100, type=int)
        
        print(f"API request for volumes with limit: {limit}")
        volumes = volume_manager.get_volume_list(limit)
        print(f"Returning {len(volumes)} volumes")
        return jsonify({'success': True, 'volumes': volumes})
    except Exception as e:
        print(f"Error in get_volumes: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/volume/<int:volume_id>/metadata', methods=['POST'])
def process_volume_metadata(volume_id):
    """Process metadata for a volume"""
    try:
        # Start background task
        task_id = f"metadata_{volume_id}_{int(time.time())}"
        
        def metadata_task():
            try:
                metadata = volume_manager.process_volume_metadata(volume_id)
                
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

@app.route('/api/task/<task_id>/status')
def get_task_status(task_id):
    """Get status of a background task"""
    if task_id in task_results:
        return jsonify(task_results[task_id])
    else:
        return jsonify({'status': 'not_found'})

@app.route('/api/volume/<int:volume_id>/xml', methods=['POST'])
def generate_xml_files(volume_id):
    """Generate XML files for a volume"""
    try:
        # Get metadata first
        metadata = volume_manager.process_volume_metadata(volume_id)
        if not metadata:
            return jsonify({'success': False, 'error': 'No metadata available for this volume'})
        
        # Generate XML files
        temp_dir = f"temp_xml_{volume_id}_{int(time.time())}"
        zip_path = volume_manager.generate_xml_files(metadata, temp_dir)
        
        if zip_path and os.path.exists(zip_path):
            # Update database status
            volume_db.update_volume_status(volume_id, xml_generated=True)
            
            return jsonify({
                'success': True,
                'zip_path': zip_path,
                'message': f'Generated {len(metadata)} XML files (only issues with files)'
            })
        else:
            return jsonify({'success': False, 'error': 'Failed to generate XML files'})
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

def test_kapowarr_connection_with_settings(settings):
    """Test Kapowarr connection using specific settings"""
    import requests
    
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

def test_comicvine_connection_with_settings(settings):
    """Test ComicVine connection using specific settings"""
    import requests
    
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

@app.route('/cleanup', methods=['POST'])
def cleanup_temp_files():
    """Clean up temporary files"""
    try:
        import shutil
        temp_dirs = [d for d in os.listdir('.') if d.startswith('temp_xml')]
        for temp_dir in temp_dirs:
            if os.path.isdir(temp_dir):
                shutil.rmtree(temp_dir)
        
        flash('Temporary files cleaned up', 'success')
        return jsonify({'success': True})
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

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)

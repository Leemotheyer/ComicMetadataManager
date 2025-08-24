"""
Scheduled Tasks System for Comic Metadata Manager
Handles automatic volume updates, metadata processing, cleanup, and monitoring
"""

import time
import threading
import schedule
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import os
import shutil
import glob
import json
import sqlite3

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('config/scheduled_tasks.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class ScheduledTaskManager:
    """Manages all scheduled tasks for the Comic Metadata Manager"""
    
    def __init__(self, volume_manager, volume_db, settings_manager):
        self.volume_manager = volume_manager
        self.volume_db = volume_db
        self.settings_manager = settings_manager
        self.running = False
        self.task_thread = None
        self.task_results = {}
        
        # Task configuration
        self.task_config = {
            'volume_update_interval': 3600,  # 1 hour in seconds
            'metadata_processing_enabled': True,
            'cleanup_interval': 1800,  # 30 minutes in seconds
            'max_concurrent_metadata_tasks': 5,  # Maximum concurrent metadata tasks
            'temp_file_retention_hours': 24,  # How long to keep temp files
            'auto_metadata_for_new_volumes': False,  # Auto-process metadata for new volumes
            'monitoring_enabled': True,
            'log_retention_days': 7
        }
        
        # Load configuration from settings
        self._load_config()
        
        # Task statistics
        self.stats = {
            'volumes_updated': 0,
            'metadata_processed': 0,
            'cleanup_runs': 0,
            'errors': 0,
            'last_run': None,
            'next_run': None
        }
    
    def _load_config(self):
        """Load task configuration from config.json"""
        try:
            config_file = 'config/config.json'
            if os.path.exists(config_file):
                with open(config_file, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)
                
                # Load scheduled task configuration
                self.task_config['metadata_processing_enabled'] = config_data.get('scheduled_tasks', {}).get('metadata_processing_enabled', True)
                self.task_config['auto_metadata_for_new_volumes'] = config_data.get('scheduled_tasks', {}).get('auto_metadata_for_new_volumes', False)
                self.task_config['volume_update_interval'] = config_data.get('scheduled_tasks', {}).get('volume_update_interval', 3600)
                self.task_config['cleanup_interval'] = config_data.get('scheduled_tasks', {}).get('cleanup_interval', 1800)
                self.task_config['max_concurrent_metadata_tasks'] = config_data.get('scheduled_tasks', {}).get('max_concurrent_metadata_tasks', 5)
                self.task_config['temp_file_retention_hours'] = config_data.get('scheduled_tasks', {}).get('temp_file_retention_hours', 24)
                self.task_config['monitoring_enabled'] = config_data.get('scheduled_tasks', {}).get('monitoring_enabled', True)
                self.task_config['log_retention_days'] = config_data.get('scheduled_tasks', {}).get('log_retention_days', 7)
                
                logger.info("Loaded scheduled task configuration from config.json")
            else:
                logger.warning("config.json not found, using default configuration")
                
        except Exception as e:
            logger.error(f"Failed to load task configuration: {e}")
            logger.info("Using default configuration values")
    
    def start(self):
        """Start the scheduled task system"""
        if self.running:
            logger.warning("Scheduled task system is already running")
            return
        
        self.running = True
        logger.info("Starting scheduled task system...")
        
        # Schedule tasks
        self._schedule_tasks()
        
        # Start the task runner thread
        self.task_thread = threading.Thread(target=self._run_scheduler, daemon=True)
        self.task_thread.start()
        
        logger.info("Scheduled task system started successfully")
    
    def stop(self):
        """Stop the scheduled task system"""
        if not self.running:
            logger.warning("Scheduled task system is not running")
            return
        
        self.running = False
        logger.info("Stopping scheduled task system...")
        
        # Wait for thread to finish
        if self.task_thread and self.task_thread.is_alive():
            self.task_thread.join(timeout=5)
        
        logger.info("Scheduled task system stopped")
    
    def _schedule_tasks(self):
        """Schedule all tasks"""
        try:
            # Volume update task
            schedule.every(self.task_config['volume_update_interval']).seconds.do(
                self._task_volume_update
            )
            
            # Cleanup task
            schedule.every(self.task_config['cleanup_interval']).seconds.do(
                self._task_cleanup
            )
            
            # Metadata processing task (if enabled)
            if self.task_config['metadata_processing_enabled']:
                schedule.every(7200).seconds.do(  # Every 2 hours
                    self._task_metadata_processing
                )
            
            # Monitoring task
            if self.task_config['monitoring_enabled']:
                schedule.every(300).seconds.do(  # Every 5 minutes
                    self._task_monitoring
                )
            
            # Log rotation task
            schedule.every().day.at("02:00").do(
                self._task_log_rotation
            )
            
            logger.info("All tasks scheduled successfully")
            
        except Exception as e:
            logger.error(f"Failed to schedule tasks: {e}")
    
    def _run_scheduler(self):
        """Main scheduler loop"""
        while self.running:
            try:
                schedule.run_pending()
                time.sleep(1)
            except Exception as e:
                logger.error(f"Error in scheduler loop: {e}")
                time.sleep(5)
    
    def _task_volume_update(self):
        """Task: Update volumes in database and check for new entries"""
        try:
            logger.info("Starting scheduled volume update task...")
            start_time = time.time()
            
            # Get current Kapowarr stats
            current_total = self._get_kapowarr_total_volumes()
            if current_total is None:
                logger.error("Could not get current Kapowarr stats")
                return
            
            # Check if stats have changed
            last_total = self.volume_db.get_last_kapowarr_stats()
            if current_total != last_total:
                logger.info(f"Kapowarr stats changed: {last_total} -> {current_total}")
                
                # Update volume list
                volumes = self.volume_manager.get_volume_list(force_refresh=True)
                logger.info(f"Updated volume list: {len(volumes)} volumes")
                
                # Auto-process metadata for new volumes if enabled
                if self.task_config['auto_metadata_for_new_volumes']:
                    self._auto_process_new_volumes(volumes)
                
                self.stats['volumes_updated'] += 1
            else:
                logger.info("No new volumes detected")
            
            # Check for new issues in existing volumes
            volumes_with_new_issues = self._check_for_new_issues_in_existing_volumes()
            if volumes_with_new_issues:
                logger.info(f"Found {len(volumes_with_new_issues)} volumes with new issues")
                
                # Auto-process metadata for new issues if enabled
                if self.task_config['auto_metadata_for_new_volumes']:
                    self._auto_process_new_issues(volumes_with_new_issues)
            
            # Update last run time
            self.stats['last_run'] = datetime.now()
            self.stats['next_run'] = datetime.now() + timedelta(seconds=self.task_config['volume_update_interval'])
            
            duration = time.time() - start_time
            logger.info(f"Volume update task completed in {duration:.2f} seconds")
            
        except Exception as e:
            logger.error(f"Error in volume update task: {e}")
            self.stats['errors'] += 1
    
    def _task_metadata_processing(self):
        """Task: Process metadata for volumes that need it"""
        try:
            logger.info("Starting scheduled metadata processing task...")
            start_time = time.time()
            
            # Get volumes that need metadata processing
            volumes_needing_metadata = self._get_volumes_needing_metadata()
            
            if not volumes_needing_metadata:
                logger.info("No volumes need metadata processing")
                return
            
            logger.info(f"Found {len(volumes_needing_metadata)} volumes needing metadata")
            
            # Process metadata for each volume (limit concurrent tasks)
            processed_count = 0
            for volume in volumes_needing_metadata[:self.task_config['max_concurrent_metadata_tasks']]:
                try:
                    volume_id = volume['id']
                    logger.info(f"Processing metadata for volume {volume_id}")
                    
                    # Check if this volume has new issues that need processing
                    if volume.get('has_new_issues', False):
                        logger.info(f"Volume {volume_id} has new issues, processing only those")
                        if self._process_new_issues_in_volume(volume_id):
                            processed_count += 1
                            self.stats['metadata_processed'] += 1
                    else:
                        # Process all issues that need metadata
                        if self._process_volume_metadata(volume_id):
                            processed_count += 1
                            self.stats['metadata_processed'] += 1
                            
                except Exception as e:
                    logger.error(f"Failed to process metadata for volume {volume_id}: {e}")
            
            duration = time.time() - start_time
            logger.info(f"Metadata processing task completed: {processed_count} volumes processed in {duration:.2f} seconds")
            
        except Exception as e:
            logger.error(f"Error in metadata processing task: {e}")
            self.stats['errors'] += 1
    
    def _task_cleanup(self):
        """Task: Clean up temporary files and old data"""
        try:
            logger.info("Starting scheduled cleanup task...")
            start_time = time.time()
            
            # Clean up temporary directories
            temp_dirs_cleaned = self._cleanup_temp_directories()
            
            # Clean up old task results
            old_results_cleaned = self._cleanup_old_task_results()
            
            # Clean up old logs
            old_logs_cleaned = self._cleanup_old_logs()
            
            # Clean up database cache if needed
            db_cleaned = self._cleanup_database_cache()
            
            self.stats['cleanup_runs'] += 1
            
            duration = time.time() - start_time
            logger.info(f"Cleanup task completed in {duration:.2f} seconds: "
                       f"{temp_dirs_cleaned} temp dirs, {old_results_cleaned} old results, "
                       f"{old_logs_cleaned} old logs, {db_cleaned} db entries cleaned")
            
        except Exception as e:
            logger.error(f"Error in cleanup task: {e}")
            self.stats['errors'] += 1
    
    def _task_monitoring(self):
        """Task: Monitor system health and performance"""
        try:
            # Check disk space
            disk_usage = self._check_disk_usage()
            
            # Check database health
            db_health = self._check_database_health()
            
            # Check task queue status
            task_queue_status = self._check_task_queue_status()
            
            # Log monitoring results
            logger.info(f"System monitoring: Disk={disk_usage}%, DB={db_health}, Tasks={task_queue_status}")
            
            # Alert if thresholds exceeded
            if disk_usage > 90:
                logger.warning(f"Disk usage is high: {disk_usage}%")
            
            if not db_health:
                logger.error("Database health check failed")
                
        except Exception as e:
            logger.error(f"Error in monitoring task: {e}")
    
    def _task_log_rotation(self):
        """Task: Rotate and compress old log files"""
        try:
            logger.info("Starting log rotation task...")
            
            # Rotate main application log
            self._rotate_log_file('app.log')
            
            # Rotate scheduled tasks log
            self._rotate_log_file('scheduled_tasks.log')
            
            # Compress old rotated logs
            self._compress_old_logs()
            
            logger.info("Log rotation task completed")
            
        except Exception as e:
            logger.error(f"Error in log rotation task: {e}")
    
    def _get_kapowarr_total_volumes(self) -> Optional[int]:
        """Get total volumes from Kapowarr stats"""
        try:
            # Use the existing Kapowarr API logic
            from KapowarrSearch import get_total_volumes_from_stats
            
            api_key = self.volume_manager.api_key
            base_url = self.volume_manager.base_url
            
            if not api_key or not base_url:
                logger.error("Kapowarr API key or URL not configured")
                return None
            
            total_volumes = get_total_volumes_from_stats(api_key, base_url)
            return total_volumes
            
        except Exception as e:
            logger.error(f"Failed to get Kapowarr total volumes: {e}")
            return None
    
    def _get_volumes_needing_metadata(self) -> List[Dict]:
        """Get list of volume IDs that need metadata processing"""
        try:
            # Query database for volumes without metadata
            if hasattr(self.volume_db, 'get_volumes_needing_metadata_ids'):
                return self.volume_db.get_volumes_needing_metadata_ids()
            else:
                # Fallback: get all volumes and filter
                all_volumes = self.volume_db.get_volumes()
                volumes_needing_metadata = []
                
                for volume in all_volumes:
                    if not volume.get('metadata_processed', False):
                        volumes_needing_metadata.append(volume)
                
                return volumes_needing_metadata
                
        except Exception as e:
            logger.error(f"Failed to get volumes needing metadata: {e}")
            return []
    
    def _process_volume_metadata(self, volume_id: int) -> bool:
        """Process metadata for a specific volume"""
        try:
            # Use the existing volume manager metadata processing
            if hasattr(self.volume_manager, 'process_volume_metadata'):
                # Scheduled tasks should NOT use manual override - only process what needs processing
                metadata = self.volume_manager.process_volume_metadata(volume_id, manual_override=False)
                return metadata is not None and len(metadata) > 0
            else:
                logger.error("Volume manager does not have process_volume_metadata method")
                return False
                
        except Exception as e:
            logger.error(f"Failed to process metadata for volume {volume_id}: {e}")
            return False
    
    def _process_new_issues_in_volume(self, volume_id: int) -> bool:
        """Process metadata only for new issues in a volume"""
        try:
            # Get new issues that need metadata processing
            new_issues = self.volume_db.detect_new_issues_in_volume(volume_id)
            if not new_issues:
                logger.info(f"No new issues found in volume {volume_id}")
                return True
            
            logger.info(f"Processing metadata for {len(new_issues)} new issues in volume {volume_id}")
            
            # Process each new issue
            processed_count = 0
            for issue_info in new_issues:
                try:
                    issue = issue_info['issue']
                    comicvine_id = issue_info['comicvine_id']
                    issue_number = issue_info['issue_number']
                    
                    logger.info(f"Processing new issue {issue_number} (ComicVine ID: {comicvine_id})")
                    
                    # Get metadata from ComicVine
                    if hasattr(self.volume_manager, 'metadata_fetcher'):
                        metadata = self.volume_manager.metadata_fetcher.get_comicvine_metadata(comicvine_id)
                        if metadata:
                            # Update issue metadata status
                            self.volume_db.update_issue_metadata_status(
                                volume_id,
                                comicvine_id,
                                issue_number,
                                metadata_processed=True
                            )
                            processed_count += 1
                            logger.info(f"✅ Successfully processed metadata for new issue {issue_number}")
                        else:
                            logger.error(f"❌ Failed to get metadata for new issue {issue_number}")
                    else:
                        logger.error("Volume manager does not have metadata_fetcher")
                        return False
                    
                    # Rate limiting
                    time.sleep(1.0)
                    
                except Exception as e:
                    logger.error(f"Failed to process new issue {issue_number}: {e}")
            
            logger.info(f"Processed metadata for {processed_count}/{len(new_issues)} new issues in volume {volume_id}")
            return processed_count > 0
            
        except Exception as e:
            logger.error(f"Failed to process new issues in volume {volume_id}: {e}")
            return False
    
    def _auto_process_new_volumes(self, volumes: List[Dict]):
        """Automatically process metadata for new volumes"""
        try:
            # This would identify new volumes and process their metadata
            # For now, just logging
            logger.info(f"Auto-processing metadata for {len(volumes)} volumes")
        except Exception as e:
            logger.error(f"Failed to auto-process new volumes: {e}")
    
    def _auto_process_new_issues(self, volumes: List[Dict]):
        """Automatically process metadata for new issues in existing volumes"""
        try:
            # This would identify new issues and process their metadata
            # For now, just logging
            logger.info(f"Auto-processing metadata for {len(volumes)} volumes with new issues")
        except Exception as e:
            logger.error(f"Failed to auto-process new issues: {e}")
    
    def _check_for_new_issues_in_existing_volumes(self) -> List[Dict]:
        """Check for new issues in existing volumes that need metadata processing"""
        try:
            # Query database for volumes that have new issues
            if hasattr(self.volume_db, 'get_volumes_with_new_issues_ids'):
                volume_ids = self.volume_db.get_volumes_with_new_issues_ids()
                volumes_with_new_issues = []
                
                for volume_id in volume_ids:
                    volume_details = self.volume_db.get_volume_details(volume_id)
                    if volume_details:
                        # Get basic volume info
                        cursor = self.volume_db.db_path
                        with sqlite3.connect(cursor) as conn:
                            cursor = conn.cursor()
                            cursor.execute('''
                                SELECT volume_folder, status, last_updated, total_issues, issues_with_files, 
                                       metadata_processed, xml_generated, metadata_injected
                                FROM volumes 
                                WHERE id = ?
                            ''', (volume_id,))
                            
                            row = cursor.fetchone()
                            if row:
                                volume = {
                                    'id': volume_id,
                                    'volume_folder': row[0],
                                    'status': row[1],
                                    'last_updated': row[2],
                                    'total_issues': row[3],
                                    'issues_with_files': row[4],
                                    'metadata_processed': bool(row[5]),
                                    'xml_generated': bool(row[6]),
                                    'metadata_injected': bool(row[7]),
                                    'has_new_issues': True
                                }
                                volumes_with_new_issues.append(volume)
                
                return volumes_with_new_issues
            else:
                # Fallback: get all volumes and check for new issues
                all_volumes = self.volume_db.get_volumes()
                volumes_with_new_issues = []
                
                for volume in all_volumes:
                    # Check if the volume has new issues
                    new_issues = self.volume_db.detect_new_issues_in_volume(volume['id'])
                    if new_issues:
                        volume['has_new_issues'] = True
                        volumes_with_new_issues.append(volume)
                
                return volumes_with_new_issues
                
        except Exception as e:
            logger.error(f"Failed to check for new issues in existing volumes: {e}")
            return []
    
    def _cleanup_temp_directories(self) -> int:
        """Clean up temporary directories"""
        try:
            cleaned_count = 0
            
            # Look for temp directories
            temp_patterns = [
                "temp_xml_*",
                "temp_injection_*",
                "temp_*"
            ]
            
            for pattern in temp_patterns:
                temp_dirs = glob.glob(pattern)
                for temp_dir in temp_dirs:
                    if os.path.exists(temp_dir) and os.path.isdir(temp_dir):
                        try:
                            # Check if directory is old enough to delete
                            dir_age = time.time() - os.path.getctime(temp_dir)
                            if dir_age > (self.task_config['temp_file_retention_hours'] * 3600):
                                shutil.rmtree(temp_dir)
                                cleaned_count += 1
                                logger.debug(f"Cleaned up temp directory: {temp_dir}")
                        except Exception as e:
                            logger.error(f"Failed to clean up temp directory {temp_dir}: {e}")
            
            return cleaned_count
            
        except Exception as e:
            logger.error(f"Error cleaning up temp directories: {e}")
            return 0
    
    def _cleanup_old_task_results(self) -> int:
        """Clean up old task results"""
        try:
            # This would clean up old task results from memory/database
            # For now, returning 0
            return 0
        except Exception as e:
            logger.error(f"Error cleaning up old task results: {e}")
            return 0
    
    def _cleanup_old_logs(self) -> int:
        """Clean up old log files"""
        try:
            cleaned_count = 0
            
            # Look for old log files in current directory and config directory
            log_patterns = ["*.log.*", "config/*.log.*"]
            for pattern in log_patterns:
                log_files = glob.glob(pattern)
                for log_file in log_files:
                    try:
                        # Check if log file is old enough to delete
                        file_age = time.time() - os.path.getctime(log_file)
                        if file_age > (self.task_config['log_retention_days'] * 86400):
                            os.remove(log_file)
                            cleaned_count += 1
                            logger.debug(f"Cleaned up old log file: {log_file}")
                    except Exception as e:
                        logger.error(f"Failed to clean up log file {log_file}: {e}")
            
            return cleaned_count
            
        except Exception as e:
            logger.error(f"Error cleaning up old logs: {e}")
            return 0
    
    def _cleanup_database_cache(self) -> int:
        """Clean up old database cache entries"""
        try:
            # This would clean up old cache entries
            # For now, returning 0
            return 0
        except Exception as e:
            logger.error(f"Error cleaning up database cache: {e}")
            return 0
    
    def _check_disk_usage(self) -> float:
        """Check disk usage percentage"""
        try:
            # This would check disk usage
            # For now, returning 0
            return 0.0
        except Exception as e:
            logger.error(f"Error checking disk usage: {e}")
            return 0.0
    
    def _check_database_health(self) -> bool:
        """Check database health"""
        try:
            # This would check database connectivity and health
            # For now, returning True
            return True
        except Exception as e:
            logger.error(f"Error checking database health: {e}")
            return False
    
    def _check_task_queue_status(self) -> str:
        """Check task queue status"""
        try:
            # This would check the current task queue
            # For now, returning "OK"
            return "OK"
        except Exception as e:
            logger.error(f"Error checking task queue status: {e}")
            return "ERROR"
    
    def _rotate_log_file(self, log_filename: str):
        """Rotate a log file"""
        try:
            # Handle both relative and absolute paths
            if log_filename == 'scheduled_tasks.log':
                log_path = 'config/scheduled_tasks.log'
            else:
                log_path = log_filename
            
            if os.path.exists(log_path):
                # Create rotated filename with timestamp
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                rotated_filename = f"{log_path}.{timestamp}"
                
                # Rename current log file
                os.rename(log_path, rotated_filename)
                
                # Create new empty log file
                open(log_path, 'a').close()
                
                logger.info(f"Rotated log file: {log_path} -> {rotated_filename}")
                
        except Exception as e:
            logger.error(f"Error rotating log file {log_path}: {e}")
    
    def _compress_old_logs(self):
        """Compress old rotated log files"""
        try:
            # This would compress old log files to save space
            # For now, just logging
            logger.info("Compressing old log files")
        except Exception as e:
            logger.error(f"Error compressing old logs: {e}")
    
    def get_stats(self) -> Dict:
        """Get current task statistics"""
        return self.stats.copy()
    
    def get_config(self) -> Dict:
        """Get current task configuration from config.json"""
        try:
            config_file = 'config/config.json'
            if os.path.exists(config_file):
                with open(config_file, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)
                
                # Return scheduled_tasks section if it exists, otherwise return in-memory config
                if 'scheduled_tasks' in config_data:
                    return config_data['scheduled_tasks'].copy()
                else:
                    return self.task_config.copy()
            else:
                return self.task_config.copy()
                
        except Exception as e:
            logger.error(f"Failed to read configuration from config.json: {e}")
            return self.task_config.copy()
    
    def update_config(self, new_config: Dict):
        """Update task configuration and save to config.json"""
        try:
            # Update in-memory configuration
            self.task_config.update(new_config)
            
            # Save to config.json
            config_file = 'config/config.json'
            if os.path.exists(config_file):
                # Read existing config
                with open(config_file, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)
            else:
                # Create new config if file doesn't exist
                config_data = {}
            
            # Ensure scheduled_tasks section exists
            if 'scheduled_tasks' not in config_data:
                config_data['scheduled_tasks'] = {}
            
            # Update scheduled_tasks section
            for key, value in new_config.items():
                config_data['scheduled_tasks'][key] = value
            
            # Write back to file
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, indent=2, ensure_ascii=False)
            
            logger.info("Task configuration updated and saved to config.json")
            
        except Exception as e:
            logger.error(f"Failed to update task configuration: {e}")
    
    def run_task_now(self, task_name: str):
        """Run a specific task immediately"""
        try:
            if task_name == 'volume_update':
                self._task_volume_update()
            elif task_name == 'metadata_processing':
                self._task_metadata_processing()
            elif task_name == 'cleanup':
                self._task_cleanup()
            elif task_name == 'monitoring':
                self._task_monitoring()
            elif task_name == 'log_rotation':
                self._task_log_rotation()
            else:
                logger.error(f"Unknown task: {task_name}")
                
        except Exception as e:
            logger.error(f"Error running task {task_name}: {e}")
    
    def get_scheduled_tasks(self) -> List[Dict]:
        """Get list of scheduled tasks and their next run times"""
        try:
            tasks = []
            for job in schedule.jobs:
                # Get meaningful task name based on the function
                task_name = self._get_task_display_name(job.job_func)
                
                tasks.append({
                    'name': task_name,
                    'next_run': job.next_run,
                    'interval': job.interval,
                    'interval_display': self._format_interval(job.interval)
                })
            return tasks
        except Exception as e:
            logger.error(f"Error getting scheduled tasks: {e}")
            return []
    
    def _get_task_display_name(self, job_func) -> str:
        """Convert internal function names to user-friendly display names"""
        try:
            # Get the function name from the partial or direct function
            if hasattr(job_func, 'func'):
                # Handle functools.partial objects
                func_name = job_func.func.__name__
            else:
                # Handle direct function objects
                func_name = job_func.__name__
            
            # Map function names to display names
            task_names = {
                '_task_volume_update': 'Volume Update',
                '_task_metadata_processing': 'Metadata Processing',
                '_task_cleanup': 'Cleanup & Maintenance',
                '_task_monitoring': 'System Monitoring',
                '_task_log_rotation': 'Log Rotation'
            }
            
            return task_names.get(func_name, func_name.replace('_', ' ').title())
            
        except Exception as e:
            logger.error(f"Error getting task display name: {e}")
            return "Unknown Task"
    
    def _format_interval(self, interval) -> str:
        """Convert interval seconds to human-readable format"""
        try:
            if interval is None:
                return "Variable"
            
            if interval < 60:
                return f"{interval} seconds"
            elif interval < 3600:
                minutes = interval // 60
                return f"{minutes} minute{'s' if minutes != 1 else ''}"
            elif interval < 86400:
                hours = interval // 3600
                return f"{hours} hour{'s' if hours != 1 else ''}"
            else:
                days = interval // 86400
                return f"{days} day{'s' if days != 1 else ''}"
                
        except Exception as e:
            logger.error(f"Error formatting interval: {e}")
            return f"{interval} seconds"
    
    def reset_config_to_defaults(self):
        """Reset configuration to default values and save to config.json"""
        try:
            # Reset to default values
            default_config = {
                'volume_update_interval': 3600,
                'metadata_processing_enabled': True,
                'cleanup_interval': 1800,
                'max_concurrent_metadata_tasks': 5,
                'temp_file_retention_hours': 24,
                'auto_metadata_for_new_volumes': False,
                'monitoring_enabled': True,
                'log_retention_days': 7
            }
            
            # Update in-memory config
            self.task_config.update(default_config)
            
            # Save to config.json
            self.update_config(default_config)
            
            logger.info("Configuration reset to defaults and saved to config.json")
            
        except Exception as e:
            logger.error(f"Failed to reset configuration: {e}")

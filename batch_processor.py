"""
Batch Metadata Processor - Handle bulk operations on comic files
Supports batch metadata injection, validation, and conflict resolution
"""

import os
import json
import time
import threading
import queue
from datetime import datetime
from typing import Dict, List, Optional, Callable
import logging

# Import app modules
try:
    from comic_metadata_reader import ComicMetadataReader
    from MetaDataAdd import ComicMetadataInjector
    from CreateXML import ComicInfoXMLGenerator
    from MetadataGather import ComicMetadataFetcher
    from settings_manager import settings_manager
    from utils import map_kapowarr_to_local_path, generate_xml_files
except ImportError as e:
    print(f"Warning: Could not import some modules: {e}")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class BatchOperationManager:
    """Manages batch operations for comic metadata processing"""
    
    def __init__(self, volume_manager=None):
        self.volume_manager = volume_manager
        self.reader = ComicMetadataReader()
        self.injector = ComicMetadataInjector()
        self.xml_generator = ComicInfoXMLGenerator()
        self.metadata_fetcher = ComicMetadataFetcher()
        
        # Operation tracking
        self.active_operations = {}
        self.operation_counter = 0
        self.max_concurrent_operations = settings_manager.get_setting('max_concurrent_tasks', 5)
        
        # Thread pools for different operation types
        self.scan_queue = queue.Queue()
        self.process_queue = queue.Queue()
        self.inject_queue = queue.Queue()
        
        # Start worker threads
        self._start_worker_threads()
    
    def _start_worker_threads(self):
        """Start background worker threads for different operation types"""
        # Scan workers (I/O bound)
        for i in range(2):
            thread = threading.Thread(
                target=self._scan_worker,
                name=f"ScanWorker-{i}",
                daemon=True
            )
            thread.start()
        
        # Process workers (CPU bound)
        for i in range(self.max_concurrent_operations):
            thread = threading.Thread(
                target=self._process_worker,
                name=f"ProcessWorker-{i}",
                daemon=True
            )
            thread.start()
        
        # Injection workers (I/O bound)
        for i in range(3):
            thread = threading.Thread(
                target=self._inject_worker,
                name=f"InjectWorker-{i}",
                daemon=True
            )
            thread.start()
    
    def create_operation(self, operation_type: str, description: str, 
                        total_items: int = 0) -> str:
        """Create a new batch operation and return its ID"""
        self.operation_counter += 1
        operation_id = f"batch_op_{self.operation_counter}_{int(time.time())}"
        
        self.active_operations[operation_id] = {
            'id': operation_id,
            'type': operation_type,
            'description': description,
            'status': 'initializing',
            'created_at': datetime.now().isoformat(),
            'started_at': None,
            'completed_at': None,
            'total_items': total_items,
            'processed_items': 0,
            'successful_items': 0,
            'failed_items': 0,
            'current_item': '',
            'results': [],
            'errors': [],
            'progress_percentage': 0
        }
        
        return operation_id
    
    def get_operation_status(self, operation_id: str) -> Optional[Dict]:
        """Get the current status of a batch operation"""
        return self.active_operations.get(operation_id)
    
    def update_operation_progress(self, operation_id: str, 
                                processed_items: int = None,
                                current_item: str = None,
                                add_result: Dict = None,
                                add_error: str = None):
        """Update the progress of a batch operation"""
        if operation_id not in self.active_operations:
            return
        
        operation = self.active_operations[operation_id]
        
        if processed_items is not None:
            operation['processed_items'] = processed_items
            if operation['total_items'] > 0:
                operation['progress_percentage'] = (processed_items / operation['total_items']) * 100
        
        if current_item is not None:
            operation['current_item'] = current_item
        
        if add_result is not None:
            operation['results'].append(add_result)
            if add_result.get('success', False):
                operation['successful_items'] += 1
            else:
                operation['failed_items'] += 1
        
        if add_error is not None:
            operation['errors'].append({
                'timestamp': datetime.now().isoformat(),
                'error': add_error,
                'item': operation.get('current_item', '')
            })
            operation['failed_items'] += 1
    
    def complete_operation(self, operation_id: str, status: str = 'completed'):
        """Mark a batch operation as completed"""
        if operation_id in self.active_operations:
            self.active_operations[operation_id]['status'] = status
            self.active_operations[operation_id]['completed_at'] = datetime.now().isoformat()
            self.active_operations[operation_id]['progress_percentage'] = 100
    
    def batch_scan_volumes(self, volume_ids: List[int], 
                          callback: Callable = None) -> str:
        """Scan metadata for multiple volumes"""
        operation_id = self.create_operation(
            'batch_scan',
            f'Scanning metadata for {len(volume_ids)} volumes',
            len(volume_ids)
        )
        
        # Queue the operation
        self.scan_queue.put({
            'operation_id': operation_id,
            'volume_ids': volume_ids,
            'callback': callback
        })
        
        return operation_id
    
    def batch_process_metadata(self, volume_ids: List[int], 
                              options: Dict = None) -> str:
        """Process metadata for multiple volumes with options"""
        if options is None:
            options = {}
        
        operation_id = self.create_operation(
            'batch_process',
            f'Processing metadata for {len(volume_ids)} volumes',
            len(volume_ids)
        )
        
        # Queue the operation
        self.process_queue.put({
            'operation_id': operation_id,
            'volume_ids': volume_ids,
            'options': options
        })
        
        return operation_id
    
    def batch_inject_metadata(self, injection_tasks: List[Dict]) -> str:
        """Inject metadata into multiple comic files"""
        operation_id = self.create_operation(
            'batch_inject',
            f'Injecting metadata into {len(injection_tasks)} comic files',
            len(injection_tasks)
        )
        
        # Queue the operation
        self.inject_queue.put({
            'operation_id': operation_id,
            'injection_tasks': injection_tasks
        })
        
        return operation_id
    
    def _scan_worker(self):
        """Worker thread for scanning operations"""
        while True:
            try:
                task = self.scan_queue.get()
                if task is None:
                    break
                
                self._execute_scan_operation(task)
                self.scan_queue.task_done()
                
            except Exception as e:
                logger.error(f"Error in scan worker: {e}")
    
    def _process_worker(self):
        """Worker thread for processing operations"""
        while True:
            try:
                task = self.process_queue.get()
                if task is None:
                    break
                
                self._execute_process_operation(task)
                self.process_queue.task_done()
                
            except Exception as e:
                logger.error(f"Error in process worker: {e}")
    
    def _inject_worker(self):
        """Worker thread for injection operations"""
        while True:
            try:
                task = self.inject_queue.get()
                if task is None:
                    break
                
                self._execute_inject_operation(task)
                self.inject_queue.task_done()
                
            except Exception as e:
                logger.error(f"Error in inject worker: {e}")
    
    def _execute_scan_operation(self, task: Dict):
        """Execute a batch scan operation"""
        operation_id = task['operation_id']
        volume_ids = task['volume_ids']
        callback = task.get('callback')
        
        # Start the operation
        self.active_operations[operation_id]['status'] = 'running'
        self.active_operations[operation_id]['started_at'] = datetime.now().isoformat()
        
        try:
            for i, volume_id in enumerate(volume_ids):
                # Update progress
                self.update_operation_progress(
                    operation_id,
                    processed_items=i,
                    current_item=f"Volume {volume_id}"
                )
                
                try:
                    if not self.volume_manager:
                        raise Exception("Volume manager not available")
                    
                    # Get volume details
                    volume_details = self.volume_manager.get_volume_details(volume_id)
                    if not volume_details:
                        self.update_operation_progress(
                            operation_id,
                            add_error=f"Volume {volume_id} not found"
                        )
                        continue
                    
                    folder_path = volume_details.get('folder', '')
                    if not folder_path:
                        self.update_operation_progress(
                            operation_id,
                            add_error=f"Volume {volume_id} has no folder path"
                        )
                        continue
                    
                    # Map to local path
                    local_folder_path = map_kapowarr_to_local_path(folder_path)
                    
                    if not os.path.exists(local_folder_path):
                        self.update_operation_progress(
                            operation_id,
                            add_error=f"Folder not found: {local_folder_path}"
                        )
                        continue
                    
                    # Scan for comic files
                    comic_files = self.reader.scan_directory_for_comics(
                        local_folder_path, recursive=True
                    )
                    
                    if comic_files:
                        # Read metadata from all comic files
                        results = self.reader.batch_read_metadata(comic_files)
                        
                        # Generate summary
                        summary = {
                            'volume_id': volume_id,
                            'volume_name': volume_details.get('name', ''),
                            'folder_path': local_folder_path,
                            'total_files': len(results),
                            'files_with_metadata': sum(1 for r in results if r['has_metadata']),
                            'files_without_metadata': sum(1 for r in results if not r['has_metadata']),
                            'files_with_errors': sum(1 for r in results if r['error']),
                            'format_breakdown': {},
                            'validation_issues': [],
                            'detailed_results': results if len(results) <= 10 else results[:10]  # Limit detailed results
                        }
                        
                        # Format breakdown
                        for result in results:
                            fmt = result['file_format']
                            if fmt not in summary['format_breakdown']:
                                summary['format_breakdown'][fmt] = {'total': 0, 'with_metadata': 0}
                            summary['format_breakdown'][fmt]['total'] += 1
                            if result['has_metadata']:
                                summary['format_breakdown'][fmt]['with_metadata'] += 1
                        
                        # Collect validation issues
                        for result in results:
                            if result.get('validation_issues'):
                                summary['validation_issues'].extend(result['validation_issues'])
                    else:
                        summary = {
                            'volume_id': volume_id,
                            'volume_name': volume_details.get('name', ''),
                            'folder_path': local_folder_path,
                            'total_files': 0,
                            'files_with_metadata': 0,
                            'files_without_metadata': 0,
                            'files_with_errors': 0,
                            'format_breakdown': {},
                            'validation_issues': [],
                            'message': 'No comic files found'
                        }
                    
                    self.update_operation_progress(
                        operation_id,
                        add_result={'success': True, 'data': summary}
                    )
                    
                except Exception as e:
                    self.update_operation_progress(
                        operation_id,
                        add_error=f"Error scanning volume {volume_id}: {str(e)}"
                    )
            
            # Complete the operation
            self.update_operation_progress(operation_id, processed_items=len(volume_ids))
            self.complete_operation(operation_id)
            
            # Call callback if provided
            if callback:
                callback(operation_id, self.active_operations[operation_id])
                
        except Exception as e:
            self.update_operation_progress(
                operation_id,
                add_error=f"Operation failed: {str(e)}"
            )
            self.complete_operation(operation_id, 'failed')
    
    def _execute_process_operation(self, task: Dict):
        """Execute a batch metadata processing operation"""
        operation_id = task['operation_id']
        volume_ids = task['volume_ids']
        options = task.get('options', {})
        
        # Start the operation
        self.active_operations[operation_id]['status'] = 'running'
        self.active_operations[operation_id]['started_at'] = datetime.now().isoformat()
        
        try:
            force_regenerate = options.get('force_regenerate', False)
            generate_xml_only = options.get('generate_xml_only', False)
            
            for i, volume_id in enumerate(volume_ids):
                # Update progress
                self.update_operation_progress(
                    operation_id,
                    processed_items=i,
                    current_item=f"Volume {volume_id}"
                )
                
                try:
                    if not self.volume_manager:
                        raise Exception("Volume manager not available")
                    
                    if generate_xml_only:
                        # Just generate XML files without injection
                        result = self._generate_xml_for_volume(volume_id, force_regenerate)
                    else:
                        # Full metadata processing including injection
                        result = self._process_volume_metadata_full(volume_id, options)
                    
                    self.update_operation_progress(
                        operation_id,
                        add_result={'success': True, 'volume_id': volume_id, 'data': result}
                    )
                    
                except Exception as e:
                    self.update_operation_progress(
                        operation_id,
                        add_error=f"Error processing volume {volume_id}: {str(e)}"
                    )
            
            # Complete the operation
            self.update_operation_progress(operation_id, processed_items=len(volume_ids))
            self.complete_operation(operation_id)
            
        except Exception as e:
            self.update_operation_progress(
                operation_id,
                add_error=f"Operation failed: {str(e)}"
            )
            self.complete_operation(operation_id, 'failed')
    
    def _execute_inject_operation(self, task: Dict):
        """Execute a batch injection operation"""
        operation_id = task['operation_id']
        injection_tasks = task['injection_tasks']
        
        # Start the operation
        self.active_operations[operation_id]['status'] = 'running'
        self.active_operations[operation_id]['started_at'] = datetime.now().isoformat()
        
        try:
            for i, injection_task in enumerate(injection_tasks):
                # Update progress
                self.update_operation_progress(
                    operation_id,
                    processed_items=i,
                    current_item=injection_task.get('comic_file', 'Unknown file')
                )
                
                try:
                    # Perform injection
                    result = self.injector.inject_metadata(
                        injection_task['volume_id'],
                        injection_task['xml_files'],
                        injection_task['folder_path']
                    )
                    
                    self.update_operation_progress(
                        operation_id,
                        add_result={'success': True, 'data': result}
                    )
                    
                except Exception as e:
                    self.update_operation_progress(
                        operation_id,
                        add_error=f"Error injecting into {injection_task.get('comic_file', 'Unknown file')}: {str(e)}"
                    )
            
            # Complete the operation
            self.update_operation_progress(operation_id, processed_items=len(injection_tasks))
            self.complete_operation(operation_id)
            
        except Exception as e:
            self.update_operation_progress(
                operation_id,
                add_error=f"Operation failed: {str(e)}"
            )
            self.complete_operation(operation_id, 'failed')
    
    def _generate_xml_for_volume(self, volume_id: int, force_regenerate: bool = False) -> Dict:
        """Generate XML files for a volume"""
        if not self.volume_manager:
            raise Exception("Volume manager not available")
        
        volume_details = self.volume_manager.get_volume_details(volume_id)
        if not volume_details:
            raise Exception(f"Volume {volume_id} not found")
        
        # Process the volume to generate metadata
        result = self.volume_manager.process_volume_metadata(volume_id, manual_override=force_regenerate)
        
        return {
            'volume_id': volume_id,
            'volume_name': volume_details.get('name', ''),
            'xml_generated': result.get('success', False),
            'message': result.get('message', ''),
            'issues_processed': result.get('issues_processed', 0)
        }
    
    def _process_volume_metadata_full(self, volume_id: int, options: Dict) -> Dict:
        """Perform full metadata processing including XML generation and injection"""
        # First generate XML
        xml_result = self._generate_xml_for_volume(
            volume_id, 
            options.get('force_regenerate', False)
        )
        
        if not xml_result['xml_generated']:
            return xml_result
        
        # If auto-injection is enabled, also inject metadata
        if options.get('auto_inject', False):
            volume_details = self.volume_manager.get_volume_details(volume_id)
            folder_path = volume_details.get('folder', '')
            
            if folder_path:
                # Find generated XML files
                temp_xml_dir = f"temp_xml_{volume_id}"
                if os.path.exists(temp_xml_dir):
                    xml_files = [
                        os.path.join(temp_xml_dir, f)
                        for f in os.listdir(temp_xml_dir)
                        if f.endswith('.xml')
                    ]
                    
                    if xml_files:
                        injection_result = self.injector.inject_metadata(
                            volume_id, xml_files, folder_path
                        )
                        xml_result['injection_result'] = injection_result
        
        return xml_result
    
    def get_all_operations(self, status_filter: str = None) -> List[Dict]:
        """Get all operations, optionally filtered by status"""
        operations = list(self.active_operations.values())
        
        if status_filter:
            operations = [op for op in operations if op['status'] == status_filter]
        
        # Sort by creation time (newest first)
        operations.sort(key=lambda x: x['created_at'], reverse=True)
        
        return operations
    
    def cleanup_old_operations(self, max_age_hours: int = 24):
        """Clean up old completed operations"""
        cutoff_time = datetime.now().timestamp() - (max_age_hours * 3600)
        
        operations_to_remove = []
        for op_id, operation in self.active_operations.items():
            if operation['status'] in ['completed', 'failed']:
                created_time = datetime.fromisoformat(operation['created_at']).timestamp()
                if created_time < cutoff_time:
                    operations_to_remove.append(op_id)
        
        for op_id in operations_to_remove:
            del self.active_operations[op_id]
        
        return len(operations_to_remove)


# Global instance
batch_manager = None

def get_batch_manager(volume_manager=None):
    """Get or create the global batch manager instance"""
    global batch_manager
    if batch_manager is None:
        batch_manager = BatchOperationManager(volume_manager)
    return batch_manager


if __name__ == "__main__":
    # Example usage
    manager = BatchOperationManager()
    print("Batch Operation Manager initialized")
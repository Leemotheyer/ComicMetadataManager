"""
MetaDataAdd.py - Comic Metadata Injection Module
Integrates with the Comic Metadata Manager app to inject metadata into comic files
"""

import os
import shutil
import sys
import time
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Import app modules
try:
    from settings_manager import settings_manager
    from utils import map_kapowarr_to_local_path
except ImportError:
    # Fallback for standalone usage
    settings_manager = None
    map_kapowarr_to_local_path = None


class ComicMetadataInjector:
    """Handles injecting metadata into comic files"""
    
    def __init__(self):
        # Only support ZIP-based formats
        self.supported_formats = ['.cbz', '.zip']
        self.temp_dir = None
    
    def inject_metadata(self, volume_id: int, xml_files: List[str], 
                       kapowarr_folder_path: str) -> Dict[str, any]:
        """
        Inject metadata into comic files for a specific volume
        
        Args:
            volume_id: The volume ID
            xml_files: List of XML metadata files to inject
            kapowarr_folder_path: The folder path from Kapowarr
            
        Returns:
            Dictionary with injection results
        """
        temp_dirs_created = []  # Track all temp directories created
        
        try:
            # Map Kapowarr path to local path
            local_folder_path = self._map_kapowarr_to_local_path(kapowarr_folder_path)
            
            if not local_folder_path:
                return {
                    'success': False,
                    'error': f'Could not map Kapowarr path: {kapowarr_folder_path}'
                }
            
            # Check if local folder exists
            if not os.path.exists(local_folder_path):
                return {
                    'success': False,
                    'error': f'Local folder not found: {local_folder_path}'
                }
            
            # Find comic files in the local folder
            comic_files = self._find_comic_files(local_folder_path)
            
            if not comic_files:
                return {
                    'success': False,
                    'error': f'No comic files found in: {local_folder_path}'
                }
            
            # Process each comic file
            results = []
            for comic_file in comic_files:
                result = self._process_comic_file(comic_file, xml_files, volume_id, temp_dirs_created)
                results.append(result)
            
            # Count successful injections
            successful = sum(1 for r in results if r['success'])
            total = len(results)
            
            return {
                'success': True,
                'message': f'Successfully injected metadata into {successful}/{total} comic files',
                'results': results,
                'local_folder': local_folder_path,
                'kapowarr_folder': kapowarr_folder_path
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Metadata injection failed: {str(e)}'
            }
        finally:
            # Clean up any remaining temp directories
            self._cleanup_temp_directories(temp_dirs_created)
            # Also clean up any orphaned temp directories from this volume
            self._cleanup_orphaned_temp_dirs(volume_id)
    
    def _map_kapowarr_to_local_path(self, kapowarr_folder_path: str) -> Optional[str]:
        """Map Kapowarr folder path to local file system path"""
        if map_kapowarr_to_local_path and settings_manager:
            kapowarr_parent_folder = settings_manager.get_setting('kapowarr_parent_folder', '/comics-1')
            return map_kapowarr_to_local_path(
                kapowarr_folder_path, 
                kapowarr_parent_folder, 
                'comics'  # Changed from '/comics' to 'comics' for relative path
            )
        else:
            # Fallback: try to convert path manually
            if kapowarr_folder_path.startswith('/comics-1/'):
                return kapowarr_folder_path.replace('/comics-1/', 'comics/')  # Changed to relative path
            return kapowarr_folder_path
    
    def _find_comic_files(self, folder_path: str) -> List[str]:
        """Find comic files in the specified folder"""
        comic_files = []
        
        try:
            for item in os.listdir(folder_path):
                item_path = os.path.join(folder_path, item)
                if os.path.isfile(item_path):
                    ext = os.path.splitext(item)[1].lower()
                    if ext in self.supported_formats:
                        comic_files.append(item_path)
        except Exception as e:
            print(f"Error scanning folder {folder_path}: {e}")
        
        return comic_files
    
    def _process_comic_file(self, comic_file: str, xml_files: List[str], 
                           volume_id: int, temp_dirs_created: List[str]) -> Dict[str, any]:
        """Process a single comic file for metadata injection"""
        try:
            comic_filename = os.path.basename(comic_file)
            comic_ext = os.path.splitext(comic_filename)[1].lower()
            
            print(f"🔍 Processing comic file: {comic_filename}")
            print(f"🔍 Available XML files: {[os.path.basename(x) for x in xml_files]}")
            
            # Find matching XML file
            matching_xml = self._find_matching_xml(comic_filename, xml_files)
            
            if not matching_xml:
                print(f"❌ No matching XML found for {comic_filename}")
                return {
                    'success': False,
                    'file': comic_filename,
                    'error': 'No matching XML metadata found'
                }
            
            print(f"✅ Found matching XML: {os.path.basename(matching_xml)}")
            
            # Create temporary directory for processing
            temp_dir = f"temp_injection_{volume_id}_{int(os.path.getmtime(comic_file))}"
            os.makedirs(temp_dir, exist_ok=True)
            print(f"📁 Created temp directory: {temp_dir}")
            temp_dirs_created.append(temp_dir) # Add to the list
            
            try:
                # Extract comic file
                print(f"📦 Extracting {comic_filename}...")
                
                # Use patoolib for ZIP/CBZ extraction
                import patoolib
                patoolib.extract_archive(comic_file, outdir=temp_dir)
                
                # List extracted files
                extracted_files = os.listdir(temp_dir)
                print(f"📋 Extracted files: {extracted_files}")
                
                # Remove existing ComicInfo.xml if present
                existing_xml = os.path.join(temp_dir, "ComicInfo.xml")
                if os.path.exists(existing_xml):
                    print(f"🗑️ Removing existing ComicInfo.xml")
                    os.remove(existing_xml)
                
                # Copy new metadata XML
                xml_dest = os.path.join(temp_dir, "ComicInfo.xml")
                print(f"📄 Copying {os.path.basename(matching_xml)} to {xml_dest}")
                shutil.copy2(matching_xml, xml_dest)
                
                # Verify XML was copied
                if os.path.exists(xml_dest):
                    print(f"✅ XML file copied successfully")
                else:
                    print(f"❌ Failed to copy XML file")
                
                # List files before archiving
                files_before_archive = os.listdir(temp_dir)
                print(f"📋 Files before archiving: {files_before_archive}")
                
                # Create new archive
                print(f"📦 Creating new archive...")
                new_comic_file = self._create_new_archive(comic_file, temp_dir, comic_ext)
                print(f"✅ New archive created: {new_comic_file}")
                
                # Create backup and replace original
                backup_file = f"{comic_file}.backup"
                print(f"💾 Creating backup: {backup_file}")
                shutil.move(comic_file, backup_file)
                print(f"🔄 Replacing original with new archive")
                shutil.move(new_comic_file, comic_file)
                
                # Remove backup (optional - could keep for safety)
                print(f"🗑️ Removing backup file")
                os.remove(backup_file)
                
                print(f"✅ Successfully injected metadata into {comic_filename}")
                
                return {
                    'success': True,
                    'file': comic_filename,
                    'xml_used': os.path.basename(matching_xml),
                    'message': 'Metadata injected successfully'
                }
                
            except Exception as e:
                print(f"❌ Error during processing of {comic_filename}: {e}")
                raise
                
        except Exception as e:
            print(f"❌ Error processing {comic_filename}: {e}")
            return {
                'success': False,
                'file': comic_filename,
                'error': str(e)
            }
    
    def _find_matching_xml(self, comic_filename: str, xml_files: List[str]) -> Optional[str]:
        """Find the XML metadata file that matches the comic file"""
        # Remove extension and any numbering from comic filename
        base_name = os.path.splitext(comic_filename)[0]
        
        print(f"🔍 Looking for XML match for comic: {comic_filename}")
        print(f"🔍 Comic base name: {base_name}")
        
        # Try to find exact match first
        for xml_file in xml_files:
            xml_basename = os.path.splitext(os.path.basename(xml_file))[0]
            print(f"🔍 Checking XML: {xml_basename} vs {base_name}")
            if xml_basename.lower() == base_name.lower():
                print(f"✅ Found exact match: {xml_basename}")
                return xml_file
        
        # Try to find partial matches
        for xml_file in xml_files:
            xml_basename = os.path.basename(xml_file).lower()
            if base_name.lower() in xml_basename or xml_basename in base_name.lower():
                print(f"✅ Found partial match: {xml_basename}")
                return xml_file
        
        # If no match found, return the first XML file as fallback
        if xml_files:
            print(f"⚠️ No exact match found, using fallback: {os.path.basename(xml_files[0])}")
            return xml_files[0]
        else:
            print(f"❌ No XML files available")
            return None
    
    def _create_new_archive(self, original_file: str, temp_dir: str, 
                           file_ext: str) -> str:
        """Create a new archive with the injected metadata"""
        try:
            # Create new archive - use just the filename, not the full path
            original_filename = os.path.basename(original_file)
            new_archive = f"{original_filename}.new{file_ext}"
            
            # Get all files in the temp directory (just filenames, not full paths)
            files_to_archive = []
            for item in os.listdir(temp_dir):
                item_path = os.path.join(temp_dir, item)
                if os.path.isfile(item_path):
                    files_to_archive.append(item)  # Just the filename, not full path
            
            print(f"📦 Creating archive with {len(files_to_archive)} files")
            print(f"📋 Files to archive: {files_to_archive}")
            print(f"📁 Archive format: {file_ext}")
            print(f"📁 New archive name: {new_archive}")
            
            # Store current working directory
            original_cwd = os.getcwd()
            print(f"📁 Current working directory: {original_cwd}")
            
            try:
                # Change to temp directory to avoid nesting
                os.chdir(temp_dir)
                print(f"📁 Changed working directory to: {temp_dir}")
                
                # Use patoolib to create ZIP archive
                print(f"📦 Creating ZIP archive...")
                import patoolib
                patoolib.create_archive(new_archive, files_to_archive)
                
                # Verify the archive was created in temp directory
                print(f"🔍 First verification - checking: {new_archive}")
                print(f"🔍 First verification - current working directory: {os.getcwd()}")
                print(f"🔍 First verification - file exists: {os.path.exists(new_archive)}")
                print(f"🔍 First verification - absolute path: {os.path.abspath(new_archive)}")
                
                if not os.path.exists(new_archive):
                    raise Exception("Archive file was not created in temp directory")
                
                print(f"✅ Archive created successfully in temp directory: {new_archive}")
                
                # Move the created archive to the original directory
                # Since we're in temp_dir, we need to go up one level to get back to original_cwd
                final_archive_path = os.path.join("..", new_archive)
                
                print(f"📁 Moving archive from {new_archive} to {final_archive_path}")
                shutil.move(new_archive, final_archive_path)
                print(f"📁 Archive moved to: {final_archive_path}")
                
            finally:
                # Always restore original working directory
                os.chdir(original_cwd)
                print(f"📁 Restored working directory to: {original_cwd}")
            
            # Verify the archive was moved successfully
            # The archive should now be in the original directory
            print(f"🔍 Verifying archive: {new_archive}")
            print(f"🔍 Current working directory: {os.getcwd()}")
            print(f"🔍 File exists: {os.path.exists(new_archive)}")
            print(f"🔍 Absolute path: {os.path.abspath(new_archive)}")
            
            if os.path.exists(new_archive):
                archive_size = os.path.getsize(new_archive)
                print(f"✅ Archive verified successfully: {os.path.basename(new_archive)} ({archive_size} bytes)")
            else:
                raise Exception(f"Archive file not found after move: {new_archive}")
            
            return new_archive
            
        except Exception as e:
            print(f"❌ Error creating new archive: {e}")
            # Try to provide more helpful error information
            if "zip" in str(e).lower():
                print(f"💡 Tip: Make sure zip tools are available for .cbz files")
            raise

    def _cleanup_temp_directories(self, temp_dirs_created: List[str]):
        """Clean up all temporary directories created by this instance."""
        for temp_dir in temp_dirs_created:
            if os.path.exists(temp_dir):
                print(f"🧹 Cleaning up temp directory: {temp_dir}")
                shutil.rmtree(temp_dir)
                print(f"✅ {temp_dir} cleaned up.")
            else:
                print(f"⚠️ {temp_dir} not found, skipping cleanup.")

    def _cleanup_orphaned_temp_dirs(self, volume_id: int):
        """Clean up any orphaned temporary directories that might be left behind."""
        print(f"🧹 Checking for orphaned temp directories for volume {volume_id}...")
        
        # Clean up injection temp directories
        temp_dir_pattern = f"temp_injection_{volume_id}_"
        injection_dirs = [d for d in os.listdir('.') if os.path.isdir(d) and d.startswith(temp_dir_pattern)]
        
        # Clean up XML temp directories
        xml_dir_pattern = f"temp_xml_{volume_id}_"
        xml_dirs = [d for d in os.listdir('.') if os.path.isdir(d) and d.startswith(xml_dir_pattern)]
        
        # Clean up all found directories
        all_temp_dirs = injection_dirs + xml_dirs
        
        if all_temp_dirs:
            print(f"🔍 Found {len(all_temp_dirs)} orphaned temp directories to clean up:")
            for temp_dir in all_temp_dirs:
                print(f"  📁 {temp_dir}")
            
            for temp_dir in all_temp_dirs:
                try:
                    print(f"🧹 Cleaning up orphaned temp directory: {temp_dir}")
                    shutil.rmtree(temp_dir)
                    print(f"✅ {temp_dir} cleaned up.")
                except Exception as e:
                    print(f"⚠️ Failed to clean up {temp_dir}: {e}")
        else:
            print(f"✅ No orphaned temp directories found for volume {volume_id}")
        
        # Also clean up any general temp directories that might be very old (older than 1 hour)
        # This is a safety measure to prevent accumulation of temp dirs from failed operations
        self._cleanup_old_temp_dirs()
    
    def _cleanup_old_temp_dirs(self):
        """Clean up any temp directories that are older than 1 hour."""
        import time
        current_time = time.time()
        one_hour_ago = current_time - 3600  # 1 hour in seconds
        
        # Look for any temp directories (injection or XML) that are older than 1 hour
        temp_patterns = ['temp_injection_', 'temp_xml_']
        old_temp_dirs = []
        
        for item in os.listdir('.'):
            if os.path.isdir(item):
                for pattern in temp_patterns:
                    if item.startswith(pattern):
                        try:
                            # Try to get the creation time from the directory name
                            # Format: temp_injection_123_1234567890 or temp_xml_123_1234567890
                            parts = item.split('_')
                            if len(parts) >= 3:
                                timestamp_str = parts[-1]
                                try:
                                    timestamp = int(timestamp_str)
                                    if timestamp < one_hour_ago:
                                        old_temp_dirs.append(item)
                                except ValueError:
                                    # If we can't parse the timestamp, skip it
                                    pass
                        except Exception:
                            # If we can't determine the age, skip it
                            pass
        
        if old_temp_dirs:
            print(f"🧹 Found {len(old_temp_dirs)} old temp directories (older than 1 hour):")
            for temp_dir in old_temp_dirs:
                print(f"  📁 {temp_dir}")
            
            for temp_dir in old_temp_dirs:
                try:
                    print(f"🧹 Cleaning up old temp directory: {temp_dir}")
                    shutil.rmtree(temp_dir)
                    print(f"✅ {temp_dir} cleaned up.")
                except Exception as e:
                    print(f"⚠️ Failed to clean up {temp_dir}: {e}")
        else:
            print(f"✅ No old temp directories found")
    
    def cleanup_all_temp_dirs(self):
        """Clean up ALL temporary directories immediately (use with caution)"""
        print(f"🧹 Starting aggressive cleanup of ALL temporary directories...")
        
        # Look for any temp directories (injection or XML)
        temp_patterns = ['temp_injection_', 'temp_xml_']
        all_temp_dirs = []
        
        for item in os.listdir('.'):
            if os.path.isdir(item):
                for pattern in temp_patterns:
                    if item.startswith(pattern):
                        all_temp_dirs.append(item)
                        break
        
        if all_temp_dirs:
            print(f"🧹 Found {len(all_temp_dirs)} temporary directories to clean up:")
            for temp_dir in all_temp_dirs:
                print(f"  📁 {temp_dir}")
            
            cleaned_count = 0
            failed_count = 0
            
            for temp_dir in all_temp_dirs:
                try:
                    print(f"🧹 Cleaning up temp directory: {temp_dir}")
                    shutil.rmtree(temp_dir)
                    print(f"✅ {temp_dir} cleaned up.")
                    cleaned_count += 1
                except Exception as e:
                    print(f"⚠️ Failed to clean up {temp_dir}: {e}")
                    failed_count += 1
            
            print(f"🧹 Cleanup complete: {cleaned_count} cleaned, {failed_count} failed")
            return {
                'success': True,
                'cleaned_count': cleaned_count,
                'failed_count': failed_count,
                'total_found': len(all_temp_dirs)
            }
        else:
            print(f"✅ No temporary directories found")
            return {
                'success': True,
                'cleaned_count': 0,
                'failed_count': 0,
                'total_found': 0
            }
    
    def process_issue_metadata(self, volume_id: int, issue_index: int, volume_details: dict, 
                             metadata_fetcher, volume_db) -> dict:
        """
        Process metadata for a specific issue and inject it into comic files
        
        Args:
            volume_id: ID of the volume
            issue_index: Index of the issue in the volume
            volume_details: Volume details from Kapowarr
            metadata_fetcher: ComicMetadataFetcher instance
            volume_db: Volume database instance
            
        Returns:
            Dictionary with processing results
        """
        try:
            print(f"🔄 Starting metadata processing for issue {issue_index} in volume {volume_id}")
            
            # Check if issue index is valid
            if 'issues' not in volume_details or issue_index < 0 or issue_index >= len(volume_details['issues']):
                return {
                    'success': False,
                    'error': f'Issue index {issue_index} is out of range. Volume has {len(volume_details.get("issues", []))} issues.'
                }
            
            # Get the specific issue by index
            target_issue = volume_details['issues'][issue_index]
            
            # Check if issue has files
            if not target_issue.get('files') or len(target_issue['files']) == 0:
                return {
                    'success': False,
                    'error': f'Issue {issue_index} has no files to process'
                }
            
            # Check if issue has ComicVine ID
            comicvine_id = target_issue.get('comicvine_id')
            if not comicvine_id:
                return {
                    'success': False,
                    'error': f'Issue {issue_index} has no ComicVine ID'
                }
            
            # Fetch metadata from ComicVine
            metadata = metadata_fetcher.get_comicvine_metadata(comicvine_id)
            if not metadata:
                return {
                    'success': False,
                    'error': f'Failed to fetch metadata from ComicVine for issue {comicvine_id}'
                }
            
            # Get the folder path from volume details
            kapowarr_folder_path = volume_details.get('folder')
            if not kapowarr_folder_path:
                return {
                    'success': False,
                    'error': 'No folder path found for this volume'
                }
            
            # Create a temporary directory for the XML
            temp_dir = f"temp_xml_issue_{volume_id}_{issue_index}_{int(time.time())}"
            os.makedirs(temp_dir, exist_ok=True)
            
            try:
                # Generate XML content for this issue using CreateXML module
                from CreateXML import ComicInfoXMLGenerator
                xml_generator = ComicInfoXMLGenerator()
                xml_content = xml_generator.generate_issue_xml(metadata, target_issue, volume_details)
                
                # Write XML to temporary file
                xml_file_path = os.path.join(temp_dir, f"issue_{issue_index}.xml")
                with open(xml_file_path, 'w', encoding='utf-8') as f:
                    f.write(xml_content)
                
                # Get the specific files for this issue only
                issue_files = target_issue.get('files', [])
                
                # Map Kapowarr path to local path
                local_folder_path = self._map_kapowarr_to_local_path(kapowarr_folder_path)
                
                if not local_folder_path or not os.path.exists(local_folder_path):
                    return {
                        'success': False,
                        'error': f'Local folder not found: {local_folder_path}'
                    }
                
                # Process only the files for this specific issue
                results = []
                for issue_file in issue_files:
                    file_path = issue_file.get('filepath', '')
                    if not file_path:
                        continue
                        
                    # Extract just the filename from the full path
                    filename = os.path.basename(file_path)
                    
                    # Look for this specific file in the local folder
                    local_file_path = os.path.join(local_folder_path, filename)
                    
                    if os.path.exists(local_file_path):
                        try:
                            # Create a temporary XML file specifically for this file
                            file_xml_path = os.path.join(temp_dir, f"file_{filename}.xml")
                            with open(file_xml_path, 'w', encoding='utf-8') as f:
                                f.write(xml_content)
                            
                            # Process just this one file
                            file_result = self._process_comic_file(
                                local_file_path, 
                                [file_xml_path], 
                                volume_id, 
                                []
                            )
                            
                            results.append({
                                'file': filename,
                                'success': file_result.get('success', False),
                                'message': file_result.get('message', 'Unknown result'),
                                'error': file_result.get('error', '')
                            })
                            
                        except Exception as e:
                            results.append({
                                'file': filename,
                                'success': False,
                                'error': str(e)
                            })
                    else:
                        results.append({
                            'file': filename,
                            'success': False,
                            'error': 'File not found in local folder'
                        })
                
                # Update issue metadata status to indicate processing and injection are complete
                volume_db.update_issue_metadata_status(
                    volume_id,
                    comicvine_id,
                    target_issue.get('issue_number', 'Unknown'),
                    metadata_processed=True,
                    metadata_injected=True
                )
                
                print(f"✅ Successfully processed and injected metadata for issue {issue_index}")
                
                # Check if all issues in the volume now have metadata processed
                all_issues_processed = True
                for issue in volume_details['issues']:
                    issue_comicvine_id = issue.get('comicvine_id')
                    if issue_comicvine_id:
                        issue_status = volume_db.get_issue_metadata_status(volume_id, issue_comicvine_id)
                        if not issue_status or not issue_status.get('metadata_processed', False):
                            all_issues_processed = False
                            break
                
                # Update volume status if all issues are processed
                if all_issues_processed:
                    volume_db.update_volume_status(volume_id, metadata_processed=True, metadata_injected=True)
                    print(f"✅ All issues in volume {volume_id} now have metadata processed and injected")
                
                return {
                    'success': True,
                    'result': {
                        'comicvine_id': comicvine_id,
                        'issue_index': issue_index,
                        'kapowarr_issue': target_issue,
                        'comicvine_metadata': metadata,
                        'injection_results': results,
                        'local_folder': local_folder_path,
                        'kapowarr_folder': kapowarr_folder_path
                    },
                    'message': f'Successfully processed and injected metadata for issue {issue_index} ({len(results)} files)'
                }
                
            finally:
                # Clean up temporary directory
                try:
                    if os.path.exists(temp_dir):
                        shutil.rmtree(temp_dir)
                except Exception as cleanup_error:
                    print(f"Error during cleanup: {cleanup_error}")
                
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }


# Standalone usage (for testing)
def main():
    """Main function for standalone usage"""
    if len(sys.argv) != 4:
        print("Usage: python MetaDataAdd.py <volume_id> <xml_directory> <kapowarr_folder_path>")
        print("Example: python MetaDataAdd.py 123 ./temp_xml_123_1234567890 '/comics-1/DC Comics/Batgirl (2025)'")
        sys.exit(1)
    
    try:
        volume_id = int(sys.argv[1])
        xml_directory = sys.argv[2]
        kapowarr_folder_path = sys.argv[3]
        
        # Validate inputs
        if not os.path.exists(xml_directory):
            print(f"Error: XML directory '{xml_directory}' not found!")
            sys.exit(1)
        
        # Find XML files
        xml_files = []
        for item in os.listdir(xml_directory):
            if item.endswith('.xml'):
                xml_files.append(os.path.join(xml_directory, item))
        
        if not xml_files:
            print(f"Error: No XML files found in '{xml_directory}'!")
            sys.exit(1)
        
        # Create injector and process
        injector = ComicMetadataInjector()
        result = injector.inject_metadata(volume_id, xml_files, kapowarr_folder_path)
        
        if result['success']:
            print(f"✅ {result['message']}")
            print(f"📁 Local folder: {result['local_folder']}")
            print(f"📊 Results:")
            for r in result['results']:
                status = "✅" if r['success'] else "❌"
                print(f"  {status} {r['file']}: {r.get('message', r.get('error', 'Unknown'))}")
        else:
            print(f"❌ {result['error']}")
            sys.exit(1)
            
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()




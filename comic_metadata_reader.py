"""
Comic Metadata Reader - Extract and analyze existing metadata from comic files
Supports CBR, CBZ, CBT, and CB7 formats
"""

import os
import xml.etree.ElementTree as ET
import tempfile
import shutil
import patoolib
import zipfile
import rarfile
from pathlib import Path
from typing import Dict, List, Optional, Union
import json
from datetime import datetime


class ComicMetadataReader:
    """Reads and analyzes existing metadata from comic files"""
    
    def __init__(self):
        self.supported_formats = ['.cbr', '.cbz', '.cbt', '.cb7']
        self.metadata_filenames = ['ComicInfo.xml', 'comicinfo.xml', 'metadata.xml']
    
    def read_comic_metadata(self, comic_file_path: str) -> Dict:
        """
        Extract and parse metadata from a comic file
        
        Args:
            comic_file_path: Path to the comic file
            
        Returns:
            Dictionary containing metadata information
        """
        result = {
            'file_path': comic_file_path,
            'file_name': os.path.basename(comic_file_path),
            'file_size': 0,
            'file_format': '',
            'has_metadata': False,
            'metadata_file': None,
            'metadata_content': None,
            'parsed_metadata': {},
            'validation_issues': [],
            'extraction_method': '',
            'error': None
        }
        
        try:
            # Check if file exists
            if not os.path.exists(comic_file_path):
                result['error'] = f"File not found: {comic_file_path}"
                return result
            
            # Get file info
            result['file_size'] = os.path.getsize(comic_file_path)
            result['file_format'] = os.path.splitext(comic_file_path)[1].lower()
            
            # Check if format is supported
            if result['file_format'] not in self.supported_formats:
                result['error'] = f"Unsupported format: {result['file_format']}"
                return result
            
            # Extract metadata based on file format
            if result['file_format'] == '.cbz':
                result.update(self._read_cbz_metadata(comic_file_path))
            elif result['file_format'] == '.cbr':
                result.update(self._read_cbr_metadata(comic_file_path))
            else:
                # Use patoolib for other formats
                result.update(self._read_generic_metadata(comic_file_path))
            
            # Parse XML if found
            if result['has_metadata'] and result['metadata_content']:
                result['parsed_metadata'] = self._parse_comicinfo_xml(result['metadata_content'])
                result['validation_issues'] = self._validate_metadata(result['parsed_metadata'])
            
        except Exception as e:
            result['error'] = f"Error reading comic metadata: {str(e)}"
        
        return result
    
    def _read_cbz_metadata(self, comic_file_path: str) -> Dict:
        """Read metadata from CBZ file using zipfile"""
        result = {'extraction_method': 'zipfile'}
        
        try:
            with zipfile.ZipFile(comic_file_path, 'r') as zip_file:
                # Look for metadata files
                for metadata_filename in self.metadata_filenames:
                    if metadata_filename in zip_file.namelist():
                        result['has_metadata'] = True
                        result['metadata_file'] = metadata_filename
                        
                        # Read the metadata content
                        with zip_file.open(metadata_filename) as metadata_file:
                            result['metadata_content'] = metadata_file.read().decode('utf-8')
                        break
                
        except zipfile.BadZipFile:
            result['error'] = "Invalid ZIP file"
        except Exception as e:
            result['error'] = f"Error reading CBZ file: {str(e)}"
        
        return result
    
    def _read_cbr_metadata(self, comic_file_path: str) -> Dict:
        """Read metadata from CBR file using rarfile"""
        result = {'extraction_method': 'rarfile'}
        
        try:
            with rarfile.RarFile(comic_file_path, 'r') as rar_file:
                # Look for metadata files
                for metadata_filename in self.metadata_filenames:
                    if metadata_filename in rar_file.namelist():
                        result['has_metadata'] = True
                        result['metadata_file'] = metadata_filename
                        
                        # Read the metadata content
                        with rar_file.open(metadata_filename) as metadata_file:
                            result['metadata_content'] = metadata_file.read().decode('utf-8')
                        break
                
        except rarfile.BadRarFile:
            result['error'] = "Invalid RAR file"
        except Exception as e:
            result['error'] = f"Error reading CBR file: {str(e)}"
        
        return result
    
    def _read_generic_metadata(self, comic_file_path: str) -> Dict:
        """Read metadata from other formats using patoolib"""
        result = {'extraction_method': 'patoolib'}
        temp_dir = None
        
        try:
            # Create temporary directory
            temp_dir = tempfile.mkdtemp(prefix="comic_metadata_read_")
            
            # Extract archive
            patoolib.extract_archive(comic_file_path, outdir=temp_dir)
            
            # Look for metadata files
            for metadata_filename in self.metadata_filenames:
                metadata_path = os.path.join(temp_dir, metadata_filename)
                if os.path.exists(metadata_path):
                    result['has_metadata'] = True
                    result['metadata_file'] = metadata_filename
                    
                    # Read the metadata content
                    with open(metadata_path, 'r', encoding='utf-8') as f:
                        result['metadata_content'] = f.read()
                    break
            
        except Exception as e:
            result['error'] = f"Error extracting with patoolib: {str(e)}"
        finally:
            # Clean up temporary directory
            if temp_dir and os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
        
        return result
    
    def _parse_comicinfo_xml(self, xml_content: str) -> Dict:
        """Parse ComicInfo.xml content into a structured dictionary"""
        parsed = {}
        
        try:
            root = ET.fromstring(xml_content)
            
            # Map XML elements to dictionary
            for child in root:
                if child.text:
                    parsed[child.tag] = child.text.strip()
                else:
                    parsed[child.tag] = child.attrib if child.attrib else ""
            
            # Convert numeric fields
            numeric_fields = ['Number', 'Count', 'Volume', 'Year', 'Month', 'Day', 'PageCount']
            for field in numeric_fields:
                if field in parsed and parsed[field]:
                    try:
                        parsed[field] = int(parsed[field])
                    except ValueError:
                        pass  # Keep as string if conversion fails
            
            # Convert boolean fields
            boolean_fields = ['BlackAndWhite']
            for field in boolean_fields:
                if field in parsed and parsed[field]:
                    parsed[field] = parsed[field].lower() in ['true', 'yes', '1']
            
        except ET.ParseError as e:
            parsed['_parse_error'] = f"XML Parse Error: {str(e)}"
        except Exception as e:
            parsed['_parse_error'] = f"Parse Error: {str(e)}"
        
        return parsed
    
    def _validate_metadata(self, metadata: Dict) -> List[str]:
        """Validate metadata and return list of issues found"""
        issues = []
        
        if not metadata:
            issues.append("No metadata found")
            return issues
        
        if '_parse_error' in metadata:
            issues.append(f"Parse error: {metadata['_parse_error']}")
        
        # Check for required fields
        required_fields = ['Title', 'Series']
        for field in required_fields:
            if field not in metadata or not metadata[field]:
                issues.append(f"Missing required field: {field}")
        
        # Check for recommended fields
        recommended_fields = ['Number', 'Year', 'Writer', 'Penciller', 'Summary']
        missing_recommended = []
        for field in recommended_fields:
            if field not in metadata or not metadata[field]:
                missing_recommended.append(field)
        
        if missing_recommended:
            issues.append(f"Missing recommended fields: {', '.join(missing_recommended)}")
        
        # Validate numeric fields
        numeric_validations = {
            'Number': lambda x: x > 0,
            'Count': lambda x: x > 0,
            'Year': lambda x: 1900 <= x <= datetime.now().year + 10,
            'Month': lambda x: 1 <= x <= 12,
            'Day': lambda x: 1 <= x <= 31,
            'PageCount': lambda x: x > 0
        }
        
        for field, validator in numeric_validations.items():
            if field in metadata and isinstance(metadata[field], int):
                if not validator(metadata[field]):
                    issues.append(f"Invalid {field}: {metadata[field]}")
        
        return issues
    
    def batch_read_metadata(self, comic_files: List[str], 
                           progress_callback=None) -> List[Dict]:
        """
        Read metadata from multiple comic files
        
        Args:
            comic_files: List of comic file paths
            progress_callback: Optional callback function for progress updates
            
        Returns:
            List of metadata dictionaries
        """
        results = []
        total_files = len(comic_files)
        
        for i, comic_file in enumerate(comic_files):
            if progress_callback:
                progress_callback(i + 1, total_files, comic_file)
            
            result = self.read_comic_metadata(comic_file)
            results.append(result)
        
        return results
    
    def scan_directory_for_comics(self, directory_path: str, 
                                 recursive: bool = True) -> List[str]:
        """
        Scan directory for comic files
        
        Args:
            directory_path: Directory to scan
            recursive: Whether to scan subdirectories
            
        Returns:
            List of comic file paths found
        """
        comic_files = []
        
        if not os.path.exists(directory_path):
            return comic_files
        
        if recursive:
            for root, dirs, files in os.walk(directory_path):
                for file in files:
                    if any(file.lower().endswith(ext) for ext in self.supported_formats):
                        comic_files.append(os.path.join(root, file))
        else:
            for file in os.listdir(directory_path):
                file_path = os.path.join(directory_path, file)
                if os.path.isfile(file_path) and any(file.lower().endswith(ext) for ext in self.supported_formats):
                    comic_files.append(file_path)
        
        return sorted(comic_files)
    
    def generate_metadata_report(self, comic_files: List[str], 
                                output_file: str = None) -> Dict:
        """
        Generate a comprehensive metadata report for comic files
        
        Args:
            comic_files: List of comic file paths
            output_file: Optional file to save the report
            
        Returns:
            Dictionary containing the report
        """
        results = self.batch_read_metadata(comic_files)
        
        # Analyze results
        report = {
            'generated_at': datetime.now().isoformat(),
            'total_files': len(results),
            'files_with_metadata': sum(1 for r in results if r['has_metadata']),
            'files_without_metadata': sum(1 for r in results if not r['has_metadata']),
            'files_with_errors': sum(1 for r in results if r['error']),
            'format_breakdown': {},
            'validation_summary': {},
            'detailed_results': results
        }
        
        # Format breakdown
        for result in results:
            fmt = result['file_format']
            if fmt not in report['format_breakdown']:
                report['format_breakdown'][fmt] = {'total': 0, 'with_metadata': 0}
            report['format_breakdown'][fmt]['total'] += 1
            if result['has_metadata']:
                report['format_breakdown'][fmt]['with_metadata'] += 1
        
        # Validation summary
        all_issues = []
        for result in results:
            if result['validation_issues']:
                all_issues.extend(result['validation_issues'])
        
        issue_counts = {}
        for issue in all_issues:
            issue_counts[issue] = issue_counts.get(issue, 0) + 1
        
        report['validation_summary'] = issue_counts
        
        # Save report if output file specified
        if output_file:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2, ensure_ascii=False)
        
        return report
    
    def compare_metadata(self, existing_metadata: Dict, 
                        new_metadata: Dict) -> Dict:
        """
        Compare existing metadata with new metadata to identify conflicts
        
        Args:
            existing_metadata: Current metadata from comic file
            new_metadata: New metadata from ComicVine or other source
            
        Returns:
            Dictionary with comparison results
        """
        comparison = {
            'conflicts': [],
            'additions': [],
            'matches': [],
            'recommendation': 'keep_existing'  # or 'use_new' or 'merge'
        }
        
        # Compare common fields
        for field in set(existing_metadata.keys()) | set(new_metadata.keys()):
            existing_value = existing_metadata.get(field, '')
            new_value = new_metadata.get(field, '')
            
            if existing_value and new_value:
                if str(existing_value).strip() != str(new_value).strip():
                    comparison['conflicts'].append({
                        'field': field,
                        'existing': existing_value,
                        'new': new_value
                    })
                else:
                    comparison['matches'].append(field)
            elif new_value and not existing_value:
                comparison['additions'].append({
                    'field': field,
                    'value': new_value
                })
        
        # Determine recommendation
        if not comparison['conflicts'] and comparison['additions']:
            comparison['recommendation'] = 'merge'
        elif len(comparison['conflicts']) > len(comparison['matches']):
            comparison['recommendation'] = 'use_new'
        else:
            comparison['recommendation'] = 'keep_existing'
        
        return comparison


def main():
    """Example usage of the ComicMetadataReader"""
    reader = ComicMetadataReader()
    
    # Example: Read metadata from a single file
    # result = reader.read_comic_metadata('/path/to/comic.cbz')
    # print(json.dumps(result, indent=2))
    
    # Example: Scan directory and generate report
    # comic_files = reader.scan_directory_for_comics('/path/to/comics')
    # report = reader.generate_metadata_report(comic_files, 'metadata_report.json')
    # print(f"Found {report['total_files']} comic files")
    # print(f"{report['files_with_metadata']} have metadata")
    
    print("ComicMetadataReader initialized. Use the class methods to read comic metadata.")


if __name__ == "__main__":
    main()
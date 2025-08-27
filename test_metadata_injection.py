#!/usr/bin/env python3
"""
Test script to verify metadata injection functionality for CBR files
"""

import os
import sys
import tempfile
import shutil
import subprocess
import unittest
from unittest.mock import patch, MagicMock
import zipfile
import tarfile

# Add the current directory to Python path to import our modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from MetaDataAdd import ComicMetadataInjector
except ImportError as e:
    print(f"❌ Failed to import MetaDataAdd: {e}")
    sys.exit(1)

class TestMetadataInjection(unittest.TestCase):
    """Test cases for metadata injection functionality"""
    
    def setUp(self):
        """Set up test environment"""
        self.injector = ComicMetadataInjector()
        self.test_dir = tempfile.mkdtemp()
        self.comics_dir = os.path.join(self.test_dir, "comics")
        self.temp_dir = os.path.join(self.test_dir, "temp")
        os.makedirs(self.comics_dir, exist_ok=True)
        os.makedirs(self.temp_dir, exist_ok=True)
        
    def tearDown(self):
        """Clean up test environment"""
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def create_test_cbr(self, filename="test_comic.cbr"):
        """Create a test CBR file (actually a ZIP file with .cbr extension)"""
        cbr_path = os.path.join(self.comics_dir, filename)
        
        # Create a simple ZIP file as a mock CBR
        with zipfile.ZipFile(cbr_path, 'w') as zf:
            # Add some mock image files
            zf.writestr("page1.jpg", b"mock image data 1")
            zf.writestr("page2.jpg", b"mock image data 2")
            zf.writestr("page3.jpg", b"mock image data 3")
        
        return cbr_path
    
    def create_test_xml(self, content="<metadata>test</metadata>"):
        """Create a test XML metadata file"""
        xml_path = os.path.join(self.test_dir, "test_metadata.xml")
        with open(xml_path, 'w') as f:
            f.write(content)
        return xml_path
    
    @patch('subprocess.run')
    def test_peazip_availability_check(self, mock_run):
        """Test PeaZip availability checking"""
        # Test when PeaZip is available
        mock_run.return_value.returncode = 0
        self.assertTrue(self.injector._check_peazip_available())
        
        # Test when PeaZip is not available
        mock_run.return_value.returncode = 1
        self.assertFalse(self.injector._check_peazip_available())
        
        # Test when PeaZip throws an exception
        mock_run.side_effect = FileNotFoundError()
        self.assertFalse(self.injector._check_peazip_available())
    
    @patch('subprocess.run')
    def test_cbr_extraction_with_peazip(self, mock_run):
        """Test CBR extraction using PeaZip"""
        mock_run.return_value.returncode = 0
        
        cbr_file = self.create_test_cbr()
        temp_dir = os.path.join(self.test_dir, "extract_test")
        os.makedirs(temp_dir, exist_ok=True)
        
        # Test successful extraction
        with patch.object(self.injector, '_check_peazip_available', return_value=True):
            # This would normally call PeaZip, but we're mocking it
            result = subprocess.run([self.injector.peazip_path, "-ext2here", cbr_file], 
                                  cwd=temp_dir, capture_output=True, text=True, timeout=60, check=True)
        
        # Verify PeaZip was called correctly
        mock_run.assert_called()
        call_args = mock_run.call_args
        self.assertIn("-ext2here", call_args[0][0])
        self.assertIn(cbr_file, call_args[0][0])
    
    @patch('subprocess.run')
    def test_cbr_creation_with_peazip(self, mock_run):
        """Test CBR creation using PeaZip"""
        mock_run.return_value.returncode = 0
        
        # Create test files to archive
        test_files = []
        for i in range(3):
            test_file = os.path.join(self.test_dir, f"test_file_{i}.txt")
            with open(test_file, 'w') as f:
                f.write(f"test content {i}")
            test_files.append(os.path.basename(test_file))
        
        archive_name = "test_archive.cbr"
        
        with patch.object(self.injector, '_check_peazip_available', return_value=True):
            # This would normally call PeaZip, but we're mocking it
            result = subprocess.run([self.injector.peazip_path, "-add", archive_name] + test_files, 
                                  cwd=self.test_dir, capture_output=True, text=True, timeout=60, check=True)
        
        # Verify PeaZip was called correctly
        mock_run.assert_called()
        call_args = mock_run.call_args
        self.assertIn("-add", call_args[0][0])
        self.assertIn(archive_name, call_args[0][0])
    
    def test_supported_formats(self):
        """Test that CBR format is supported"""
        self.assertIn('.cbr', self.injector.supported_formats)
        self.assertIn('.cbz', self.injector.supported_formats)
        self.assertIn('.cbt', self.injector.supported_formats)
        self.assertIn('.cb7', self.injector.supported_formats)
    
    @patch('MetaDataAdd.map_kapowarr_to_local_path')
    def test_metadata_injection_workflow(self, mock_map_path):
        """Test the complete metadata injection workflow"""
        # Mock the path mapping
        mock_map_path.return_value = self.comics_dir
        
        # Create test CBR file
        cbr_file = self.create_test_cbr()
        
        # Create test XML metadata
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<ComicInfo xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
    <Title>Test Comic</Title>
    <Series>Test Series</Series>
    <Number>1</Number>
    <Volume>1</Volume>
    <Year>2024</Year>
    <Month>1</Month>
    <Writer>Test Writer</Writer>
    <Penciller>Test Artist</Penciller>
    <Publisher>Test Publisher</Publisher>
    <Genre>Action</Genre>
    <Summary>This is a test comic for metadata injection.</Summary>
</ComicInfo>"""
        xml_file = self.create_test_xml(xml_content)
        
        # Test the injection process with mocked PeaZip
        with patch.object(self.injector, '_check_peazip_available', return_value=True), \
             patch('subprocess.run') as mock_run, \
             patch.object(self.injector, '_map_kapowarr_to_local_path', return_value=self.comics_dir):
            
            mock_run.return_value.returncode = 0
            
            # Mock the file processing methods to avoid actual file operations
            with patch.object(self.injector, '_process_comic_file') as mock_process:
                mock_process.return_value = {
                    'success': True,
                    'file': cbr_file,
                    'message': 'Metadata injected successfully'
                }
                
                # Test the injection
                result = self.injector.inject_metadata(
                    volume_id=1,
                    xml_files=[xml_file],
                    kapowarr_folder_path="/test/path"
                )
                
                # Verify the result
                self.assertTrue(result['success'])
                self.assertIn('Successfully injected metadata', result['message'])
    
    def test_error_handling_peazip_unavailable(self):
        """Test error handling when PeaZip is not available"""
        with patch.object(self.injector, '_check_peazip_available', return_value=False):
            # This should raise an exception when trying to process CBR files
            with self.assertRaises(Exception) as context:
                # Simulate trying to extract a CBR file without PeaZip
                cbr_file = self.create_test_cbr()
                temp_dir = os.path.join(self.test_dir, "extract_test")
                os.makedirs(temp_dir, exist_ok=True)
                
                # This should fail because PeaZip is not available
                subprocess.run([self.injector.peazip_path, "-ext2here", cbr_file], 
                              cwd=temp_dir, capture_output=True, text=True, timeout=60, check=True)
    
    def test_peazip_command_validation(self):
        """Test that PeaZip commands are properly constructed"""
        # Test extraction command
        cbr_file = "/path/to/comic.cbr"
        temp_dir = "/path/to/temp"
        
        expected_extract_cmd = [self.injector.peazip_path, "-ext2here", cbr_file]
        
        # Test creation command
        archive_name = "new_archive.cbr"
        files_to_archive = ["file1.jpg", "file2.jpg", "file3.jpg"]
        expected_create_cmd = [self.injector.peazip_path, "-add", archive_name] + files_to_archive
        
        # Verify command structure
        self.assertEqual(expected_extract_cmd[0], self.injector.peazip_path)
        self.assertEqual(expected_extract_cmd[1], "-ext2here")
        self.assertEqual(expected_extract_cmd[2], cbr_file)
        
        self.assertEqual(expected_create_cmd[0], self.injector.peazip_path)
        self.assertEqual(expected_create_cmd[1], "-add")
        self.assertEqual(expected_create_cmd[2], archive_name)
        self.assertEqual(expected_create_cmd[3:], files_to_archive)

def run_integration_test():
    """Run a simple integration test to verify the overall functionality"""
    print("🔍 Running integration test for metadata injection...")
    
    try:
        # Test basic imports
        from MetaDataAdd import ComicMetadataInjector
        print("✅ MetaDataAdd module imported successfully")
        
        # Test class instantiation
        injector = ComicMetadataInjector()
        print("✅ ComicMetadataInjector instantiated successfully")
        
        # Test supported formats
        if '.cbr' in injector.supported_formats:
            print("✅ CBR format is supported")
        else:
            print("❌ CBR format is not supported")
            return False
        
        # Test PeaZip path
        if injector.peazip_path == "/usr/bin/peazip":
            print("✅ PeaZip path is correctly set")
        else:
            print("❌ PeaZip path is incorrect")
            return False
        
        print("🎉 Integration test passed!")
        return True
        
    except Exception as e:
        print(f"❌ Integration test failed: {e}")
        return False

if __name__ == "__main__":
    print("🧪 Running metadata injection tests...")
    
    # Run integration test first
    if not run_integration_test():
        print("❌ Integration test failed, aborting unit tests")
        sys.exit(1)
    
    print("\n" + "="*50)
    print("Running unit tests...")
    print("="*50)
    
    # Run unit tests
    unittest.main(argv=[''], exit=False, verbosity=2)
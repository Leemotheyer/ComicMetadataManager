#!/usr/bin/env python3
"""
Test script to verify PeaZip functionality in Docker container
"""

import os
import sys
import tempfile
import shutil
import subprocess

def test_peazip_functionality():
    """Test if PeaZip functionality works in the container"""
    print("🔍 Testing PeaZip functionality in Docker container...")
    
    # Test 1: Check if PeaZip binary is available
    print("\n1. Checking PeaZip binary availability...")
    peazip_path = "/usr/bin/peazip"
    
    if os.path.exists(peazip_path):
        print(f"✅ Found PeaZip at: {peazip_path}")
    else:
        print("❌ PeaZip binary not found!")
        return False
    
    # Test 2: Check if PeaZip can run and show help
    print("\n2. Testing PeaZip command execution...")
    try:
        result = subprocess.run([peazip_path, "-help"], 
                              capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            print("✅ PeaZip command executed successfully")
        else:
            print(f"❌ PeaZip command failed with return code: {result.returncode}")
            return False
    except subprocess.TimeoutExpired:
        print("❌ PeaZip command timed out")
        return False
    except Exception as e:
        print(f"❌ Failed to execute PeaZip: {e}")
        return False
    
    # Test 3: Check if patoolib can import (for other formats)
    print("\n3. Testing patoolib package import...")
    try:
        import patoolib
        print("✅ patoolib package imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import patoolib: {e}")
        return False
    
    # Test 4: Test archive creation with PeaZip
    print("\n4. Testing PeaZip archive creation...")
    try:
        # Create a test file
        test_content = "This is a test file for PeaZip functionality"
        test_file = "test_file.txt"
        
        with open(test_file, 'w') as f:
            f.write(test_content)
        
        print(f"✅ Created test file: {test_file}")
        
        # Try to create a RAR archive using PeaZip
        test_rar = "test_archive.cbr"
        
        # Use PeaZip to create the archive
        result = subprocess.run([peazip_path, "-add", test_rar, test_file], 
                              capture_output=True, text=True, timeout=30, check=True)
        
        if os.path.exists(test_rar):
            print(f"✅ Successfully created RAR archive with PeaZip: {test_rar}")
            
            # Test extraction
            print("\n5. Testing PeaZip archive extraction...")
            extract_dir = "test_extract"
            os.makedirs(extract_dir, exist_ok=True)
            
            # Extract the archive
            result = subprocess.run([peazip_path, "-ext2here", test_rar], 
                                  cwd=extract_dir, capture_output=True, text=True, timeout=30, check=True)
            
            if os.path.exists(os.path.join(extract_dir, test_file)):
                print(f"✅ Successfully extracted RAR archive with PeaZip")
            else:
                print(f"❌ Failed to extract RAR archive")
                return False
            
            # Clean up test files
            os.remove(test_file)
            os.remove(test_rar)
            shutil.rmtree(extract_dir)
            print("✅ Cleaned up test files")
        else:
            print(f"❌ Failed to create RAR archive with PeaZip")
            return False
            
    except subprocess.CalledProcessError as e:
        print(f"❌ Error during PeaZip archive creation test: {e}")
        print(f"stdout: {e.stdout}")
        print(f"stderr: {e.stderr}")
        # Clean up any test files that might have been created
        for file in ["test_file.txt", "test_archive.cbr"]:
            if os.path.exists(file):
                os.remove(file)
        if os.path.exists("test_extract"):
            shutil.rmtree("test_extract")
        return False
    except Exception as e:
        print(f"❌ Error during archive creation test: {e}")
        # Clean up any test files that might have been created
        for file in ["test_file.txt", "test_archive.cbr"]:
            if os.path.exists(file):
                os.remove(file)
        if os.path.exists("test_extract"):
            shutil.rmtree("test_extract")
        return False
    
    print("\n🎉 All PeaZip functionality tests passed!")
    return True

if __name__ == "__main__":
    success = test_peazip_functionality()
    sys.exit(0 if success else 1)
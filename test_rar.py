#!/usr/bin/env python3
"""
Test script to verify RAR functionality in Docker container
"""

import os
import sys
import tempfile
import shutil

def test_rar_functionality():
    """Test if RAR functionality works in the container"""
    print("🔍 Testing RAR functionality in Docker container...")
    
    # Test 1: Check if unrar binary is available
    print("\n1. Checking unrar binary availability...")
    unrar_paths = ["/usr/bin/unrar", "/usr/bin/rar"]
    unrar_found = False
    
    for path in unrar_paths:
        if os.path.exists(path):
            print(f"✅ Found unrar at: {path}")
            unrar_found = True
            break
    
    if not unrar_found:
        print("❌ No unrar binary found!")
        return False
    
    # Test 2: Check if rarfile package can import
    print("\n2. Testing rarfile package import...")
    try:
        import rarfile
        print("✅ rarfile package imported successfully")
        
        # Configure rarfile
        rarfile.UNRAR_TOOL = "/usr/bin/unrar"
        print(f"✅ Set rarfile.UNRAR_TOOL to: {rarfile.UNRAR_TOOL}")
        
    except ImportError as e:
        print(f"❌ Failed to import rarfile: {e}")
        return False
    
    # Test 3: Check if patoolib can import
    print("\n3. Testing patoolib package import...")
    try:
        import patoolib
        print("✅ patoolib package imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import patoolib: {e}")
        return False
    
    # Test 4: Test archive creation (if we have files to test with)
    print("\n4. Testing archive creation...")
    try:
        # Create a test file
        test_content = "This is a test file for RAR functionality"
        test_file = "test_file.txt"
        
        with open(test_file, 'w') as f:
            f.write(test_content)
        
        print(f"✅ Created test file: {test_file}")
        
        # Try to create a RAR archive
        test_rar = "test_archive.cbr"
        patoolib.create_archive(test_rar, [test_file])
        
        if os.path.exists(test_rar):
            print(f"✅ Successfully created RAR archive: {test_rar}")
            
            # Clean up test files
            os.remove(test_file)
            os.remove(test_rar)
            print("✅ Cleaned up test files")
        else:
            print(f"❌ Failed to create RAR archive")
            return False
            
    except Exception as e:
        print(f"❌ Error during archive creation test: {e}")
        # Clean up any test files that might have been created
        for file in ["test_file.txt", "test_archive.cbr"]:
            if os.path.exists(file):
                os.remove(file)
        return False
    
    print("\n🎉 All RAR functionality tests passed!")
    return True

if __name__ == "__main__":
    success = test_rar_functionality()
    sys.exit(0 if success else 1)
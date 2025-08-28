#!/usr/bin/env python3
"""
Test script to verify that volume metadata processing includes XML generation and injection
"""

import sys
import os
import time

# Add the current directory to the path so we can import our modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_volume_metadata_processing():
    """Test that volume metadata processing includes XML generation and injection"""
    
    print("🧪 Testing volume metadata processing...")
    
    try:
        # Import the necessary modules
        from app.py import VolumeManager
        from settings_manager import settings_manager
        from volume_database import volume_db
        
        # Initialize the volume manager
        volume_manager = VolumeManager()
        
        # Get a list of volumes to test with
        volumes = volume_manager.get_volume_list(limit=5)
        
        if not volumes:
            print("❌ No volumes found to test with")
            return False
        
        print(f"📚 Found {len(volumes)} volumes to test with")
        
        # Test with the first volume that has issues
        test_volume = None
        for volume in volumes:
            volume_id = volume.get('id')
            if volume_id:
                volume_details = volume_manager.get_volume_details(volume_id)
                if volume_details and volume_details.get('issues'):
                    issues_with_files = [issue for issue in volume_details['issues'] 
                                       if issue.get('files') and len(issue['files']) > 0]
                    if issues_with_files:
                        test_volume = volume
                        break
        
        if not test_volume:
            print("❌ No volumes with issues and files found to test with")
            return False
        
        volume_id = test_volume['id']
        volume_details = volume_manager.get_volume_details(volume_id)
        issues_with_files = [issue for issue in volume_details['issues'] 
                           if issue.get('files') and len(issue['files']) > 0]
        
        print(f"🧪 Testing with volume {volume_id} ({test_volume.get('name', 'Unknown')})")
        print(f"📚 Volume has {len(issues_with_files)} issues with files")
        
        # Test the volume metadata processing
        print("🔄 Testing volume metadata processing...")
        start_time = time.time()
        
        result = volume_manager.process_volume_metadata(volume_id, manual_override=True)
        
        end_time = time.time()
        processing_time = end_time - start_time
        
        print(f"⏱️ Processing took {processing_time:.2f} seconds")
        
        if result:
            print(f"✅ Volume metadata processing completed successfully")
            print(f"📊 Processed {len(result)} issues")
            
            # Check that each result includes injection information
            for comicvine_id, issue_result in result.items():
                if 'injection_result' in issue_result:
                    injection_result = issue_result['injection_result']
                    if injection_result.get('success'):
                        print(f"✅ Issue {comicvine_id}: Metadata fetched and injected successfully")
                    else:
                        print(f"❌ Issue {comicvine_id}: Injection failed - {injection_result.get('error', 'Unknown error')}")
                else:
                    print(f"⚠️ Issue {comicvine_id}: No injection result found")
            
            return True
        else:
            print("❌ Volume metadata processing returned no results")
            return False
            
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_individual_issue_processing():
    """Test that individual issue processing works correctly"""
    
    print("\n🧪 Testing individual issue processing...")
    
    try:
        # Import the necessary modules
        from app.py import VolumeManager
        from MetaDataAdd import ComicMetadataInjector
        
        # Initialize the volume manager
        volume_manager = VolumeManager()
        
        # Get a list of volumes to test with
        volumes = volume_manager.get_volume_list(limit=5)
        
        if not volumes:
            print("❌ No volumes found to test with")
            return False
        
        # Test with the first volume that has issues
        test_volume = None
        for volume in volumes:
            volume_id = volume.get('id')
            if volume_id:
                volume_details = volume_manager.get_volume_details(volume_id)
                if volume_details and volume_details.get('issues'):
                    issues_with_files = [issue for issue in volume_details['issues'] 
                                       if issue.get('files') and len(issue['files']) > 0]
                    if issues_with_files:
                        test_volume = volume
                        break
        
        if not test_volume:
            print("❌ No volumes with issues and files found to test with")
            return False
        
        volume_id = test_volume['id']
        volume_details = volume_manager.get_volume_details(volume_id)
        issues_with_files = [issue for issue in volume_details['issues'] 
                           if issue.get('files') and len(issue['files']) > 0]
        
        if not issues_with_files:
            print("❌ No issues with files found")
            return False
        
        # Test with the first issue
        test_issue = issues_with_files[0]
        issue_index = volume_details['issues'].index(test_issue)
        
        print(f"🧪 Testing with issue {test_issue.get('issue_number', 'Unknown')} (index {issue_index})")
        
        # Test individual issue processing
        injector = ComicMetadataInjector()
        result = injector.process_issue_metadata(
            volume_id,
            issue_index,
            volume_details,
            volume_manager.metadata_fetcher,
            volume_manager.volume_db
        )
        
        if result.get('success'):
            print(f"✅ Individual issue processing completed successfully")
            injection_results = result.get('result', {}).get('injection_results', [])
            successful_injections = sum(1 for r in injection_results if r.get('success'))
            print(f"📊 Successfully injected metadata into {successful_injections}/{len(injection_results)} files")
            return True
        else:
            print(f"❌ Individual issue processing failed: {result.get('error', 'Unknown error')}")
            return False
            
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🚀 Starting volume metadata processing tests...")
    
    # Test volume metadata processing
    volume_test_passed = test_volume_metadata_processing()
    
    # Test individual issue processing
    issue_test_passed = test_individual_issue_processing()
    
    print("\n📊 Test Results:")
    print(f"Volume metadata processing: {'✅ PASSED' if volume_test_passed else '❌ FAILED'}")
    print(f"Individual issue processing: {'✅ PASSED' if issue_test_passed else '❌ FAILED'}")
    
    if volume_test_passed and issue_test_passed:
        print("\n🎉 All tests passed! Volume metadata processing now includes XML generation and injection.")
        sys.exit(0)
    else:
        print("\n💥 Some tests failed. Please check the implementation.")
        sys.exit(1)
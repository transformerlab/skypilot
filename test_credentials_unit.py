#!/usr/bin/env python3
"""
Simple test to verify the custom credentials feature works.
This tests just the credential handling without actually launching anything.
"""

import os
import sys
import tempfile

# Add the current directory to Python path
sys.path.insert(0, '/Users/deep.gandhi/transformerlab-repos/skypilot-new/skypilot')

def test_credential_handling():
    """Test that the credential handling works correctly."""
    
    print("Testing custom credential handling...")
    
    # Import the function we added
    from sky.backends import backend_utils
    
    # Test the credential handling function
    test_credentials = {
        'runpod': {
            'api_key': 'test_api_key_12345'
        }
    }
    
    print(f"Input credentials: {test_credentials}")
    
    # Call our function
    file_mounts = backend_utils._handle_task_cloud_credentials(test_credentials)
    
    print(f"Generated file mounts: {file_mounts}")
    
    # Verify the file was created
    if '~/.runpod/config.toml' in file_mounts:
        local_path = file_mounts['~/.runpod/config.toml']
        print(f"Temporary config file created at: {local_path}")
        
        # Read and verify content
        with open(local_path, 'r') as f:
            content = f.read()
        print(f"File content:\n{content}")
        
        # Check if it contains our API key
        if 'test_api_key_12345' in content:
            print("✅ SUCCESS: API key found in generated config file!")
            return True
        else:
            print("❌ FAILED: API key not found in config file")
            return False
    else:
        print("❌ FAILED: No RunPod config file mount generated")
        return False


def test_task_creation():
    """Test creating a task with cloud credentials."""
    
    print("\nTesting Task creation with cloud_credentials...")
    
    import sky
    
    # Create a task with credentials
    task = sky.Task(
        name='test-task',
        run='echo "test"',
        cloud_credentials={
            'runpod': {
                'api_key': 'test_api_key_67890'
            }
        }
    )
    
    print(f"Task name: {task.name}")
    print(f"Task cloud_credentials: {task.cloud_credentials}")
    
    # Verify the credentials are stored correctly
    if 'runpod' in task.cloud_credentials:
        if task.cloud_credentials['runpod']['api_key'] == 'test_api_key_67890':
            print("✅ SUCCESS: Task credentials stored correctly!")
            return True
        else:
            print("❌ FAILED: Wrong API key in task")
            return False
    else:
        print("❌ FAILED: RunPod credentials not found in task")
        return False


def main():
    """Run all tests."""
    print("SkyPilot Custom Credentials - Unit Tests")
    print("=" * 45)
    
    success = True
    
    # Test 1: Credential handling function
    if not test_credential_handling():
        success = False
    
    # Test 2: Task creation
    if not test_task_creation():
        success = False
    
    print("\n" + "=" * 45)
    if success:
        print("🎉 All tests PASSED! The feature is working correctly.")
        print("\nNow you can run the full demo:")
        print("python demo_custom_credentials.py")
    else:
        print("❌ Some tests FAILED!")
    
    return success


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Demo script to test the new cloud_cre    # Set resources to use RunPod with a small CPU instance for testing
    print("🔧 Setting resources to use RunPod...")
    task.set_resources(Resources(
        cloud=sky.RunPod(),
        instance_type='cpu-1x1',  # Small CPU instance for testing
        disk_size=20
    ))s feature for SkyPilot.

This script demonstrates launching a RunPod instance using credentials passed
directly to the Task object instead of relying on filesystem-stored credentials.

Usage:
1. Make sure you have no ~/.runpod/config.toml file (delete it if it exists)
2. Run: python demo_custom_credentials.py
"""

import os
import sys
import tempfile
import time

# Add the current directory to the Python path so we can import sky
sys.path.insert(0, '/Users/deep.gandhi/transformerlab-repos/skypilot-new/skypilot')

import sky
from sky import Resources


def test_custom_credentials():
    """Test launching with custom RunPod credentials."""
    
    print("🚀 SkyPilot Custom Credentials Demo")
    print("=" * 50)
    
    # Your RunPod API key (you should replace this with your actual key)
    # Get it from environment variable for security
    runpod_api_key = "<ADD YOUR RUNPOD KEY HERE>"
    # Verify that ~/.runpod/config.toml doesn't exist or is empty
    config_path = os.path.expanduser('~/.runpod/config.toml')
    if os.path.exists(config_path):
        print(f"⚠️  WARNING: {config_path} exists!")
        print("   Please delete it to test the custom credentials feature:")
        print(f"   rm {config_path}")
        return False
    else:
        print(f"✅ Confirmed: {config_path} does not exist")
    
    print("\n📝 Creating task with custom credentials...")
    
    # Create a simple task that will test the credentials
    task = sky.Task(
        name='credentials-test',
        setup=['echo "Setting up environment..."'],
        run=[
            'echo "Hello from RunPod instance!"',
            'echo "Testing if credentials work..."',
            'pip install runpod',
            'ls -la ~/.runpod/',
            'cat ~/.runpod/config.toml',
            'python -c "import runpod; print(f\'RunPod client initialized: {runpod.__version__}\')"'
        ],
        cloud_credentials={
            'runpod': {
                'api_key': runpod_api_key
            }
        }
    )
    
    # Set resources to use RunPod with a small CPU instance for testing
    print("🔧 Setting resources to use RunPod...")
    task.set_resources(Resources(
        cloud=sky.RunPod(),
        instance_type='cpu3c-2-4',  # Small CPU instance for testing
        disk_size=10
    ))
    
    print(f"\n📊 Task configuration:")
    print(f"   Name: {task.name}")
    print(f"   Cloud: RunPod")
    print(f"   Instance type: cpu3c-2-4")
    print(f"   Custom credentials: {'runpod' in task.cloud_credentials}")
    
    # Generate a unique cluster name
    cluster_name = f'demo-custom-creds-{int(time.time())}'
    print(f"   Cluster name: {cluster_name}")
    
    try:
        print(f"\n🚀 Launching cluster '{cluster_name}'...")
        print("   This will test the custom credentials feature...")
        
        # Launch with dryrun first to test the config generation
        print("\n🧪 Testing with dryrun=True first...")
        sky.launch(task, cluster_name=cluster_name, dryrun=True)
        print("✅ Dryrun successful! Config generation works.")
        
        # Now try the actual launch
        user_input = input("\n❓ Proceed with actual launch? (y/N): ")
        if user_input.lower() == 'y':
            print("🚀 Launching for real...")
            sky.launch(task, cluster_name=cluster_name, dryrun=False)
            print("✅ Launch completed!")
            
            print(f"\n📝 To check the cluster status: sky status {cluster_name}")
            print(f"📝 To ssh into the cluster: sky ssh {cluster_name}")
            print(f"📝 To delete the cluster: sky down {cluster_name}")
        else:
            print("⏭️  Skipping actual launch.")
            
    except Exception as e:
        print(f"❌ Error during launch: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True


def verify_environment():
    """Verify the environment is set up correctly."""
    print("🔍 Verifying environment...")
    
    try:
        import sky
        print(f"✅ SkyPilot imported successfully (version: {getattr(sky, '__version__', 'unknown')})")
    except ImportError as e:
        print(f"❌ Failed to import SkyPilot: {e}")
        return False
    
    try:
        import runpod
        print(f"✅ RunPod library available (version: {getattr(runpod, '__version__', 'unknown')})")
    except ImportError:
        print("❌ RunPod library not available. Install with: pip install runpod")
        return False
    
    return True


def main():
    """Main demo function."""
    print("SkyPilot Custom Credentials Demo")
    print("=" * 40)
    
    if not verify_environment():
        print("❌ Environment verification failed!")
        return
    
    if test_custom_credentials():
        print("\n🎉 Demo completed successfully!")
    else:
        print("\n❌ Demo failed!")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Example of using sky.launch with custom RunPod credentials passed in-memory
instead of storing them in the filesystem.
"""

import sky

def launch_with_custom_credentials():
    """Example of launching with custom RunPod credentials."""
    
    # Define your RunPod API key (you would get this from environment, config, etc.)
    runpod_api_key = "rpa_YOUR_API_KEY_HERE"
    
    # Create a task with custom cloud credentials
    task = sky.Task(
        name='my-task',
        setup='echo "Setting up..."',
        run='echo "Hello from RunPod with custom credentials!"',
        cloud_credentials={
            'runpod': {
                'api_key': runpod_api_key
            }
        }
    )
    
    # Set resources to use RunPod
    task.set_resources(sky.Resources(
        cloud=sky.RunPod(),
        instance_type='cpu3c-2-4'
    ))
    
    # Launch the task - the credentials will be automatically
    # created as temporary files and mounted to the instance
    sky.launch(task, cluster_name='my-runpod-cluster')

if __name__ == "__main__":
    launch_with_custom_credentials()

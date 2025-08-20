#!/usr/bin/env python3
"""Demo script for Azure service principal credentials."""

import argparse
import sys
import sky

def main():
    parser = argparse.ArgumentParser(description='Demo Azure service principal credentials')
    parser.add_argument('--tenant-id', required=True, help='Azure tenant ID')
    parser.add_argument('--client-id', required=True, help='Azure client ID')
    parser.add_argument('--client-secret', required=True, help='Azure client secret')
    parser.add_argument('--subscription-id', required=True, help='Azure subscription ID')
    parser.add_argument('--cluster-name', default='azure-sp-test', 
                       help='Cluster name to use')
    parser.add_argument('--down', action='store_true',
                       help='Tear down the cluster instead of launching')
    
    args = parser.parse_args()
    
    # Build service principal credentials
    credentials = {
        'azure': {
            'service_principal': {
                'tenant_id': args.tenant_id,
                'client_id': args.client_id,
                'client_secret': args.client_secret,
                'subscription_id': args.subscription_id
            }
        }
    }
    
    print(f"Testing Azure service principal credentials with cluster: {args.cluster_name}")
    
    if args.down:
        try:
            print("Tearing down cluster...")
            request_id = sky.down(cluster_name=args.cluster_name, credentials=credentials)
            sky.stream_and_get(request_id)
            print("SUCCESS: Cluster torn down!")
        except Exception as e:
            print(f"ERROR: Failed to tear down cluster: {e}")
            sys.exit(1)
    else:
        try:
            # Simple task to test Azure service principal credentials
            task = sky.Task(run='echo "Hello from Azure with service principal!" && hostname')
            task.set_resources(sky.Resources(
                cloud=sky.Azure(), 
                instance_type='Standard_E16s_v5',
                region='westus'
            ))
            
            # Launch with service principal credentials
            print("Launching cluster...")
            request_id = sky.launch(
                task=task,
                cluster_name=args.cluster_name,
                credentials=credentials
            )
            sky.stream_and_get(request_id)
            
            print("SUCCESS: Azure service principal credentials worked!")
            
        except Exception as e:
            print(f"ERROR: Azure service principal credentials failed: {e}")
            sys.exit(1)

if __name__ == '__main__':
    main()
